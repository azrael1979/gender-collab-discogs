# Errori trovati e corretti

Sono elencati tutti, anche quelli che non hanno cambiato alcun numero. Un
errore che non cambia i risultati oggi può cambiarli domani, e sapere *come* è
stato trovato vale quanto sapere che è stato corretto.

Gli errori sono ordinati per gravità, non per data; il numero dice invece
l'ordine in cui sono stati trovati.

---

## E13 — Il nullo della tesi centrale era cieco all'attività

**Gravità: la più alta.** Cambiava la forma del risultato centrale e il titolo
che lo riassumeva.

**Che cos'era.** La serie per decennio — «fino agli anni Settanta le donne
erano legate fra loro *meno* del caso, dagli anni Novanta *più*: un'inversione
di segno» — poggiava sulla permutazione uniforme delle etichette. Quel nullo dà
a ogni artista la stessa probabilità di essere donna, qualunque sia il suo
numero di legami. Nei primi decenni le donne avevano fra 0,65 e 0,70 volte il
grado medio: il nullo si aspettava legami che loro non avevano occasione di
formare, e il deficit che ne risultava (0,48-0,61) era scarsità di legami, non
distanza fra donne.

**Come è emerso.** Rileggendo il paper per accorciarlo: la Figura 2 (mixing a
grado preservato) dava 1,54 per donna-donna sulla rete intera, la Tabella della
permutazione uniforme 0,82. Due numeri sullo stesso dato con segno opposto, e
il testo spiegava il secondo con una ragione («dominato dai decenni in cui si
sono formati più legami») che i dati non sostenevano: proprio quei decenni
avevano rapporti sopra 1. Il logit per decennio, che controlla l'attività,
aveva già `same_F` non significativo fino agli anni Settanta — il segnale c'era
ed era stato letto come conferma invece che come obiezione.

**Come è stato verificato.** Fase 4j: permutazione entro strati di grado, più
un controllo positivo su una rete senza omofilia con la stessa sproporzione di
attività (il nullo uniforme vede 0,41, quello per strati 0,94). Previsione
scritta nel docstring prima di eseguire.

**Che cosa ha cambiato.** Fra artisti ugualmente attivi il rapporto F è 1,13 e
1,07 negli anni Cinquanta e Sessanta (non significativo), 1,18 nei Settanta
(*z* 3,7), 1,56 nei Novanta, ~1,7 dal 2000. **Nessuna inversione di segno:
un'emersione.** Il balzo degli anni Venti (1,66 contro 1,17 del decennio prima)
era in parte lo stesso artefatto al contrario, perché in quel decennio il grado
delle donne raggiunge quello degli uomini; col nullo per strati è un plateau.
Il risultato che sopravvive è più solido — e il titolo «the emergence of…» gli
calza meglio di quanto calzasse all'inversione.

**Lezione.** Tenere fissa la rete non basta a rendere un nullo neutrale: conta
che cosa si permuta rispetto a che cosa. In un campo dove la minoranza è anche
meno attiva, un nullo cieco all'attività confonde evitamento e scarsità.

---

## E14 — Il paper riportava la betweenness campionata come se fosse esatta

**Gravità: media.** Un coefficiente e un *p* sbagliati in tabella, e una
contraddizione interna.

**Che cos'era.** `paper.py` leggeva gli effetti di posizione da
`report_numbers.json`, scritto dalla Fase 7 il 21 settembre — prima che la
Fase 3b passasse alla betweenness esatta. La tabella della posizione mostrava
quindi −0,252 (*p* 0,14), mentre la tabella «che cosa costava approssimare»
dichiarava esatto −0,236 (*p* 0,21).

**Correzione.** Il paper legge le regressioni direttamente da
`position_regressions.parquet`. Il valore campionato, non più riproducibile dai
dati, resta in `paper.py` come costante documentata per il confronto.

**Principio.** Un file di numeri intermedio scritto da un'altra fase è una
cache, e le cache invecchiano. Ogni cifra va letta dal prodotto della fase che
la calcola.

---

## E15 — Incoerenze interne del paper, trovate alla riscrittura

**Gravità: media, cumulativamente.** Nessuna cambiava un risultato; tutte le
avrebbe trovate un referee.

* **«Sempre nella direzione di attenuare»** — detto di due approssimazioni su
  quattro, nel paper e in `04-calcolo-esatto.md`. Vero per il logit
  caso-controllo; falso per la betweenness campionata, che *esagerava* un
  effetto di marginalità inesistente.
* **Conteggio dei fallimenti ERGM** sulla rete integrale: «quattro falliti più un
  quinto ad approssimazione stocastica». Erano quattro in tutto, il quarto era
  quello stocastico.
* **Rimandi interni sbagliati**: 1.2 → «Section 4.6» (era 4.8); 3.1 e 3.2 →
  «Section 4.7» (era 4.9); 3.4 → «Section 4.1» (era 4.3). La nota di commit
  diceva «21 rinvii interni risolti»: esistevano, ma non puntavano giusto.
* **Numerazione**: due Tabelle 3, due Tabelle 5, nessuna Figura 2 — la figura
  del mixing veniva generata ma non inclusa.
* **Residui della tesi ritirata**: la 2.2 diceva di usare gli ERGM «proprio per
  questa ragione»; i limiti citavano la «coorte post-2000 dell'ERGM» e le
  «dimensioni appaiate delle sottoreti»; la robustezza descriveva la bontà di
  adattamento dei vecchi modelli su sottorete («riproducono bene il centro»),
  il contrario di quanto mostrano i decenni; l'Appendice B affermava che la
  terminazione di Hummel «porta ogni modello a convergenza in pochi minuti».
* **«0,17 per decennio»**: lo scarto del caso-controllo era una sottostima di
  `same_F` di 0,17 negli anni Venti, non una pendenza.
* **«Esatta alla quarta cifra decimale»** per la permutazione a mille repliche,
  due righe sotto la tabella che diceva «entro lo 0,4%».
* **«Zero interazioni significative su dodici»**: erano dodici per il solo
  autovettore. Sulle tre misure le interazioni sono 36 e una (coreness) è
  significativa al 5% — meno di quante ne produrrebbe il caso.

---

## E16 — Un test che falliva da giorni, e una cifra che ne dipendeva

**Gravità: bassa sui risultati, alta sul metodo.** Nessuna stima era sbagliata;
un'affermazione di precisione sì.

**Che cos'era.** `tests/test_logit_esatto.py` chiedeva scarti assoluti sotto
10⁻⁷ fra il Newton a blocchi e `statsmodels`. Dopo E8 il Newton si ferma anche
quando la log-verosimiglianza migliora meno di 10⁻³, e sulla rete di prova
questo lo arresta a scarti di 10⁻⁵ sui coefficienti. Il test falliva da allora.
Nel frattempo `04-calcolo-esatto.md` e il paper continuavano a dichiarare una
coincidenza «entro 10⁻⁹», misurata prima di E8.

**Come è emerso.** Rieseguendo tutti i test dopo aver aggiunto la Fase 4j. Un
test che nessuno riesegue non verifica niente.

**Correzione.** Soglia in unità di errore standard (scarto massimo osservato:
3,7·10⁻⁴ errori standard; log-verosimiglianza identica alla quarta decimale) e
testo corretto nel documento e nel paper.

---

## E1 — Correzione caso-controllo con il segno invertito

**Gravità: alta.** Un coefficiente pubblicato era sbagliato.

**Che cos'era.** Nel logit diadico caso-controllo si tengono tutti gli archi e
una frazione *f* delle non-connesse, e l'intercetta va riportata alla
popolazione. La correzione di Prentice-Pyke è

    b0_popolazione = b0_campione + log(f)

con `log(f)` negativo. Il codice **sottraeva** invece di sommare, sbagliando
l'intercetta di `2·log(f)`, cioè di circa 12,9 unità.

**Come è emerso.** Non da una revisione del codice. Il calcolo esatto sulla
rete intera è stato avviato a caldo dai coefficienti campionari, e l'intercetta
di partenza, −0,615, era **incompatibile con la densità osservata** della rete
(3,2·10⁻⁴, che in logit fa −8,04). Un'intercetta così alta con una rete così
rada non sta in piedi.

**Come è stato verificato.** Non per ragionamento: costruendo una popolazione
simulata con verità nota (4 milioni di diadi, `b0 = −8`), campionandola e
guardando quale correzione la restituisce. `b0 + log(f)` dà −7,957; `b0 − log(f)`
dà +4,010. Il test è in `tests/test_correzione_casocontrollo.py`.

**Che cosa ha cambiato.** Solo l'intercetta: da −0,615 a −13,478. **Nessuna
pendenza** — il risultato è invariante al disegno campionario, verificato sia
in teoria sia nella simulazione. Tutti i coefficienti di omofilia pubblicati
restano validi.

**Perché era invisibile.** Proprio perché le pendenze non ne risentono.
L'intercetta di un logit diadico non ha interpretazione sostantiva qui, quindi
nessuno la guardava.

---

## E2 — Il logit caso-controllo comprimeva sistematicamente l'effetto

**Gravità: alta.** Non è un errore di codice ma di metodo, e alterava il
risultato principale.

**Che cos'era.** Il campionamento a cinque controlli per caso produceva stime
che differiscono da quelle esatte **più di quanto il loro errore standard
nominale suggerisse**.

| termine | campionario | esatto | scarto |
|---|---|---|---|
| `same_F` | +0,317 | **+0,348** | −0,031 (1,7 se) |
| `same_M` | +0,231 | **+0,209** | +0,022 (4,2 se) |

Il divario fra omofilia femminile e maschile passava da 0,086 a **0,139**: il
campionamento lo **comprimeva del 40%**, cioè attenuava esattamente la
quantità di interesse.

Sulla serie temporale l'effetto era peggiore: fino a **0,17** di sottostima di
`same_F` negli anni Venti, cioè proprio dove la curva sale.

**Come è emerso.** Dal confronto diretto con il calcolo esatto. Per nessun'altra
via: la stima campionaria era internamente coerente e i suoi intervalli
bootstrap non segnalavano nulla.

**Che cosa ha cambiato.** La curva esatta sale più ripida. Il risultato
centrale è più forte di quanto sembrasse.

---

## E3 — Una regex ha ucciso una stima sana

**Gravità: alta in termini di tempo perso.** Nessun risultato sbagliato, ma
quattordici ore di macchina ferma.

**Che cos'era.** L'orchestratore ERGM leggeva il passo dell'ottimizzatore da
righe della forma `1 Optimizing with step length 0.5774.` con la regex
`([0-9.]+)`, che cattura **anche il punto finale della frase**.
`float("0.5774.")` solleva `ValueError`, l'eccezione usciva dal ciclo di
lettura e uccideva l'orchestratore; R moriva poi di `SIGPIPE`.

**L'aggravante.** Il passo era 0,5774, cioè la stima stava andando **bene**. La
sorveglianza ha interrotto proprio ciò che doveva proteggere.

**Correzione.** Regex `step length\s+([0-9]*\.?[0-9]+)`, più un principio
generale: il generatore che legge l'output di R **non solleva mai** — ogni
errore viene registrato e ingoiato. La sorveglianza è un ausilio e non deve
poter interrompere ciò che sorveglia.

**Conseguenza.** Otto modalità di guasto revisionate e sei test pre-lancio.

---

## E4 — La sorveglianza dipendeva da ciò che sorvegliava

**Gravità: media.** Ha permesso a E3 di restare invisibile per ore.

**Che cos'era.** Tutti i controlli — tempo trascorso, memoria, progresso —
stavano **dentro il ciclo di lettura dell'output di R**. Ma il passo viene
stampato alla *fine* di un'iterazione: quando le iterazioni si allungano senza
limite — 29 minuti, poi 62, poi 125, poi oltre 243 — l'output tace per ore e
nessun controllo può scattare.

**Correzione.** Un `Sorvegliante` su thread indipendente, che ogni sessanta
secondi verifica tempo, memoria e **silenzio**, qualunque cosa faccia R.

**Verifica.** Testato uccidendo un processo silenzioso e tollerando uno già
morto.

**Conseguenza.** È questo meccanismo ad aver poi chiuso correttamente la stima
degli anni Cinquanta, abbandonata per due ore di silenzio.

---

## E5 — Betweenness campionata, e non era neutra

**Gravità: media.** Cambiava un coefficiente e un livello di significatività.

**Che cos'era.** La betweenness era approssimata su 400 sorgenti campionate,
con la motivazione — scritta nel codice — che la versione esatta «non è
praticabile». Era falso: `igraph` calcola Brandes su tutte e 79.013 le sorgenti
in **56 minuti**.

| | campionata (k=400) | esatta |
|---|---|---|
| effetto principale F | −0,252 (p = 0,14) | **−0,236 (p = 0,21)** |
| R² | 0,539 | 0,546 |

**Perché conta più di quanto sembri.** Il campionamento a *k* sorgenti stima
bene i valori alti e male quelli bassi — e sono i valori bassi a rispondere
alla domanda sulla marginalità delle donne. L'approssimazione spostava il
risultato verso un effetto apparentemente più forte.

**Conclusione invariata:** nessun effetto Smurfette posizionale. Ma ora poggia
su un calcolo.

---

## E6 — Classificatore dei ruoli troppo stretto

**Gravità: media.** Distorceva RQ5.

**Che cos'era.** 1,1 milioni di crediti finivano in «altro», e fra questi
strumenti veri: *Tenor Saxophone*, *Double Bass*, *Viola*, *Voice*. La
distinzione fra ruolo creativo ed esecutivo — che è il cuore di RQ5 — era
quindi costruita su una classificazione che scartava un quarto dei dati.

**Correzione.** Classificatore per famiglie di parole chiave invece che per
elenco. «Altro» è sceso a **210.705**.

---

## E7 — Saturazione della macchina

**Gravità: media.** Nessun risultato sbagliato, ma gli altri servizi della
macchina sono stati affamati.

**Che cos'era.** `MPLE.samplesize = 20.000.000`. La matrice di disegno della
pseudo-verosimiglianza occupa circa un gigabyte ogni quattro milioni di diadi,
e con `PSOCK` viene **copiata in ogni worker**. Con sei catene: otto processi R,
circa 60 GB, swap pieno, carico 34.

**Correzione.** `mple_samplesize` a 1.000.000 (2,8 GB di picco), campione MCMC
da 10.000 a 3.000, parallelismo da 6 a 2. Risultato: tre processi, 4,1 GB.

**Principio adottato.** I parametri sono tarati sulla **memoria**, non sulla
velocità: il tempo non è un vincolo, la convivenza con gli altri servizi sì.

---

## E8 — Tolleranza di convergenza irraggiungibile

**Gravità: bassa.** Nessun risultato sbagliato, sette ore sprecate evitate.

**Che cos'era.** Il Newton esatto usava `TOLLERANZA = 1e-9` sul passo. Ma la
log-verosimiglianza è una somma di **1,6 miliardi di termini** in virgola mobile
a doppia precisione, e l'errore di accumulo pone un pavimento intorno a 10⁻⁷.
La stima era convergita — log-verosimiglianza identica e coefficienti stabili
alla quarta decimale per tre iterazioni — ma il criterio non poteva mai dirsi
soddisfatto, e il programma avrebbe girato a vuoto fino al limite di 40
iterazioni.

**Correzione.** Tolleranza a 10⁻⁶ (tre ordini di grandezza sotto il più piccolo
errore standard, che è ~10⁻³), più un secondo criterio indipendente sul
miglioramento della verosimiglianza, più un **checkpoint per iterazione** —
una passata costa quattordici minuti e non deve ricominciare da zero.

---

## E9 — Newton senza ricerca di linea

**Gravità: bassa.** Trovato subito, mai entrato nei risultati.

**Che cos'era.** La prima versione del Newton esatto prendeva il passo intero.
Partendo lontano dall'ottimo, la log-verosimiglianza è **peggiorata** da −4,7 a
−27,3 milioni fra la prima e la seconda iterazione. La concavità garantisce un
massimo unico, non che un passo intero lo avvicini.

**Correzione.** Ricerca di linea su una griglia di frazioni del passo, valutate
tutte nella stessa percorrenza delle diadi — costa sei prodotti scalari sulla
stessa matrice, cioè quasi nulla rispetto al costruirla.

---

## E10 — `pkill -f` che uccide la propria shell

**Gravità: bassa, ma ricorrente.** Accaduto due volte.

**Che cos'era.** `pkill -f "phase4e_esatto"` lanciato in una shell il cui
*command line* contiene quella stessa stringa — perché il comando include un
here-document che nomina il file — uccide sé stesso prima di arrivare al
bersaglio. Uscita 144, bersaglio ancora vivo.

**Correzione.** Il trucco delle parentesi (`phase4e_esatt[o]`) funziona solo se
la stringa non compare *altrove* nella riga di comando. La soluzione robusta è
separare le operazioni e **uccidere per PID**.

---

## E11 — Errori minori di ambiente

Raccolti per completezza; nessuno ha toccato i risultati.

* `groupby.nth` con `KeyError` su pandas 1.5 → sostituito con `cumcount()`.
* Backslash in f-string, vietato in Python 3.9 → didascalie a virgolette doppie.
* WDQS che risponde 429, 502, 504 e JSON troncato → suddivisione ricorsiva dei
  lotti, con il 429 contato separatamente dai fallimenti veri.
* `nodematch("musical_genre")` collineare con `edges` dentro sottoreti a genere
  unico → termine incluso solo quando l'attributo varia.
* Tabelle della Fase 4f mai scritte perché il ciclo è stato interrotto e la
  raccolta avviene in fondo → prodotte a mano; `data/` non è versionato, quindi
  senza sarebbero andate perse.

---

## E12 — L'attendente che aspetta sé stesso

**Gravità: bassa.** Variante di E10, con un bersaglio diverso.

**Che cos'era.** Un processo in attesa della fine di una fase, scritto come

    until ! pgrep -f "phase4i_proiezione_null[a]"; do sleep 60; done
    tail -4 logs/phase4i_proiezione_nulla.log

Il trucco delle parentesi protegge `pgrep` dal corrispondere a sé stesso — ma
**solo per quella occorrenza**. La riga successiva nomina
`logs/phase4i_proiezione_nulla.log`, che corrisponde al pattern; l'attendente
trovava sé stesso e aspettava all'infinito.

**Come è emerso.** La fase era finita da nove ore ma l'attendente risultava
ancora vivo, con carico macchina a 0,07 — cioè nessuno stava calcolando nulla.

**Correzione.** Il pattern deve essere assente dall'**intera** riga di comando,
non solo dall'invocazione di `pgrep`. In pratica: attendere per PID, o
riferirsi al file di log per via indiretta.

**Costo.** Nessun risultato sbagliato; nove ore di ritardo nel leggere un
risultato già pronto.
