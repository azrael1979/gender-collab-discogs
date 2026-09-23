# Omofilia di genere nelle collaborazioni musicali italiane

Pipeline analitica per uno studio sui pattern di collaborazione fra musicisti
italiani, a partire da un dump Discogs locale in PostgreSQL.

## Domande di ricerca

| | |
|---|---|
| **RQ1** | Quota di donne per genere musicale e decennio |
| **RQ2** | Omofilia di genere sessuale: varia per genere musicale? |
| **RQ3** | Posizione delle donne nella rete (pattern "Smurfette") |
| **RQ4** | Probabilita' di collaborare a parita' di attivita' e coorte (ERGM) |
| **RQ5** | Differenze fra ruoli creativi e ruoli di esecuzione |

## Documentazione di processo

Il codice e' documentato nei docstring; **come si e' arrivati ai risultati** e'
documentato in [`docs/`](docs/). Quella cartella contiene le decisioni prese e
quelle rovesciate, gli errori trovati e che cosa hanno cambiato, e i test che
non hanno deciso nulla — comprese le strade chiuse, che sono documentate quanto
quelle aperte.

| | |
|---|---|
| [`docs/01-percorso.md`](docs/01-percorso.md) | la narrazione: dal mandato a oggi, con i punti in cui l'impostazione e' cambiata |
| [`docs/02-decisioni.md`](docs/02-decisioni.md) | registro delle decisioni metodologiche, con le alternative scartate |
| [`docs/03-errori.md`](docs/03-errori.md) | errori trovati, come sono emersi, quali numeri hanno cambiato |
| [`docs/04-calcolo-esatto.md`](docs/04-calcolo-esatto.md) | che cosa significa «esatto» qui, la matematica, come e' verificata |
| [`docs/05-ergm.md`](docs/05-ergm.md) | il verbale completo dei tentativi ERGM e del risultato negativo |
| [`docs/06-risultati.md`](docs/06-risultati.md) | stato dei risultati, etichettati per solidita' |

## Prerequisiti

* **PostgreSQL** con il dump Discogs caricato nel database `discogs`. La
  pipeline lo legge in sola lettura e non vi scrive mai nulla.
* **Python 3.9+** con: pandas, numpy, networkx, scipy, statsmodels, matplotlib,
  seaborn, pyarrow, psycopg2, gender-guesser, pyyaml.
* **R con statnet** per gli ERGM, e **pandoc + weasyprint** per il report. Se
  non sono disponibili nel sistema si installano in userspace, senza permessi
  di amministratore, con micromamba:

  ```bash
  mkdir -p opt && cd opt
  curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xj bin/micromamba
  export MAMBA_ROOT_PREFIX=$PWD/mamba
  ./bin/micromamba create -y -p $MAMBA_ROOT_PREFIX/envs/ergm -c conda-forge \
      r-base=4.3 r-ergm r-network r-sna r-statnet.common r-intergraph r-jsonlite r-arrow
  ./bin/micromamba create -y -p $MAMBA_ROOT_PREFIX/envs/doc  -c conda-forge \
      pandoc weasyprint
  ```

## Credenziali

La password del database **non sta nel repository**. Si legge dalla variabile
d'ambiente indicata da `db.password_env` in `config.yaml`:

```bash
cp .env.example .env
# poi modifica .env inserendo la password reale
```

In alternativa basta esportarla nella shell:

```bash
export PGPASSWORD_DISCOGS='...'
```

Il file `.env` e' escluso dal versionamento.

## Avvio rapido

```bash
./run_all.sh                 # pipeline completa
./run_all.sh --from 3        # riparte dalla Fase 3
./run_all.sh --only 6        # solo le figure
./run_all.sh --force         # ignora i checkpoint

python3 src/score_validation.py   # dopo aver compilato data/validation_sample.csv
```

Il risultato e' `report/report.pdf` (e `.html`, `.md`), piu' il pacchetto dati
in `export/`.

## Che cosa NON sta nel repository

Per tenerlo leggero sono esclusi, e si rigenerano tutti con `./run_all.sh`:
i dataset intermedi (`data/*.parquet`, ~383 MB), il pacchetto per i reviewer
(`export/`, ~420 MB), la cache delle risposte Wikidata (`cache/`, ~53 MB) e gli
ambienti R e pandoc installati in userspace (`opt/`, ~2,7 GB). Restano
versionati il codice, la configurazione, il report completo con figure e
tabelle, il campione di validazione e le query SQL.

## Struttura

```
config.yaml                tutti i parametri, in un posto solo
run_all.sh                 orchestratore, idempotente
src/
  common.py                config, connessione read-only, checkpoint, tabelle
  viz.py                   palette validata per daltonismo, stile delle figure
  phase1_extract.py        estrazione da PostgreSQL (SOLA LETTURA)
  phase1b_wikidata.py      P21 di Wikidata agganciato all'id Discogs (P1953)
  phase1b2_names.py        nomi Discogs degli artisti etichettati da Wikidata
  phase1c_population.py    crediti, coorti, genere musicale
  phase1d_gender.py        cascata di inferenza del genere sessuale
  phase2_network.py        rete bipartita e proiezione pesata
  phase3_homophily.py      mixing matrix, assortativita', modello nullo
  phase3b_position.py      centralita', coreness, regressioni
  phase3c_mf_only.py       assortativita' sui soli nodi con genere determinato
  phase4_ergm.py           driver ERGM su sottoreti campionate
  phase4b_ergm_full.py     ERGM sulla rete integrale, per scala crescente
  wikidata_enrich.py       genere, cittadinanza e occupazione per lotti di QID
  wikidata_dump.py         alternativa: passata sul dump Wikidata completo
  phase5_robustness.py     Monte Carlo e analisi di sensibilita'
  phase6_figures.py        figure PNG a 300 dpi
  phase7_report.py         report Markdown -> HTML -> PDF
  score_validation.py      metriche sul campione annotato a mano
R/ergm_models.R            modelli ERGM su sottorete (statnet)
R/ergm_full.R              modelli ERGM sulla rete integrale
data/                      parquet, checkpoint, dati grezzi estratti
report/                    report.md/html/pdf, figures/, tables/ (CSV + LaTeX)
logs/                      un log per fase, piu' i tempi di esecuzione
opt/mamba/envs/ergm        R + statnet installati in userspace
opt/mamba/envs/doc         pandoc + weasyprint
```

## Scelte di metodo che conviene conoscere prima di leggere i risultati

**Il database non viene mai scritto.** Ogni sessione gira con
`default_transaction_read_only = on`, che in PostgreSQL vieta anche le tabelle
temporanee: l'estrazione non crea alcun oggetto sul server e le liste di
identificativi tornano al database come letterali `int[]`.

**Non tutti i crediti valgono uguale.** Un credito risolto sulla singola traccia
pesa piu' di un credito da artista principale, che pesa piu' di un credito "a
ombrello" senza indicazione di tracce. Il campo `tracks` di `release_artist`
(`A1`, `1 to 3`, `4, 6, 12`) viene risolto in tracce reali passando per
`release_track`; le formule libere non interpretabili sono degradate a ombrello
invece che forzate.

**Il genere sessuale e' inferito, non osservato.** La cascata parte dal join
esatto fra id Discogs e Wikidata (`P1953`), prosegue con un dizionario
onomastico costruito dai dati stessi e finisce sulla composizione dei gruppi.
Il livello onomastico consulta il dizionario italiano *prima* di quello globale,
e usa il secondo solo per nomi che il primo non riconosce: senza questo vincolo
Andrea, Simone, Nicola e Michele verrebbero classificati come femminili.

**L'assortativita' di riferimento esclude gli `unknown`.** Trattarli come quarta
categoria gonfia l'indice di circa un terzo, perche' gli artisti poco
documentati collaborano fra loro piu' del caso per ragioni di copertura dei
dati. Entrambe le misure sono riportate.

## Limiti dichiarati

1. La validazione manuale dell'inferenza di genere non e' stata eseguita:
   `data/validation_sample.csv` e' pronto ma la colonna `human_gender` e' vuota.
2. `release_label` e' vuota nel dump: l'italianita' si appoggia al solo paese di
   pubblicazione, quindi confonde "artista italiano" e "artista pubblicato in
   Italia".
3. `release_genre` e' vuota: il genere musicale passa solo dai master, e circa
   un quarto della popolazione resta senza.
4. iTunes e' escluso per scelta del committente: nessuna verifica incrociata fra
   fonti.
5. L'ERGM vale sulle sottoreti stimate, non sull'intera rete.
6. Il livello 2 della cascata (Wikidata per nome) non e' stato popolato: WDQS ha
   risposto con 429/502/504 in modo persistente. Vedi
   `data/wikidata_status.json`.

## L'articolo

`paper/` contiene il manoscritto in inglese destinato alla rivista *Poetics*,
in Markdown, PDF e DOCX, con le figure in PNG a 300 dpi e in PDF vettoriale.
Come il report, non contiene cifre scritte a mano: si rigenera con

```bash
python3 src/paper_figures.py && python3 src/paper.py
```

**Prima di sottomettere leggi `paper/NOTE_PER_AUTORE.md`**: elenca le
citazioni da verificare, gli elementi editoriali mancanti e la validazione
manuale del genere, che resta da fare.

## Licenza

Questo lavoro — codice, report, figure e tabelle — e' distribuito sotto
**Creative Commons Attribuzione 4.0 Internazionale (CC BY 4.0)**.
Testo completo in [`LICENSE`](LICENSE); sintesi leggibile su
<https://creativecommons.org/licenses/by/4.0/deed.it>.

Sei libero di condividere e adattare il materiale, anche a fini commerciali,
a condizione di **attribuirne la paternita'**, indicare se hai apportato
modifiche e fornire un collegamento alla licenza.

Una nota pratica: CC BY nasce per opere dell'ingegno piu' che per il software.
Copre bene report, figure e tabelle; per chi volesse riusare il solo codice
sorgente e' meno idiomatica di una licenza come MIT, ma resta pienamente
valida e permissiva.

### Come citare

```
Pipeline per l'analisi dell'omofilia di genere nelle collaborazioni musicali
italiane (2026). https://github.com/azrael1979/gender-collab-discogs
Distribuito sotto licenza CC BY 4.0.
```

### Una precisazione sui dati

La licenza copre il materiale di questo repository. **Non si estende ai dati
Discogs sottostanti**, che restano soggetti alle condizioni della fonte: i
dump Discogs sono rilasciati in CC0, ma chi li riusa e' tenuto a verificarne
autonomamente i termini correnti. Il repository non contiene dati Discogs
grezzi: contiene il codice che li legge e i risultati aggregati che ne
derivano.
