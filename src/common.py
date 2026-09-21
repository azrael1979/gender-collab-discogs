"""Utilita' condivise: config, connessione read-only, logging, checkpoint parquet."""
from __future__ import annotations
import os, sys, time, json, hashlib, logging, subprocess, functools
from pathlib import Path
import yaml
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def load_config(path: str | os.PathLike | None = None) -> dict:
    p = Path(path) if path else ROOT / "config.yaml"
    with open(p) as fh:
        cfg = yaml.safe_load(fh)
    cfg["_root"] = str(ROOT)
    cfg["db"]["password"] = _db_password(cfg)
    return cfg


def _db_password(cfg: dict) -> str:
    """La password del database non sta nel repository.

    Si legge dalla variabile d'ambiente indicata da `db.password_env`, che puo'
    essere esportata nella shell o messa in un file `.env` accanto al config
    (non versionato). Se manca, si fallisce subito con un messaggio esplicito
    invece di tentare una connessione che darebbe un errore oscuro.
    """
    var = cfg["db"].get("password_env", "PGPASSWORD_DISCOGS")
    val = os.environ.get(var)
    if not val:
        env_file = ROOT / ".env"
        if env_file.exists():
            for riga in env_file.read_text().splitlines():
                riga = riga.strip()
                if riga and not riga.startswith("#") and "=" in riga:
                    k, _, v = riga.partition("=")
                    if k.strip() == var:
                        val = v.strip().strip("'\"")
                        break
    if not val:
        raise SystemExit(
            f"Password del database non trovata.\n"
            f"Imposta la variabile d'ambiente {var}, per esempio:\n"
            f"    export {var}='...'\n"
            f"oppure scrivila in {ROOT / '.env'} nella forma {var}=...\n"
            f"(il file .env non viene versionato).")
    return val


# --------------------------------------------------------------------- logging
def setup_logging(phase: str, cfg: dict) -> logging.Logger:
    logdir = ROOT / "logs"
    logdir.mkdir(parents=True, exist_ok=True)
    lg = logging.getLogger(phase)
    if lg.handlers:
        return lg
    lg.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
                            "%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(logdir / f"{phase}.log")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    lg.addHandler(fh)
    lg.addHandler(sh)
    return lg


class Timer:
    """Cronometra un blocco e registra il timing per l'appendice tecnica."""
    _records: list[dict] = []

    def __init__(self, label: str, logger: logging.Logger | None = None):
        self.label, self.logger = label, logger

    def __enter__(self):
        self.t0 = time.time()
        if self.logger:
            self.logger.info(f"[start] {self.label}")
        return self

    def __exit__(self, *exc):
        dt = time.time() - self.t0
        Timer._records.append({"step": self.label, "seconds": round(dt, 2)})
        if self.logger:
            self.logger.info(f"[done ] {self.label} ({dt:.1f}s)")
        return False

    @classmethod
    def dump(cls, path: Path):
        if cls._records:
            df = pd.DataFrame(cls._records)
            if path.exists():
                df = pd.concat([pd.read_csv(path), df], ignore_index=True)
            df.to_csv(path, index=False)


# ------------------------------------------------------------------ database
def pg_env(cfg: dict) -> dict:
    env = os.environ.copy()
    env["PGPASSWORD"] = cfg["db"]["password"]
    return env


def psql_args(cfg: dict) -> list[str]:
    d = cfg["db"]
    return ["psql", "-U", d["user"], "-h", d["host"], "-p", str(d["port"]), "-d", d["dbname"],
            "-v", "ON_ERROR_STOP=1"]


READ_ONLY_PREAMBLE = """
SET default_transaction_read_only = on;
SET work_mem = '1GB';
SET max_parallel_workers_per_gather = 8;
SET jit = off;
"""


# Il cluster gira su disco ROTAZIONALE (/dev/sdc, rotational=1) ma e' configurato
# con random_page_cost=1.1, valore da SSD: il planner sceglie allora scansioni
# indicizzate che sull'HDD degradano a ~5 MB/s. Questi GUC di SESSIONE (che non
# toccano la configurazione del server ne' i dati) riportano il costo del random
# su valori da HDD e riducono il parallelismo, favorendo letture sequenziali.
HDD_TUNING = {
    "random_page_cost": "4.0",
    "seq_page_cost": "1.0",
    "effective_io_concurrency": "2",
    "max_parallel_workers_per_gather": "4",
    "work_mem": "4GB",
    "hash_mem_multiplier": "4.0",
    "jit": "off",
}


def get_conn(cfg: dict, tuning: dict | None = None):
    """Connessione psycopg2 in SOLA LETTURA (transazione read-only forzata)."""
    import psycopg2
    d = cfg["db"]
    conn = psycopg2.connect(host=d["host"], port=d["port"], user=d["user"],
                            password=d["password"], dbname=d["dbname"])
    conn.set_session(readonly=True, autocommit=False)
    gucs = {**HDD_TUNING, **(tuning or {})}
    with conn.cursor() as cur:
        for k, v in gucs.items():
            cur.execute(f"SET {k} = %s", (v,))
    return conn


def read_sql(cfg: dict, sql: str, logger=None) -> pd.DataFrame:
    conn = get_conn(cfg)
    try:
        with Timer(f"SQL {hashlib.md5(sql.encode()).hexdigest()[:8]}", logger):
            return pd.read_sql(sql, conn)
    finally:
        conn.close()


def copy_to_csv(cfg: dict, sql: str, out_csv: Path, logger=None) -> Path:
    """COPY (query) TO STDOUT: estrazione a passata singola, molto piu' veloce
    di un cursore Python per volumi da milioni di righe."""
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    full = READ_ONLY_PREAMBLE + f"\nCOPY ({sql}) TO STDOUT WITH (FORMAT csv, HEADER true);"
    with Timer(f"COPY -> {out_csv.name}", logger):
        with open(out_csv, "wb") as fh:
            p = subprocess.run(psql_args(cfg) + ["-q", "-c", full],
                               stdout=fh, stderr=subprocess.PIPE, env=pg_env(cfg))
        if p.returncode != 0:
            raise RuntimeError(f"psql COPY fallita: {p.stderr.decode()[:2000]}")
    return out_csv


# ---------------------------------------------------------------- checkpoint
def data_path(name: str) -> Path:
    p = ROOT / "data" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def checkpoint(name: str, force: bool = False):
    """Decoratore: salta il calcolo se il parquet esiste (idempotenza)."""
    def deco(fn):
        @functools.wraps(fn)
        def wrap(*a, **kw):
            path = data_path(name)
            if path.exists() and not (force or kw.pop("force", False)):
                return pd.read_parquet(path)
            df = fn(*a, **kw)
            df.to_parquet(path, index=False)
            return df
        return wrap
    return deco


def save(df: pd.DataFrame, name: str) -> Path:
    p = data_path(name)
    df.to_parquet(p, index=False)
    return p


def load(name: str) -> pd.DataFrame:
    return pd.read_parquet(data_path(name))


def exists(name: str) -> bool:
    return data_path(name).exists()


# ------------------------------------------------------------------- output
def save_table(df: pd.DataFrame, stem: str, caption: str = "", float_fmt: str = "%.3f"):
    """Salva una tabella in CSV + LaTeX sotto report/tables/."""
    tdir = ROOT / "report" / "tables"
    tdir.mkdir(parents=True, exist_ok=True)
    caption = italiano(caption)
    df.to_csv(tdir / f"{stem}.csv", index=False)
    import warnings
    with warnings.catch_warnings():
        # pandas 1.5 avvisa che l'implementazione di to_latex cambiera': qui
        # serve solo l'output tabellare, e l'avviso sporca i log di ogni fase
        warnings.simplefilter("ignore", FutureWarning)
        try:
            tex = df.to_latex(index=False, float_format=float_fmt, escape=True,
                              caption=caption or stem, label=f"tab:{stem}",
                              longtable=False)
        except Exception:
            tex = df.to_latex(index=False, escape=True)
    (tdir / f"{stem}.tex").write_text(tex)
    return tdir / f"{stem}.csv"


def fig_path(stem: str) -> Path:
    d = ROOT / "report" / "figures"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{stem}.png"


def savefig(fig, stem: str, cfg: dict):
    p = fig_path(stem)
    fig.savefig(p, dpi=cfg["report"]["dpi"], bbox_inches="tight", facecolor="white")
    import matplotlib.pyplot as plt
    plt.close(fig)
    return p


def set_style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt, seaborn as sns
    sns.set_theme(style="whitegrid", context="paper")
    plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 300, "font.size": 10,
                         "axes.titlesize": 11, "axes.labelsize": 10,
                         "axes.titleweight": "semibold", "figure.autolayout": False})


def write_json(obj, name: str):
    p = ROOT / "data" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str))
    return p


def read_json(name: str):
    return json.loads((ROOT / "data" / name).read_text())


# --------------------------------------------------------------- ortografia
# I sorgenti sono scritti in ASCII puro per evitare problemi di codifica nei
# log e nei CSV; il testo destinato al lettore va pero' reso in italiano
# corretto. Questa tabella converte le forme con apostrofo nelle vocali
# accentate, e viene applicata alle didascalie e al Markdown del report.
_ACCENTI = {
    "e'": "è", "E'": "È", "cioe'": "cioè", "c'e'": "c'è", "dov'e'": "dov'è",
    "piu'": "più", "puo'": "può", "da'": "dà", "sta'": "sta",
    "perche'": "perché", "poiche'": "poiché", "finche'": "finché",
    "anziche'": "anziché", "nonche'": "nonché", "benche'": "benché",
    "affinche'": "affinché", "giacche'": "giacché", "sicche'": "sicché",
    "percio'": "perciò", "pero'": "però", "cio'": "ciò", "giu'": "giù",
    "virtu'": "virtù", "tribu'": "tribù", "dopodiche'": "dopodiché", "cosi'": "così", "gia'": "già",
    "ne'": "né", "se'": "sé", "la'": "là", "li'": "lì", "piu'": "più",
    "sara'": "sarà", "avra'": "avrà", "potra'": "potrà", "uscira'": "uscirà",
    "significativita'": "significatività", "andra'": "andrà", "verra'": "verrà",
    "restera'": "resterà", "dira'": "dirà", "fara'": "farà", "dara'": "darà",
    "attivita'": "attività", "parita'": "parità", "qualita'": "qualità",
    "quantita'": "quantità", "identita'": "identità", "densita'": "densità",
    "specificita'": "specificità", "assortativita'": "assortatività",
    "italianita'": "italianità", "centralita'": "centralità",
    "sensibilita'": "sensibilità", "possibilita'": "possibilità",
    "probabilita'": "probabilità", "difficolta'": "difficoltà",
    "meta'": "metà", "liberta'": "libertà", "verita'": "verità",
    "gravita'": "gravità", "bonta'": "bontà", "novita'": "novità",
    "societa'": "società", "varieta'": "varietà", "unita'": "unità",
    "eta'": "età", "citta'": "città", "proprieta'": "proprietà",
    "necessita'": "necessità", "utilita'": "utilità",
    "disponibilita'": "disponibilità", "ambiguita'": "ambiguità",
    "riproducibilita'": "riproducibilità", "praticabilita'": "praticabilità",
    "eterogeneita'": "eterogeneità",
    "omogeneita'": "omogeneità",
    "capacita'": "capacità", "realta'": "realtà", "meta'": "metà",
    "singolarita'": "singolarità", "modalita'": "modalità",
    "affidabilita'": "affidabilità", "stabilita'": "stabilità",
    "velocita'": "velocità", "rarita'": "rarità",
    "entita'": "entità", "nazionalita'": "nazionalità",
    "validita'": "validità", "casualita'": "casualità",
    "indisponibilita'": "indisponibilità", "si'": "sì",
    "andre'": "andré", "complessita'": "complessità",
    "generalita'": "generalità", "specialita'": "specialità",
    "autorita'": "autorità", "maggioranza'": "maggioranza",
    "numerosita'": "numerosità", "granularita'": "granularità",
    "puo'": "può", "finalita'": "finalità", "attendibilita'": "attendibilità",
    "comparabilita'": "comparabilità", "incertezza'": "incertezza",
    "dignita'": "dignità", "meta'": "metà", "sanita'": "sanità",
}
_ACC_RE = None


def italiano(text: str) -> str:
    """Rende in italiano corretto un testo scritto con apostrofi al posto
    degli accenti. Opera solo su parole intere, quindi non tocca le elisioni
    legittime (l'omofilia, dell'arco, un'altra)."""
    global _ACC_RE
    import re as _re
    if not isinstance(text, str):
        return text
    if _ACC_RE is None:
        keys = sorted(_ACCENTI, key=len, reverse=True)
        _ACC_RE = _re.compile(r"(?<![\w])(" + "|".join(_re.escape(k) for k in keys) +
                              r")(?![\w])", _re.IGNORECASE)

    def _sost(m):
        orig = m.group(1)
        rep = _ACCENTI.get(orig) or _ACCENTI.get(orig.lower())
        if rep is None:
            return orig
        # conserva la maiuscola iniziale del testo di partenza
        return rep[0].upper() + rep[1:] if orig[:1].isupper() else rep

    return _ACC_RE.sub(_sost, text)
