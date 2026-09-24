# Errori trovati e corretti

Sono elencati tutti, anche quelli che non hanno cambiato alcun numero. Un
errore che non cambia i risultati oggi può cambiarli domani, e sapere *come* è
stato trovato vale quanto sapere che è stato corretto.

Gli errori sono ordinati per gravità, non per data.

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
