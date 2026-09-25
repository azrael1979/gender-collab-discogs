# Stato dei risultati

Ogni risultato è etichettato per solidità: **misurato** (calcolato sui dati,
cade solo se i dati sono sbagliati), **stimato** (dipende da un modello e dalle
sue assunzioni), **interpretato** (una spiegazione proposta per un fatto, può
essere sbagliata anche se il fatto è giusto).

> **Valori aggiornati al 25 settembre 2026, dopo l'esclusione dei gruppi**
> (D16 in [`02-decisioni.md`](02-decisioni.md)): l'unità d'analisi è la persona.
> I valori precedenti, con i gruppi come nodi, sono conservati in
> `data/con_gruppi_2026-09-24/` e nella storia git di questo file. Le
> conclusioni non cambiano; le grandezze sono più piccole.

---

## Il risultato centrale — l'emersione

**Statuto: misurato.** Il test di permutazione non assume indipendenza fra
diadi: permuta le etichette tenendo la rete fissa. Il riferimento è la
permutazione **entro strati di grado** (Fase 4j), che confronta ogni donna con
artisti che hanno lo stesso numero di legami; quella uniforme, cieca
all'attività, è riportata accanto perché era la lettura precedente.

| decennio | quota donne | F–F oss/attesi, per grado | *z* | F–F, uniforme | M–M, per grado | logit `same_F` | logit `same_M` |
|---|---|---|---|---|---|---|---|
| 1950 | 13,4% | 1,075 | 0,8 | 0,460 | 1,002 | +0,082 | +0,032 |
| 1960 | 16,5% | 1,033 | 0,7 | 0,480 | 1,004 | +0,053 | +0,039 |
| 1970 | 14,1% | **1,201** | **4,3** | 0,574 | 1,003 | +0,086 | +0,174 |
| 1980 | 11,9% | **1,284** | **5,6** | 0,884 | 1,004 | +0,194 | +0,115 |
| 1990 | 11,5% | **1,457** | **9,7** | 1,182 | 1,009 | +0,368 | +0,120 |
| 2000 | 10,7% | **1,583** | **16,8** | 1,212 | 1,005 | +0,413 | +0,141 |
| 2010 | 10,9% | **1,555** | **15,0** | 1,075 | 1,006 | +0,398 | +0,161 |
| 2020 | 11,4% | **1,519** | **10,6** | 1,362 | 1,006 | **+0,508** | −0,006 |

Tre fatti distinti, che insieme fanno il risultato:

1. **È un'emersione, non un'inversione.** Fra artisti ugualmente attivi, negli
   anni Cinquanta e Sessanta le donne non si legavano fra loro né più né meno
   del caso. L'eccesso diventa significativo negli anni Settanta, cresce fino
   ai Duemila e da lì resta attorno a 1,55. Il logit, che controlla genere
   musicale, coorte e attività, dice lo stesso con un decennio di ritardo:
   `same_F` non significativo fino agli anni Settanta, poi da +0,19 a +0,51.
   **Un ERGM sugli anni Cinquanta**, che controlla anche la chiusura
   triadica, conferma l'assenza iniziale: `gender.F` +0,058 (*p* 0,56),
   `gender.M` +0,032 (*p* 0,13).
2. **È asimmetrica.** Il rapporto maschile sta fra 1,002 e 1,009 in ogni
   decennio; `same_M` fra −0,01 e 0,17, senza tendenza.
3. **Non è composizione.** La quota femminile **scende** dal 16,5% al 10,7% e
   risale appena all'11,4%. Con *meno* donne in proporzione, quelle che ci sono
   collaborano fra loro sempre di più.

> Le musiciste italiane non hanno guadagnato terreno in numero.
> Si sono trovate fra loro.

**Che cosa è caduto, in due tempi.** Con il nullo uniforme la serie sembrava
un'inversione di segno (deficit fino agli anni Settanta, 0,46-0,57): era un
effetto dell'attività minore delle donne (E13). Con i gruppi come nodi
l'eccesso recente sembrava attorno a 1,7: i legami gruppo–membro lo gonfiavano
di circa un decimo (D16).

---

## Per tipo di coppia, decennio e genere musicale (Fase 4k)

**Statuto: misurato** (le densità); gli intervalli di Poisson dei rapporti
assumono indipendenza fra legami e sono ottimistici.

| decennio | donna–donna / mista | uomo–uomo / mista | donna–donna / uomo–uomo | FF per grado | MF per grado |
|---|---|---|---|---|---|
| 1950 | 0,68 | 1,64 | 0,41 | 1,08 | 0,98 |
| 1980 | 1,08 | 1,29 | 0,84 | 1,28 | 0,97 |
| 2000 | 1,45 | 1,24 | 1,17 | 1,58 | 0,95 |
| 2020 | 1,51 | 1,13 | 1,34 | 1,52 | 0,94 |

Le coppie miste sotto il caso **non sono una prova in più**: il nullo tiene
fisso il numero di legami di ogni artista, quindi ogni legame donna–donna oltre
l'atteso è un legame donna–uomo sotto l'atteso. Dice però che i legami fra
donne hanno **sostituito** quelli con gli uomini.

**L'emersione non è uniforme fra i generi.** Pop: a caso fino agli anni
Settanta (0,93-1,03), 1,35-1,72 dagli Ottanta. Rock: 1,34-2,08 dagli Ottanta.
Elettronica: da 1,02 negli anni Ottanta a 1,56 nei Duemiladieci. Folk e jazz:
picchi significativi senza tendenza. **Classica: 1,14-1,52, mai
significativa** — nessuna emersione. Molte celle hanno troppe poche donne per
dire qualcosa. Nell'articolo: sezione 4.4, Tabella 5, Figura 4.

---

## Il risultato più robusto — il genere musicale domina

**Statuto: misurato.**

| | assortatività |
|---|---|
| genere musicale | **0,562** |
| genere sessuale | **0,0432** |

Un ordine di grandezza. È il risultato che sopravvive a ogni variante di
robustezza provata, e all'esclusione dei gruppi.

---

## L'omofilia condizionale, sulla rete intera

**Statuto: stimato.** Stime puntuali esatte su tutte le 1.306.346.055 diadi;
errori standard ottimistici perché assumono indipendenza fra diadi.

| termine | coefficiente | IC 95% | odds ratio |
|---|---|---|---|
| `same_F` | **+0,242** | [0,216 – 0,268] | **1,274** |
| `same_M` | **+0,167** | [0,159 – 0,174] | 1,181 |
| `same_genre` | +1,644 | [1,638 – 1,650] | 5,176 |
| `same_cohort` | +1,195 | [1,189 – 1,201] | 3,304 |

Gli intervalli non si sovrappongono: a parità di genere musicale, coorte e
attività, un legame fra due donne è più probabile di uno fra due uomini. La
permutazione per strati di grado concorda sulla rete intera; quella uniforme
dà F 0,735, per la ragione detta sopra.

---

## Il ruolo nei crediti

**Statuto: misurato.**

| sottorete | assortatività di genere |
|---|---|
| creativo (compositori, arrangiatori, produttori) | **0,0224** |
| esecutivo (voci, strumenti) | **0,1054** |

Un fattore 4,7. L'omofilia di genere è concentrata nei ruoli esecutivi e
quasi assente in quelli creativi (H4 respinta).

---

## La domanda Smurfette — risposta negativa, con una cautela

**Statuto: stimato**, con la betweenness **esatta** su tutte le sorgenti.

| asse | effetto principale F | p |
|---|---|---|
| eigenvector | +0,180 | 0,31 |
| coreness | +0,036 | 0,65 |
| betweenness | −0,293 | **0,083** |

Nessun effetto significativo al 5%, nessuna delle 36 interazioni con il genere
musicale. La betweenness è la più vicina alla soglia. **Con la betweenness
campionata su 400 sorgenti (Fase 3d) lo stesso effetto sarebbe −0,323 con
*p* 0,040**: l'approssimazione usuale avrebbe prodotto un effetto Smurfette
significativo che il calcolo esatto non conferma. La disuguaglianza sta nella
coda: fra i 100 artisti con autovettore più alto le donne sono 2.

---

## Che cosa costava approssimare, su questa rete

| | campionato | esatto |
|---|---|---|
| logit caso-controllo, `same_F` / `same_M` | 0,201 / 0,194 | **0,242 / 0,167** |
| betweenness, effetto F | −0,323 (*p* 0,040) | **−0,293 (*p* 0,083)** |
| permutazione, 1.000 repliche | rapporti uguali alla quarta cifra | forma chiusa |

Il caso-controllo comprime il divario donne/uomini del 91%: con il
campionamento H2 non sarebbe risultata confermata.

---

## Il contributo metodologico

**Statuto: dimostrato.**

**Misurato:** su tutti i 586.040 archi, dove una singola release può spiegare i
partner condivisi di un arco li spiega al **98,5%**; dove non può, al **26,5%**.

**Osservato:** la bontà di adattamento degli ERGM sbaglia con una forma a U in
**tre** decenni indipendenti (1930, 1940, 1950).

**Dimostrato:** la proiezione randomizzata, senza parametri, riproduce la forma
della distribuzione dei partner condivisi meglio dell'ERGM stimato in entrambi
i decenni confrontabili — **12 volte** negli anni Quaranta (scarto 0,236 contro
2,779), **1,4 volte** negli anni Cinquanta (0,720 contro 1,015). Il margine è
molto diverso: va riportato l'intervallo, non il caso migliore.

**ERGM:** stimabile fino a 13.919 legami (anni Cinquanta), non oltre 30.629
(anni Venti); gli anni Sessanta falliscono. Con i gruppi la soglia era fra 1.932
e 15.177: le cricche gruppo–membri aggiungevano triangoli meccanici.

---

## Le collaborazioni si ripetono

**Statuto: misurato.** Sulla rete intera la proiezione randomizzata produce
1.875.273 archi contro 765.363 osservati: la collaborazione reale è **2,45 volte
più concentrata** del caso. Il meccanismo di proiezione spiega la *forma* della
distribuzione dei partner condivisi, il processo sociale la sua
*concentrazione*.

---

## Quanto è solida la base di dati

| | |
|---|---|
| voci italiane in Discogs | 100.201, di cui 12.972 gruppi |
| **artisti individuali** | **87.229** |
| genere determinato | 74,6% (55.480 M, 9.613 F) |
| quota femminile fra i determinati | **14,8%** |
| crediti | 3.682.616, di cui 64,1% risolti a livello di traccia |
| rete | 70.712 nodi con archi, 586.040 archi, componente gigante 95,4% |
| validazione dell'italianità | **94,5%** su 4.634 verificabili con `P27` |

---

## Che cosa resta aperto

* **Validazione manuale** del nuovo campione (`data/validation_sample_DA_ANNOTARE.csv`,
  solo individui). È il limite principale del paper.
* **Report italiano** (Fase 7): fermo alla tesi ritirata; va riscritto o
  dichiarato superato.
* **Confronto internazionale** (Spagna, Francia, Germania Ovest ed Est, Svezia):
  proposto il 25 settembre, da pre-registrare prima di toccare i dati.
* **Deposito Zenodo** del pacchetto dati, senza il manoscritto (D15).
