"""FASE 8 — pacchetto di dati ispezionabile da chi revisiona.

Produce `export/`, che contiene **tutto** il materiale intermedio in formati
aperti, con un manifesto, un dizionario delle colonne e i checksum. L'idea e'
che un revisore debba poter rifare ogni conto senza accesso al database
sorgente e senza eseguire la pipeline.

  export/dati/        ogni dataset in Parquet **e** in CSV (compresso sopra
                      una certa soglia): il Parquet conserva i tipi, il CSV si
                      apre ovunque
  export/tabelle/     le tabelle del report, in CSV e LaTeX
  export/figure/      le figure a 300 dpi
  export/log/         i log di esecuzione e i tempi
  export/MANIFEST.md  che cos'e' ogni file, quante righe, quale fase lo produce
  export/DIZIONARIO.md   significato di ogni colonna dei dataset principali
  export/CHECKSUMS.sha256
  export/README.md    come ispezionare il pacchetto
"""
from __future__ import annotations
import sys, shutil, hashlib, gzip, json
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import ROOT, Timer

EXPORT = ROOT / "export"
CSV_GZIP_SOGLIA_MB = 20          # sopra questa dimensione il CSV esce compresso

# --------------------------------------------------------------------------
# A che cosa serve ciascun file. Chi revisiona non deve dedurlo dal nome.
# --------------------------------------------------------------------------
DESCRIZIONI = {
    # --- Fase 1a: estrazione grezza dal database
    "raw/raw_artist_counts": ("1a", "Per ogni artista con almeno due pubblicazioni "
        "italiane: quante sono (n_it) e quante in totale (n_all). E' la base da cui "
        "si ricava la popolazione, ed e' qui che si possono rifare le soglie."),
    "raw/raw_artistmeta": ("1a", "Anagrafica Discogs dei candidati prima del filtro "
        "sui nomi: nome, vero nome, profilo testuale, qualita' del dato."),
    "raw/raw_artists": ("1a", "Popolazione finale: i 100.201 artisti italiani, con i "
        "conteggi di italianita' e la quota."),
    "raw/raw_ra": ("1a", "Crediti a livello RELEASE (release_artist) dei soli artisti "
        "della popolazione. `extra=0` indica l'artista principale; `tracks` e' il "
        "campo testuale con le posizioni dei brani, quando c'e'."),
    "raw/raw_rta": ("1a", "Crediti a livello TRACCIA (release_track_artist). "
        "`track_id` e' l'identificativo globale della traccia in Discogs."),
    "raw/raw_releases": ("1a", "Anagrafica delle pubblicazioni toccate: anno estratto "
        "dal campo testuale `released`, paese, identificativo del master."),
    "raw/raw_relsize": ("1a", "Numero di artisti accreditati su ciascuna pubblicazione "
        "(tutti, non solo gli italiani). Serve al filtro `max_credits`."),
    "raw/raw_relsize_track": ("1a", "Stesso conteggio per le pubblicazioni che hanno "
        "crediti solo a livello traccia e quindi mancano in raw_relsize."),
    "raw/raw_various": ("1a", "Pubblicazioni attribuite a un artista di nome "
        "'Various'. Sono tre: in questo dump il segnaposto non viene usato."),
    "raw/raw_relgenre": ("1a", "Generi musicali delle pubblicazioni, via master_genre. "
        "E' l'unica fonte disponibile: release_genre e' vuota nel dump."),
    "raw/raw_relstyle": ("1a", "Stili (sottogeneri) via master_style, usati come "
        "ripiego quando manca il genere."),
    "raw/raw_reltracks": ("1a", "Mappa posizione -> traccia per le pubblicazioni che "
        "hanno crediti posizionali da risolvere (es. 'A1' -> track_id)."),
    "raw/raw_groups": ("1a", "Composizione dei gruppi (group_member): serve a "
        "classificare un gruppo come misto od omogeneo."),
    "raw/raw_namevar": ("1a", "Varianti del nome d'arte registrate in Discogs."),
    "raw/raw_wd_names": ("1b", "Nome e vero nome, presi da Discogs, dei 199.812 "
        "artisti che Wikidata etichetta con un genere. E' il corpus da cui nasce "
        "il dizionario onomastico."),

    # --- Fase 1b: Wikidata
    "wd_by_discogs": ("1b", "Tutte le entita' Wikidata con proprieta' P1953 "
        "(identificativo Discogs) e P21 (genere). L'aggancio e' esatto "
        "sull'identificativo, non per nome. `ambiguous` marca gli identificativi "
        "legati a piu' entita' con generi discordi."),
    "onomastic_prior_it": ("1d", "Dizionario nome->genere costruito sui soli artisti "
        "italiani etichettati con certezza da Wikidata. `purity` e' la quota del "
        "genere prevalente, `n` il numero di osservazioni."),
    "onomastic_prior_global": ("1d", "Stesso dizionario costruito sull'intero corpus "
        "mondiale. Usato SOLO per nomi che il lookup italiano non riconosce."),
    "onomastic_prior_disaccordo": ("1d", "Nomi su cui i due dizionari sono in "
        "disaccordo. E' vuoto, ed e' un controllo di coerenza, non un risultato."),

    # --- Fase 1c/1d: popolazione e genere
    "population": ("1c", "Popolazione con gli attributi calcolati: anno di debutto, "
        "decennio di coorte, epoca, numero di pubblicazioni, genere musicale "
        "prevalente e quota del tag principale, se e' un gruppo o un membro."),
    "population_gender": ("1d", "**Tabella centrale dello studio.** La popolazione "
        "piu' il genere sessuale inferito, con `label_source` (quale livello della "
        "cascata ha prodotto l'etichetta) e `confidence`."),
    "credits": ("1c", "**Tavola unificata dei crediti**, una riga per "
        "(artista, contesto). `scope` e' la specificita': `track` credito su una "
        "traccia precisa, `main` artista principale, `umbrella` credito senza "
        "indicazione di tracce. `source` dice da dove viene il credito. "
        "`role_class` e' la classificazione del ruolo."),

    # --- Fase 2: rete
    "edges_all": ("2", "Proiezione pesata artista-artista, rete completa. `w` e' il "
        "peso calcolato come descritto nella sezione 3.1 del report."),
    "edges_creative": ("2", "Stessa proiezione, ristretta ai crediti creativi "
        "(produzione, scrittura, arrangiamento, composizione)."),
    "edges_performance": ("2", "Stessa proiezione, ristretta ai crediti di esecuzione "
        "(voce, strumenti, direzione, featuring)."),
    "network_stats": ("2", "Descrittive delle tre reti: nodi, archi, densita', "
        "gradi, componenti, quota della componente gigante."),

    # --- Fase 3: omofilia e posizione
    "assortativity_overall": ("3", "Assortativita' complessiva per genere sessuale e "
        "per genere musicale, con media e deviazione del modello nullo."),
    "assortativity_strata": ("3", "Assortativita' per sottorete di ruolo ed epoca, "
        "con intervalli bootstrap. Calcolata su tutte e quattro le categorie."),
    "assortativity_mf": ("3", "**Misura di riferimento.** La stessa assortativita' "
        "calcolata sui soli archi fra nodi con genere determinato, affiancata alla "
        "versione a quattro categorie per rendere visibile l'artefatto."),
    "homophily_by_genre": ("3", "Omofilia di genere sessuale dentro ciascun genere "
        "musicale, con i rapporti osservato/atteso separati per uomini e donne."),
    "women_share": ("3", "Quota di donne per genere musicale e decennio di debutto, "
        "con intervalli di Wilson."),
    "position": ("3", "Centralita' di ogni nodo della componente gigante: "
        "eigenvector, betweenness (esatta, su tutte le sorgenti), coreness, grado, forza, "
        "clustering; piu' tutti gli attributi dell'artista."),
    "position_regressions": ("3", "Coefficienti delle regressioni OLS sulla posizione "
        "nella rete, con errori standard robusti HC3."),

    # --- Fase 4: ERGM
    "ergm_coef": ("4", "Coefficienti ERGM per ciascuna sottorete e ciascun modello "
        "della gerarchia (M0 senza gwesp, M1 con gwesp, M2 con nodemix)."),
    "ergm_summary": ("4", "Per ogni sottorete: dimensione, se e' stata campionata, "
        "quali modelli sono arrivati a convergenza, se il termine gwesp ha retto."),

    # --- Fase 5: robustezza
    "mc_gender": ("5", "Esito di ogni replica Monte Carlo sull'imputazione degli "
        "artisti di genere ignoto, piu' i due scenari estremi."),
    "sensitivity": ("5", "Metriche chiave sotto ciascuna variante dei parametri di "
        "costruzione della rete, una variazione per volta."),
    "genre_weak_variants": ("5", "Metriche chiave trattando in tre modi diversi gli "
        "artisti con attribuzione di genere musicale debole."),

    # --- Fase 1e: verifica dell'italianita'
    "italy_validation": ("1", "Artisti della popolazione con cittadinanza (P27) "
        "registrata in Wikidata: la verifica dell'euristica di italianita'. "
        "`italiano` dice se almeno una cittadinanza e' italiana, stati storici compresi."),
    "wikidata_enriched": ("1", "Entita' Wikidata con identificativo Discogs (P1953): "
        "genere (P21), cittadinanze (P27), occupazioni, per lotti di QID."),
    "wd_italian": ("1", "Entita' Wikidata con cittadinanza italiana usate per il "
        "dizionario onomastico italiano."),

    # --- Fase 4c-4j: rete integrale, calcolo esatto, proiezione
    "dyadic_logit": ("4", "Logit diadico caso-controllo (Fase 4c), SUPERATO dal "
        "calcolo esatto: resta come termine di confronto. Intercetta gia' corretta "
        "con il segno giusto (errore E1)."),
    "qap_gender": ("4", "Test QAP a mille permutazioni (Fase 4c), superato dalla "
        "forma chiusa di `permutazione_esatta`."),
    "edges_datati": ("4", "Ogni arco datato con l'anno della prima release condivisa "
        "dai due artisti, e il decennio corrispondente. Base di tutta la serie "
        "temporale."),
    "homophily_temporal": ("4", "Serie temporale campionata (Fase 4d), superata da "
        "`temporale_esatto`."),
    "logit_esatto": ("4", "**Logit diadico esatto** su tutte le 1.619.630.155 diadi "
        "della rete a genere determinato: coefficienti, errori standard "
        "dall'informazione osservata (che assumono indipendenza fra diadi), "
        "log-verosimiglianza."),
    "logit_esatto_parziale": ("4", "Checkpoint per iterazione del Newton esatto; "
        "serve solo a riprendere una stima interrotta."),
    "permutazione_esatta": ("4", "Permutazione UNIFORME delle etichette sulla rete "
        "intera: media e deviazione in forma chiusa. Cieca all'attivita': vedi "
        "`nullo_grado`."),
    "temporale_esatto": ("4", "Serie per decennio di formazione dell'arco: quota di "
        "donne, rapporti sotto permutazione uniforme in forma chiusa, logit esatto "
        "per decennio su tutte le diadi del periodo."),
    "nullo_grado": ("4", "**Nullo di riferimento della serie temporale** (Fase 4j): "
        "legami entro-genere osservati su attesi permutando le etichette fra artisti "
        "con lo stesso numero di legami (2.000 permutazioni per decennio), accanto al "
        "nullo uniforme e al rapporto sul modello di configurazione."),
    "densita_genere": ("4", "Per decennio e genere musicale (legami fra artisti dello "
        "stesso genere): probabilita' che una coppia donna-donna, uomo-uomo o mista "
        "sia legata, rapporti fra queste probabilita' con intervalli di Poisson "
        "(ottimistici), e osservato/atteso per tipo di coppia sotto la permutazione "
        "per strati di grado, con z. `affidabile` = almeno 30 donne e 10 legami FF."),
    "proiezione_esp": ("4", "Per ogni arco: partner condivisi totali, quelli imposti "
        "dalla proiezione bipartita, il cast della release condivisa piu' grande e "
        "se l'arco sta oltre il tetto che una sola release puo' imporre."),
    "proiezione_distribuzione": ("4", "Quota di partner condivisi imposti dalla "
        "proiezione, per numero di partner condivisi."),
    "proiezione_riassunto": ("4", "Riassunto della misura di proiezione su tutti gli "
        "archi."),
    "proiezione_tetto": ("4", "Archi entro e oltre il tetto di proiezione, con la "
        "quota di partner condivisi spiegata in ciascun gruppo (98,8% contro 27,6%)."),
    "proiezione_nulla": ("4", "Distribuzione dei partner condivisi osservata e da "
        "proiezione bipartita randomizzata a gradi invariati (Fase 4i), per tre "
        "insiemi."),
    "ergm_full_coef": ("4", "Coefficienti delle stime ERGM sulla rete integrale "
        "(Fase 4b). Nessuna e' valida: vedi `ergm_full_esiti` e docs/05-ergm.md."),
    "ergm_full_esiti": ("4", "Esito delle stime ERGM sulla rete integrale, con il "
        "motivo dell'abbandono."),
    "ergm_decenni_coef": ("4", "Coefficienti ERGM per decennio (Fase 4f); validi solo "
        "per i decenni convergiti, 1930 e 1940."),
    "ergm_decenni_esiti": ("4", "Esito delle stime ERGM per decennio."),
    "ergm_bimodale": ("4", "Controllo della bimodalita' sul decennio 1940 (Fase 4h): "
        "ampiezza dello scarto a U per il riferimento; le tre varianti non "
        "convergono, controllo negativo compreso."),
}

# --------------------------------------------------------------------------
# Significato delle colonne che ricorrono.
# --------------------------------------------------------------------------
DIZIONARIO = {
    "decennio": "Decennio di formazione dell'arco: anno della prima release condivisa dai due artisti.",
    "rapporto_uniforme": "Archi entro-categoria osservati su attesi permutando le etichette su tutti i nodi, "
                         "senza tener conto del grado. Cieco all'attivita'.",
    "rapporto_grado": "Archi entro-categoria osservati su attesi permutando le etichette solo fra nodi "
                      "con lo stesso grado (strati di almeno 30). Riferimento dell'articolo.",
    "z_grado": "Scarto dell'osservato dalla media della permutazione per strati, in deviazioni standard.",
    "grado_medio_relativo": "Grado medio dei nodi della categoria diviso per il grado medio di tutti i nodi.",
    "esp": "Edgewise shared partners: numero di vicini comuni ai due estremi di un arco.",
    "artist_id": "Identificativo Discogs dell'artista. Chiave di join fra tutte le tavole.",
    "release_id": "Identificativo Discogs della pubblicazione.",
    "track_key": "Identificativo della traccia: `track_id` di Discogs quando c'e', "
                 "altrimenti una chiave sintetica release+sequenza.",
    "name": "Nome d'arte come compare in Discogs, suffisso di disambiguazione incluso.",
    "name_clean": "Nome d'arte senza il suffisso di disambiguazione: 'Mina (3)' -> 'Mina'.",
    "realname": "Nome anagrafico dichiarato in Discogs, quando presente.",
    "realname_clean": "Come sopra, ripulito.",
    "profile": "Testo descrittivo libero della scheda Discogs.",
    "n_it": "Numero di pubblicazioni dell'artista con country = 'Italy'.",
    "n_all": "Numero totale di pubblicazioni accreditate all'artista.",
    "italian_share": "n_it / n_all. La soglia di inclusione e' 0,50.",
    "n_release": "Pubblicazioni distinte su cui l'artista risulta accreditato.",
    "debut_year": "Anno della prima pubblicazione datata accreditata all'artista.",
    "cohort_decade": "Decennio di debutto. Il valore piu' basso e' un contenitore "
                     "'tutto cio' che precede', non un decennio vero.",
    "era": "pre2000 o post2000, secondo l'anno di debutto.",
    "musical_genre": "Genere musicale prevalente: il tag piu' frequente sulle "
                     "pubblicazioni dell'artista. 'Unknown' se nessuna e' taggata.",
    "musical_genre_2": "Secondo tag per frequenza, usato nelle varianti di robustezza.",
    "genre_share": "Quota del tag prevalente sul totale dei tag dell'artista.",
    "genre_weak": "Vero se il tag prevalente copre meno del 40% dei tag.",
    "gender": "Genere sessuale inferito: M, F, mixed (gruppo con membri di entrambi), "
              "unknown. **Non e' un dato osservato: e' inferito.**",
    "label_source": "Quale livello della cascata ha prodotto l'etichetta. "
                    "`wikidata_p1953` e' il piu' affidabile (aggancio esatto).",
    "confidence": "Confidenza dichiarata per quell'etichetta, da 0 a 1. E' un "
                  "parametro di configurazione per livello, non una probabilita' stimata.",
    "is_group": "Vero se l'artista ha membri registrati in Discogs.",
    "is_member": "Vero se l'artista risulta membro di almeno un gruppo.",
    "scope": "Specificita' del credito: track / main / umbrella.",
    "source": "Provenienza del credito: rta, ra_main, ra_umbrella, ra_tracks, "
              "ra_tracks_unresolved.",
    "role": "Ruolo come scritto in Discogs, testo libero.",
    "role_class": "Ruolo normalizzato: creative / performance / technical / other.",
    "extra": "Campo Discogs: 0 = artista principale, 1 = credito secondario.",
    "tracks": "Campo Discogs con le posizioni dei brani, in forma testuale.",
    "u": "Primo estremo dell'arco (artist_id, sempre il minore dei due).",
    "v": "Secondo estremo dell'arco.",
    "w": "Peso dell'arco: tracce condivise piu' co-presenza scalata dalla specificita'.",
    "eigenvector": "Centralita' autovettoriale, pesata.",
    "betweenness": "Centralita' di intermediazione, approssimata su un campione di sorgenti.",
    "coreness": "Numero di k-core: a quale strato del nucleo denso appartiene il nodo.",
    "degree": "Numero di collaboratori distinti.",
    "strength": "Somma dei pesi degli archi incidenti.",
    "r": "Coefficiente di assortativita' di Newman per attributi categoriali.",
    "r_null": "Valore medio dello stesso coefficiente sotto il modello nullo.",
    "ci_lo / ci_hi": "Estremi dell'intervallo di confidenza bootstrap al 95%.",
    "z": "Scostamento dell'osservato dal modello nullo, in deviazioni standard.",
    "estimate": "Coefficiente ERGM, in log-odds.",
    "or": "exp(estimate): il coefficiente come rapporto di probabilita'.",
    "gender_wd": "Genere secondo Wikidata, mappato su M / F / other.",
    "discogs_id": "Valore della proprieta' P1953 di Wikidata, cioe' l'artist_id Discogs.",
    "ambiguous": "Vero se lo stesso identificativo Discogs risulta legato a piu' "
                 "entita' Wikidata con generi discordi: quei casi sono scartati.",
}


def sha256(path: Path, blocco: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(blocco), b""):
            h.update(chunk)
    return h.hexdigest()


def esporta_dataset(log) -> list[dict]:
    dati = EXPORT / "dati"
    dati.mkdir(parents=True, exist_ok=True)
    righe = []
    sorgenti = sorted((ROOT / "data").glob("*.parquet")) + \
               sorted((ROOT / "data" / "raw").glob("*.parquet"))
    for src in sorgenti:
        chiave = ("raw/" if src.parent.name == "raw" else "") + src.stem
        fase, descr = DESCRIZIONI.get(chiave, ("—", "(nessuna descrizione registrata)"))
        dest_dir = dati / ("grezzi" if src.parent.name == "raw" else "elaborati")
        dest_dir.mkdir(parents=True, exist_ok=True)
        pq_dest = dest_dir / src.name
        shutil.copy2(src, pq_dest)

        df = pd.read_parquet(src)
        mb = src.stat().st_size / 1048576
        if mb > CSV_GZIP_SOGLIA_MB or len(df) > 1_000_000:
            csv_dest = dest_dir / f"{src.stem}.csv.gz"
            with gzip.open(csv_dest, "wt", newline="", encoding="utf-8") as fh:
                df.to_csv(fh, index=False)
        else:
            csv_dest = dest_dir / f"{src.stem}.csv"
            df.to_csv(csv_dest, index=False, encoding="utf-8")

        righe.append({
            "file_parquet": str(pq_dest.relative_to(EXPORT)),
            "file_csv": str(csv_dest.relative_to(EXPORT)),
            "fase": fase,
            "righe": len(df),
            "colonne": len(df.columns),
            "elenco_colonne": ", ".join(df.columns),
            "byte_parquet": pq_dest.stat().st_size,
            "byte_csv": csv_dest.stat().st_size,
            "sha256_parquet": sha256(pq_dest),
            "descrizione": common.italiano(descr),
        })
        log.info(f"  {chiave:<38} {len(df):>10,} righe")
    return righe


def copia_contorno(log):
    for sorg, dest in [(ROOT / "report" / "tables", EXPORT / "tabelle"),
                       (ROOT / "report" / "figures", EXPORT / "figure"),
                       (ROOT / "logs", EXPORT / "log")]:
        if not sorg.exists():
            continue
        dest.mkdir(parents=True, exist_ok=True)
        n = 0
        for f in sorg.iterdir():
            if f.is_file():
                shutil.copy2(f, dest / f.name)
                n += 1
        log.info(f"  {sorg.name}: {n} file")
    # i risultati grezzi dell'ERGM, cartella per cartella
    eg = ROOT / "data" / "ergm"
    if eg.exists():
        dest = EXPORT / "ergm"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(eg, dest)
        log.info(f"  ergm: {len(list(dest.iterdir()))} sottoreti")
    # configurazione, campione di validazione, stato delle fonti esterne
    for f in [ROOT / "config.yaml", ROOT / "README.md",
              ROOT / "data" / "validation_sample.csv",
              ROOT / "data" / "wikidata_status.json",
              ROOT / "data" / "report_numbers.json",
              ROOT / "data" / "extract.sql"]:
        if f.exists():
            shutil.copy2(f, EXPORT / f.name)
    for f in [ROOT / "report" / "report.md", ROOT / "report" / "report.html",
              ROOT / "report" / "report.pdf"]:
        if f.exists():
            shutil.copy2(f, EXPORT / f.name)
    # l'articolo, e la documentazione di processo che dice come ci si e' arrivati
    # (il report italiano qui sopra e' fermo al 21 settembre: fa fede l'articolo)
    art = EXPORT / "articolo"
    art.mkdir(parents=True, exist_ok=True)
    for f in (ROOT / "paper").glob("paper_poetics.*"):
        shutil.copy2(f, art / f.name)
    for f in [ROOT / "paper" / "NOTE_PER_AUTORE.md", ROOT / "paper" / "VERIFICA_CITAZIONI.md"]:
        if f.exists():
            shutil.copy2(f, art / f.name)
    for sorg, dest in [(ROOT / "paper" / "figures", art / "figures"),
                       (ROOT / "docs", EXPORT / "docs")]:
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(sorg, dest)
    # il codice, cosi' che ogni numero sia rintracciabile fino alla riga che lo produce
    for sorg, dest in [(ROOT / "src", EXPORT / "codice" / "src"),
                       (ROOT / "R", EXPORT / "codice" / "R"),
                       (ROOT / "tests", EXPORT / "codice" / "tests")]:
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(sorg, dest, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(ROOT / "run_all.sh", EXPORT / "codice" / "run_all.sh")


def scrivi_manifesto(righe: list[dict], cfg, log):
    man = pd.DataFrame(righe)
    man.to_csv(EXPORT / "manifest.csv", index=False)

    def mb(b):
        return f"{b/1048576:.1f} MB" if b >= 1048576 else f"{b/1024:.0f} KB"

    sezioni = {"elaborati": "Dataset elaborati", "grezzi": "Dataset grezzi (estratti dal database)"}
    corpo = []
    for chiave, titolo in sezioni.items():
        sub = man[man.file_parquet.str.contains(f"/{chiave}/")]
        if sub.empty:
            continue
        corpo.append(f"\n## {titolo}\n")
        for _, r in sub.sort_values("fase").iterrows():
            corpo.append(
                f"### `{Path(r.file_parquet).name}`\n\n"
                f"*Fase {r.fase} — {r.righe:,} righe × {r.colonne} colonne — "
                f"{mb(r.byte_parquet)} in Parquet, {mb(r.byte_csv)} in CSV*\n\n"
                f"{r.descrizione}\n\n"
                f"**Colonne:** `{r.elenco_colonne}`\n\n"
                f"**Percorsi:** `{r.file_parquet}` · `{r.file_csv}`\n\n"
                f"**sha256 (Parquet):** `{r.sha256_parquet}`\n")
    testo = ("# Manifesto dei dati\n\n"
             f"Pacchetto generato il {pd.Timestamp.now():%d/%m/%Y %H:%M}. "
             f"Contiene {len(man)} dataset, "
             f"{man.righe.sum():,} righe complessive.\n\n"
             "Ogni dataset e' fornito **due volte**: in Parquet, che conserva i tipi "
             "ed e' leggibile da pandas, R (arrow), DuckDB e Polars; e in CSV, che si "
             "apre ovunque. I CSV piu' grandi sono compressi con gzip.\n"
             + "".join(corpo))
    (EXPORT / "MANIFEST.md").write_text(common.italiano(testo))
    log.info(f"manifesto: {len(man)} dataset, {man.righe.sum():,} righe")
    return man


def scrivi_dizionario(log):
    voci = "\n".join(f"| `{k}` | {common.italiano(v)} |" for k, v in sorted(DIZIONARIO.items()))
    testo = f"""# Dizionario delle colonne

Significato delle colonne che ricorrono nei dataset. Le colonne specifiche di
una singola tabella sono descritte nel manifesto, accanto alla tabella.

| colonna | significato |
|---|---|
{voci}

## Tre avvertenze da leggere prima di usare i dati

**Il genere sessuale e' inferito, non osservato.** La colonna `gender` non viene
da nessuna fonte: e' il risultato della cascata descritta nella sezione 2 del
report. `label_source` dice da quale livello proviene ciascuna etichetta e
`confidence` con quanta fiducia. Le etichette `wikidata_p1953` derivano da un
aggancio esatto sull'identificativo Discogs e sono le piu' solide; quelle
onomastiche sono inferenze sul nome proprio. La validazione manuale che ne
misurerebbe l'errore **non e' stata eseguita**: il campione stratificato e'
in `validation_sample.csv`, con la colonna `human_gender` da compilare.

**L'italianita' e' una quota, non una nazionalita'.** Un artista entra nella
popolazione se almeno meta' delle sue pubblicazioni ha `country = 'Italy'`.
E' un criterio sul luogo di pubblicazione, non sulla biografia, perche' il dump
non contiene ne' nazionalita' ne' legame con le etichette discografiche.

**`unknown` non e' una categoria come le altre.** Gli artisti di genere
indeterminato collaborano fra loro piu' del caso, ma per ragioni di copertura
dei dati, non sociali. Le misure di riferimento del report li escludono; i
dataset li conservano perche' l'esclusione sia una scelta di chi analizza e non
un dato gia' perso.
"""
    (EXPORT / "DIZIONARIO.md").write_text(common.italiano(testo))


def scrivi_readme(man: pd.DataFrame, cfg, log):
    testo = f"""# Pacchetto dati — omofilia di genere nelle collaborazioni musicali italiane

Questo pacchetto contiene tutto il materiale intermedio dello studio, in formati
aperti, perche' chi revisiona possa rifare i conti senza accedere al database
sorgente e senza rieseguire la pipeline.

## Che cosa c'e'

```
MANIFEST.md        che cos'e' ogni file, quante righe, quale fase lo produce
DIZIONARIO.md      significato di ogni colonna
manifest.csv       lo stesso manifesto in forma tabellare
CHECKSUMS.sha256   impronta di ogni file
config.yaml        tutti i parametri usati in questa esecuzione
extract.sql        le query di estrazione dal database
articolo/          l'articolo per Poetics (MD, PDF, DOCX), figure, note per l'autore
docs/              la documentazione di processo: decisioni, errori, verbale ERGM
report.pdf/.html/.md   il report italiano, FERMO AL 21 SETTEMBRE: racconta la
                       tesi ritirata. Fa fede l'articolo
validation_sample.csv  campione per la validazione manuale del genere (da compilare)
wikidata_status.json   esito del recupero da Wikidata, degradazioni incluse
report_numbers.json    ogni cifra citata nel report, in forma leggibile da macchina

dati/elaborati/    i dataset prodotti dall'analisi     (Parquet + CSV)
dati/grezzi/       i dati estratti dal database        (Parquet + CSV)
tabelle/           le tabelle del report               (CSV + LaTeX)
figure/            le figure                           (PNG 300 dpi)
ergm/              input e output grezzi di ogni modello ERGM
log/               log di esecuzione e tempi di ogni fase
codice/            il codice sorgente completo, con i test di verifica
```

## Come aprirli

```python
import pandas as pd
pop = pd.read_parquet("dati/elaborati/population_gender.parquet")
archi = pd.read_parquet("dati/elaborati/edges_all.parquet")
```

```r
library(arrow)
pop <- read_parquet("dati/elaborati/population_gender.parquet")
```

```sql
-- DuckDB, senza importare nulla
SELECT gender, count(*) FROM 'dati/elaborati/population_gender.parquet' GROUP BY 1;
```

I CSV si aprono con qualunque strumento; quelli sopra i {CSV_GZIP_SOGLIA_MB} MB
sono compressi con gzip (`pandas.read_csv` li legge direttamente).

## Da dove ricominciare per verificare un numero

| per verificare | partire da |
|---|---|
| la definizione della popolazione | `dati/grezzi/raw_artist_counts.parquet` — contiene n_it e n_all per tutti i candidati, quindi le soglie si possono rifare |
| l'inferenza del genere | `dati/elaborati/population_gender.parquet` piu' `wd_by_discogs.parquet` e i due `onomastic_prior_*` |
| il peso degli archi | `dati/elaborati/credits.parquet` (colonne `scope` e `source`) e `edges_all.parquet` |
| l'omofilia | `assortativity_mf.parquet` e' la misura di riferimento; `assortativity_strata.parquet` quella a quattro categorie |
| la posizione nella rete | `position.parquet` e `position_regressions.parquet` |
| la serie temporale (risultato centrale) | `edges_datati.parquet`, poi `nullo_grado.parquet` (nullo di riferimento) e `temporale_esatto.parquet` (nullo uniforme e logit per decennio) |
| il logit sulla rete intera | `logit_esatto.parquet`; il confronto caso-controllo in `dyadic_logit.parquet` |
| l'artefatto di proiezione | `proiezione_esp.parquet` (arco per arco), `proiezione_tetto.parquet`, `proiezione_nulla.parquet` |
| gli ERGM | `ergm/<sottorete>/` contiene nodes.csv, edges.csv, control.json e i risultati |

## Riproducibilita'

Seme casuale: **{cfg['project']['seed']}**. Il codice completo e' in `codice/`;
`codice/run_all.sh` riesegue tutta la pipeline. L'unico passo non riproducibile
senza il database sorgente e' la Fase 1a, i cui output sono pero' inclusi qui in
`dati/grezzi/`.

## Avvertenza

Il genere sessuale e' **inferito**, non osservato, e la sua validazione manuale
non e' stata eseguita. L'italianita' e' definita sul paese di pubblicazione, non
sulla biografia. Entrambi i limiti sono discussi nel report, sezioni 1 e 2, e
riassunti in `DIZIONARIO.md`.
"""
    (EXPORT / "README.md").write_text(common.italiano(testo))


def scrivi_checksum(log):
    righe = []
    for f in sorted(EXPORT.rglob("*")):
        if f.is_file() and f.name != "CHECKSUMS.sha256":
            righe.append(f"{sha256(f)}  {f.relative_to(EXPORT)}")
    (EXPORT / "CHECKSUMS.sha256").write_text("\n".join(righe) + "\n")
    log.info(f"checksum: {len(righe)} file")


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase8_export", cfg)
    if EXPORT.exists():
        shutil.rmtree(EXPORT)
    EXPORT.mkdir(parents=True)
    with Timer("esportazione dataset", log):
        righe = esporta_dataset(log)
    with Timer("copia di tabelle, figure, log e codice", log):
        copia_contorno(log)
    man = scrivi_manifesto(righe, cfg, log)
    scrivi_dizionario(log)
    scrivi_readme(man, cfg, log)
    with Timer("checksum", log):
        scrivi_checksum(log)
    tot = sum(f.stat().st_size for f in EXPORT.rglob("*") if f.is_file())
    log.info(f"pacchetto: {EXPORT} ({tot/1048576:.0f} MB)")
    # archivio unico, per chi preferisce scaricare un file solo
    with Timer("archivio tar.gz", log):
        import tarfile
        arch = ROOT / "gender_collab_export.tar.gz"
        if arch.exists():
            arch.unlink()
        with tarfile.open(arch, "w:gz", compresslevel=6) as tf:
            tf.add(EXPORT, arcname="gender_collab_export")
        log.info(f"archivio: {arch} ({arch.stat().st_size/1048576:.0f} MB)")
    log.info("=== esportazione completata ===")
    arch = ROOT / "gender_collab_export.tar.gz"
    common.write_json({"percorso": str(EXPORT), "byte": tot,
                       "archivio": str(arch) if arch.exists() else None,
                       "byte_archivio": arch.stat().st_size if arch.exists() else None,
                       "dataset": len(man), "righe_totali": int(man.righe.sum())},
                      "export_status.json")
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
