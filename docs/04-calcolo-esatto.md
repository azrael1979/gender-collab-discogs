# Il calcolo esatto

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

È per questo che la tesi dell'articolo poggia sul **test di permutazione**, i
cui momenti in forma chiusa non dipendono da alcuna assunzione di indipendenza:
le etichette si permutano tenendo la rete fissa, quindi chiusura triadica,
distribuzione dei gradi e ogni altra proprietà strutturale restano identiche per
costruzione.

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
    termine     statsmodels      blocchi        scarto
 intercetta     -5.98875223  -5.98875223   4.44e-16
     same_F      1.04606598   1.04606598
     same_M      0.31997631   0.31997631
 same_genre      1.49308611   1.49308611
sum_lognrel      0.39473209   0.39473209

scarto massimo sui coefficienti : 1.19e-09
scarto massimo sugli errori std : 1.93e-10
```

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

Due su quattro distorcevano, e **sempre nella direzione di attenuare
l'effetto**. Una era un errore vero, trovato solo perché il calcolo esatto ha
fatto da controllo su quello approssimato.

---

## D. Che cosa resta non calcolabile

Solo l'ERGM, e non per pigrizia. La sua verosimiglianza contiene una costante
di normalizzazione che è una somma su **tutti i grafi possibili** con 56.915
nodi: 2^1.619.630.155 termini. Non è «lungo», è matematicamente intrattabile —
ed è quella intrattabilità a rendere necessario l'MCMC, e quindi a rendere
possibile che l'MCMC fallisca. Il verbale sta in [`05-ergm.md`](05-ergm.md).
