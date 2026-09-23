# Stato dei risultati

Ogni risultato è etichettato per solidità: **misurato** (calcolato sui dati,
cade solo se i dati sono sbagliati), **stimato** (dipende da un modello e dalle
sue assunzioni), **interpretato** (una spiegazione proposta per un fatto, può
essere sbagliata anche se il fatto è giusto).

---

## Il risultato centrale — l'inversione

**Statuto: misurato.** Il test di permutazione non assume indipendenza fra
diadi: permuta le etichette tenendo la rete fissa, quindi chiusura triadica e
distribuzione dei gradi restano identiche per costruzione. I momenti sono in
forma chiusa.

| decennio | quota donne | legami F–F oss/attesi | *z* esatto | logit `same_F` | logit `same_M` |
|---|---|---|---|---|---|
| 1950 | 12,9% | 0,479 | **−2,2** | +0,054 | −0,013 |
| 1960 | 15,5% | 0,499 | **−3,5** | +0,047 | +0,003 |
| 1970 | 13,1% | 0,606 | **−3,6** | +0,071 | +0,144 |
| 1980 | 11,0% | 0,901 | −0,9 | +0,209 | +0,155 |
| 1990 | 10,4% | 1,236 | **+2,6** | +0,352 | +0,123 |
| 2000 | 9,6% | 1,224 | **+3,0** | +0,482 | +0,230 |
| 2010 | 10,0% | 1,168 | **+2,6** | +0,519 | +0,215 |
| 2020 | 10,8% | **1,664** | **+8,6** | **+0,739** | +0,069 |

Tre fatti distinti, che insieme fanno il risultato:

1. **È un'inversione di segno, non una deriva.** Fino agli anni Settanta le
   musiciste erano collegate fra loro *meno* del caso; dagli anni Novanta *più*.
   Il punto di svolta è negli anni Ottanta.
2. **È asimmetrica.** `same_M` oscilla fra 0,00 e 0,23 senza tendenza, e il
   rapporto maschile resta fra 1,02 e 1,11 in ogni decennio.
3. **Non è composizione.** La quota femminile **scende** dal 15,5% al 9,6% e
   risale appena. Con *meno* donne in proporzione, quelle che ci sono
   collaborano fra loro sempre di più.

> Le musiciste italiane non hanno guadagnato terreno in numero.
> Si sono trovate fra loro.

Figura: `report/figures/f_omofilia_nel_tempo_esatta.png`.

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
due uomini.

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

Nessun effetto significativo su nessun asse, e **zero interazioni significative
su dodici** con il genere musicale. Non c'è evidenza che le donne, dove ci sono,
occupino posizioni marginali.

---

## Il contributo metodologico

**Statuto: misurato** per il dato, **interpretato** per la spiegazione.

**Misurato:** su tutti i 702.613 archi, dove una singola release può spiegare i
partner condivisi di un arco li spiega al **98,8%**; dove non può, al **27,6%**.
Il 33,9% di tutti i partner condivisi è imposto meccanicamente dalla proiezione
bipartita.

**Osservato:** la bontà di adattamento degli ERGM sbaglia con una forma a U —
centro sovrastimato, code sottostimate — identica in due decenni indipendenti.

**Interpretato:** la U deriva dalla bimodalità prodotta dalla proiezione, che un
`gwesp` a un parametro non può riprodurre.

**Non dimostrato:** il tentativo di confermarlo — riestimare con termini a due
componenti — **è fallito**, perché quelle specifiche non convergono affatto.
L'interpretazione resta plausibile e non provata, e va scritto così.

Figura: `report/figures/f_proiezione_bipartita.png`.

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

* **Riscrivere l'articolo.** La tesi non è più «omofilia di minoranza» come
  stato ma un'inversione datata, e la parte metodologica diventa un risultato
  invece di una giustificazione per l'ERGM mancato.
* **Simulare la proiezione** per verificare l'interpretazione della bimodalità
  senza passare dall'ERGM (vedi [`05-ergm.md`](05-ergm.md#il-test-che-resta-da-fare)).
* **Validazione manuale** del campione in `data/validation_sample.csv`: richiede
  giudizio umano, non è stata eseguita.
* **Verifica delle citazioni** elencate in `paper/NOTE_PER_AUTORE.md`.
* **Deposito Zenodo** del pacchetto dati per i reviewer (239 MB), opzionale.
