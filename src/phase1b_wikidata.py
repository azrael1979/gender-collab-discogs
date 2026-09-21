"""FASE 1b — genere sessuale da Wikidata (P21), primo livello della cascata.

Due raccolte, entrambe messe in cache su disco (idempotente, riprendibile):

  A) TUTTE le entita' con `P1953` (Discogs artist ID) + `P21`.
     E' un JOIN ESATTO sull'identificativo Discogs: nessun matching per nome,
     nessun rischio di omonimia. E' la fonte di gran lunga piu' affidabile.
     Paginata per prefisso dell'id Discogs (chunk piccoli = niente timeout WDQS).

  B) Italiani (P27=Q38) con occupazione musicale + P21, con etichette e alias.
     Serve da recupero per gli artisti Discogs privi di P1953, via nome
     normalizzato. Copertura minore e rischio di omonimia: marcato di
     conseguenza nel `label_source` e nella `confidence`.

Se WDQS e' irraggiungibile la fase degrada: si prosegue con la sola cache
disponibile e il report lo dichiara.
"""
from __future__ import annotations
import sys, json, time, urllib.request, urllib.parse, urllib.error
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import ROOT, Timer

GENDER_QID = {
    "Q6581097": "M",      # maschio
    "Q6581072": "F",      # femmina
    "Q2449503": "M",      # uomo transgender
    "Q1052281": "F",      # donna transgender
    "Q1097630": "other",  # intersessuale
    "Q48270":   "other",  # non binario
    "Q48279":   "other",  # terzo genere
}


class WDQS:
    def __init__(self, cfg, log):
        w = cfg["gender"]["wikidata"]
        self.endpoint, self.ua = w["endpoint"], w["user_agent"]
        self.timeout, self.retries, self.backoff = w["timeout_s"], w["max_retries"], w["backoff_s"]
        self.cache = ROOT / w["cache_dir"]
        self.cache.mkdir(parents=True, exist_ok=True)
        self.log = log
        self.failures = []
        self.throttled = 0

    def query(self, sparql: str, key: str, retries: int | None = None):
        """Query con cache su disco e backoff esponenziale. Restituisce None se
        il chunk non e' recuperabile: il chiamante lo suddividera'."""
        cf = self.cache / f"{key}.json"
        if cf.exists():
            return json.loads(cf.read_text())
        url = self.endpoint + "?format=json&query=" + urllib.parse.quote(sparql)
        req = urllib.request.Request(url, headers={
            "User-Agent": self.ua, "Accept": "application/sparql-results+json"})
        # `attempts` conta i fallimenti VERI (timeout, 5xx): esauriti,
        # il chiamante suddivide il chunk. I 429 sono throttling, non un
        # problema di dimensione, quindi hanno un contatore separato e non
        # spingono verso la suddivisione.
        attempts = self.retries if retries is None else retries
        i, throttle_waits = 0, 0
        while i < attempts and throttle_waits < 12:
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    rows = json.load(r)["results"]["bindings"]
                cf.write_text(json.dumps(rows))
                return rows
            except json.JSONDecodeError:
                # risposta troncata: il chunk e' troppo grande, si suddivide
                self.log.warning(f"WDQS {key}: risposta troncata, suddivido")
                return None
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    ra = e.headers.get("Retry-After")
                    wait = min(int(ra) if (ra or "").isdigit() else 60, 300)
                    self.throttled += 1
                    throttle_waits += 1
                    self.log.warning(f"WDQS {key}: HTTP 429, attendo {wait}s "
                                     f"(attesa {throttle_waits}/12)")
                    time.sleep(wait)
                    continue
                wait = min(self.backoff * (2 ** i), 120)
                self.log.warning(f"WDQS {key} tentativo {i+1}/{attempts}: "
                                 f"HTTP {e.code}, attendo {wait}s")
                time.sleep(wait)
                i += 1
            except Exception as e:
                wait = min(self.backoff * (2 ** i), 120)
                self.log.warning(f"WDQS {key} tentativo {i+1}/{attempts}: "
                                 f"{repr(e)[:70]}, attendo {wait}s")
                time.sleep(wait)
                i += 1
        return None


def q_discogs_chunk(prefix: str) -> str:
    return f"""
SELECT ?p ?d ?g WHERE {{
  ?p wdt:P1953 ?d ; wdt:P21 ?g .
  FILTER(STRSTARTS(?d, "{prefix}"))
}}"""


def q_italian_musicians(occ_qid: str) -> str:
    """Una query per occupazione: piccola, veloce, niente OFFSET.
    La paginazione con OFFSET su un sotto-SELECT DISTINCT mandava WDQS in
    timeout (504); scomporre per occupazione tiene ogni richiesta leggera."""
    return f"""
SELECT ?p ?g ?label ?alias WHERE {{
  ?p wdt:P27 wd:Q38 ; wdt:P106 wd:{occ_qid} ; wdt:P21 ?g .
  OPTIONAL {{ ?p rdfs:label ?label . FILTER(lang(?label) = "it") }}
  OPTIONAL {{ ?p skos:altLabel ?alias . FILTER(lang(?alias) IN ("it","en")) }}
}}"""


def qid(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def fetch_discogs_ids(wd: WDQS, log) -> pd.DataFrame:
    """Blocco A — chunking RICORSIVO sul prefisso dell'id Discogs.

    Si parte dalle nove cifre iniziali; se un chunk va in timeout o torna
    troncato lo si divide in dieci sottochunk (prefisso + cifra) e si riprova,
    fino a profondita' 5. I prefissi densi si assottigliano da soli, quelli
    radi restano una sola richiesta. Partendo da prefissi di UNA cifra sono
    coperti anche gli id Discogs a cifra singola.
    """
    rows, giveup = [], []

    def walk(prefix: str, depth: int = 1):
        r = wd.query(q_discogs_chunk(prefix), f"discogs_p{prefix}",
                     retries=2 if depth < 5 else wd.retries)
        if r is not None:
            for b in r:
                rows.append({"wd_qid": qid(b["p"]["value"]),
                             "discogs_id": b["d"]["value"],
                             "gender_qid": qid(b["g"]["value"])})
            log.info(f"  prefisso {prefix:<6} {len(r):>6,}  (totale {len(rows):,})")
            time.sleep(1.5)   # cortesia verso WDQS: riduce i 429
            return
        if depth >= 5:
            giveup.append(prefix)
            log.error(f"  prefisso {prefix}: non recuperabile, salto")
            return
        log.info(f"  prefisso {prefix}: suddivido in {prefix}0..{prefix}9")
        for d in range(10):
            walk(prefix + str(d), depth + 1)

    for first in range(1, 10):
        walk(str(first))

    wd.failures.extend(giveup)
    df = pd.DataFrame(rows).drop_duplicates()
    if df.empty:
        return df
    df["gender_wd"] = df.gender_qid.map(GENDER_QID).fillna("other")
    df["discogs_id"] = pd.to_numeric(df.discogs_id, errors="coerce")
    df = df.dropna(subset=["discogs_id"])
    # qualche valore di P1953 su Wikidata e' malformato (id concatenati,
    # overflow): fuori dall'intervallo degli id Discogs va scartato
    n0 = len(df)
    df = df[(df.discogs_id >= 1) & (df.discogs_id <= 2147483647)]
    if len(df) < n0:
        log.warning(f"scartati {n0 - len(df)} valori P1953 malformati")
    df["discogs_id"] = df.discogs_id.astype("int64")
    amb = df.groupby("discogs_id").gender_wd.nunique()
    ambiguous = set(amb[amb > 1].index)
    df["ambiguous"] = df.discogs_id.isin(ambiguous)
    log.info(f"blocco A: {len(df):,} righe, {df.discogs_id.nunique():,} id Discogs distinti, "
             f"{len(ambiguous):,} ambigui, {len(giveup)} chunk persi")
    return df


def fetch_italian_musicians(wd: WDQS, cfg, log) -> pd.DataFrame:
    """Blocco B — italiani con occupazione musicale, una richiesta per
    occupazione. Serve da recupero per gli artisti privi di P1953: il
    collegamento avviene per nome normalizzato, quindi e' piu' fragile del
    blocco A e viene marcato con confidenza minore."""
    occs = cfg["gender"]["wikidata"]["occupation_qids"]
    rows, persi = [], []
    for q in occs:
        r = wd.query(q_italian_musicians(q), f"itmus_{q}")
        if r is None:
            persi.append(q)
            log.error(f"  occupazione {q}: non recuperata")
            continue
        for b in r:
            rows.append({"wd_qid": qid(b["p"]["value"]),
                         "gender_qid": qid(b["g"]["value"]),
                         "label": b.get("label", {}).get("value"),
                         "alias": b.get("alias", {}).get("value")})
        log.info(f"  occupazione {q:<12} {len(r):>6,} righe (totale {len(rows):,})")
        time.sleep(1.5)
    wd.failures.extend(persi)
    if not rows:
        return pd.DataFrame(columns=["wd_qid", "gender_qid", "label", "alias", "gender_wd"])
    df = pd.DataFrame(rows).drop_duplicates()
    df["gender_wd"] = df.gender_qid.map(GENDER_QID).fillna("other")
    log.info(f"blocco B: {df.wd_qid.nunique():,} persone italiane, "
             f"{len(df):,} righe nome, {len(persi)} occupazioni perse")
    return df


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase1b_wikidata", cfg)
    if not cfg["gender"]["wikidata"]["enabled"]:
        log.warning("Wikidata disabilitato da config: la cascata parte dall'onomastica")
        common.save(pd.DataFrame(columns=["discogs_id", "gender_wd"]), "wd_by_discogs.parquet")
        common.save(pd.DataFrame(columns=["wd_qid", "gender_wd"]), "wd_italian.parquet")
        return
    wd = WDQS(cfg, log)
    if not common.exists("wd_by_discogs.parquet") or force:
        with Timer("wikidata_blocco_A_discogs_ids", log):
            common.save(fetch_discogs_ids(wd, log), "wd_by_discogs.parquet")
    if not common.exists("wd_italian.parquet") or force:
        with Timer("wikidata_blocco_B_italiani", log):
            common.save(fetch_italian_musicians(wd, cfg, log), "wd_italian.parquet")
    common.write_json({"wdqs_chunk_falliti": wd.failures,
                       "n_falliti": len(wd.failures),
                       "richieste_throttled": wd.throttled}, "wikidata_status.json")
    if wd.failures:
        log.warning(f"{len(wd.failures)} chunk non recuperati: copertura parziale, "
                    f"da dichiarare nel report")
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
