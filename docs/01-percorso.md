# Il percorso

## Il mandato

Studiare l'omofilia nelle collaborazioni fra musicisti italiani su due assi —
il genere sessuale e il genere musicale prevalente — usando esclusivamente dati
locali. Cinque domande: la quota di donne per genere musicale e decennio;
se l'omofilia di genere vari col genere musicale; se le donne occupino posizioni
marginali («Smurfette»); la probabilità di collaborazione a parità di attività
e coorte; le differenze per ruolo nei crediti.

Vincoli fissati dall'inizio e mai violati: **sola lettura** sui database
sorgente, materiale nuovo solo sotto `analysis/`; idempotenza e checkpoint;
nessuna infrastruttura esterna; le fonti esterne irraggiungibili si degradano
documentandolo invece di bloccare.

Dopo la prima esplorazione il perimetro si è ristretto a **Discogs soltanto**,
su indicazione esplicita: iTunes è stato abbandonato.

## Le cinque fasi, e dove ciascuna si è complicata

### 1. Estrazione e popolazione

Il primo ostacolo è stato il vincolo di sola lettura: PostgreSQL con
`default_transaction_read_only = on` **vieta anche le tabelle temporanee**, che
sono il modo naturale di passare liste di identificativi fra query. L'estrazione
è stata riscritta senza creare alcun oggetto lato server, rimandando gli
elenchi come letterali `int[]`.

Il secondo è stato di prestazioni: il cluster gira su disco rotante ma è
configurato con `random_page_cost = 1.1`, che è un valore da SSD. Il
pianificatore sceglieva scansioni a indice e l'estrazione procedeva a 5 MB/s.
Risolto con GUC di sessione e una sola passata aggregata sequenziale.

L'italianità non è un campo dei dati: si inferisce dalla quota di pubblicazioni
con `country = 'Italy'`. È un'euristica, quindi è stata **validata** contro
`P27` (cittadinanza) di Wikidata su 4.663 artisti verificabili: **94,5%** di
cittadini italiani, con precisione che cresce monotonamente con la soglia
(95,7% a 0,60, 96,8% a 0,70, 97,4% a 0,80).

**Popolazione finale: 100.201 artisti.**

### 2. Il genere sessuale, che nessuna fonte contiene

Nessuno dei due database ha un campo di genere. L'inferenza è a cascata, e
l'ordine conta:

1. **Wikidata `P21`**, agganciato tramite `P1953` — l'identificativo Discogs —
   quindi per corrispondenza esatta, **mai per nome**;
2. **dizionari onomastici**, consultando il prior **italiano prima di quello
   globale**. Non è un dettaglio: Andrea, Simone, Nicola, Daniele, Michele e
   Gabriele sono nomi maschili in italiano e femminili nei dizionari a
   dominanza anglofona. L'ordine inverso avrebbe introdotto un errore
   sistematico e sbilanciato per genere;
3. **composizione dei gruppi** via `group_member`, che produce la categoria
   `mixed`.

Esito: **71,2% determinato** (60.671 M, 9.703 F, 997 misti, 28.830 ignoti), con
una quota femminile del **13,8%** fra i determinati — un rapporto di 6,25 a 1.

### 3. La rete, e il peso dei crediti

Su indicazione esplicita, i **crediti di traccia sono fondamentali** e devono
pesare di più; i crediti di release con tracce specificate sono paragonabili; i
crediti «a ombrello», senza traccia, devono pesare meno. Da qui la formula
di peso con tre livelli di specificità (traccia 1,0; release principale 0,7;
ombrello 0,3).

Il campo `release_artist.tracks` di Discogs è **testo libero** — `A1`,
`1 to 3`, `4, 6, 12` — e viene risolto sulle tracce reali; ciò che non si
analizza viene **degradato a ombrello, non forzato**.

**4.169.130 crediti**, di cui il 64,0% risolti a livello di traccia.
**Rete: 82.595 nodi con archi, 702.613 archi**, componente gigante al 95,7%.

### 4. Omofilia, e il primo risultato solido

L'assortatività di Newman sul genere musicale è **0,5865**; sul genere sessuale
**0,0511**. Un ordine di grandezza di differenza, ed è il risultato più robusto
dell'intero lavoro: chi fa musica in Italia si raggruppa per genere musicale,
non per sesso.

Per ruolo la differenza è netta: **creativo 0,0235 contro esecutivo 0,1175**,
un fattore cinque.

Sulla domanda Smurfette: **nessun effetto posizionale**. Zero interazioni
significative su dodici, e l'effetto principale femminile non è significativo su
nessuno dei tre assi (eigenvector +0,223 p=0,19; coreness +0,039 p=0,60;
betweenness −0,236 p=0,21).

### 5. L'ERGM, e i suoi quattro fallimenti

Qui il lavoro si è fermato a lungo. Il modello con termine di chiusura triadica
non converge sulla rete integrale, in nessuna delle parametrizzazioni provate.
Il verbale completo sta in [`05-ergm.md`](05-ergm.md); qui basta l'esito: **non
stimabile**, con una convergenza apparente smascherata dalla bontà di
adattamento.

## I tre punti in cui l'impostazione è cambiata

Il lavoro non è proceduto in linea retta. Tre interventi esterni lo hanno
riorientato, e ciascuno ha migliorato il risultato.

### Primo: «voglio la rete integrale, non sottoreti campionate»

La versione precedente dell'articolo dichiarava che la rete intera era fuori
portata e stimava su sottoreti estratte a valanga. L'obiezione era corretta e
metodologicamente decisiva: **di una stima su campione a valanga non si può
dire di che cosa sia stima**. Il campione non rappresenta nulla di definibile.

Ne sono seguiti il logit diadico e il QAP sulla rete integrale — metodi che
scalano per costruzione — e l'abbandono definitivo delle sottoreti.

### Secondo: «bisogna vedere come evolve nel tempo»

Ha prodotto il risultato centrale del lavoro. Datando ogni legame con **l'anno
della prima pubblicazione condivisa** invece che con l'accordo delle coorti di
debutto — definizione che scartava proprio le collaborazioni
intergenerazionali — è emersa una serie che nessuna misura aggregata mostrava.

### Terzo: «perché non calcoli sulla rete intera invece di stimare?»

L'obiezione più incisiva, e quella a cui non c'era una buona risposta. Molte
quantità erano state stimate per campionamento **pur essendo calcolabili
esattamente**: il logit su tre milioni di diadi invece che su tutte e
1.619.630.155; il QAP su mille permutazioni invece che sui momenti in forma
chiusa; la betweenness su 400 sorgenti invece che su tutte e 79.013.

Rimuoverle ha prodotto tre effetti, documentati in
[`04-calcolo-esatto.md`](04-calcolo-esatto.md) e [`03-errori.md`](03-errori.md):

* due approssimazioni su quattro **distorcevano i risultati sistematicamente**,
  sempre attenuando l'effetto;
* il confronto fra esatto e approssimato ha rivelato un **errore di segno**
  nella correzione caso-controllo, invisibile per altra via;
* il divario fra omofilia femminile e maschile è risultato **quasi doppio** di
  quanto sembrasse.

## Dove siamo

La tesi è cambiata. Non più «omofilia di minoranza» come stato stabile, ma
un'**inversione datata**: fino agli anni Settanta le musiciste italiane erano
collegate fra loro *meno* di quanto il caso prevedesse; dagli anni Novanta *più*;
negli anni Venti di questo secolo molto di più — mentre la loro quota **non
cresce**, anzi scende dal 15,5% al 9,6% prima di risalire appena.

A questa si è aggiunto un contributo metodologico che non era previsto: la
dimostrazione, misurata arco per arco, che su una rete ottenuta per proiezione
bipartita un termine di chiusura triadica misura in buona parte la dimensione
dei cast e non un processo sociale. Vale per qualunque rete di co-autorialità.

Resta da riscrivere l'articolo con questi risultati.
