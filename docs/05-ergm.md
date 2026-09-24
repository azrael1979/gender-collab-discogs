# Il verbale ERGM

Documento più lungo degli altri perché l'ERGM ha assorbito la maggior parte del
tempo e ha prodotto, alla fine, un risultato **negativo** — che è però
diventato il contributo metodologico del lavoro. Il percorso conta quanto
l'esito.

---

## Perché un ERGM

Le misure di omofilia — assortatività, matrici di mixing, test di permutazione
— dicono se chi si somiglia collabori più del caso. Non dicono **perché**. Due
donne possono trovarsi collegate perché si cercano, oppure perché condividono
un conoscente e la chiusura triadica fa il resto. L'ERGM con un termine di
chiusura (`gwesp`) è il modo standard di separare le due cose.

La specifica di riferimento:

    net ~ edges
        + nodematch('gender', diff = TRUE)
        + nodematch('musical_genre')
        + nodecov('log_nrel')
        + nodematch('cohort_decade')
        + gwesp(0.25, fixed = TRUE)

---

## Fase 1 — Sottoreti campionate: funziona, ma non significa nulla

Con un tetto di 1.500 nodi e 5.000 archi, estratti a valanga, l'ERGM converge.
Risultato: omofilia femminile mediana **0,679** contro **0,074** maschile.

**Il problema non era la convergenza ma il riferimento.** Di una stima su
campione a valanga non si può dire di che cosa sia stima: il campione non è
rappresentativo di alcuna popolazione definibile. È il limite che un referee
avrebbe aperto per primo, e la ragione per cui queste stime **non compaiono nei
risultati finali**.

Una nota tecnica utile: `nodematch("musical_genre")` è collineare con `edges`
dentro una sottorete a genere musicale unico. Il termine viene incluso solo
quando l'attributo varia davvero.

---

## Fase 2 — La rete integrale: quattro fallimenti

Quattro parametrizzazioni, tutte fallite. Vale la pena distinguere le firme,
perché sono diagnosticamente diverse.

| # | specifica | metodo | come è finita |
|---|---|---|---|
| 1 | `gwesp(0.25)` | MCMLE | passo dell'ottimizzatore crollato da ~0,46 a ~0,005 |
| 2 | `gwesp(0.5)` | MCMLE | iterazioni raddoppiate: 29 min, 62, 125, oltre 243 |
| 3 | `gwesp(0.25) + gwdegree` | MCMLE | idem |
| 4 | `gwesp(0.5)` | Stoch. Approx. | **convergenza dichiarata, e falsa** |

### Le due firme

**Passo che crolla** (#1): l'ottimizzatore riduce di due ordini di grandezza la
lunghezza del passo per non uscire dalla regione ammissibile. È la
quasi-degenerazione classica.

**Iterazioni che si allungano** (#2, #3): 29 minuti, poi 62, poi 125, poi oltre
243. Proiettando, la settima sarebbe durata trentadue ore. Una stima che si
allunga così non sta convergendo lentamente: sta divergendo lentamente.

### Il quarto caso, che è il più istruttivo

L'approssimazione stocastica ha **dichiarato successo**. La bontà di
adattamento l'ha smentita:

* dimensione efficace del campione ≈ **3** (dovrebbe essere centinaia);
* reti simulate con il **40%** degli archi osservati;
* il **4%** dei legami fra donne;
* coefficienti di genere musicale e coorte **negativi**, cioè il modello
  prediceva che chi condivide il genere musicale collabori *meno*.

Era un collasso verso il grafo vuoto travestito da convergenza. Senza la GOF
sarebbe finito nell'articolo.

**Da qui la regola D11:** la bontà di adattamento non è un accessorio, è il
solo controllo che distingua una convergenza vera da una apparente.

---

## Fase 3 — Per decennio: l'idea giusta, per la ragione giusta

L'obiezione ricevuta — *e se lo facessimo per decadi? ridurrebbe la
complessità?* — è corretta, ma non per il motivo apparente.

**Che cosa risolve.** La taglia. I decenni fino agli anni Cinquanta sono 163,
364, 1.515 nodi, cioè l'ordine di grandezza in cui la stima funzionava.

**Che cosa risolve davvero.** Un decennio è una **popolazione completa**, non un
campione. È la correzione del difetto della Fase 1.

**Che cosa NON risolve.** Il clustering, misurato decennio per decennio, resta
fra **0,43 e 0,56 in tutti i periodi**. Non scende spezzando la rete, e non può
scendere: è un artefatto di proiezione.

### Esito

| decennio | nodi | archi | clustering | esito | firma |
|---|---|---|---|---|---|
| 1930 | 150 | 514 | 0,466 | ✅ 21 min | — |
| 1940 | 338 | 1.932 | 0,466 | ✅ 52 min | — |
| 1950 | 1.398 | 15.177 | 0,526 | ❌ | iterazioni divergenti (2h di silenzio) |
| 2020 | 11.772 | 33.548 | 0,426 | ❌ | passo < 0,02 per 3 iterazioni |

**La previsione dichiarata prima di lanciare era sbagliata.** Nel docstring del
modulo stava scritto «converge fino agli anni Sessanta o Settanta». Si rompe
già a 15.177 archi. La previsione era stata scritta *prima* proprio perché
fosse falsificabile, e lo è stata.

**Il test sugli anni Venti era mal disegnato.** Erano stati messi in coda come
prova per separare taglia da clustering: sono la decade meno clusterizzata ma
**anche più grande** dei Cinquanta. Fallendo, il loro esito è confuso fra le
due cause e non decide nulla — non dimostra che il vincolo sia la taglia, e non
salva l'ipotesi del clustering.

Resta stabilito il meno: la soglia di stimabilità sta **fra 1.932 e 15.177
archi**.

**La coda è stata interrotta.** Restavano 1960, 1970, 1980, 2010, 1990, 2000:
tutti più grandi di *entrambi* i fallimenti, cioè circa 36 ore per confermare un
esito già determinato.

### Che cosa dicono i due decenni convergiti

| | `gwesp` | `gender.F` | `gender.M` | `genere_musicale` |
|---|---|---|---|---|
| 1930 | +2,391 | −0,262 (p 0,79) | +0,011 (p 0,89) | +0,275 |
| 1940 | +3,582 | −0,246 (p 0,36) | **−0,173** (p<10⁻⁴) | +0,361 |

Nessuna omofilia femminile, semmai negativa. **Concorda con la permutazione
esatta**, che per quei decenni dà rapporti F di 0,24 e 0,50.

Due metodi con assunzioni opposte — l'ERGM controlla per la chiusura triadica,
la permutazione tiene la struttura fissa per costruzione — dicono la stessa cosa
sul periodo in cui entrambi funzionano. Il che rafforza l'estremo opposto:
l'aggregazione degli anni Novanta-Venti è un cambiamento reale, non un artefatto
di misura che varrebbe per tutta la serie.

---

## La diagnosi

La bontà di adattamento dei due decenni convergiti sbaglia in un punto preciso
e **con la stessa forma**:

| partner condivisi | 1930 oss/sim | 1940 oss/sim |
|---|---|---|
| 0 | **2,36** | **8,69** |
| 1 | 0,46 | 0,43 |
| 2 | 0,42 | 0,41 |
| 4 | 1,55 | 1,31 |
| 6 | 5,78 | 4,38 |
| 8 | **20,55** | **6,54** |

È una **U**: centro sovrastimato, entrambe le code sottostimate. È ciò che si
ottiene adattando una distribuzione **unimodale** — l'unica che `gwesp` può
produrre, avendo un parametro solo — a una **bimodale**.

### L'ipotesi, e la sua verifica diretta

L'ipotesi: la bimodalità non è un fenomeno sociale ma un artefatto di
costruzione. Questa rete è la **proiezione di un grafo bipartito
artisti-release**, e ogni pubblicazione con *k* artisti accreditati genera una
clique di *k* in cui ogni arco ha *k−2* partner condivisi **per costruzione** —
senza che nessuno abbia chiuso alcun triangolo in senso sociale.

È verificabile **esattamente**, arco per arco, senza stimare nulla. Per ogni
arco si distinguono i partner condivisi *totali* — ciò che `gwesp` modella — da
quelli *imposti dalla proiezione*, cioè chi compare in una release condivisa dai
due estremi.

**Su tutti i 702.613 archi:**

```
 9.460.875  partner condivisi totali
 3.208.170  imposti dalla proiezione            (33,9%)
   259.458  archi interamente spiegati          (36,9%)
    17.353  archi senza alcun partner condiviso  (2,5%)
```

Il 33,9% globale **non è alto**: presa così, l'ipotesi era sbagliata, e va
detto. Ma la disaggregazione mostra la struttura. Con `max_credits = 8` una
release può imporre al massimo 8−2 = **6** partner condivisi:

| partner condivisi | quota spiegata |
|---|---|
| 1 | 0,823 |
| 3 | 0,824 |
| 5 | 0,810 |
| 6 | 0,792 |
| **7** | **0,659** |
| 12 | 0,445 |
| 19 | 0,319 |

Piatta all'80% fino a 6, poi crolla. Il **test del tetto** rende la coincidenza
una dimostrazione — per ogni arco si calcola *k−2* dalla release condivisa più
grande:

| | archi | quota spiegata |
|---|---|---|
| **entro** il tetto | 232.783 (33,1%) | **0,988** |
| **oltre** il tetto | 452.477 (64,4%) | **0,276** |

Dove una singola release *può* spiegare i triangoli, li spiega al **98,8%**.
Dove non può, la quota crolla. Non è una correlazione: è la firma aritmetica del
meccanismo.

**Statuto: misurato.** Non dipende da alcun modello.

---

## Il tentativo di conferma causale, e il suo fallimento

La diagnosi, fin qui, è **correlazionale**: si osserva un difetto e se ne
propone una causa. Un referee ha ragione a non accontentarsi.

### Il disegno

Riestimare il decennio 1940 — quello che converge in meno di un'ora — con
termini di dipendenza a **due** componenti, capaci per costruzione di una forma
bimodale, e misurare se la U si appiattisce. Con un **controllo negativo** che
rende il test un test.

| specifica | componenti | previsione se l'ipotesi è giusta |
|---|---|---|
| `gwesp(0.25)` — riferimento | 1 | U marcata |
| `gwesp(0.25) + gwesp(1.5)` | 2 | U appiattita |
| `gwesp(0.25) + esp(0)` | 2 | U appiattita |
| `gwesp(0.75)` — controllo negativo | 1 | U ancora marcata |

Il controllo negativo serve a separare «due componenti» da «decay sbagliato»,
che è l'alternativa ovvia.

Il confronto **non è sull'AIC** ma sulla forma dello scarto: la domanda non è
quale modello si adatti meglio in media, ma se il difetto abbia ancora quella
forma. Misurata come rapporto fra la media degli estremi (esp 0 e coda 6-9) e il
centro (esp 1-2); **1 significa piatta**.

### L'esito

| specifica | esito |
|---|---|
| `gwesp(0.25)` — riferimento | ✅ converge, **U = 16,90** (esp0 8,69; centro 0,42; coda 5,51) |
| `gwesp(0.25) + gwesp(1.5)` | ❌ non converge (28 min) |
| `gwesp(0.25) + esp(0)` | ❌ non converge (60 min) |
| `gwesp(0.75)` — controllo negativo | in corso |

**Entrambe le specifiche a due componenti falliscono su un decennio dove quella
a una componente converge in 52 minuti.** La previsione era che ammettere la
bimodalità appiattisse la U; invece aggiungere una seconda componente di
dipendenza rompe la stima del tutto.

### Che cosa cade e che cosa no

**Resta in piedi:** il dato della proiezione — 98,8% contro 27,6% — perché è una
*misura* sui dati, non un'affermazione su un modello. E resta lo scarto a U,
osservato in due decenni indipendenti con la stessa forma.

**Cade:** la dimostrazione causale *per questa via*. Non si può dire «un
modello che ammette la bimodalità si adatta», perché quel modello non è
stimabile. Il tentativo fallito resta scritto.

La conferma è poi arrivata da un'altra strada — vedi
[La conferma, fuori dall'ERGM](#la-conferma-fuori-dallergm) — che non passa da
alcuna stima.

### La strada che non funziona, e perché

Sembra ovvio dare al modello la dimensione del cast come covariata di arco
(`edgecov`), così che `gwesp` debba spiegare solo il residuo. **Non funziona:**
se due artisti condividono una release hanno un arco per costruzione, quindi
quella covariata sarebbe non nulla esattamente sugli archi e nulla altrove —
separerebbe perfettamente i dati.

---

## La conferma, fuori dall'ERGM

Cercare la conferma **dentro** l'ERGM era l'errore di impostazione. Se l'ERGM
non sa descrivere questa rete, non può nemmeno servire a dimostrare *perché*
non sa descriverla. L'affermazione da verificare non riguarda un modello:
riguarda il **meccanismo** che genera la rete, e un meccanismo si verifica
facendolo girare.

### Il disegno

Si prende la struttura bipartita artisti-release, la si randomizza conservando
**esattamente** entrambe le distribuzioni di grado — quante release per artista,
quanti artisti per release — e la si riproietta, cento volte. Nessuna
preferenza sociale vi entra: gli artisti sono assegnati alle release a caso.
Contiene **solo il meccanismo**.

Il confronto è di **forma**, ciascun modello contro il *proprio* osservato e
normalizzato a quote. Gli insiemi differiscono per costruzione — l'ERGM gira
sui 338 nodi a genere determinato della componente gigante, la proiezione su
tutti i 515 artisti del decennio — e confrontarli direttamente sarebbe
scorretto. Una prima lettura lo faceva ed è stata rifatta.

Prima di lanciare è stato verificato che il doppio scambio bipartito conservi
esattamente entrambe le distribuzioni di grado, non crei doppioni e randomizzi
davvero l'appaiamento (99,6% dei crediti riappaiati). Se lo scambio sbagliasse
i gradi il confronto non varrebbe nulla. Test in
`tests/test_scambio_bipartito.py`.

### L'esito

Rapporto fra quota simulata e quota osservata, anni Quaranta:

| partner condivisi | ERGM stimato | proiezione randomizzata |
|---|---|---|
| 0 | **0,13** | 0,49 |
| 1 | **2,59** | 0,72 |
| 2 | **2,67** | 0,74 |
| 4 | 0,85 | 0,86 |
| 6 | **0,25** | 0,83 |
| 8 | **0,17** | 0,97 |
| 12 | **0,27** | 0,98 |

Scarto medio in log₂, replicato su tre insiemi indipendenti:

| insieme | archi osservati | archi randomizzati | scarto \|log₂\| |
|---|---|---|---|
| 1940s — ERGM | 1.932 | 1.749 | **1,799** |
| 1940s — proiezione | 3.016 | 4.465 | **0,297** |
| 1950s — proiezione | 21.990 | 43.690 | **0,768** |
| rete intera — proiezione | 898.475 | 2.189.834 | **0,322** |

Conta la **forma**, non il livello. L'ERGM oscilla di un fattore venti fra 0,13
e 2,67 — è la U. La proiezione randomizzata è monotona e piatta in tutti e tre
gli insiemi: `0,49 → 0,72 → 0,80 → 0,86 → 0,96` negli anni Quaranta, senza
alcuna inversione.

E lo fa un modello **senza alcun parametro stimato**, che batte di sei volte un
ERGM con sei parametri adattati sui dati.

> La forma bimodale della distribuzione dei partner condivisi è prodotta dal
> meccanismo di proiezione bipartita, non da un processo di chiusura triadica.
> La U è una proprietà del modello, non dei dati.

**Statuto: dimostrato.** Nessun parametro stimato, nessuna assunzione
inferenziale: si è fatto girare un processo noto e si è guardato che forma
produce.

### Un secondo risultato, non previsto

La randomizzazione produce **sistematicamente più archi dell'osservato**: 1,5
volte negli anni Quaranta, 2,0 nei Cinquanta, **2,4 sulla rete intera**.

Significa che i musicisti italiani **ricollaborano con le stesse persone** molto
più di quanto il caso produrrebbe: le stesse coppie ricorrono su release
diverse, quindi generano meno archi *distinti*. La randomizzazione le disperde.

È sostantivo, non metodologico, e scompone il fenomeno in due parti che vanno
tenute separate:

* il **meccanismo** spiega la *forma* della distribuzione dei partner condivisi;
* il **processo sociale** spiega la sua *concentrazione*.

### Che cosa resta non spiegato

A esp = 0 la proiezione randomizzata dà 0,49: sottoproduce della metà gli archi
isolati. Molto meglio dell'ERGM (0,13), ma non perfetta. Il meccanismo non
esaurisce i dati, e il testo deve dirlo.

---

## Conclusione

L'ERGM **non è stimabile su questa rete** oltre i ~2.000 archi. Sei fallimenti
documentati su quattro parametrizzazioni della rete integrale, due decenni e due
specifiche a due componenti.

Ma la ragione non è la taglia in sé, ed è questo il risultato: su una rete
ottenuta per proiezione bipartita, un termine di chiusura triadica misura in
buona parte la **dimensione dei cast** e non un processo sociale. Non è più
un'interpretazione: un modello nullo senza parametri riproduce la forma della
distribuzione dei partner condivisi **sei volte meglio** dell'ERGM stimato, e
senza produrre la U. Vale per qualunque rete di co-autorialità, che è metà
della letteratura su collaborazione e omofilia.

E giustifica a posteriori la scelta di calcolare invece di stimare: se la
dipendenza che l'ERGM doveva assorbire è in buona parte meccanica, allora il
logit esatto e il test di permutazione — che tengono la struttura fissa per
costruzione invece di modellarla — non sono un ripiego. Sono la scelta corretta.
