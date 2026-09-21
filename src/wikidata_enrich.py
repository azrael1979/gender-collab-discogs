"""Arricchisce il DB locale dei musicisti Wikidata con genere, cittadinanza e
occupazione, interrogando WDQS per lotti di QID gia' noti.

Perche' cosi' e non rianalizzando il dump completo
--------------------------------------------------
Il dump `latest-all.json.bz2` contiene tutto, ma una passata costa quindici ore
di sola decompressione. Il database locale `wikidata_musicians.db` ha gia' i
QID che ci interessano — 261.500 entita' con un identificativo Discogs — e a
quel punto non serve rileggere centoventun milioni di entita' per ricavare tre
proprieta' di duecentomila: basta chiederle.

Le query per lotti di QID sono anche il tipo di interrogazione che WDQS serve
volentieri: sono strette, deterministiche e non richiedono al servizio di
esplorare il grafo. E' l'opposto delle query per occupazione e nazionalita'
che avevano fatto fallire il livello 2 della cascata.

Rispetto allo scarico per prefisso di P1953 questo aggiunge:
  * gli agganci Discogs che quella query non aveva, perche' pretendeva anche
    P21 mentre qui il genere e' facoltativo;
  * la cittadinanza P27, che consente di verificare l'euristica di italianita';
  * l'occupazione P106.
"""
from __future__ import annotations
import sys, json, time, sqlite3, urllib.request, urllib.parse, urllib.error
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import ROOT, Timer

DB_LOCALE = Path("/media/disk2/itsright_extract/mudaag/dumps/wiki/wikidata_musicians.db")
CACHE = ROOT / "cache" / "wikidata_lotti"
LOTTO = 300

GENDER_QID = {
    "Q6581097": "M", "Q6581072": "F", "Q2449503": "M", "Q1052281": "F",
    "Q1097630": "other", "Q48270": "other", "Q48279": "other",
}


def query(sparql: str, chiave: str, cfg, log, tentativi: int = 6):
    """Interroga WDQS con cache su disco. I 429 non consumano tentativi: sono
    throttling, non un problema della query."""
    CACHE.mkdir(parents=True, exist_ok=True)
    cf = CACHE / f"{chiave}.json"
    if cf.exists():
        return json.loads(cf.read_text())
    w = cfg["gender"]["wikidata"]
    url = w["endpoint"] + "?format=json&query=" + urllib.parse.quote(sparql)
    req = urllib.request.Request(url, headers={
        "User-Agent": w["user_agent"],
        "Accept": "application/sparql-results+json"})
    i = attese = 0
    while i < tentativi and attese < 10:
        try:
            with urllib.request.urlopen(req, timeout=w["timeout_s"]) as r:
                righe = json.load(r)["results"]["bindings"]
            cf.write_text(json.dumps(righe))
            return righe
        except urllib.error.HTTPError as e:
            if e.code == 429:
                ra = e.headers.get("Retry-After")
                pausa = min(int(ra) if (ra or "").isdigit() else 45, 180)
                attese += 1
                log.warning(f"{chiave}: 429, attendo {pausa}s")
                time.sleep(pausa)
                continue
            i += 1
            time.sleep(min(8 * 2 ** i, 120))
        except Exception as e:
            i += 1
            log.warning(f"{chiave} tentativo {i}/{tentativi}: {repr(e)[:70]}")
            time.sleep(min(8 * 2 ** i, 120))
    return None


def leggi_qid(log) -> pd.DataFrame:
    if not DB_LOCALE.exists():
        log.error(f"database locale non trovato: {DB_LOCALE}")
        raise SystemExit(1)
    con = sqlite3.connect(DB_LOCALE)
    df = pd.read_sql(
        "SELECT qid, label, discogs_id FROM musicians "
        "WHERE discogs_id IS NOT NULL AND trim(discogs_id) <> ''", con)
    con.close()
    df["discogs_id"] = pd.to_numeric(df.discogs_id, errors="coerce")
    df = df.dropna(subset=["discogs_id"])
    df = df[df.discogs_id.between(1, 2147483647)]
    df["discogs_id"] = df.discogs_id.astype("int64")
    log.info(f"QID con identificativo Discogs nel DB locale: {len(df):,}")
    return df


def sparql_lotto(qids) -> str:
    vals = " ".join("wd:" + q for q in qids)
    return f"""SELECT ?p ?g ?c ?o WHERE {{
  VALUES ?p {{ {vals} }}
  OPTIONAL {{ ?p wdt:P21 ?g }}
  OPTIONAL {{ ?p wdt:P27 ?c }}
  OPTIONAL {{ ?p wdt:P106 ?o }}
}}"""


def qid_da_uri(u: str) -> str:
    return u.rsplit("/", 1)[-1]


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("wikidata_enrich", cfg)
    if common.exists("wikidata_enriched.parquet") and not force:
        log.info("arricchimento gia' presente, salto")
        return

    base = leggi_qid(log)
    qids = base.qid.tolist()
    lotti = [qids[i:i + LOTTO] for i in range(0, len(qids), LOTTO)]
    log.info(f"{len(lotti):,} lotti da {LOTTO} QID")

    gen, citt, occ, persi = {}, {}, {}, []
    t0 = time.time()
    for k, lotto in enumerate(lotti):
        r = query(sparql_lotto(lotto), f"lotto_{k:05d}", cfg, log)
        if r is None:
            persi.extend(lotto)
            log.error(f"lotto {k}: non recuperato")
            continue
        for b in r:
            p = qid_da_uri(b["p"]["value"])
            if "g" in b:
                gen[p] = qid_da_uri(b["g"]["value"])
            if "c" in b:
                citt.setdefault(p, set()).add(qid_da_uri(b["c"]["value"]))
            if "o" in b:
                occ.setdefault(p, set()).add(qid_da_uri(b["o"]["value"]))
        if k % 50 == 0 and k:
            dt = time.time() - t0
            resta = dt / k * (len(lotti) - k)
            log.info(f"lotto {k:,}/{len(lotti):,} | {len(gen):,} con genere | "
                     f"{dt/60:.0f} min trascorsi, ~{resta/60:.0f} min rimanenti")
        time.sleep(0.4)

    df = base.copy()
    df["gender_qid"] = df.qid.map(gen)
    df["gender"] = df.gender_qid.map(GENDER_QID)
    df["cittadinanze"] = df.qid.map(lambda q: "|".join(sorted(citt.get(q, []))) or None)
    df["italiano"] = df.qid.map(lambda q: "Q38" in citt.get(q, set()))
    df["occupazioni"] = df.qid.map(lambda q: "|".join(sorted(occ.get(q, []))) or None)

    # un identificativo Discogs rivendicato da piu' QID con generi discordi
    # non e' utilizzabile
    amb = df[df.gender.isin(["M", "F"])].groupby("discogs_id").gender.nunique()
    ambigui = set(amb[amb > 1].index)
    df["ambiguous"] = df.discogs_id.isin(ambigui)

    common.save(df, "wikidata_enriched.parquet")
    log.info(f"=== arricchimento concluso in {(time.time()-t0)/60:.0f} min ===")
    log.info(f"  entita'              : {len(df):,}")
    log.info(f"  con genere           : {df.gender.notna().sum():,} "
             f"({df.gender.notna().mean():.1%})")
    log.info(f"  con cittadinanza     : {df.cittadinanze.notna().sum():,}")
    log.info(f"  cittadini italiani   : {int(df.italiano.sum()):,}")
    log.info(f"  id Discogs ambigui   : {len(ambigui):,}")
    if persi:
        log.warning(f"  QID non recuperati   : {len(persi):,}")
    common.write_json({"qid": len(df), "con_genere": int(df.gender.notna().sum()),
                       "italiani": int(df.italiano.sum()), "persi": len(persi),
                       "minuti": round((time.time() - t0) / 60, 1)},
                      "wikidata_enrich_status.json")
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
