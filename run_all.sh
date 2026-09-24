#!/usr/bin/env bash
# ==========================================================================
# Pipeline completa — omofilia di genere nelle collaborazioni musicali italiane
#
#   ./run_all.sh                esegue tutte le fasi (salta quelle gia' fatte)
#   ./run_all.sh --from 3       riparte dalla Fase 3
#   ./run_all.sh --force        ignora i checkpoint e ricalcola tutto
#   ./run_all.sh --only 6       esegue solo la fase indicata
#
# Ogni fase e' idempotente: se il suo checkpoint in data/ esiste, viene saltata.
# ==========================================================================
set -uo pipefail
cd "$(dirname "$0")"
ROOT="$PWD"
FROM=0; FORCE=""; ONLY=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --from)  FROM="$2"; shift 2 ;;
    --only)  ONLY="$2"; shift 2 ;;
    --force) FORCE="--force"; shift ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "opzione sconosciuta: $1" >&2; exit 2 ;;
  esac
done

mkdir -p logs data report/figures report/tables
STAMP=$(date +%Y%m%d_%H%M%S)
MAIN="logs/run_${STAMP}.log"
FAILED=()

run () {   # run <numero> <etichetta> <script...>
  local num="$1"; shift
  local label="$1"; shift
  if [[ -n "$ONLY" && "$ONLY" != "$num" ]]; then return 0; fi
  if [[ -z "$ONLY" && "$num" -lt "$FROM" ]]; then
    echo "── fase $num ($label): saltata (--from $FROM)" | tee -a "$MAIN"; return 0
  fi
  echo "" | tee -a "$MAIN"
  echo "══ fase $num — $label ══ $(date '+%H:%M:%S')" | tee -a "$MAIN"
  if python3 "$@" $FORCE 2>&1 | tee -a "$MAIN"; then
    echo "   fase $num completata" | tee -a "$MAIN"
  else
    echo "   !! fase $num FALLITA" | tee -a "$MAIN"; FAILED+=("$num:$label")
  fi
}

echo "pipeline avviata $(date)" | tee "$MAIN"
echo "radice: $ROOT" | tee -a "$MAIN"

run 1 "estrazione da PostgreSQL (sola lettura)"   src/phase1_extract.py
run 1 "Wikidata: P21 via Discogs ID"              src/phase1b_wikidata.py
run 1 "nomi degli artisti etichettati"            src/phase1b2_names.py
run 1 "popolazione, coorti, genere musicale"      src/phase1c_population.py
run 1 "inferenza del genere sessuale"             src/phase1d_gender.py
run 1 "arricchimento Wikidata per lotti"          src/wikidata_enrich.py
run 1 "verifica euristica di italianita"          src/phase1e_validate_italy.py
run 2 "costruzione delle reti"                    src/phase2_network.py
run 3 "omofilia e mixing"                         src/phase3_homophily.py
run 3 "assortativita M/F soltanto"             src/phase3c_mf_only.py
run 3 "centralita, coreness, regressioni"       src/phase3b_position.py
run 4 "ERGM (R + statnet) su sottoreti"           src/phase4_ergm.py
run 4 "omofilia sulla rete integrale (logit, QAP)" src/phase4c_dyadic.py
run 4 "omofilia nel tempo (archi datati)"          src/phase4d_temporal.py
run 4 "calcolo esatto su tutte le 1,62 mld diadi" src/phase4e_esatto.py
run 4 "proiezione: i triangoli sono meccanici?"     src/phase4g_proiezione.py
# La 4h e' un esperimento a esito NEGATIVO, conservato perche' un risultato
# negativo va riprodotto quanto uno positivo: nessuna delle tre specifiche
# converge, controllo negativo compreso, e costa circa due ore e mezza.
run 4 "controllo bimodalita' (fallisce: atteso)"    src/phase4h_bimodale.py
run 4 "proiezione randomizzata: la conferma"        src/phase4i_proiezione_nulla.py
run 4 "nullo per strati di grado (serie temporale)" src/phase4j_nullo_grado.py
run 4 "probabilita' di legame per coppia, decennio, genere" src/phase4k_densita_genere.py
run 5 "robustezza"                                src/phase5_robustness.py
run 6 "figure"                                    src/phase6_figures.py
run 7 "report Markdown, HTML, PDF"                src/phase7_report.py
run 8 "pacchetto dati per i reviewer"             src/phase8_export.py
# Il manoscritto non e' nel repository pubblico: la fase 9 gira solo dove
# src/paper.py e src/paper_figures.py sono presenti in locale.
if [[ -f src/paper.py && -f src/paper_figures.py ]]; then
  run 9 "figure del paper (inglese)"                src/paper_figures.py
  run 9 "paper per Poetics (EN): MD, PDF, DOCX"     src/paper.py
else
  echo "── fase 9 (paper): saltata, manoscritto non presente in locale" | tee -a "$MAIN"
fi

echo "" | tee -a "$MAIN"
if [[ ${#FAILED[@]} -eq 0 ]]; then
  echo "══ pipeline completata senza errori — $(date '+%H:%M:%S')" | tee -a "$MAIN"
else
  echo "══ pipeline completata con ${#FAILED[@]} fase/i fallite:" | tee -a "$MAIN"
  printf '   - %s\n' "${FAILED[@]}" | tee -a "$MAIN"
fi
echo "report:  $ROOT/report/report.pdf" | tee -a "$MAIN"
echo "dati:    $ROOT/export/  (manifesto in export/MANIFEST.md)" | tee -a "$MAIN"
echo "log:     $MAIN" | tee -a "$MAIN"

# La validazione manuale non fa parte della pipeline automatica: richiede
# giudizio umano. Una volta compilata la colonna human_gender in
# data/validation_sample.csv, eseguire:
#     python3 src/score_validation.py
