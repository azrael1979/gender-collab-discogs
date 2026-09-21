"""Estrazione dal dump Wikidata completo (`latest-all.json.bz2`).

NOTA — questa NON e' la strada usata per i risultati pubblicati. Una passata
completa costa quindici ore di sola decompressione, e si e' rivelata inutile:
gli identificativi che servono sono gia' nel database locale dei musicisti, e
chiederne le proprieta' a WDQS per lotti costa due ore e mezza. Si veda
`wikidata_enrich.py`, che e' il percorso effettivamente seguito.

Questo modulo resta per due ragioni: e' l'unica via se WDQS non e' raggiungibile,
ed e' l'unica che recuperi anche le persone PRIVE di identificativo Discogs,
che servirebbero a un recupero onomastico piu' ampio di quello attuale.

Perche' non basta l'endpoint SPARQL
-----------------------------------
WDQS ha servito bene le query strette per prefisso di P1953, ma ha rifiutato
in modo persistente (429/502/504) tutto cio' che fosse piu' ampio: il livello
2 della cascata — il recupero per nome degli italiani — non e' mai stato
popolato. Il dump locale non ha quei limiti, e in piu' consente di estrarre
proprieta' che dall'endpoint non avremmo comunque ottenuto in blocco:
cittadinanza, occupazione, alias.

Che cosa estrae, per ogni entita' che superi il pre-filtro:
    qid, P1953 (id Discogs), P21 (genere), P27 (cittadinanza),
    P106 (occupazione), P569 (anno di nascita), etichette e alias it/en

Pre-filtro
----------
Il dump ha ~121 milioni di entita' e decomprimerlo e' il collo di bottiglia.
Fare `json.loads` su tutte costerebbe ore di CPU inutili, perche' ci interessa
una frazione piccola. Si filtra quindi sulla riga grezza, prima di parsare:

    '"P1953"'    -> entita' con un identificativo Discogs   (~3,8%)
    '"id":"Q38"' -> entita' che citano l'Italia in un claim (~2,4%)

Il secondo e' un confronto esatto: nel dump gli identificativi sono codificati
come `"id":"Q38"`, quindi non cattura Q380 o Q3812 come farebbe una ricerca
del solo `Q38`.

Il lavoro e' ripartibile: i risultati vengono scritti a blocchi e un file di
stato registra l'ultima riga elaborata.
"""
from __future__ import annotations
import sys, json, bz2, time, subprocess, shutil
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import ROOT, Timer

DUMP = Path("/media/disk2/itsright_extract/mudaag/dumps/wiki/latest-all.json.bz2")
OUT = ROOT / "data" / "wikidump"
BLOCCO = 200_000          # entita' estratte per file parquet
LOG_OGNI = 2_000_000      # righe fra due righe di log

GENDER_QID = {
    "Q6581097": "M", "Q6581072": "F", "Q2449503": "M", "Q1052281": "F",
    "Q1097630": "other", "Q48270": "other", "Q48279": "other",
}


def apri(log):
    """Flusso decompresso. `lbzip2` usa tutti i core e va circa tre volte piu'
    veloce del modulo bz2, che e' monothread: su un file da 100 GB la
    differenza sono giorni."""
    lb = ROOT / "opt" / "mamba" / "envs" / "bz" / "bin" / "lbzip2"
    if not lb.exists():
        lb = shutil.which("lbzip2") or shutil.which("pbzip2")
    if lb:
        log.info(f"decompressione con {lb} (parallela)")
        p = subprocess.Popen([str(lb), "-dc", "-n", "14", str(DUMP)],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             bufsize=1024 * 1024)
        return p.stdout, p
    log.warning("lbzip2 assente: si usa bz2 monothread, molto piu' lento")
    return bz2.open(DUMP, "rb"), None


def primo(claims, prop, estrai):
    c = claims.get(prop)
    if not c:
        return None
    try:
        return estrai(c[0]["mainsnak"]["datavalue"]["value"])
    except Exception:
        return None


def tutti(claims, prop, estrai):
    out = []
    for c in claims.get(prop, []):
        try:
            v = estrai(c["mainsnak"]["datavalue"]["value"])
            if v is not None:
                out.append(v)
        except Exception:
            pass
    return out


def estrai_entita(e: dict) -> dict | None:
    claims = e.get("claims", {})
    discogs = tutti(claims, "P1953", lambda v: str(v))
    gender_q = primo(claims, "P21", lambda v: v["id"])
    citt = tutti(claims, "P27", lambda v: v["id"])
    # si tiene solo cio' che serve: o un aggancio Discogs, o una persona con
    # genere legata all'Italia (per il recupero onomastico)
    if not discogs and not (gender_q and "Q38" in citt):
        return None
    lab = e.get("labels", {})
    ali = e.get("aliases", {})
    return {
        "qid": e.get("id"),
        "discogs_id": discogs[0] if discogs else None,
        "discogs_tutti": "|".join(discogs) if len(discogs) > 1 else None,
        "gender_qid": gender_q,
        "gender": GENDER_QID.get(gender_q) if gender_q else None,
        "cittadinanze": "|".join(citt) if citt else None,
        "italiano": "Q38" in citt,
        "occupazioni": "|".join(tutti(claims, "P106", lambda v: v["id"])) or None,
        "anno_nascita": primo(claims, "P569",
                              lambda v: int(str(v["time"])[1:5]) if v.get("time") else None),
        "label_it": lab.get("it", {}).get("value"),
        "label_en": lab.get("en", {}).get("value"),
        "alias_it": "|".join(a["value"] for a in ali.get("it", [])) or None,
        "alias_en": "|".join(a["value"] for a in ali.get("en", [])) or None,
    }


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("wikidata_dump", cfg)
    OUT.mkdir(parents=True, exist_ok=True)
    stato = OUT / "_stato.json"
    if (OUT / "_completo").exists() and not force:
        log.info("estrazione dal dump gia' completata, salto")
        return
    if not DUMP.exists():
        log.error(f"dump non trovato: {DUMP}")
        raise SystemExit(1)

    log.info(f"dump: {DUMP} ({DUMP.stat().st_size / 2**30:.0f} GB compressi)")
    flusso, proc = apri(log)
    t0 = time.time()
    righe = tenute = blocco_n = 0
    buffer: list[dict] = []
    # i due pre-filtri, in byte: il confronto su bytes evita di decodificare
    # in UTF-8 centoventun milioni di righe
    F_DISCOGS, F_ITALIA = b'"P1953"', b'"id":"Q38"'

    try:
        for riga in flusso:
            righe += 1
            if F_DISCOGS not in riga and F_ITALIA not in riga:
                continue
            try:
                e = json.loads(riga.rstrip(b",\n").decode("utf-8"))
            except Exception:
                continue
            rec = estrai_entita(e)
            if rec is None:
                continue
            buffer.append(rec)
            tenute += 1
            if len(buffer) >= BLOCCO:
                pd.DataFrame(buffer).to_parquet(
                    OUT / f"parte_{blocco_n:04d}.parquet", index=False)
                blocco_n += 1
                buffer.clear()
                stato.write_text(json.dumps(
                    {"righe": righe, "tenute": tenute, "blocchi": blocco_n}))
            if righe % LOG_OGNI == 0:
                dt = time.time() - t0
                log.info(f"{righe:,} entita' lette | {tenute:,} tenute | "
                         f"{righe/dt:,.0f}/s | {dt/3600:.1f}h trascorse")
    finally:
        if buffer:
            pd.DataFrame(buffer).to_parquet(
                OUT / f"parte_{blocco_n:04d}.parquet", index=False)
            blocco_n += 1
        if proc:
            proc.terminate()

    dt = time.time() - t0
    log.info(f"lettura conclusa: {righe:,} entita' in {dt/3600:.1f}h, "
             f"{tenute:,} tenute in {blocco_n} blocchi")

    parti = sorted(OUT.glob("parte_*.parquet"))
    df = pd.concat([pd.read_parquet(p) for p in parti], ignore_index=True)
    df["discogs_id"] = pd.to_numeric(df.discogs_id, errors="coerce")
    df = df[df.discogs_id.isna() | df.discogs_id.between(1, 2147483647)]
    common.save(df, "wikidata_full.parquet")
    log.info(f"tabella unificata: {len(df):,} entita'")
    log.info(f"  con id Discogs   : {df.discogs_id.notna().sum():,}")
    log.info(f"  con genere       : {df.gender.notna().sum():,}")
    log.info(f"  cittadini italiani: {df.italiano.sum():,}")
    (OUT / "_completo").write_text("ok")
    common.write_json({"entita_lette": righe, "tenute": tenute,
                       "ore": round(dt / 3600, 2)}, "wikidump_status.json")
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
