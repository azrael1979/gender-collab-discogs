# Il calcolo esatto

> Le cifre di questo documento si riferiscono alla rete con i gruppi come nodi,
> su cui i metodi sono stati sviluppati e verificati. I valori attuali, senza
> gruppi (D16), sono in [`06-risultati.md`](06-risultati.md); i metodi e le
> verifiche non cambiano.

## Che cosa significa «esatto», e che cosa no

La parola qualifica il **calcolo**, non l'inferenza. La distinzione è
importante e va fatta prima dei numeri, non dopo.

**È esatto**, nel senso che non contiene errore di campionamento né di
simulazione:

* il massimo di verosimiglianza del logit diadico, ottenuto percorrendo tutte
  e **1.619.630.155** le diadi invece di un campione;
* media e varianza della distribuzione nulla per permutazione, ottenute in
  forma chiusa invece che da mille repliche Monte Carlo;
* la betweenness, calcolata su tutte e **79.013** le sorgenti.

**Non è esatto**, e nessun calcolo potrebbe renderlo tale:

* gli **errori standard** del logit. Vengono dall'informazione osservata di un
  modello che assume **indipendenza fra diadi**, e quell'assunzione è falsa in
  modo strutturale — la [Fase 4g](05-ergm.md#la-diagnosi) lo misura. Le stime
  puntuali non hanno errore di campionamento; gli errori standard restano
  ottimistici.

È per questo che la tesi dell'articolo poggia sul **test di permutazione**, che
non dipende da alcuna assunzione di indipendenza: le etichette si permutano
tenendo la rete fissa, quindi chiusura triadica, distribuzione dei gradi e ogni
altra proprietà strutturale restano identiche per costruzione.

**Ma quale permutazione conta quanto il fatto di permutare.** Tenere fissa la
rete non basta: la permutazione uniforme dà a ogni nodo la stessa probabilità di
ricevere l'etichetta F, qualunque sia il suo grado, e le donne hanno meno legami.
Il riferimento dell'articolo è la permutazione **entro strati di grado**
(sezione D); quella uniforme resta come calcolo esatto, ma risponde a una
domanda diversa.

---

## A. Il logit su tutte le diadi

### Il problema

Una regressione logistica su 1,6 miliardi di osservazioni non entra in memoria:
la sola matrice di disegno sarebbe 1,6·10⁹ × 7 in doppia precisione, cioè
**90 GB**.

### La soluzione

Non serve tenerla. Un passo di Newton richiede solo due quantità aggregate —
l'informazione osservata `X'WX` (una matrice 7×7) e il gradiente `X'(y−p)` (un
vettore di 7) — ed entrambe sono **somme sulle diadi**. Si percorrono le diadi
a blocchi di righe, si accumula, si butta via il blocco.

Memoria costante, circa 2 GB. Una percorrenza completa: **cinque minuti**.

### La ricerca di linea

La verosimiglianza logistica è concava, quindi ha un massimo unico. Non ne
segue che un passo di Newton intero lo avvicini: partendo lontano, la prima
versione ha **peggiorato** la log-verosimiglianza da −4,7 a −27,3 milioni.

Ogni iterazione fa quindi due percorrenze: una per gradiente e informazione nel
punto corrente, una per valutare la verosimiglianza in sei frazioni del passo e
adottare la migliore. Vicino all'ottimo la frazione intera vince sempre, quindi
la convergenza resta quadratica. Costo: dieci percorrenze in tutto.

### La verifica

Non si dichiara l'esattezza: si misura. Su una rete da 900 nodi — abbastanza
piccola perché **tutte** le 404.550 diadi entrino in memoria — si confronta con
`statsmodels`:

```
    termine     statsmodels      blocchi    scarto in errori std
 intercetta     -5.98875223  -5.98873703   3,7e-04
     same_F      1.04606598   1.04606198   9,8e-05
     same_M      0.31997631   0.31997369   1,1e-04
 same_genre      1.49308611   1.49308420   8,1e-05
sum_lognrel      0.39473209   0.39473005   2,7e-04

log-verosimiglianza: -43.178,4153 in entrambi
```

Lo scarto massimo è **meno di un millesimo di errore standard**. Non è zero
perché il Newton si ferma quando la log-verosimiglianza migliora meno di 10⁻³
(errore E8): è un criterio pensato per la rete intera, dove una somma di 1,6
miliardi di termini ha un pavimento numerico, e su una rete piccola ferma la
stima a scarti di 10⁻⁵ sui coefficienti. Una prima versione di questo documento
riportava uno scarto di 1,19·10⁻⁹, misurato *prima* che E8 cambiasse il
criterio di arresto; il test, rimasto con la soglia assoluta di 10⁻⁷, falliva
da allora senza che nessuno lo rieseguisse. Ora la soglia è in unità di errore
standard, che è la sola scala su cui uno scarto numerico abbia un significato.

I dati di prova sono generati da coefficienti noti, e il metodo li recupera.
Il test è in `tests/test_logit_esatto.py`.

### Il risultato

Su tutte e 1.619.630.155 le diadi della rete a genere determinato:

| termine | coefficiente | errore std | IC 95% | odds ratio |
|---|---|---|---|---|
| intercetta | −14,01783 | 0,00598 | — | — |
| `same_F` | **+0,34796** | 0,01310 | [0,3223 – 0,3736] | **1,416** |
| `same_M` | **+0,20920** | 0,00363 | [0,2021 – 0,2163] | 1,233 |
| `same_mixed` | +0,53341 | 0,05671 | [0,4223 – 0,6446] | 1,705 |
| `same_genre` | +1,66704 | 0,00290 | [1,6614 – 1,6727] | 5,296 |
| `same_cohort` | +1,19208 | 0,00289 | [1,1864 – 1,1978] | 3,294 |
| `sum_lognrel` | +0,74138 | 0,00056 | — | 2,099 |

log-verosimiglianza −3.601.952,06.

Gli intervalli di `same_F` e `same_M` **non si sovrappongono**.

---

## B. La permutazione in forma chiusa

### Il problema

Il test QAP permuta le etichette dei nodi tenendo la rete fissa e guarda dove
cade il valore osservato. Mille permutazioni danno una *stima* della
distribuzione nulla, con il suo errore Monte Carlo.

### La soluzione

Media e varianza si scrivono in forma chiusa. Sia `X` il numero di archi con
entrambi gli estremi di categoria *c*, con *m* archi, *n* nodi e *n_c* nodi di
quella categoria:

    E[X] = m · p₂        con   p₂ = n_c(n_c−1) / (n(n−1))

Per la varianza servono le probabilità che **due** archi siano entrambi interni,
e dipendono da quanti nodi distinti coinvolgono: tre se condividono un estremo,
quattro se sono disgiunti.

    E[X²] = E[X] + A·p₃ + D·p₄

dove `A` è il numero di coppie ordinate di archi adiacenti — cioè `Σᵢ dᵢ(dᵢ−1)`
sui gradi — e `D = m(m−1) − A` quelle disgiunte;
`p₃ = p₂·(n_c−2)/(n−2)` e `p₄ = p₃·(n_c−3)/(n−3)`.

Il calcolo è istantaneo: è una somma sui gradi.

### La verifica

Confronto con **200.000** permutazioni Monte Carlo, su una rete con gradi
deliberatamente pareto — il caso in cui la varianza dipende davvero dalla
struttura, quindi quello in cui una formula sbagliata si vedrebbe:

```
  cat   oss   attesi_esatti  attesi_MC  sd_esatta   sd_MC   rapporto sd
    F   267        245,17     245,15      39,47     39,56      0,998
    M  2652       2615,47    2615,45     130,29    130,31      1,000
mixed     4          6,63       6,64       3,70      3,71      0,997
```

Scarto della media entro 1,3 errori Monte Carlo; deviazioni entro lo 0,3%.
Il test è in `tests/test_permutazione_esatta.py`.

### Il risultato, sulla rete intera

56.915 nodi, 521.438 archi:

| | nodi | archi osservati | attesi | sd esatta | rapporto | *z* |
|---|---|---|---|---|---|---|
| F | 6.931 | 6.329 | 7.731,90 | 418,20 | **0,819** | **−3,35** |
| M | 49.111 | 420.181 | 388.244,70 | 3.064,90 | 1,082 | +10,42 |
| misti | 873 | 323 | 122,54 | 22,27 | 2,636 | +9,00 |

---

## C. Che cosa costava approssimare

Il confronto fra le due versioni è il vero prodotto dell'operazione, perché
dice quali approssimazioni erano innocue e quali no. Non era prevedibile.

| approssimazione | costava? | entità |
|---|---|---|
| QAP a 1.000 permutazioni | **no** | scarti sotto lo 0,4% — era già esatta |
| betweenness su 400 sorgenti | **sì, moderatamente** | coefficiente 7%, *p* da 0,21 a 0,14 |
| **logit caso-controllo** | **sì, molto** | divario F/M compresso del **40%**; pendenza temporale fino a −0,17 |
| correzione dell'intercetta | **era sbagliata** | segno invertito, 12,9 unità |

Due su quattro distorcevano, e **non nella stessa direzione**: il logit
caso-controllo attenuava il divario F/M, che è l'effetto di interesse; la
betweenness campionata spingeva verso la significatività un effetto di
marginalità femminile che non c'è (−0,252 con *p* 0,14 invece di −0,236 con
*p* 0,21). Una prima stesura di questo documento, e dell'articolo, diceva
«sempre nella direzione di attenuare»: era vero solo per il primo. Il terzo
caso era un errore vero, trovato solo perché il calcolo esatto ha fatto da
controllo su quello approssimato.

---

## D. Il nullo che rispetta l'attività (Fase 4j)

### Il problema

La permutazione della sezione B è esatta, ma il suo nullo è **cieco
all'attività**: ogni artista ha la stessa probabilità di portare l'etichetta F.
Nei decenni 1950-1970 le donne hanno fra 0,65 e 0,70 volte il grado medio. Il
nullo uniforme si aspetta quindi legami donna-donna che donne con così pochi
legami non avevano occasione di formare, e legge la scarsità di legami come
distanza fra donne.

Il sintomo era già nei dati: la matrice di mixing della Fase 3, che usa un nullo
a grado preservato, dà 1,54 per donna-donna sulla rete intera; la permutazione
uniforme, sulla stessa rete, 0,82. Stesso dato, segno opposto.

### La soluzione

Le etichette si permutano **entro strati di grado**: artisti con lo stesso
numero di legami, strati contigui fusi finché ognuno ha almeno 30 nodi. Ogni
genere conserva così la propria distribuzione dei gradi e la rete resta fissa.
Con gli strati la forma chiusa non vale più: media e deviazione vengono da 2.000
permutazioni per decennio (1.000 sulla rete intera). Accanto si calcola il
rapporto di Newman sul modello di configurazione, che dà gli stessi valori a
meno di qualche centesimo.

### La verifica

Controllo positivo, in `tests/test_permutazione_per_grado.py`: una rete
**senza alcuna omofilia**, in cui la categoria rara sta sui nodi a basso grado
(0,65 del grado medio, come le donne dei primi decenni). Il nullo uniforme vede
un deficit spurio, **0,405**; il nullo per strati dà **0,943** (*z* −1,5). Il
test verifica anche che la permutazione non esca mai dagli strati.

Controllo di coerenza: sul nullo uniforme la Fase 4j riproduce i rapporti della
4e con uno scarto massimo di 1,1·10⁻¹⁶.

### Il risultato

| decennio | grado medio F / medio | F uniforme | **F per grado** | *z* | M per grado |
|---|---|---|---|---|---|
| 1950 | 0,65 | 0,479 | **1,125** | 1,3 | 1,003 |
| 1960 | 0,68 | 0,499 | **1,074** | 1,7 | 1,000 |
| 1970 | 0,70 | 0,606 | **1,178** | 3,7 | 1,006 |
| 1980 | 0,83 | 0,900 | **1,289** | 5,9 | 1,007 |
| 1990 | 0,89 | 1,236 | **1,561** | 13,3 | 1,011 |
| 2000 | 0,85 | 1,224 | **1,710** | 19,3 | 1,007 |
| 2010 | 0,83 | 1,168 | **1,669** | 17,9 | 1,009 |
| 2020 | 1,00 | 1,664 | **1,703** | 15,0 | 1,010 |
| rete intera | 0,74 | 0,819 | **1,436** | 26,9 | 1,008 |

Il deficit dei primi decenni **sparisce**: fra artisti ugualmente attivi le
donne degli anni Cinquanta e Sessanta non si legavano fra loro né meno né più
del caso. L'eccesso compare negli anni Settanta, cresce fino ai Duemila e da lì
resta attorno a 1,7. Anche il balzo degli anni Venti del nullo uniforme era in
parte lo stesso artefatto al contrario: in quel decennio il grado medio delle
donne raggiunge quello degli uomini (0,997).

Non c'è inversione di segno: c'è un'**emersione**, da zero a circa il 70% in
più del caso. Il logit per decennio, che controlla l'attività tramite le
release, lo diceva già: `same_F` fra +0,047 e +0,071 fino agli anni Settanta,
mai significativo.

---

## E. Che cosa resta non calcolabile

Solo l'ERGM, e non per pigrizia. La sua verosimiglianza contiene una costante
di normalizzazione che è una somma su **tutti i grafi possibili** con 56.915
nodi: 2^1.619.630.155 termini. Non è «lungo», è matematicamente intrattabile —
ed è quella intrattabilità a rendere necessario l'MCMC, e quindi a rendere
possibile che l'MCMC fallisca. Il verbale sta in [`05-ergm.md`](05-ergm.md).
