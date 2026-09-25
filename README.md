# Omofilia di genere nelle collaborazioni musicali italiane

Pipeline analitica per uno studio sui pattern di collaborazione fra musicisti
italiani, a partire da un dump Discogs locale in PostgreSQL.

## Domanda di ricerca

> L'omofilia di genere nelle collaborazioni della musica registrata italiana è
> cambiata fra il 1950 e il 2026? E se sì, quando, fra chi e in quali generi
> musicali, tenendo conto della dimensione dei gruppi e dell'attività?

| | ipotesi (dall'articolo, §2.7) | esito |
|---|---|---|
| **H1** | la collaborazione segue il genere musicale più del genere sessuale | confermata |
| **H2** | a parità di attività, genere musicale e coorte, l'omofilia è più alta fra le donne che fra gli uomini (contro **H2′**, chiusura della maggioranza) | confermata; H2′ respinta |
| **H3** | l'omofilia varia fra i decenni di formazione del legame (senza direzione) | confermata: emerge dagli anni Settanta |
| **H4** | l'omofilia è più forte nei ruoli creativi e tecnici che in quelli esecutivi | respinta: il contrario, di un fattore 5 |
| **H5** | a parità di attività le donne occupano posizioni più periferiche | respinta |
| **H6** | su una rete proiettata, la riproiezione casuale senza parametri riproduce i partner condivisi almeno quanto un ERGM | confermata, da 1,4 a 12 volte meglio secondo il decennio |

Esplorative: le differenze fra generi musicali e la sensibilità al nullo che
tiene conto dell'attività. Le domande del mandato iniziale (quota di donne,
omofilia per genere musicale, posizione, ruoli) sono tutte coperte.

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
* **Python 3.9+** con: pandas, numpy, networkx, python-igraph (betweenness
  esatta), scipy, statsmodels, matplotlib, seaborn, pyarrow, psycopg2,
  gender-guesser, pyyaml, tabulate.
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

I prodotti sono l'articolo in `paper/` (Markdown, PDF, DOCX), il pacchetto
dati per i reviewer in `export/` e il report italiano in `report/`.

> **Attenzione:** il report italiano (`report/report.*`, Fase 7) e' fermo al 21
> settembre e racconta la tesi ritirata (ERGM su sottoreti, «omofilia di
> minoranza»). Il riferimento aggiornato e' l'articolo, con `docs/` per il
> percorso.

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
  phase3d_betweenness_campionata.py  la betweenness approssimata, per il confronto
  phase4_ergm.py           driver ERGM su sottoreti campionate (stime ritirate)
  phase4b_ergm_full.py     ERGM sulla rete integrale: quattro tentativi falliti
  phase4c_dyadic.py        logit diadico caso-controllo e QAP (superati dalla 4e)
  phase4d_temporal.py      archi datati alla prima release condivisa
  phase4e_esatto.py        logit esatto su tutte le diadi, permutazione in forma chiusa
  phase4f_ergm_decenni.py  ERGM per decennio: convergono solo 1930 e 1940
  phase4g_proiezione.py    quota dei partner condivisi imposta dalla proiezione
  phase4h_bimodale.py      controllo della bimodalita' (esito negativo, atteso)
  phase4i_proiezione_nulla.py  proiezione bipartita randomizzata contro ERGM
  phase4j_nullo_grado.py   permutazione entro strati di grado: il nullo di riferimento
  phase4k_densita_genere.py  probabilita' di legame FF, MM, MF per decennio e genere
  phase4l_nonpersone.py    sensibilita': senza le voci che non sono persone
  wikidata_enrich.py       genere, cittadinanza e occupazione per lotti di QID
  wikidata_dump.py         alternativa: passata sul dump Wikidata completo
  phase5_robustness.py     Monte Carlo e analisi di sensibilita'
  phase6_figures.py        figure PNG a 300 dpi
  phase7_report.py         report Markdown -> HTML -> PDF (fermo al 21 settembre)
  phase8_export.py         pacchetto dati per i reviewer, con manifesto e dizionario
  score_validation.py      metriche sul campione annotato a mano
tests/                     verifiche delle affermazioni di esattezza (tests/README.md)
docs/                      documentazione di processo
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

1. L'inferenza del genere e' validata su 200 casi codificati a mano: 94,6%
   di concordanza sulle etichette M/F (`docs/06-risultati.md`).
   pubblicazione, quindi confonde "artista italiano" e "artista pubblicato in
   Italia".
3. `release_genre` e' vuota: il genere musicale passa solo dai master, e circa
   un quarto della popolazione resta senza.
4. iTunes e' escluso per scelta del committente: nessuna verifica incrociata fra
   fonti.
5. Nessun ERGM e' stimabile oltre circa 2.000 archi: l'omofilia non e' stimata
   congiuntamente alla chiusura triadica. Le stime su sottoreti a valanga sono
   state ritirate (`docs/05-ergm.md`).
6. Il livello 2 della cascata (Wikidata per nome) non e' stato popolato: WDQS ha
   risposto con 429/502/504 in modo persistente. Vedi
   `data/wikidata_status.json`.

## L'articolo

Il manoscritto per *Poetics* **non è nel repository**, e non lo sono i due
script che lo generano (`src/paper.py`, `src/paper_figures.py`): restano in
locale, esclusi da `.gitignore`, finché l'articolo non è pubblicato. La fase 9
di `run_all.sh` gira solo dove quei file sono presenti.

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
