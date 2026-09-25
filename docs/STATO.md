# Stato del progetto — studio italiano (paper per *Poetics*)

**Aggiornato:** 25 settembre 2026, sera. Documento di passaggio di consegne per
chi riprende il lavoro senza memoria della conversazione. Il percorso completo
è in `01-percorso.md`, le decisioni in `02-decisioni.md` (D1–D17), gli errori in
`03-errori.md` (E1–E18), i risultati in `06-risultati.md`.

---

## 1. Il paper

- **Titolo:** *Finding each other: the emergence of gender homophily in Italian
  recorded music, 1950–2026.*
- **Tesi:** un'**emersione**. Fra artisti ugualmente attivi, le donne non si
  legavano fra loro più del caso negli anni Cinquanta e Sessanta; l'eccesso
  compare negli anni Settanta e dal 2000 si stabilizza attorno a 1,55 volte il
  caso. Gli uomini restano al caso, la quota femminile non cresce, e
  l'emersione riguarda pop, rock ed elettronica, non la classica. Ipotesi H1–H6
  in §2.7; le differenze per genere musicale e la scelta del nullo sono
  dichiarate esplorative (D14).
- **Lunghezza: 7.989 parole** di testo principale (limite 8.000, richiesta
  dell'autore). Conteggio in `data/paper_status.json` e nel log di
  `src/paper.py`; ogni aggiunta va compensata.
- **Il manoscritto NON è nel repository** (D15): `paper/`, `src/paper.py`
  (contiene il testo) e `src/paper_figures.py` sono in `.gitignore` e sono
  stati tolti da tutta la storia git. Restano in locale. La versione lunga
  precedente è in `paper/versioni/`.
- **Rigenerare:** `python3 src/paper_figures.py && python3 src/paper.py`. Nessuna
  cifra è scritta a mano: tutto viene letto dai file di risultato (eccezione
  dichiarata: i dati esterni USC/Goodreau).

## 2. Scelte recenti da conoscere

- **I gruppi sono esclusi** (D16): unità d'analisi = persona; 87.229 artisti
  individuali su 100.201 voci. Pipeline rieseguita il 24–25/9.
- **Nullo di riferimento per strati di grado** (D12, Fase 4j): quello
  uniforme produceva una falsa inversione di segno (E13).
- **Validazione del genere fatta** (25/9): 200 casi codificati dall'autore alla
  cieca, **94,6%** di concordanza sulle etichette M/F, 97,5% sui casi
  determinabili, 4 inversioni. È in §3.2 e nei limiti. File annotato unico
  (anche per il confronto): `data/validation_ITALIA_unico_ANNOTATO.csv`.
- **Voci che non sono persone** (D17, Fase 4l): sensibilità, non una nuova
  definizione. Toglierle (3,6% delle voci) non cambia nulla.
- **Livello «Wikidata per nome»** della cascata tornato attivo alla
  riesecuzione (E18): 145 etichette cambiate su 87.229.

## 3. Che cosa resta prima della sottomissione

Da `paper/NOTE_PER_AUTORE.md` (in locale), in ordine:

1. **Data del dump Discogs:** non registrata nel database né nei log; serve
   anche per il modulo OSF del confronto.
2. **Autori, affiliazioni, dichiarazioni** (conflitti, finanziamenti, CRediT,
   **uso dell'IA**, disponibilità dei dati).
3. **Citazioni:** verificate il 24/9 (`paper/VERIFICA_CITAZIONI.md`). Restano
   da controllare a mano la pagina NYT di Pollitt e la formulazione di Blau;
   lo stile bibliografico va confrontato con la Guide for Authors.
4. **Report italiano** (`report/`, Fase 7): fermo alla tesi ritirata. Va
   riscritto o dichiarato superato; oggi il README lo segnala.
5. **Pacchetto per i reviewer** (`export/`, Fase 8): non rigenerato dopo la
   validazione e la Fase 4l. Rilanciare `python3 src/phase8_export.py --force`
   prima di qualunque deposito. Il pacchetto contiene il manoscritto: **non**
   va caricato su Zenodo così com'è finché l'articolo non è pubblicato.
6. **Commit vecchi su GitHub:** la storia è stata ripulita e forzata (D15), ma
   GitHub serve ancora i commit rimossi a chi conosce l'hash. Si risolve con
   una richiesta al supporto GitHub o ricreando il repository. L'autore non ha
   ancora detto quale strada vuole.

## 4. Dove stanno le cose

| | |
|---|---|
| `run_all.sh` | pipeline completa; la fase 9 (paper) gira solo se i file del paper sono presenti |
| `data/con_gruppi_2026-09-24/` | istantanea dei risultati prima di D16, per il confronto |
| `data/validation_sample.csv` | campione di validazione (senza gruppi), con `human_gender` compilata |
| `data/validation_sample_con_gruppi_2026-09-20.csv` | campione precedente, mai annotato |
| `data/validazione_ia/` | annotazione IA alla cieca del campione **precedente** (con gruppi): non usata |
| `docs/07-confronto-internazionale.md` | fattibilità del confronto con altri paesi, da cui è nato il secondo progetto |
| `tests/` | 5 test di verifica, tutti verdi al 25/9 |

## 5. Il progetto collegato

Il confronto internazionale è in `../gender_collab_comparativo/`
(repository privato), pre-registrato su OSF. Il suo stato è in
`../gender_collab_comparativo/docs/STATO.md`. L'Italia vi compare come caso di
riferimento, con lo stesso codice ma senza il livello «Wikidata per nome»: il
collaudo riproduce questo studio alla terza cifra.
