# Stato dei risultati

Ogni risultato è etichettato per solidità: **misurato** (calcolato sui dati,
cade solo se i dati sono sbagliati), **stimato** (dipende da un modello e dalle
sue assunzioni), **interpretato** (una spiegazione proposta per un fatto, può
essere sbagliata anche se il fatto è giusto).

---

## Il risultato centrale — l'emersione

**Statuto: misurato.** Il test di permutazione non assume indipendenza fra
diadi: permuta le etichette tenendo la rete fissa. Il riferimento è la
permutazione **entro strati di grado** (Fase 4j), che confronta ogni donna con
artisti che hanno lo stesso numero di legami; quella uniforme, cieca
all'attività, è riportata accanto perché era la lettura precedente.

| decennio | quota donne | F–F oss/attesi, per grado | *z* | F–F, uniforme | M–M, per grado | logit `same_F` | logit `same_M` |
|---|---|---|---|---|---|---|---|
| 1950 | 12,9% | 1,125 | 1,3 | 0,479 | 1,003 | +0,054 | −0,013 |
| 1960 | 15,5% | 1,074 | 1,7 | 0,499 | 1,000 | +0,047 | +0,003 |
| 1970 | 13,1% | **1,178** | **3,7** | 0,606 | 1,006 | +0,071 | +0,144 |
| 1980 | 11,0% | **1,289** | **5,9** | 0,901 | 1,007 | +0,209 | +0,155 |
| 1990 | 10,4% | **1,561** | **13,3** | 1,236 | 1,011 | +0,352 | +0,123 |
| 2000 | 9,6% | **1,710** | **19,3** | 1,224 | 1,007 | +0,482 | +0,230 |
| 2010 | 10,0% | **1,669** | **17,9** | 1,168 | 1,009 | +0,519 | +0,215 |
| 2020 | 10,8% | **1,703** | **15,0** | 1,664 | 1,010 | **+0,739** | +0,069 |

Tre fatti distinti, che insieme fanno il risultato:

1. **È un'emersione, non un'inversione.** Fra artisti ugualmente attivi, negli
   anni Cinquanta e Sessanta le donne non si legavano fra loro né più né meno
   del caso. L'eccesso diventa significativo negli anni Settanta, cresce fino
   ai Duemila e da lì resta attorno a 1,7. Il logit, che controlla genere
   musicale, coorte e attività, dice lo stesso: `same_F` non significativo fino
   agli anni Settanta, poi in salita fino a +0,739.
2. **È asimmetrica.** Il rapporto maschile sta fra 1,000 e 1,011 in ogni
   decennio; `same_M` non supera 0,23 e non ha tendenza.
3. **Non è composizione.** La quota femminile **scende** dal 15,5% al 9,6% e
   risale appena. Con *meno* donne in proporzione, quelle che ci sono
   collaborano fra loro sempre di più.

> Le musiciste italiane non hanno guadagnato terreno in numero.
> Si sono trovate fra loro.

**Che cosa è caduto.** La versione precedente, costruita sul nullo uniforme,
parlava di un'inversione di segno: legami fra donne *sotto* il caso fino agli
anni Settanta (0,48-0,61, *z* fino a −3,6) e un balzo negli anni Venti (1,66).
Il deficit era un effetto di attività — le donne di quei decenni avevano
0,65-0,70 volte il grado medio — e il balzo in parte lo stesso effetto al
contrario, perché negli anni Venti il loro grado raggiunge quello degli uomini.
Vedi E13 in [`03-errori.md`](03-errori.md) e la sezione D di
[`04-calcolo-esatto.md`](04-calcolo-esatto.md).

Figura: `paper/figures/fig3_emergence.png` (serie per grado, con quella
uniforme tratteggiata).

---

## Per tipo di coppia, decennio e genere musicale (Fase 4k)

**Statuto: misurato** (le densità); **stimato** l'intervallo di Poisson dei
rapporti, che assume indipendenza fra legami ed è ottimistico. Tabella completa
in `data/densita_genere.parquet` e `report/tables/t6_densita_genere.csv`.

La probabilità che una coppia sia legata, per tipo di coppia, su tutti i
generi:

| decennio | donna–donna / mista | uomo–uomo / mista | donna–donna / uomo–uomo | FF oss/att per grado | MF oss/att per grado |
|---|---|---|---|---|---|
| 1950 | 0,71 | 1,62 | 0,44 | 1,06 | 0,96 |
| 1970 | 0,85 | 1,55 | 0,55 | 1,22 | 0,98 |
| 1990 | 1,50 | 1,24 | 1,22 | 1,60 | 0,93 |
| 2020 | 1,83 | 1,12 | 1,63 | 1,73 | 0,92 |

Le densità grezze non tengono conto dell'attività: negli anni Cinquanta due
uomini hanno 2,3 volte la probabilità di due donne di collaborare, ma a parità
di numero di legami la differenza sparisce.

Le coppie miste scendono sotto il caso (0,92 negli anni Venti, *z* fino a −19
nei Duemiladieci), ma **non è una prova in più**: il nullo tiene fisso il
numero di legami di ogni artista, quindi ogni legame donna–donna oltre l'atteso
è un legame donna–uomo sotto l'atteso. È lo stesso fatto visto dall'altro lato.
Dice però una cosa che le altre colonne non dicono: i legami fra donne hanno
**sostituito** quelli con gli uomini, non si sono aggiunti. Una prima lettura lo
aveva presentato come un secondo risultato; è stata corretta prima di entrare
nell'articolo.

**L'emersione non è uniforme fra i generi.** Pop, rock ed elettronica la
portano: il pop passa da circa 1,0 (non significativo) fino agli anni Settanta
a 1,3-1,8 dagli Ottanta, il rock sta a 2,0-2,7 dagli Ottanta, l'elettronica
sale con regolarità da 1,05 a 2,0. La classica resta a 1,1-1,5 in ogni
decennio, quasi mai significativa: nessuna emersione. Jazz e folk hanno picchi
(2,7 negli anni Novanta per il jazz) senza tendenza netta. Hip hop e teatro
hanno troppe poche donne per dire qualcosa: 23 celle su 59 sono marcate come
poco affidabili (meno di 30 donne o 10 legami donna–donna).

Nell'articolo: sezione 4.4, Tabella 5, Figura 4, più un paragrafo in 5.1.

---

## Il risultato più robusto — il genere musicale domina

**Statuto: misurato.**

| | assortatività |
|---|---|
| genere musicale | **0,5865** |
| genere sessuale | **0,0511** |

Un ordine di grandezza. Chi fa musica in Italia si raggruppa per genere
musicale, non per sesso. È il risultato che sopravvive a ogni variante di
robustezza provata.

---

## L'omofilia condizionale, sulla rete intera

**Statuto: stimato.** Le stime puntuali sono il massimo di verosimiglianza
esatto su tutte e 1.619.630.155 le diadi, senza errore di campionamento. Gli
**errori standard** però vengono da un modello che assume indipendenza fra
diadi, e quell'assunzione è falsa in modo strutturale: sono ottimistici.

| termine | coefficiente | IC 95% | odds ratio |
|---|---|---|---|
| `same_F` | **+0,348** | [0,322 – 0,374] | **1,416** |
| `same_M` | **+0,209** | [0,202 – 0,216] | 1,233 |
| `same_genre` | +1,667 | [1,661 – 1,673] | 5,296 |
| `same_cohort` | +1,192 | [1,186 – 1,198] | 3,294 |

Gli intervalli di `same_F` e `same_M` non si sovrappongono: a parità di genere
musicale, coorte e attività, un legame fra due donne è più probabile di uno fra
due uomini. La permutazione per strati di grado concorda sulla rete intera
(F 1,436, *z* 26,9; M 1,008); quella uniforme dà F 0,819, per la ragione detta
sopra.

---

## Il ruolo nei crediti

**Statuto: misurato.**

| sottorete | assortatività di genere |
|---|---|
| creativo (compositori, arrangiatori, produttori) | **0,0235** |
| esecutivo (voci, strumenti) | **0,1175** |

Un fattore cinque. L'omofilia di genere è concentrata nei ruoli esecutivi e
quasi assente in quelli creativi.

---

## La domanda Smurfette — risposta negativa

**Statuto: stimato**, ma con la betweenness ora **esatta** su tutte le 79.013
sorgenti.

| asse | effetto principale F | p |
|---|---|---|
| eigenvector | +0,223 | 0,19 |
| coreness | +0,039 | 0,60 |
| betweenness | −0,236 | 0,21 |

Nessun effetto significativo su nessun asse. Delle 36 interazioni con il genere
musicale sulle tre misure, una (coreness) è significativa al 5%: meno di quante
ne produrrebbe il caso. Non c'è evidenza che le donne, dove ci sono, occupino
posizioni marginali. La disuguaglianza sta nella coda: fra i 100 artisti con
autovettore più alto le donne sono 2.

---

## Il contributo metodologico

**Statuto: dimostrato.**

**Misurato:** su tutti i 702.613 archi, dove una singola release può spiegare i
partner condivisi di un arco li spiega al **98,8%**; dove non può, al **27,6%**.
Il 33,9% di tutti i partner condivisi è imposto meccanicamente dalla proiezione
bipartita.

**Osservato:** la bontà di adattamento degli ERGM sbaglia con una forma a U —
centro sovrastimato, code sottostimate — identica in due decenni indipendenti.

**Dimostrato:** randomizzando la struttura bipartita a distribuzioni di grado
invariate e riproiettandola, si ottiene la forma osservata **sei volte meglio**
che dall'ERGM stimato, e senza alcuna U:

| | scarto medio \|log₂\| |
|---|---|
| ERGM stimato, sei parametri | **1,799** |
| proiezione randomizzata, **zero parametri** | **0,297** |

Replicato su tre insiemi indipendenti (1940s 0,297; 1950s 0,768; rete intera
0,322). Nessuna stima, nessuna assunzione inferenziale: si è fatto girare un
processo noto e si è guardato che forma produce.

> La U è una proprietà del modello, non dei dati.

**Il tentativo fallito resta documentato.** La prima strada — riestimare con
termini di dipendenza a due componenti — è fallita per intero, controllo
negativo compreso, perché nessuna di quelle specifiche converge. Cercare la
conferma dentro lo strumento che si stava criticando era l'errore di
impostazione.

**Che cosa resta non spiegato:** a esp = 0 la proiezione randomizzata dà 0,49,
cioè sottoproduce della metà gli archi isolati. Molto meglio dell'ERGM (0,13),
ma il meccanismo non esaurisce i dati.

Figura: `report/figures/f_proiezione_bipartita.png`.

---

## Le collaborazioni si ripetono

**Statuto: misurato.** Risultato non previsto, emerso dal test precedente.

La proiezione randomizzata produce **sistematicamente più archi** dell'osservato:

| insieme | archi osservati | randomizzati | rapporto |
|---|---|---|---|
| 1940s | 3.016 | 4.465 | 0,68 |
| 1950s | 21.990 | 43.690 | 0,50 |
| **rete intera** | 898.475 | 2.189.834 | **0,41** |

Sulla rete intera la collaborazione reale è **2,4 volte più concentrata** di
quanto il caso produrrebbe: le stesse coppie ricorrono su release diverse,
quindi generano meno archi *distinti*. La randomizzazione le disperde.

Questo separa due cose che il termine «chiusura triadica» confonde: il
**meccanismo** di proiezione spiega la *forma* della distribuzione dei partner
condivisi, il **processo sociale** ne spiega la *concentrazione*.

---

## Quanto è solida la base di dati

| | |
|---|---|
| artisti italiani | 100.201 |
| genere determinato | 71,2% (60.671 M, 9.703 F, 997 misti) |
| quota femminile fra i determinati | **13,8%** (6,25 : 1) |
| crediti | 4.169.130, di cui **64,0%** risolti a livello di traccia |
| rete | 82.595 nodi con archi, 702.613 archi |
| componente gigante | 95,7% |
| validazione dell'italianità | **94,5%** su 4.663 verificabili con `P27` |

---

## Che cosa resta aperto

* **Validazione manuale** del campione in `data/validation_sample.csv`: richiede
  giudizio umano, non è stata eseguita. È il limite principale del paper.
* **Citazioni**: verificate il 24 settembre contro Crossref e le fonti
  editoriali; esito e correzioni in `paper/NOTE_PER_AUTORE.md`.
* **Elementi editoriali** del paper (autori, dichiarazioni): vedi
  `paper/NOTE_PER_AUTORE.md`.
* **Report italiano** (`report/report.md`, Fase 7): fermo al 21 settembre,
  racconta ancora la tesi ritirata. Va riscritto o dichiarato superato.
* **Deposito Zenodo** del pacchetto dati per i reviewer, opzionale.
