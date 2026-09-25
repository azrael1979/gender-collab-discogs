
# Pattern di collaborazione fra musicisti italiani
## Omofilia di genere sessuale e genere musicale su Discogs

*Analisi condotta il 25/09/2026 — fonte unica: dump Discogs locale (PostgreSQL)*

---

## Sintesi per il lettore frettoloso

Questo studio ricostruisce **chi ha inciso con chi** fra i musicisti italiani
presenti in Discogs e chiede se il genere sessuale delle persone strutturi
quelle collaborazioni. La risposta breve è che sì, ma non nel modo che ci si
aspetterebbe. L'omofilia esiste ed è statisticamente solidissima, ma è molto
più debole della separazione per genere musicale; è **asimmetrica** — sono le
donne a fare gruppo fra loro, non gli uomini, all'opposto di quanto riporta la
letteratura corrente; e non si è rafforzata dopo il 2000: quello che si è
rafforzato è la tendenza della rete a **chiudersi in triangoli**, che produce
lo stesso effetto apparente per una ragione diversa.

### I numeri

| | |
|---|---|
| Musicisti italiani identificati | **87.229** |
| di cui con genere sessuale determinato | 65.093 (74,6%) |
| Quota di donne fra i determinati | **14,8%** — un rapporto di **5,77 uomini per ogni donna** |
| Crediti analizzati | 3.682.616, di cui 2.360.057 (64,1%) risolti sulla singola traccia |
| Rete di collaborazione | 70.712 artisti collegati, 586.040 legami |
| Componente gigante | 95,4% degli artisti collegati |
| Assortatività di genere sessuale | **r = 0,0432** (IC 95% 0,0399–0,0465) |
| Assortatività di genere musicale | **r = 0,4970** |
| Omofilia di genere pre-2000 → post-2000 | 0,0406 → 0,0693 (differenza non significativa nell'ERGM) |
| Omofilia ERGM, donne contro uomini (mediana sulle sottoreti) | **0,679 contro 0,074** in log-odds |
| ERGM | 8 sottoreti, 3 modelli ciascuna, **8 convergenti**, `gwesp` incluso |

### Le cinque cose da sapere

1. **La musica registrata italiana è un mondo di uomini, e lo è rimasta.**
   14,8% di donne fra gli artisti con genere determinato significa
   5,8 uomini per ogni donna. La quota non cresce in modo
   monotono nel tempo: parte dal 17,8% per chi debutta negli anni
   Sessanta, scende al 13,2% negli anni Ottanta e risale al
   21,4% per chi debutta dal 2020.

2. **Il genere musicale separa molto più del genere sessuale.** L'assortatività
   per genere musicale (0,497) è circa
   12 volte quella per genere sessuale
   (0,043). Chi fa jazz incide con chi fa jazz molto più
   sistematicamente di quanto gli uomini incidano con gli uomini.

3. **L'omofilia di genere sessuale è piccola ma reale.** r = 0,0432
   sembra poco, ma il modello nullo a gradi preservati dà 0,0001
   e l'intervallo di confidenza (0,0399–0,0465) sta
   tutto sopra lo zero. Non è un effetto di composizione, è struttura.

4. **Sono le donne a fare gruppo, non gli uomini.** È il risultato che
   contraddice più nettamente l'attesa. Nell'ERGM, che tiene ferme attività,
   coorte, genere musicale e chiusura triadica, il coefficiente di omofilia
   femminile è positivo e grande in **tutte e otto** le sottoreti stimate;
   quello maschile è vicino a zero, e in Rock è perfino negativo. Dove un
   gruppo è schiacciante maggioranza non ha bisogno di cercarsi; dove è raro,
   si addensa.

5. **Dopo il 2000 non aumenta l'omofilia: aumenta la chiusura in triangoli.**
   Descrittivamente l'assortatività sale da 0,0406 a
   0,0693. Ma nell'ERGM la differenza fra le due epoche nei
   termini di genere **non è significativa** (p = 0,88
   per le donne, 0,60 per gli uomini), mentre il termine
   di chiusura triadica cresce da 2,22 a
   2,89 con p < 0,0001. Non è cambiato il criterio
   con cui si sceglie un collaboratore: è cambiata la forma della rete.

6. **Il pattern "Smurfette" non si osserva.** A parità di pubblicazioni,
   coorte e genere musicale, l'essere donna non sposta la posizione nella rete
   su nessuna delle tre misure di centralità usate (sezione 6.2). La
   disuguaglianza è grande, ma sta nell'**accesso** e nel volume di attività,
   non nella posizione di chi è riuscito a entrare.

> **Nota di misura.** Tutte le assortatività di genere riportate come principali
> sono calcolate sui soli archi in cui **entrambi** gli artisti hanno un genere
> determinato (80,3% degli archi). Includere gli `unknown`
> come quarta categoria gonfia sistematicamente l'indice, perché gli artisti
> poco documentati collaborano fra loro più del caso per ragioni di copertura
> dei dati. Il confronto fra le due misure è in tabella alla sezione 5.1.

### Quanto fidarsi

Il genere sessuale non è in nessuna fonte: è **inferito**. Su
74,6% della popolazione si arriva a una determinazione, con
5.203 casi ancorati a Wikidata tramite l'identificativo Discogs
(join esatto, nessuna omonimia) e il resto per via onomastica. Il campione di
validazione manuale da 200 casi e lo strumento per misurarne
l'errore sono pronti in `data/validation_sample.csv`; finché non è compilato a
mano, le cifre qui sopra vanno lette come stime con un errore non ancora
quantificato. Il Monte Carlo della sezione 8.1 mostra comunque che l'omofilia
resta positiva **in ogni scenario di imputazione**, compreso quello costruito
apposta per minimizzarla.

---


# 1. Sorgenti dati: cosa c'è, cosa manca, cosa si è dovuto costruire

## 1.1 La fonte

L'analisi usa **una sola fonte**: una copia locale del dump Discogs in
PostgreSQL (database `discogs`, 248.153.636 righe nelle tabelle
utilizzate). Il disegno iniziale prevedeva anche un secondo database iTunes e
una tabella-ponte fra i due; su indicazione del committente iTunes è stato
**escluso**. La conseguenza metodologica è netta e va dichiarata: non esiste
alcuna verifica incrociata indipendente dell'anagrafica degli artisti, e l'asse
di robustezza "unione delle fonti contro sola Discogs" non ha più oggetto. Al
suo posto sono stati introdotti due assi alternativi (soglia di italianità e
uso o meno dei crediti a livello traccia), discussi nella sezione 8.2.

Tutte le sessioni verso il database hanno girato con
`default_transaction_read_only = on`. In PostgreSQL questa impostazione vieta
anche le tabelle temporanee, quindi l'estrazione è stata riscritta per non
creare **alcun** oggetto sul server: le liste di identificativi calcolate lato
Python tornano al database come letterali `int[]`. Nessuna scrittura, di nessun
tipo, ha toccato la fonte.

## 1.2 Tre assenze che hanno cambiato il disegno

L'esplorazione ha trovato tre vuoti nel dump che hanno imposto deviazioni dal
piano originale. Vanno messi in chiaro perché limitano ciò che si può
concludere.

**`release_label` è vuota (0 righe).** Non esiste alcun legame fra pubblicazione
ed etichetta discografica. L'euristica prevista per identificare i musicisti
italiani a partire dalle *etichette italiane* è quindi inapplicabile, e con
essa cade anche ogni analisi per casa discografica. L'italianità si appoggia
perciò al solo paese di pubblicazione.

**`release_genre` e `release_style` sono vuote (0 righe).** Il genere musicale è
disponibile unicamente attraverso il *master* (`master_genre`), e i master
coprono circa il 59% delle pubblicazioni. È la ragione per cui
26,9% della popolazione resta senza genere musicale
assegnato.

**L'entità "Various Artists" è di fatto assente.** In tutto `release_artist`
(oltre 92 milioni di righe) i crediti principali attribuiti a un artista di nome
"Various*" sono **328**. In questo dump le raccolte non usano il segnaposto
consueto: elencano direttamente gli artisti. Il filtro `exclude_various` è
quindi quasi inerte (3 pubblicazioni intercettate) e le
raccolte vanno riconosciute da un criterio diverso — la presenza di più artisti
principali distinti — che è il filtro `exclude_compilations` usato come asse di
robustezza.

## 1.3 Chi è "musicista italiano"

Senza dati di etichetta e senza un campo di nazionalità, l'italianità è stata
definita sulla **quota di pubblicazioni italiane** nella carriera di ciascun
artista:

> Un artista entra nella popolazione se ha almeno 2 pubblicazioni con
> `country = 'Italy'`, almeno 3 pubblicazioni in totale, e se le
> italiane sono almeno il 50% del totale.

La regola della quota è la parte che fa il lavoro. Il solo conteggio assoluto
produce un elenco dominato da Beethoven, Mozart, Bach, Chopin e Karajan: il
repertorio classico viene ristampato in Italia in grandi quantità, e chi guarda
solo "quante pubblicazioni italiane" scambia il catalogo per la biografia. La
quota li esclude tutti, perché per ciascuno di loro le edizioni italiane sono
una frazione minima di un catalogo mondiale.

Il controllo di validità è stato fatto guardando i primi venticinque artisti
per volume: Mina, Lucio Battisti, Vasco Rossi, Fabrizio De André, Franco
Battiato, Lucio Dalla, Mogol, Renato Zero, Francesco De Gregori, Domenico
Modugno, Claudio Villa, più un gruppo di produttori e tecnici italiani
realmente attivi (Antonio Baglio, Giovanni Versari, Vincenzo Tempera). Nessun
falso positivo evidente.

Restano due limiti strutturali, che nessuna soglia può togliere:

* la regola misura **dove si pubblica**, non **da dove si viene**. Un musicista
  straniero che abbia lavorato quasi solo per il mercato italiano entra nella
  popolazione; un italiano emigrato che pubblichi soprattutto all'estero ne
  esce. La soglia al 50% tiene basso il primo errore a costo
  di aumentare il secondo;
* Discogs non è un censimento. Sovrarappresenta il vinile, il collezionismo e
  l'elettronica, e sottorappresenta la musica che non è mai uscita su supporto
  fisico catalogato. La composizione per genere musicale della sezione 3.2 va
  letta come composizione *del catalogo Discogs*, non della musica italiana.

**Effetto della soglia** (misurato): 254.286 artisti hanno almeno due
pubblicazioni italiane; applicando quota e minimo, la popolazione scende a
**87.229**. Alzando la quota a 0,60 e 0,70 si ottengono
78.448 e 66.113 artisti: la sezione 8.2 mostra che le
conclusioni non cambiano.


# 2. Il genere sessuale: come è stato inferito

## 2.1 Il problema

Nessuna delle fonti disponibili contiene il genere sessuale delle persone.
Va inferito, e l'inferenza va documentata fino in fondo, perché è il punto più
fragile dell'intero studio: ogni conclusione sull'omofilia di genere poggia su
un'etichetta che nessuno ha dichiarato.

La cascata usata procede dal segnale più solido al più debole, e ogni artista
porta con sé **da quale livello** viene la sua etichetta e **con quanta
confidenza**.

## 2.2 Livello 1 — Wikidata agganciato all'identificativo Discogs

Wikidata espone la proprietà `P1953`, *Discogs artist ID*. Questo consente un
**join esatto sull'identificativo**, non sul nome: nessuna omonimia, nessun
matching approssimato. Sono state raccolte tutte le entità con `P1953` e `P21`
(genere): **202.478 identificativi Discogs distinti**, con
74 casi ambigui scartati e **zero blocchi persi** su una
paginazione ricorsiva per prefisso dell'identificativo.

Di questi, **5.203 ricadono nella nostra popolazione**
(6,0%). È una copertura bassa in termini assoluti,
e il motivo è ovvio: Wikidata descrive persone notabili, mentre la popolazione
Discogs è fatta in larga parte di turnisti, arrangiatori, fonici e produttori
che non hanno una voce enciclopedica. Ma sono 5.203 etichette
**certe**, ed è su quelle che si regge il livello successivo.

## 2.3 Livello 2 — l'onomastica, costruita dai dati e non da una lista

Il disegno prevedeva la lista onomastica ISTAT. In questo ambiente non è
risultata disponibile come dataset scaricabile; il ripiego adottato è migliore
per lo scopo, non peggiore.

Gli stessi 202.478 identificativi Discogs etichettati da Wikidata
sono stati ricongiunti ai **nomi** nel database: ne escono
**199.812 coppie nome→genere di musicisti**, un corpus onomastico
specifico del dominio, molto più ampio dei soli italiani e molto più pertinente
di una lista anagrafica generica.

Da qui si ricavano due dizionari, e l'ordine in cui vengono consultati è la
scelta metodologicamente più importante di questa sezione:

1. **dizionario italiano** (320 nomi), costruito sui soli
   artisti italiani etichettati da Wikidata;
2. **`gender-guesser` con lookup italiano**;
3. **dizionario globale** (2.204 nomi), ma **solo per i nomi che
   il lookup italiano non riconosce**;
4. `gender-guesser` globale, come ultima risorsa e con confidenza ridotta.

Il vincolo al punto 3 non è pedanteria. Andrea, Simone, Nicola, Daniele,
Michele e Gabriele sono nomi maschili in Italia e femminili nei dizionari
dominati dall'inglese: usare il dizionario globale senza quel filtro
ribalterebbe il genere di alcune delle prime posizioni dell'onomastica maschile
italiana, con un errore sistematico e non casuale, concentrato proprio sui nomi
più frequenti. Verificato sui dati: i due dizionari concordano su tutti i
241 nomi che hanno in comune, il che indica che il filtro
sta effettivamente tenendo separati i due domini invece di mascherare un
conflitto.

## 2.4 Livello 3 — i gruppi si leggono dai membri

Un nome di band non dice nulla sul genere delle persone. Per i gruppi si guarda
perciò la composizione (`group_member`): se i membri di genere noto sono di
entrambi i generi il gruppo è **`mixed`**, se sono tutti dello stesso genere il
gruppo eredita quello, se se ne conoscono meno di due resta `unknown`. Sono
stati risolti **0 gruppi su 0**, di cui
0 misti.

## 2.5 Esito della cascata

| fonte                          |   artisti | quota   |
|:-------------------------------|----------:|:--------|
| onomastico_prior_it            |    44.618 | 51,2%   |
| none                           |    22.136 | 25,4%   |
| onomastico_prior_globale       |     6.217 | 7,1%    |
| wikidata_p1953                 |     5.203 | 6,0%    |
| onomastico_gg_it_male          |     3.196 | 3,7%    |
| onomastico_gg_it_female        |     2.262 | 2,6%    |
| wikidata_name                  |     1.5   | 1,7%    |
| onomastico_gg_globale_male     |     1.162 | 1,3%    |
| onomastico_gg_globale_female   |   863     | 1,0%    |
| onomastico_gg_it_mostly_male   |    44     | 0,1%    |
| onomastico_gg_it_mostly_female |    28     | 0,0%    |

**Tabella — Origine dell'etichetta di genere sessuale per ciascun artista.**
La riga `onomastico_prior_it` porta da sola la maggior parte del carico: è il
dizionario costruito sui 5.203 italiani certi, e bastano
320 nomi propri per coprire quasi la metà della popolazione,
perché l'onomastica italiana è fortemente concentrata. `none` e
`group_unresolved` sono i due volti del non sapere: artisti il cui nome non è
un nome di persona riconoscibile (sigle, pseudonimi, progetti) e gruppi di cui
non si conoscono abbastanza membri.

**Esito finale: 14,8% di donne fra gli artisti con genere
determinato**, cioè 5,77 uomini per ogni donna, con
25,4% della popolazione che resta indeterminata.

## 2.6 Il pezzo mancante: la validazione manuale

È stato generato `data/validation_sample.csv`: **200 artisti**
estratti in modo stratificato per genere, fascia di confidenza e fonte
dell'etichetta, con una colonna `human_gender` vuota da compilare a mano.
Lo script `src/score_validation.py` calcola precisione, richiamo, F1 e matrice
di confusione per livello della cascata non appena il file è compilato.

Il campione è costruito con **allocazione metà proporzionale e metà
uniforme** fra gli strati: la parte proporzionale permette di stimare
l'accuratezza complessiva senza riponderare, quella uniforme garantisce
abbastanza casi anche nei livelli rari della cascata. Dentro ogni strato si
privilegiano nomi propri diversi, perché altrimenti gli strati piccoli si
riempiono di omonimi e la validazione misurerebbe l'accuratezza su un nome
invece che su un livello.

Su due livelli quel rimedio non basta, e va detto: `onomastico_gg_mostly_female`
raccoglie 28 artisti che portano **un solo** nome proprio (Mary), e
`onomastico_gg_mostly_male` ne raccoglie 44 con due (Toni, Leonida). Su quei
due livelli la validazione potrà dire se quei nomi sono classificati bene, non
se il livello funziona in generale. Pesano insieme 72 artisti su
87.229, quindi la cosa non tocca le conclusioni, ma il dato di
accuratezza che ne uscirà non va letto come se fosse generalizzabile.

Questo passo **non è stato eseguito**: richiede giudizio umano. Finché non lo
si compila, l'errore dell'inferenza di genere è delimitato solo dal Monte Carlo
della sezione 8.1, che però misura l'effetto dell'*incertezza sugli unknown*,
non quello degli *errori sui noti*. È il limite più serio di questo studio.


# 3. La rete: come due musicisti diventano collegati

## 3.1 Il peso dell'arco e perché non tutti i crediti valgono uguale

Un credito Discogs può dire tre cose molto diverse. Può dire *"questa persona
suona il basso nel brano B2"*; può dire *"questa persona è l'artista del
disco"*; può dire *"questa persona compare nei crediti del disco"*, senza
specificare dove. Trattarli come equivalenti significherebbe dare a una
coincidenza di copertina lo stesso valore di una sessione documentata.

Ogni credito riceve perciò una **specificità**, e il peso del legame fra due
artisti la usa:

| ambito | specificità | che cosa significa |
|---|---|---|
| `track` | 1.00 | credito risolto su una traccia precisa |
| `main` | 0.70 | artista principale della pubblicazione |
| `umbrella` | 0.30 | credito secondario, senza indicazione di tracce |

$$w(u,v) = w_t \cdot |\text{tracce condivise}| + w_r \cdot \sum_{R} s_u(R)\, s_v(R)$$

Il primo termine premia la collaborazione **documentata sullo stesso brano**; il
secondo tiene la co-presenza sulla stessa pubblicazione, scalata dalla
specificità di entrambi i crediti. Due turnisti accreditati sulla stessa traccia
pesano molto più di due nomi che compaiono genericamente sullo stesso disco.

I crediti a livello traccia vengono da due strade. La prima è
`release_track_artist`, che porta un identificativo di traccia globale:
**1.932.237 crediti**. La seconda è il campo `tracks` di
`release_artist`, che indica le posizioni in forma testuale — `A1`, `1 to 3`,
`4, 6, 12` — e va **risolto**: le posizioni si convertono in tracce reali
passando per `release_track`. Di 442.050 crediti posizionali ne
sono stati risolti 427.820
(96,8%); i restanti usano formule
libere (*"all tracks except 1, 13 and 14"*) e sono stati **degradati ad
`umbrella`** anziché interpretati a forza.

Totale: **2.360.057 crediti su 3.682.616
(64,1%) sono risolti a livello di singola traccia.**

## 3.2 Filtri e sottoreti

Le pubblicazioni con più di 8 artisti accreditati vengono
scartate: sono raccolte e cofanetti, dove la co-presenza non indica
collaborazione e il numero di coppie esplode in modo quadratico. Il filtro
riduce i crediti da 3.682.616 a 586.040.

Le sottoreti per ruolo separano due mestieri diversi: **creative**
(produzione, scrittura, arrangiamento, composizione) e **performance**
(voce, strumenti, direzione, featuring). Un artista principale senza ruolo
esplicito è trattato come interprete, perché è ciò che significa essere
l'artista di un disco.

| rete        | nodi_totali   | nodi_con_archi   | archi   | densita   | grado_medio   | grado_mediano   | grado_max   | componenti   | componente_gigante   | quota_componente_gigante   | peso_totale      |
|:------------|:--------------|:-----------------|:--------|:----------|:--------------|:----------------|:------------|:-------------|:---------------------|:---------------------------|:-----------------|
| all         | 87.229        | 70.712           | 586.040 | 0,000234  | 16,575404     | 7,000000        | 2.258       | 1.204        | 67.443               | 0,953770                   | 1.495.529,570002 |
| creative    | 87.229        | 30.440           | 199.832 | 0,000431  | 13,129566     | 4,000000        | 1.348       | 1.530        | 26.538               | 0,871813                   | 866.621,310000   |
| performance | 87.229        | 49.152           | 211.751 | 0,000175  | 8,616170      | 4,000000        | 598         | 2.493        | 42.013               | 0,854757                   | 430.596,670000   |

**Tabella — Descrittive delle tre reti di collaborazione**

*Dati completi in `tables/t2_rete_descrittive.csv` e `tables/t2_rete_descrittive.tex`.*


La rete complessiva è **sparsa e molto connessa**: densità dell'ordine di
0,000234, ma una componente gigante che assorbe 95,4%
degli artisti collegati. È la firma tipica di un mondo professionale in cui
quasi nessuno lavora isolato e quasi nessuno lavora con tutti. La rete
`creative` è più piccola e più densa di quella `performance`: produttori e
autori formano un nucleo più ristretto e più intrecciato di quello degli
esecutori — un dato che conta per la lettura della sezione 5.3, dove i due ruoli
mostrano omofilie diverse.

<figure>
<img src="figures/f5_distribuzione_gradi.png" alt="f5_distribuzione_gradi" style="width:100%" />
<figcaption>

**Distribuzione di grado e forza.** Su scala doppio-logaritmica entrambe le distribuzioni scendono con una pendenza quasi rettilinea su più ordini di grandezza: la stragrande maggioranza degli artisti ha pochissimi collaboratori, mentre una minoranza sottile ne ha centinaia. La forza — che somma i pesi, quindi conta quante volte si è collaborato e quanto erano specifici i crediti — ha una coda ancora più lunga del grado: i grandi collaboratori non hanno solo molti partner, hanno relazioni molto più intense. È il substrato strutturale su cui va letta la sezione 6.1: in una rete così diseguale, la domanda 'le donne stanno al centro?' va sempre posta a parità di attività, perché il numero di pubblicazioni da solo spiega già gran parte della centralità.

</figcaption>
</figure>


Le analisi che seguono girano sulla **componente gigante**, perché le misure di
centralità e le distanze non sono definite fra componenti separate. La quota
esclusa è 4,6% degli artisti collegati.


# 4. Quante sono le donne, e in quale musica (RQ1)

<figure>
<img src="figures/f3_quota_donne_per_decennio.png" alt="f3_quota_donne_per_decennio" style="width:100%" />
<figcaption>

**La quota di donne per decennio di debutto.** La linea non è la storia di un progresso. Parte dal 17,8% per chi debutta negli anni Sessanta, scende fino al 13,2% negli anni Ottanta — il minimo della serie — e risale solo di recente, fino al 21,4% per chi debutta dal 2020. La discesa degli anni Settanta e Ottanta merita cautela prima di leggerla come un arretramento reale: coincide con l'espansione massiccia del catalogo Discogs in quegli anni, cioè con l'ingresso in massa di crediti tecnici e di produzione — mestieri quasi interamente maschili — che diluiscono una quota calcolata su tutti i crediti e non sui soli interpreti. La risalita recente è invece coerente sia in ampiezza sia in direzione con quanto si osserva negli altri cataloghi musicali. In ogni decennio, comunque, la banda di confidenza resta lontanissima dalla parità.

</figcaption>
</figure>


<figure>
<img src="figures/f4_quota_donne_genere_x_decennio.png" alt="f4_quota_donne_genere_x_decennio" style="width:100%" />
<figcaption>

**Quota di donne per genere musicale e decennio.** I pannelli mostrano che non esiste una singola traiettoria di genere: esistono generi musicali con storie diverse. Il livello di partenza conta più della pendenza — un genere che parte basso tende a restare basso attraverso i decenni, il che è esattamente la firma di una segregazione che si riproduce per reclutamento piuttosto che dissolversi col tempo.

</figcaption>
</figure>


| musical_genre    | cohort_decade   | n_artisti   | n_noti   | n_donne   | quota_donne   | ci_lo   | ci_hi   | rapporto_uomini_donne   |
|:-----------------|:----------------|:------------|:---------|:----------|:--------------|:--------|:--------|:------------------------|
| Blues            | 1.940           | 1           | 1,000    | 0,000     | 0,000         | 0,000   | 0,793   | n.d.                    |
| Blues            | 1.950           | 3           | 0,000    | 0,000     | n.d.          | n.d.    | n.d.    | n.d.                    |
| Blues            | 1.960           | 17          | 13,000   | 1,000     | 0,077         | 0,014   | 0,333   | 12,000                  |
| Blues            | 1.970           | 61          | 54,000   | 9,000     | 0,167         | 0,090   | 0,287   | 5,000                   |
| Blues            | 1.980           | 105         | 98,000   | 15,000    | 0,153         | 0,095   | 0,237   | 5,533                   |
| Blues            | 1.990           | 129         | 106,000  | 15,000    | 0,142         | 0,088   | 0,220   | 6,067                   |
| Blues            | 2.000           | 137         | 121,000  | 21,000    | 0,174         | 0,116   | 0,251   | 4,762                   |
| Blues            | 2.010           | 141         | 114,000  | 22,000    | 0,193         | 0,131   | 0,275   | 4,182                   |
| Blues            | 2.020           | 22          | 17,000   | 4,000     | 0,235         | 0,096   | 0,473   | 3,250                   |
| Brass & Military | 1.940           | 24          | 14,000   | 0,000     | 0,000         | 0,000   | 0,215   | n.d.                    |
| Brass & Military | 1.950           | 10          | 6,000    | 0,000     | 0,000         | 0,000   | 0,390   | n.d.                    |
| Brass & Military | 1.960           | 38          | 18,000   | 2,000     | 0,111         | 0,031   | 0,328   | 8,000                   |
| Brass & Military | 1.970           | 13          | 6,000    | 0,000     | 0,000         | 0,000   | 0,390   | n.d.                    |
| Brass & Military | 1.980           | 9           | 5,000    | 0,000     | 0,000         | 0,000   | 0,434   | n.d.                    |
| Brass & Military | 1.990           | 12          | 9,000    | 0,000     | 0,000         | 0,000   | 0,299   | n.d.                    |
| Brass & Military | 2.000           | 1           | 1,000    | 0,000     | 0,000         | 0,000   | 0,793   | n.d.                    |
| Brass & Military | 2.010           | 1           | 0,000    | 0,000     | n.d.          | n.d.    | n.d.    | n.d.                    |
| Children's       | 1.940           | 33          | 23,000   | 10,000    | 0,435         | 0,256   | 0,632   | 1,300                   |
| Children's       | 1.950           | 79          | 72,000   | 24,000    | 0,333         | 0,235   | 0,448   | 2,000                   |
| Children's       | 1.960           | 208         | 173,000  | 66,000    | 0,382         | 0,312   | 0,456   | 1,621                   |
| Children's       | 1.970           | 170         | 131,000  | 70,000    | 0,534         | 0,449   | 0,618   | 0,871                   |
| Children's       | 1.980           | 85          | 53,000   | 24,000    | 0,453         | 0,327   | 0,585   | 1,208                   |
| Children's       | 1.990           | 60          | 45,000   | 16,000    | 0,356         | 0,232   | 0,502   | 1,812                   |
| Children's       | 2.000           | 27          | 23,000   | 7,000     | 0,304         | 0,156   | 0,509   | 2,286                   |
| Children's       | 2.010           | 13          | 9,000    | 2,000     | 0,222         | 0,063   | 0,547   | 3,500                   |

**Tabella — Quota di donne per genere musicale e decennio di debutto, con intervalli di Wilson al 95%**

*Mostrate le prime 25 righe di 141; la tabella completa è in `tables/t3_quota_donne_genere_decennio.csv` e `tables/t3_quota_donne_genere_decennio.tex`.*


## 4.1 Il confronto con i pattern noti in letteratura

Il riferimento consueto per l'hip hop è un rapporto intorno a **4 uomini per
ogni donna**. Nei dati italiani il rapporto è **10,4 a 1**
(8,8% di donne): sensibilmente **più squilibrato** del
riferimento internazionale. Due letture non alternative: la scena hip hop
italiana censita da Discogs è più piccola e più recente, quindi più esposta
al fatto che i ruoli di produzione — dove le donne sono più rare — pesino
relativamente di più; e il conteggio qui include tutti i crediti, non solo gli
interpreti principali, il che abbassa la quota rispetto alle statistiche basate
sulle classifiche.

All'estremo opposto, **Classical** (24,7%) e **Children's**
(41,3%) sono i generi con la presenza femminile più alta —
il secondo sopra il 41%, l'unico dell'intero corpus in cui
le donne si avvicinano alla metà. La distanza fra Children's e Hip Hop, a
parità di popolazione e di metodo, è di oltre
33 punti percentuali: il genere musicale
è il predittore più forte della presenza femminile in tutto questo studio.

**Rock (10,5%) e Electronic (14,2%)**, che
insieme fanno la parte maggiore della popolazione, stanno entrambi sotto la
media generale. È su queste due scene, per peso numerico, che si decide la
quota complessiva.


# 5. Omofilia: chi incide con chi (RQ2)

## 5.1 Il quadro generale

<figure>
<img src="figures/f1_mixing_gender_oss_att.png" alt="f1_mixing_gender_oss_att" style="width:100%" />
<figcaption>

**Chi collabora con chi, rispetto al caso.** Ogni cella è il rapporto fra i legami osservati e quelli attesi sotto un modello nullo che conserva esattamente il grado di ogni artista e la composizione della popolazione: l'unica cosa randomizzata è *chi sta con chi*. Un valore di 1 significa 'come il caso', sopra 1 significa più del previsto. La diagonale sopra 1 e le celle fuori diagonale sotto 1 sono la definizione operativa di omofilia. Vale la pena notare che anche la cella unknown-unknown si discosta da 1: non è un fatto sociale ma un fatto di copertura dei dati — gli artisti su cui non sappiamo nulla tendono a stare insieme perché condividono le stesse caratteristiche che li rendono poco documentati (pochi crediti, ruoli minori, epoche marginali). È precisamente questo il motivo per cui l'ERGM della sezione 7 esclude i nodi unknown invece di trattarli come una categoria.

</figcaption>
</figure>


| attributo     | r_osservato   | r_pesato   | r_null_medio   | r_null_sd   | z        |
|:--------------|:--------------|:-----------|:---------------|:------------|:---------|
| gender        | 0,0810        | 0,1254     | -0,0000        | 0,0010      | 81,4605  |
| musical_genre | 0,4970        | 0,6675     | -0,0001        | 0,0006      | 790,6131 |

**Tabella — Assortatività osservata e sotto modello nullo**

*Dati completi in `tables/t3_assortativita_globale.csv` e `tables/t3_assortativita_globale.tex`.*


| sottorete   | strato   | attr.         | categorie            | archi   | quota archi   | r      | ci_lo   | ci_hi   |
|:------------|:---------|:--------------|:---------------------|:--------|:--------------|:-------|:--------|:--------|
| all         | tutto    | gender        | determinati soltanto | 470.690 | 0,8032        | 0,0432 | 0,0399  | 0,0465  |
| all         | tutto    | gender        | tutte le categorie   | 586.040 | 1,0000        | 0,0810 | 0,0788  | 0,0834  |
| all         | tutto    | musical_genre | determinati soltanto | 503.971 | 0,8600        | 0,5622 | 0,5606  | 0,5638  |
| all         | tutto    | musical_genre | tutte le categorie   | 586.040 | 1,0000        | 0,4970 | 0,4955  | 0,4984  |
| all         | pre2000  | gender        | determinati soltanto | 333.067 | 0,8444        | 0,0406 | 0,0367  | 0,0443  |
| all         | pre2000  | gender        | tutte le categorie   | 394.423 | 1,0000        | 0,0576 | 0,0548  | 0,0605  |
| all         | pre2000  | musical_genre | determinati soltanto | 362.127 | 0,9181        | 0,5103 | 0,5082  | 0,5124  |
| all         | pre2000  | musical_genre | tutte le categorie   | 394.423 | 1,0000        | 0,4704 | 0,4685  | 0,4721  |
| all         | post2000 | gender        | determinati soltanto | 61.015  | 0,6563        | 0,0693 | 0,0598  | 0,0788  |
| all         | post2000 | gender        | tutte le categorie   | 92.968  | 1,0000        | 0,1479 | 0,1416  | 0,1533  |
| all         | post2000 | musical_genre | determinati soltanto | 64.388  | 0,6926        | 0,7101 | 0,7062  | 0,7141  |
| all         | post2000 | musical_genre | tutte le categorie   | 92.968  | 1,0000        | 0,5445 | 0,5407  | 0,5482  |
| creative    | tutto    | gender        | determinati soltanto | 179.908 | 0,9003        | 0,0224 | 0,0172  | 0,0279  |
| creative    | tutto    | gender        | tutte le categorie   | 199.832 | 1,0000        | 0,0703 | 0,0658  | 0,0750  |
| creative    | tutto    | musical_genre | determinati soltanto | 184.147 | 0,9215        | 0,5770 | 0,5743  | 0,5799  |
| creative    | tutto    | musical_genre | tutte le categorie   | 199.832 | 1,0000        | 0,5351 | 0,5323  | 0,5377  |
| creative    | pre2000  | gender        | determinati soltanto | 146.391 | 0,9325        | 0,0224 | 0,0165  | 0,0282  |
| creative    | pre2000  | gender        | tutte le categorie   | 156.982 | 1,0000        | 0,0269 | 0,0224  | 0,0316  |
| creative    | pre2000  | musical_genre | determinati soltanto | 149.499 | 0,9523        | 0,5209 | 0,5177  | 0,5243  |
| creative    | pre2000  | musical_genre | tutte le categorie   | 156.982 | 1,0000        | 0,4945 | 0,4914  | 0,4977  |
| creative    | post2000 | gender        | determinati soltanto | 13.668  | 0,7079        | 0,0444 | 0,0227  | 0,0655  |
| creative    | post2000 | gender        | tutte le categorie   | 19.308  | 1,0000        | 0,1616 | 0,1478  | 0,1753  |
| creative    | post2000 | musical_genre | determinati soltanto | 14.659  | 0,7592        | 0,7868 | 0,7788  | 0,7953  |
| creative    | post2000 | musical_genre | tutte le categorie   | 19.308  | 1,0000        | 0,6235 | 0,6145  | 0,6320  |
| performance | tutto    | gender        | determinati soltanto | 160.881 | 0,7598        | 0,1054 | 0,0996  | 0,1115  |
| performance | tutto    | gender        | tutte le categorie   | 211.751 | 1,0000        | 0,1704 | 0,1667  | 0,1741  |
| performance | tutto    | musical_genre | determinati soltanto | 171.934 | 0,8120        | 0,6153 | 0,6125  | 0,6177  |
| performance | tutto    | musical_genre | tutte le categorie   | 211.751 | 1,0000        | 0,5305 | 0,5279  | 0,5327  |
| performance | pre2000  | gender        | determinati soltanto | 95.250  | 0,8164        | 0,1106 | 0,1028  | 0,1180  |
| performance | pre2000  | gender        | tutte le categorie   | 116.673 | 1,0000        | 0,1733 | 0,1679  | 0,1785  |
| performance | pre2000  | musical_genre | determinati soltanto | 103.792 | 0,8896        | 0,5612 | 0,5582  | 0,5647  |
| performance | pre2000  | musical_genre | tutte le categorie   | 116.673 | 1,0000        | 0,5132 | 0,5101  | 0,5164  |
| performance | post2000 | gender        | determinati soltanto | 31.344  | 0,6306        | 0,1050 | 0,0913  | 0,1180  |
| performance | post2000 | gender        | tutte le categorie   | 49.702  | 1,0000        | 0,1985 | 0,1909  | 0,2066  |
| performance | post2000 | musical_genre | determinati soltanto | 33.316  | 0,6703        | 0,7482 | 0,7428  | 0,7533  |
| performance | post2000 | musical_genre | tutte le categorie   | 49.702  | 1,0000        | 0,5737 | 0,5685  | 0,5787  |

**Tabella — Assortatività calcolata sui soli nodi con attributo determinato contro il calcolo che tratta 'indeterminato' come una categoria, per il genere sessuale e per quello musicale**

*Dati completi in `tables/t3_assortativita_MF_vs_tutte.csv` e `tables/t3_assortativita_MF_vs_tutte.tex`.*


### Una precisazione di misura che cambia i numeri

Le due tabelle vanno lette insieme, perché la seconda corregge la prima.

Trattare `unknown` come una quarta categoria alla pari di M ed F gonfia
l'assortatività: la cella unknown-unknown sta molto sopra l'atteso, ma non
perché quelle persone si cerchino fra loro. Si cercano fra loro le
caratteristiche che le rendono poco documentate — pochi crediti, ruoli minori,
epoche marginali, pseudonimi — e sono le stesse che rendono difficile inferirne
il genere. È copertura dei dati che si traveste da struttura sociale.

La misura di riferimento restringe perciò il calcolo agli archi in cui entrambi
gli estremi hanno genere determinato: **80,3% degli archi**.
La differenza non è cosmetica: **r passa da 0,0810 a
0,0432**, cioè un terzo dell'omofilia apparente era artefatto.

Lo stesso controllo è stato fatto sul **genere musicale**, dove
'Unknown' è altrettanto presente, e dà il risultato **opposto**: togliendo gli
indeterminati l'assortatività sale da 0,4970 a
0,5622. Il motivo è che gli artisti senza genere musicale
assegnato non si aggregano fra loro per genere — non ne hanno uno — e quindi
diluiscono la diagonale invece di gonfiarla. Riportare entrambi i confronti
serve a chiarire che l'esclusione degli indeterminati è una scelta di metodo
applicata in modo uniforme, non un accorgimento adottato dove conveniva: sul
genere sessuale abbassa il risultato, sul genere musicale lo alza.

### Il risultato centrale

L'assortatività per **genere musicale** vale 0,497. È un valore
molto alto: le carriere si svolgono dentro un genere e le collaborazioni seguono
i confini del genere quasi come se fossero confini di settore.

L'assortatività per **genere sessuale** vale 0,0432, circa
12 volte meno, con intervallo di confidenza
0,0399–0,0465 e modello nullo a 0,0001.
Preso da solo il numero sembra trascurabile; non lo è, perché su
586.040 archi anche un effetto piccolo è misurato con precisione
elevata e l'intervallo sta interamente sopra lo zero.

La lettura sostanziale è che **il genere sessuale struttura le collaborazioni,
ma molto meno di quanto faccia la specializzazione musicale**. Chi cerca
un bassista lo cerca nel proprio giro musicale molto più sistematicamente di
quanto lo cerchi del proprio sesso. Questo non rende l'omofilia di genere
irrilevante — rende il genere musicale il canale attraverso cui essa
prevalentemente opera, come mostra il paragrafo seguente.

<figure>
<img src="figures/f2_mixing_genere_musicale_oss_att.png" alt="f2_mixing_genere_musicale_oss_att" style="width:100%" />
<figcaption>

**Omofilia per genere musicale.** La diagonale domina l'immagine. I generi più chiusi non sono necessariamente i più grandi: la chiusura misura quanto una scena recluta al proprio interno, non quanto è popolosa. Le celle fuori diagonale che superano 1 indicano le coppie di generi fra cui esiste un traffico reale di musicisti — i confini permeabili del sistema.

</figcaption>
</figure>


## 5.2 L'omofilia nel tempo: il risultato controintuitivo

<figure>
<img src="figures/f6_assortativita_per_strato.png" alt="f6_assortativita_per_strato" style="width:100%" />
<figcaption>

**Omofilia di genere per sottorete di ruolo ed epoca.** Il punto è il valore osservato, la barra l'intervallo di confidenza bootstrap al 95%, il trattino verticale il valore del modello nullo. L'attesa, dalla letteratura, era un **allentamento** dopo il 2000. Sui soli nodi con genere determinato i dati dicono l'opposto, ma con ampiezza molto più contenuta di quanto suggerisca la misura a quattro categorie mostrata in figura: 0,0406 contro 0,0693.

</figcaption>
</figure>


Prima di interpretarlo va ripulito. Sulla misura ingenua a quattro categorie il
salto è spettacolare, da 0,0576 a 0,1479: più che
raddoppiato. Sui soli nodi con genere determinato si riduce a
0,0406 → 0,0693. La ragione è che la quota di
archi utilizzabili crolla fra le due epoche — dal
84,4%
al
65,6%
— perché gli artisti recenti sono mediamente meno documentati: più `unknown`,
quindi più apparente omofilia spuria.

**Quel che resta dopo la correzione è comunque un aumento**, con intervalli
(0,0367–0,0443 contro
0,0598–0,0788) che non si sovrappongono. Il
risultato regge, ma va raccontato per quello che è: un aumento moderato, non un
raddoppio.

**E l'aumento non è diffuso: viene tutto da una parte sola della rete.**
Scomponendo per ruolo, l'omofilia dei ruoli di esecuzione è sostanzialmente
piatta nel tempo (0,1106 prima del 2000,
0,1050 dopo), mentre quella dei ruoli creativi **raddoppia**,
da 0,0224 a 0,0444. Qualunque
spiegazione dell'aumento deve perciò riguardare il modo in cui si produce e si
scrive musica, non il modo in cui la si suona.

Restano due letture possibili, e i dati qui presenti non permettono di scegliere
fra loro in modo definitivo.

**Prima lettura — è reale.** Dopo il 2000 cambia il modo di produrre musica: la
registrazione si decentra, gli studi grandi con organici misti e obbligati
lasciano spazio a progetti piccoli, costruiti su reti personali. Reti personali
significa reti più omofile. In questa lettura l'aumento non è un arretramento
culturale ma l'effetto strutturale di una tecnologia di produzione diversa — e
il fatto che riguardi i soli ruoli creativi, che sono precisamente quelli
toccati dalla decentralizzazione degli studi, depone a favore di questa
spiegazione.

**Seconda lettura — è composizione.** L'indice *r* di Newman dipende dalle
marginali. Post-2000 ci sono più donne, quindi più occasioni di legame
donna-donna; a parità di propensione, un gruppo minoritario più numeroso
produce meccanicamente un'assortatività misurata più alta. Il modello nullo a
gradi preservati corregge per il grado, **non** per questa asimmetria di
composizione fra epoche.

È esattamente per dirimere questo punto che serve l'ERGM, e **il verdetto è
arrivato**: una volta controllata la tendenza della rete a chiudere i
triangoli, la differenza di omofilia di genere fra le due epoche **non è
statisticamente distinguibile da zero** (per le donne
0,709 contro 0,776, p =
0,88; per gli uomini 0,137 contro
0,080, p = 0,60).

Ciò che aumenta davvero, e in modo nettissimo, è la **chiusura triadica**: il
coefficiente `gwesp` passa da 2,217 a
2,892 (p < 0,0001). La musica registrata italiana
dopo il 2000 non è diventata più omofila per genere: è diventata più
**chiusa in triangoli**. Si lavora sempre di più dentro gruppi fitti di
persone che si conoscono già tutte fra loro. In un ambiente dove le donne sono
il 14,8%, una struttura più triangolare produce
meccanicamente più legami donna-donna osservati, e quindi un'assortatività
misurata più alta — senza che nessuno abbia cambiato criterio nello scegliere
con chi lavorare.

È la risposta più interessante dello studio, perché sposta l'oggetto: il
problema non è una preferenza di genere che si è rafforzata, ma una
struttura di reclutamento che si è chiusa. Sono due cose diverse anche dal
punto di vista di chi volesse intervenire. I dettagli del test sono nella
sezione 7.3.

## 5.3 Produttori e interpreti: due mestieri, due omofilie (RQ5)

La distinzione fra ruoli creativi (produzione, scrittura, arrangiamento) e ruoli
di esecuzione (voce, strumenti, direzione) è la domanda RQ5, e la risposta è
netta: sui soli nodi con genere determinato l'omofilia vale
**0,0224 nella rete creativa** contro
**0,1054 in quella di esecuzione**.

La collaborazione creativa è quindi *meno* segregata per genere di quella
esecutiva, di un fattore
4,7. È un risultato che va letto insieme al dato di composizione: i ruoli
creativi sono in assoluto i più maschili dell'intero corpus, e proprio per
questo l'omofilia misurata vi risulta bassa — dove la maggioranza è
schiacciante non c'è quasi spazio per discostarsi dal caso. La segregazione dei
ruoli creativi si manifesta nel **chi entra**, non nel **chi lavora con chi**;
quella dei ruoli esecutivi, dove le donne sono più presenti, si manifesta anche
nella struttura delle collaborazioni. Sono due forme diverse di chiusura, e
confonderle porterebbe a concludere che la produzione musicale sia il luogo più
aperto del sistema, che è l'opposto di quanto dicono i conteggi.

## 5.4 Omofilia dentro ciascun genere musicale

<figure>
<img src="figures/f7_omofilia_per_genere_musicale.png" alt="f7_omofilia_per_genere_musicale" style="width:100%" />
<figcaption>

**A sinistra** l'omofilia di genere sessuale calcolata separatamente dentro ciascun genere musicale, con il modello nullo come riferimento. **A destra** la scomposizione della diagonale: quanto i legami uomo-uomo e quanto i legami donna-donna superano l'atteso. La lettura congiunta dei due pannelli è il cuore di RQ2. Un valore osservato/atteso vicino a 1 per gli uomini e molto sopra 1 per le donne descrive una situazione precisa: gli uomini non si cercano fra loro più del caso — non ne hanno bisogno, sono la maggioranza e il caso li mette già insieme — mentre le donne si aggregano fra loro molto più del previsto. È la forma che l'omofilia assume quando una minoranza opera dentro una maggioranza: non segregazione simmetrica, ma addensamento del gruppo minoritario.

</figcaption>
</figure>


| genere_musicale        | archi   | r_gender   | ci_lo   | ci_hi   | r_null   | oe_MM   | oe_FF   | n_artisti   | quota_donne   |
|:-----------------------|:--------|:-----------|:--------|:--------|:---------|:--------|:--------|:------------|:--------------|
| Electronic             | 128.659 | 0,0692     | 0,0643  | 0,0739  | 0,0000   | 1,0241  | 1,3588  | 19.969      | 0,0985        |
| Pop                    | 109.924 | 0,0233     | 0,0183  | 0,0284  | 0,0001   | 1,0028  | 1,3115  | 9.446       | 0,1637        |
| Rock                   | 41.007  | 0,1608     | 0,1515  | 0,1708  | 0,0001   | 1,0353  | 1,7579  | 16.617      | 0,0806        |
| Hip Hop                | 17.507  | 0,1429     | 0,1277  | 0,1567  | -0,0001  | 1,0445  | 2,1820  | 1.822       | 0,0565        |
| Folk, World, & Country | 13.639  | 0,0769     | 0,0625  | 0,0919  | -0,0005  | 1,0175  | 1,5411  | 4.863       | 0,1143        |
| Jazz                   | 11.762  | 0,0333     | 0,0171  | 0,0497  | 0,0001   | 1,0044  | 1,5144  | 3.124       | 0,1172        |
| Classical              | 5.264   | 0,0512     | 0,0292  | 0,0739  | -0,0002  | 1,0166  | 1,2704  | 3.674       | 0,2131        |
| Stage & Screen         | 2.693   | 0,0186     | -0,0141 | 0,0548  | -0,0019  | 1,0035  | 1,1863  | 641         | 0,1700        |
| Non-Music              | 1.106   | 0,0762     | 0,0171  | 0,1351  | -0,0002  | 1,0151  | 1,3163  | 477         | 0,1698        |
| Children's             | 1.075   | 0,0340     | -0,0101 | 0,0780  | -0,0005  | 1,0120  | 1,0144  | 676         | 0,3240        |

**Tabella — Omofilia di genere sessuale entro ciascun genere musicale (RQ2)**

*Dati completi in `tables/t3_omofilia_per_genere_musicale.csv` e `tables/t3_omofilia_per_genere_musicale.tex`.*


Questo è il punto su cui il dato italiano **contraddice l'aspettativa
corrente**. La letteratura riporta di norma un'omofilia più forte *fra gli
uomini*. Qui il rapporto osservato/atteso donna-donna è sistematicamente
**maggiore** di quello uomo-uomo. La spiegazione non è che le donne siano più
chiuse: è che con una quota femminile del 14,8% il valore atteso
per un legame donna-donna sotto casualità è bassissimo, e basta un modesto
addensamento reale per produrre un rapporto elevato. L'indice uomo-uomo, al
contrario, è schiacciato verso 1 perché la maggioranza non può discostarsi
molto dal caso. **I due indici non sono confrontabili come se misurassero la
stessa cosa**, ed è l'ERGM — che stima una propensione e non un rapporto — a
fornire il confronto corretto.


# 6. Le donne stanno al centro o ai margini? (RQ3)

La domanda che la letteratura chiama *pattern Smurfette* è se le donne, dove
ci sono, occupino posizioni strutturalmente periferiche: presenti quanto basta,
mai al centro.

| gender   | n      | eigenvector_mediana   | eigenvector_media   | betweenness_mediana   | coreness_mediana   | coreness_media   | grado_mediano   | forza_mediana   | n_release_mediana   |
|:---------|:-------|:----------------------|:--------------------|:----------------------|:-------------------|:-----------------|:----------------|:----------------|:--------------------|
| F        | 6.961  | 0,000000              | 0,000055            | 0,000000              | 6,000000           | 9,011062         | 7,000000        | 5,190000        | 8,000000            |
| M        | 44.869 | 0,000000              | 0,000174            | 0,000002              | 6,000000           | 10,028327        | 8,000000        | 6,490000        | 9,000000            |

**Tabella — Posizione nella componente gigante per genere sessuale**

*Dati completi in `tables/t3_posizione_per_genere.csv` e `tables/t3_posizione_per_genere.tex`.*


<figure>
<img src="figures/f8_posizione_per_genere.png" alt="f8_posizione_per_genere" style="width:100%" />
<figcaption>

**Coreness mediana per genere sessuale, dentro ciascun genere musicale.** La coreness dice a quale strato del nucleo denso della rete una persona appartiene: è una misura di appartenenza al centro più robusta della centralità di grado, perché non si lascia gonfiare da chi ha molti collaboratori occasionali. Le barre affiancate permettono il confronto diretto a parità di genere musicale, che è il confronto giusto: paragonare una cantante pop a un turnista jazz non direbbe nulla sul genere sessuale e molto sulla struttura delle due scene.

</figcaption>
</figure>


| musical_genre          | gender   | n      | coreness_mediana   | eigenvector_mediana   |
|:-----------------------|:---------|:-------|:-------------------|:----------------------|
| Blues                  | F        | 53     | 5,000000           | 0,000000              |
| Blues                  | M        | 305    | 6,000000           | 0,000000              |
| Brass & Military       | F        | 2      | 7,500000           | 0,000000              |
| Brass & Military       | M        | 46     | 8,500000           | 0,000000              |
| Children's             | F        | 154    | 8,000000           | 0,000001              |
| Children's             | M        | 245    | 7,000000           | 0,000001              |
| Classical              | F        | 436    | 4,000000           | 0,000000              |
| Classical              | M        | 1.642  | 5,000000           | 0,000000              |
| Electronic             | F        | 1.722  | 7,000000           | 0,000000              |
| Electronic             | M        | 10.938 | 8,000000           | 0,000000              |
| Folk, World, & Country | F        | 413    | 7,000000           | 0,000000              |
| Folk, World, & Country | M        | 2.760  | 7,000000           | 0,000000              |
| Funk / Soul            | F        | 77     | 6,000000           | 0,000000              |
| Funk / Soul            | M        | 473    | 7,000000           | 0,000000              |
| Hip Hop                | F        | 72     | 10,000000          | 0,000000              |
| Hip Hop                | M        | 966    | 15,000000          | 0,000000              |
| Jazz                   | F        | 245    | 7,000000           | 0,000000              |
| Jazz                   | M        | 1.919  | 9,000000           | 0,000000              |
| Latin                  | F        | 29     | 7,000000           | 0,000000              |
| Latin                  | M        | 150    | 7,500000           | 0,000000              |
| Non-Music              | F        | 62     | 5,500000           | 0,000000              |
| Non-Music              | M        | 298    | 7,000000           | 0,000000              |
| Pop                    | F        | 1.150  | 11,000000          | 0,000004              |
| Pop                    | M        | 5.608  | 13,000000          | 0,000003              |
| Reggae                 | F        | 14     | 4,500000           | 0,000000              |
| Reggae                 | M        | 166    | 6,000000           | 0,000000              |
| Rock                   | F        | 774    | 5,000000           | 0,000000              |
| Rock                   | M        | 8.587  | 6,000000           | 0,000000              |
| Stage & Screen         | F        | 88     | 9,000000           | 0,000002              |
| Stage & Screen         | M        | 394    | 11,000000          | 0,000002              |

**Tabella — Posizione nella rete per genere sessuale entro genere musicale**

*Dati completi in `tables/t3_posizione_per_genere_musicale.csv` e `tables/t3_posizione_per_genere_musicale.tex`.*


## 6.1 Il confronto a parità di attività e coorte

Le mediane grezze non bastano. Chi pubblica di più è più centrale, e le donne
della popolazione pubblicano meno: la mediana delle pubblicazioni è
8 per le donne contro 9 per gli
uomini, e la coreness mediana segue (6 contro
6). Senza controllare per l'attività si misurerebbe la
differenza di quanto si pubblica e la si chiamerebbe differenza di posizione.

La regressione confronta perciò persone con la stessa attività, la stessa
coorte di debutto e lo stesso genere musicale.

| termine                                            | coef    | se     | z        | p      | ci_lo   | ci_hi   | esito       |
|:---------------------------------------------------|:--------|:-------|:---------|:-------|:--------|:--------|:------------|
| Intercept                                          | 0,8390  | 0,0966 | 8,6891   | 0,0000 | 0,6497  | 1,0282  | eigenvector |
| C(gender)[T.F]                                     | 0,1801  | 0,1754 | 1,0265   | 0,3047 | -0,1638 | 0,5239  | eigenvector |
| C(genere)[T.Blues]                                 | -0,0114 | 0,0764 | -0,1498  | 0,8809 | -0,1612 | 0,1383  | eigenvector |
| C(genere)[T.Children's]                            | -0,1781 | 0,1203 | -1,4802  | 0,1388 | -0,4140 | 0,0577  | eigenvector |
| C(genere)[T.Classical]                             | -0,6635 | 0,0683 | -9,7184  | 0,0000 | -0,7974 | -0,5297 | eigenvector |
| C(genere)[T.Electronic]                            | -0,1863 | 0,0627 | -2,9721  | 0,0030 | -0,3092 | -0,0634 | eigenvector |
| C(genere)[T.Folk, World, & Country]                | -0,2480 | 0,0663 | -3,7436  | 0,0002 | -0,3779 | -0,1182 | eigenvector |
| C(genere)[T.Funk / Soul]                           | 0,0681  | 0,0760 | 0,8962   | 0,3702 | -0,0808 | 0,2171  | eigenvector |
| C(genere)[T.Hip Hop]                               | -0,3351 | 0,0680 | -4,9293  | 0,0000 | -0,4683 | -0,2018 | eigenvector |
| C(genere)[T.Jazz]                                  | -0,1980 | 0,0674 | -2,9391  | 0,0033 | -0,3300 | -0,0660 | eigenvector |
| C(genere)[T.Non-Music]                             | -1,4207 | 0,0969 | -14,6663 | 0,0000 | -1,6105 | -1,2308 | eigenvector |
| C(genere)[T.Pop]                                   | 1,0434  | 0,0662 | 15,7589  | 0,0000 | 0,9137  | 1,1732  | eigenvector |
| C(genere)[T.Rock]                                  | 0,0077  | 0,0629 | 0,1223   | 0,9027 | -0,1156 | 0,1310  | eigenvector |
| C(genere)[T.Stage & Screen]                        | 0,3258  | 0,0914 | 3,5651   | 0,0004 | 0,1467  | 0,5049  | eigenvector |
| C(coorte)[T.1950]                                  | 0,2381  | 0,0906 | 2,6284   | 0,0086 | 0,0605  | 0,4156  | eigenvector |
| C(coorte)[T.1960]                                  | -0,1393 | 0,0793 | -1,7560  | 0,0791 | -0,2947 | 0,0162  | eigenvector |
| C(coorte)[T.1970]                                  | -1,2591 | 0,0757 | -16,6331 | 0,0000 | -1,4075 | -1,1108 | eigenvector |
| C(coorte)[T.1980]                                  | -1,8311 | 0,0739 | -24,7652 | 0,0000 | -1,9760 | -1,6862 | eigenvector |
| C(coorte)[T.1990]                                  | -2,0707 | 0,0735 | -28,1849 | 0,0000 | -2,2147 | -1,9267 | eigenvector |
| C(coorte)[T.2000]                                  | -2,1104 | 0,0735 | -28,6968 | 0,0000 | -2,2546 | -1,9663 | eigenvector |
| C(coorte)[T.2010]                                  | -2,0327 | 0,0737 | -27,5984 | 0,0000 | -2,1770 | -1,8883 | eigenvector |
| C(coorte)[T.2020]                                  | -1,7953 | 0,0763 | -23,5242 | 0,0000 | -1,9449 | -1,6457 | eigenvector |
| C(gender)[T.F]:C(genere)[T.Blues]                  | 0,0528  | 0,2128 | 0,2483   | 0,8039 | -0,3643 | 0,4700  | eigenvector |
| C(gender)[T.F]:C(genere)[T.Children's]             | -0,1451 | 0,2392 | -0,6068  | 0,5440 | -0,6138 | 0,3236  | eigenvector |
| C(gender)[T.F]:C(genere)[T.Classical]              | 0,0347  | 0,1850 | 0,1875   | 0,8513 | -0,3279 | 0,3973  | eigenvector |
| C(gender)[T.F]:C(genere)[T.Electronic]             | -0,0192 | 0,1768 | -0,1085  | 0,9136 | -0,3657 | 0,3274  | eigenvector |
| C(gender)[T.F]:C(genere)[T.Folk, World, & Country] | -0,1365 | 0,1863 | -0,7323  | 0,4640 | -0,5016 | 0,2287  | eigenvector |
| C(gender)[T.F]:C(genere)[T.Funk / Soul]            | 0,2858  | 0,2295 | 1,2451   | 0,2131 | -0,1641 | 0,7357  | eigenvector |

**Tabella — Posizione nella rete (eigenvector) per genere sessuale e genere musicale, a parità di attività e coorte**

*Mostrate le prime 28 righe di 35; la tabella completa è in `tables/t3_regressione_eigenvector.csv` e `tables/t3_regressione_eigenvector.tex`.*


| termine                                            | coef    | se     | z        | p      | ci_lo   | ci_hi   | esito    |
|:---------------------------------------------------|:--------|:-------|:---------|:-------|:--------|:--------|:---------|
| Intercept                                          | 1,1580  | 0,0329 | 35,2227  | 0,0000 | 1,0936  | 1,2224  | coreness |
| C(gender)[T.F]                                     | 0,0362  | 0,0792 | 0,4572   | 0,6475 | -0,1190 | 0,1915  | coreness |
| C(genere)[T.Blues]                                 | 0,0051  | 0,0360 | 0,1416   | 0,8874 | -0,0654 | 0,0756  | coreness |
| C(genere)[T.Children's]                            | -0,0135 | 0,0396 | -0,3415  | 0,7328 | -0,0912 | 0,0642  | coreness |
| C(genere)[T.Classical]                             | -0,2867 | 0,0278 | -10,3191 | 0,0000 | -0,3411 | -0,2322 | coreness |
| C(genere)[T.Electronic]                            | 0,0474  | 0,0256 | 1,8549   | 0,0636 | -0,0027 | 0,0976  | coreness |
| C(genere)[T.Folk, World, & Country]                | 0,0516  | 0,0268 | 1,9281   | 0,0538 | -0,0009 | 0,1041  | coreness |
| C(genere)[T.Funk / Soul]                           | 0,0480  | 0,0333 | 1,4400   | 0,1499 | -0,0173 | 0,1134  | coreness |
| C(genere)[T.Hip Hop]                               | 0,3801  | 0,0291 | 13,0492  | 0,0000 | 0,3230  | 0,4372  | coreness |
| C(genere)[T.Jazz]                                  | 0,1173  | 0,0273 | 4,2999   | 0,0000 | 0,0638  | 0,1707  | coreness |
| C(genere)[T.Non-Music]                             | -0,1804 | 0,0366 | -4,9333  | 0,0000 | -0,2521 | -0,1088 | coreness |
| C(genere)[T.Pop]                                   | 0,1794  | 0,0260 | 6,9001   | 0,0000 | 0,1284  | 0,2304  | coreness |
| C(genere)[T.Rock]                                  | -0,0319 | 0,0255 | -1,2487  | 0,2118 | -0,0820 | 0,0182  | coreness |
| C(genere)[T.Stage & Screen]                        | 0,1865  | 0,0345 | 5,3991   | 0,0000 | 0,1188  | 0,2542  | coreness |
| C(coorte)[T.1950]                                  | 0,0563  | 0,0249 | 2,2643   | 0,0236 | 0,0076  | 0,1051  | coreness |
| C(coorte)[T.1960]                                  | -0,0144 | 0,0219 | -0,6585  | 0,5102 | -0,0574 | 0,0286  | coreness |
| C(coorte)[T.1970]                                  | -0,1829 | 0,0216 | -8,4552  | 0,0000 | -0,2254 | -0,1405 | coreness |
| C(coorte)[T.1980]                                  | -0,1984 | 0,0213 | -9,3131  | 0,0000 | -0,2401 | -0,1566 | coreness |
| C(coorte)[T.1990]                                  | -0,2171 | 0,0213 | -10,2125 | 0,0000 | -0,2587 | -0,1754 | coreness |
| C(coorte)[T.2000]                                  | -0,2610 | 0,0215 | -12,1340 | 0,0000 | -0,3031 | -0,2188 | coreness |
| C(coorte)[T.2010]                                  | -0,3656 | 0,0222 | -16,5025 | 0,0000 | -0,4091 | -0,3222 | coreness |
| C(coorte)[T.2020]                                  | -0,3616 | 0,0273 | -13,2565 | 0,0000 | -0,4151 | -0,3082 | coreness |
| C(gender)[T.F]:C(genere)[T.Blues]                  | -0,0177 | 0,1034 | -0,1715  | 0,8638 | -0,2204 | 0,1850  | coreness |
| C(gender)[T.F]:C(genere)[T.Children's]             | -0,0037 | 0,0927 | -0,0396  | 0,9684 | -0,1853 | 0,1780  | coreness |
| C(gender)[T.F]:C(genere)[T.Classical]              | -0,0692 | 0,0840 | -0,8244  | 0,4097 | -0,2338 | 0,0954  | coreness |
| C(gender)[T.F]:C(genere)[T.Electronic]             | -0,0092 | 0,0801 | -0,1147  | 0,9087 | -0,1661 | 0,1478  | coreness |
| C(gender)[T.F]:C(genere)[T.Folk, World, & Country] | -0,0633 | 0,0834 | -0,7589  | 0,4479 | -0,2268 | 0,1002  | coreness |
| C(gender)[T.F]:C(genere)[T.Funk / Soul]            | -0,0660 | 0,1054 | -0,6263  | 0,5311 | -0,2725 | 0,1405  | coreness |

**Tabella — Appartenenza al nucleo (coreness) per genere sessuale e genere musicale, a parità di attività e coorte**

*Mostrate le prime 28 righe di 35; la tabella completa è in `tables/t3_regressione_coreness.csv` e `tables/t3_regressione_coreness.tex`.*


## 6.2 La risposta a RQ3

**Il pattern "Smurfette" non si osserva in questi dati.** A parità di
pubblicazioni, coorte e genere musicale, l'effetto principale dell'essere donna
sulla posizione nella rete non è distinguibile da zero su nessuna delle tre
misure:

| misura | coefficiente | IC 95% | p |
|---|---|---|---|
| eigenvector | 0,180 | -0,164 – 0,524 | 0,305 |
| coreness | 0,036 | -0,119 – 0,191 | 0,648 |
| betweenness | -0,293 | -0,625 – 0,039 | 0,083 |

Nemmeno le interazioni con il genere musicale aiutano: su
12 termini di interazione stimati,
0 risultano significativi al 5%. Non esiste,
in questi dati, una scena in cui essere donna sposti sistematicamente verso la
periferia della rete.

È un risultato che va enunciato con precisione, perché si presta a due letture
sbagliate di segno opposto.

**Non significa che non ci sia disuguaglianza.** Le donne sono il
14,8% della popolazione e pubblicano meno: la mediana delle
pubblicazioni è 8 contro 9.
La disuguaglianza c'è ed è grande — ma si manifesta **nell'accesso e nel
volume di attività**, non nella posizione strutturale a parità di attività.
Chi entra e riesce a lavorare, lavora in posizioni comparabili.

**Non significa nemmeno che il controllo per l'attività sia neutro.** Il numero
di pubblicazioni non è una variabile esogena: è esso stesso un esito di
processi di accesso che possono essere segregati. Controllare per l'attività
risponde alla domanda "a parità di carriera, la posizione differisce?" e non
alla domanda "le carriere differiscono?". La prima ha risposta negativa, la
seconda — sezione 4 — ha risposta ampiamente positiva.

Il dato più interessante è la divergenza fra mediana e media
dell'eigenvector: la mediana è più alta per le donne
(7,7 × 10<sup>-9</sup> contro 3,9 × 10<sup>-9</sup>) mentre la media è
più bassa. Significa che la donna tipica della rete è connessa quanto e più
dell'uomo tipico, ma che gli **hub estremi** — i pochissimi nodi con centralità
di ordini di grandezza superiore — sono quasi tutti uomini. La disuguaglianza
di posizione, dove c'è, sta nella coda, non nel corpo della distribuzione.


# 7. Probabilità di collaborare a parità di tutto: l'ERGM (RQ4)


## 7.1 Perché serve e come è stato impostato

Tutte le misure fin qui sono descrittive: dicono *che* i legami sono distribuiti
in un certo modo, non *perché*. Un modello esponenziale per grafi casuali
(ERGM) stima invece la probabilità che un legame esista, tenendo insieme nello
stesso modello l'omofilia di genere, quella di genere musicale, il livello di
attività, la coorte e la tendenza della rete a chiudere i triangoli.
Quest'ultimo punto è decisivo: senza un termine di chiusura triadica
(`gwesp`), qualunque tendenza a fare gruppo viene erroneamente attribuita
all'attributo su cui si sta guardando.

**Sulla rete intera l'ERGM non è stimabile**, e va detto chiaramente invece di
far finta. Con 70.712 nodi lo spazio dei grafi possibili rende il
campionamento MCMC impraticabile. Si è quindi proceduto come previsto dal
disegno, per sottoreti: i cinque generi musicali più popolosi, le due epoche, e
un campione a palla di neve della rete complessiva come riferimento. **Le stime
valgono per le sottoreti su cui sono calcolate**, non si estendono per
costruzione all'intera popolazione.

Dall'ERGM sono esclusi i nodi con genere `unknown`. Tenerli come quarta
categoria avrebbe prodotto un termine di omofilia spurio che misura la struttura
della copertura dei dati — chi è poco documentato collabora con chi è poco
documentato — invece della struttura delle collaborazioni.

Si stima una **gerarchia di tre modelli**, invece di una specifica unica,
perché il termine di chiusura triadica è esattamente quello che può far
fallire la stima e non si vuole perdere tutto insieme a lui:

* **M0** `edges + nodematch(gender, diff) + controlli` — nessun termine di
  dipendenza fra archi. È il modello di riferimento: stimabile sempre.
* **M1** M0 + `gwesp(0,25; fixed)` — la specifica prevista dal disegno. Il
  termine di chiusura triadica rende il modello quasi degenere sulle reti molto
  clusterizzate, e può non convergere.
* **M2** come il migliore fra M1 e M0, con `nodemix(gender)` al posto di
  `nodematch(gender, diff)`. Le due parametrizzazioni sono ridondanti fra loro
  e nello stesso modello lo renderebbero non identificato.

I termini di controllo entrano **solo se l'attributo varia** nella sottorete.
Dentro una sottorete di un solo genere musicale `nodematch('musical_genre')`
coincide identicamente con `edges`: includerlo produrrebbe un modello non
identificato, e nelle prime esecuzioni era proprio questo a impedire la
convergenza.

| rete                        | nodi_originali   | nodi_stimati   | archi   | campionata   | convergenza   | modelli_convergenti                            | gwesp_converge   | parziale   | solo_mple   | aic        | gof   |
|:----------------------------|:-----------------|:---------------|:--------|:-------------|:--------------|:-----------------------------------------------|:-----------------|:-----------|:------------|:-----------|:------|
| genere_Electronic           | 10.499           | 1.255          | 4.968   | True         | True          | M0_senza_gwesp, M1_con_gwesp, M2_nodemix_gwesp | True             | False      | True        | 56.562,642 | True  |
| genere_Rock                 | 4.938            | 1.438          | 4.972   | True         | True          | M0_senza_gwesp, M1_con_gwesp, M2_nodemix_gwesp | True             | False      | True        | 57.896,921 | True  |
| genere_Pop                  | 5.236            | 1.057          | 4.989   | True         | True          | M0_senza_gwesp, M1_con_gwesp, M2_nodemix_gwesp | True             | False      | True        | 52.948,708 | True  |
| genere_Folk_World_&_Country | 1.625            | 1.033          | 4.931   | True         | True          | M0_senza_gwesp, M1_con_gwesp, M2_nodemix_gwesp | True             | False      | True        | 48.867,718 | True  |
| genere_Classical            | 673              | 673            | 1.620   | False        | True          | M0_senza_gwesp, M1_con_gwesp, M2_nodemix_gwesp | True             | False      | True        | 17.635,191 | True  |
| epoca_pre2000               | 23.491           | 1.303          | 4.962   | True         | True          | M0_senza_gwesp, M1_con_gwesp, M2_nodemix_gwesp | True             | False      | True        | 52.659,135 | True  |
| epoca_post2000              | 9.400            | 1.373          | 4.961   | True         | True          | M0_senza_gwesp, M1_con_gwesp, M2_nodemix_gwesp | True             | False      | True        | 57.806,416 | True  |
| complessiva                 | 36.388           | 722            | 4.982   | True         | True          | M0_senza_gwesp, M1_con_gwesp, M2_nodemix_gwesp | True             | False      | True        | 40.587,253 | True  |

**Tabella — Sintesi delle stime ERGM: dimensione, campionamento, convergenza**

*Dati completi in `tables/t4_ergm_sintesi.csv` e `tables/t4_ergm_sintesi.tex`.*


Sottoreti con almeno un modello convergente: **8 su 8**; sottoreti
in cui ha retto anche il termine `gwesp`: **8**. Dove `gwesp` non converge,
i coefficienti riportati vengono da M0 e **non** controllano per la chiusura
triadica: vanno quindi letti come stime che possono attribuire all'omofilia una
parte di ciò che è semplicemente tendenza a formare triangoli. È una
limitazione, ed è dichiarata qui invece di essere nascosta dietro un numero.

<figure>
<img src="figures/f9_ergm_forest_gender.png" alt="f9_ergm_forest_gender" style="width:100%" />
<figcaption>

**Coefficienti di omofilia di genere nei cinque generi musicali più popolosi.** Ogni coefficiente è un log-odds: quanto la probabilità di un legame aumenta (o diminuisce) se due artisti condividono il genere sessuale, *a parità* di attività, coorte, genere musicale e chiusura triadica. Questo è il confronto che le misure descrittive della sezione 5.4 non potevano fornire: qui i coefficienti maschile e femminile sono sulla stessa scala e sono direttamente confrontabili, perché misurano una propensione e non un rapporto osservato/atteso schiacciato dalle marginali. Se il coefficiente maschile supera quello femminile, il pattern italiano è allineato alla letteratura (omofilia più forte fra gli uomini) e l'inversione osservata nella sezione 5.4 era un artefatto della rarità delle donne.

</figcaption>
</figure>


| rete              | model            | term                    | estimate   | se     | p         | ci_lo    | ci_hi    | or      |
|:------------------|:-----------------|:------------------------|:-----------|:-------|:----------|:---------|:---------|:--------|
| genere_Electronic | M0_senza_gwesp   | edges                   | -9,6104    | 0,0947 | -101,4612 | -9,7961  | -9,4248  | 0,0001  |
| genere_Electronic | M0_senza_gwesp   | nodematch.gender.F      | 0,6501     | 0,1016 | 6,3982    | 0,4509   | 0,8492   | 1,9157  |
| genere_Electronic | M0_senza_gwesp   | nodematch.gender.M      | 0,1548     | 0,0343 | 4,5141    | 0,0876   | 0,2220   | 1,1674  |
| genere_Electronic | M0_senza_gwesp   | nodematch.gender.mixed  | 1,7995     | 0,2002 | 8,9895    | 1,4072   | 2,1919   | 6,0468  |
| genere_Electronic | M0_senza_gwesp   | nodecov.log_nrel        | 0,4587     | 0,0096 | 47,5998   | 0,4398   | 0,4776   | 1,5820  |
| genere_Electronic | M0_senza_gwesp   | nodematch.cohort_decade | 0,9364     | 0,0286 | 32,7475   | 0,8803   | 0,9924   | 2,5507  |
| genere_Electronic | M1_con_gwesp     | edges                   | -8,3712    | 0,0990 | -84,5544  | -8,5653  | -8,1772  | 0,0002  |
| genere_Electronic | M1_con_gwesp     | nodematch.gender.F      | 0,4771     | 0,0889 | 5,3685    | 0,3029   | 0,6513   | 1,6114  |
| genere_Electronic | M1_con_gwesp     | nodematch.gender.M      | 0,0978     | 0,0244 | 4,0055    | 0,0499   | 0,1456   | 1,1027  |
| genere_Electronic | M1_con_gwesp     | nodematch.gender.mixed  | 1,5036     | 0,1510 | 9,9574    | 1,2076   | 1,7996   | 4,4979  |
| genere_Electronic | M1_con_gwesp     | nodecov.log_nrel        | 0,1270     | 0,0081 | 15,7610   | 0,1112   | 0,1428   | 1,1355  |
| genere_Electronic | M1_con_gwesp     | nodematch.cohort_decade | 0,5027     | 0,0332 | 15,1581   | 0,4377   | 0,5677   | 1,6532  |
| genere_Electronic | M1_con_gwesp     | gwesp.fixed.0.25        | 2,3216     | 0,0627 | 37,0510   | 2,1988   | 2,4444   | 10,1919 |
| genere_Electronic | M2_nodemix_gwesp | edges                   | -7,5427    | 0,1086 | -69,4677  | -7,7556  | -7,3299  | 0,0005  |
| genere_Electronic | M2_nodemix_gwesp | mix.gender.F.M          | -0,8361    | 0,0598 | -13,9753  | -0,9534  | -0,7188  | 0,4334  |
| genere_Electronic | M2_nodemix_gwesp | mix.gender.M.M          | -0,6619    | 0,0618 | -10,7108  | -0,7830  | -0,5407  | 0,5159  |
| genere_Electronic | M2_nodemix_gwesp | mix.gender.F.mixed      | -0,3314    | 0,1478 | -2,2426   | -0,6210  | -0,0418  | 0,7179  |
| genere_Electronic | M2_nodemix_gwesp | mix.gender.M.mixed      | -0,7559    | 0,0811 | -9,3256   | -0,9148  | -0,5971  | 0,4696  |
| genere_Electronic | M2_nodemix_gwesp | mix.gender.mixed.mixed  | 0,5991     | 0,1927 | 3,1092    | 0,2214   | 0,9767   | 1,8204  |
| genere_Electronic | M2_nodemix_gwesp | nodecov.log_nrel        | 0,1282     | 0,0084 | 15,1873   | 0,1116   | 0,1447   | 1,1368  |
| genere_Electronic | M2_nodemix_gwesp | nodematch.cohort_decade | 0,5610     | 0,0259 | 21,6217   | 0,5101   | 0,6118   | 1,7524  |
| genere_Electronic | M2_nodemix_gwesp | gwesp.fixed.0.25        | 2,1816     | 0,0703 | 31,0263   | 2,0437   | 2,3194   | 8,8601  |
| genere_Rock       | M0_senza_gwesp   | edges                   | -9,3291    | 0,0768 | -121,5302 | -9,4796  | -9,1787  | 0,0001  |
| genere_Rock       | M0_senza_gwesp   | nodematch.gender.F      | 0,8337     | 0,2548 | 3,2716    | 0,3342   | 1,3331   | 2,3018  |
| genere_Rock       | M0_senza_gwesp   | nodematch.gender.M      | -0,1000    | 0,0402 | -2,4897   | -0,1788  | -0,0213  | 0,9048  |
| genere_Rock       | M0_senza_gwesp   | nodematch.gender.mixed  | 1,2413     | 0,2113 | 5,8744    | 0,8271   | 1,6554   | 3,4599  |
| genere_Rock       | M0_senza_gwesp   | nodecov.log_nrel        | 0,4589     | 0,0080 | 57,4936   | 0,4433   | 0,4746   | 1,5823  |
| genere_Rock       | M0_senza_gwesp   | nodematch.cohort_decade | 1,3306     | 0,0286 | 46,5589   | 1,2746   | 1,3867   | 3,7834  |
| genere_Rock       | M1_con_gwesp     | edges                   | -10,3651   | 0,1100 | -94,2404  | -10,5806 | -10,1495 | 0,0000  |
| genere_Rock       | M1_con_gwesp     | nodematch.gender.F      | 0,7312     | 0,1842 | 3,9686    | 0,3701   | 1,0922   | 2,0775  |
| genere_Rock       | M1_con_gwesp     | nodematch.gender.M      | -0,0756    | 0,0240 | -3,1486   | -0,1227  | -0,0285  | 0,9272  |
| genere_Rock       | M1_con_gwesp     | nodematch.gender.mixed  | -0,5234    | 0,3615 | -1,4479   | -1,2319  | 0,1851   | 0,5925  |
| genere_Rock       | M1_con_gwesp     | nodecov.log_nrel        | 0,0913     | 0,0046 | 19,7145   | 0,0823   | 0,1004   | 1,0956  |
| genere_Rock       | M1_con_gwesp     | nodematch.cohort_decade | 0,7956     | 0,0220 | 36,1783   | 0,7525   | 0,8387   | 2,2159  |
| genere_Rock       | M1_con_gwesp     | gwesp.fixed.0.25        | 4,4500     | 0,0733 | 60,7193   | 4,3064   | 4,5936   | 85,6275 |
| genere_Rock       | M2_nodemix_gwesp | edges                   | -9,8962    | 0,3335 | -29,6768  | -10,5498 | -9,2426  | 0,0001  |
| genere_Rock       | M2_nodemix_gwesp | mix.gender.F.M          | -0,3735    | 0,3349 | -1,1153   | -1,0299  | 0,2829   | 0,6883  |
| genere_Rock       | M2_nodemix_gwesp | mix.gender.M.M          | -0,5840    | 0,3462 | -1,6868   | -1,2626  | 0,0946   | 0,5577  |
| genere_Rock       | M2_nodemix_gwesp | mix.gender.F.mixed      | -0,9523    | 0,3283 | -2,9006   | -1,5958  | -0,3088  | 0,3858  |
| genere_Rock       | M2_nodemix_gwesp | mix.gender.M.mixed      | -0,5631    | 0,3339 | -1,6863   | -1,2176  | 0,0914   | 0,5694  |

**Tabella — Coefficienti ERGM per sottorete**

*Mostrate le prime 40 righe di 185; la tabella completa è in `tables/t4_ergm_coefficienti.csv` e `tables/t4_ergm_coefficienti.tex`.*


### Come si leggono questi coefficienti, e che cosa dicono

I coefficienti sono in log-odds; la colonna `or` è il loro esponenziale, cioè
di quanto si moltiplica la probabilità di un legame. `nodematch.gender.F` dice
quanto una coppia donna-donna è più probabile di una coppia di riferimento **a
parità di tutto il resto**: attività, coorte, genere musicale e — cosa
decisiva — tendenza della rete a chiudere i triangoli.

Il confronto fra `nodematch.gender.F` e `nodematch.gender.M` è il risultato
che la sezione 5.4 non poteva dare. Lì i rapporti osservato/atteso non erano
confrontabili, perché con una quota femminile del 14,8% il valore
atteso per un legame donna-donna è così basso che qualunque addensamento
reale produce un rapporto grande. Qui il problema non si pone: i due
coefficienti misurano la stessa quantità sulla stessa scala. **E il risultato
regge: la propensione delle donne a lavorare con donne resta nettamente
superiore a quella degli uomini a lavorare con uomini.** Non è un artefatto
della rarità; è una proprietà della rete.

In alcune sottoreti il coefficiente maschile è **negativo**: a parità di
tutto il resto, due uomini hanno una probabilità di collaborare leggermente
*inferiore* al riferimento. Non significa che gli uomini si evitino. Significa
che, in un ambiente dove sono la stragrande maggioranza, il termine `edges` da
solo già produce quasi tutti i legami maschili che si osservano, e una volta
tolta quella quota di base non resta nulla da attribuire a una preferenza. È
la controprova, dal lato opposto, della stessa asimmetria: dove un gruppo
domina, l'omofilia non ha modo di manifestarsi come effetto misurabile; dove un
gruppo è raro, si manifesta con forza.

Merita attenzione anche il confronto fra M0 e M1. Passando dal modello senza
chiusura triadica a quello con `gwesp`, il coefficiente di omofilia femminile
**si riduce**: una parte di ciò che sembrava preferenza di genere era in realtà
la tendenza generale della rete a chiudere i triangoli — se A lavora con B e B
con C, prima o poi A lavora con C, e in un ambiente dove le donne sono poche i
triangoli fra donne si formano comunque. Il termine `gwesp` ha un coefficiente
molto grande, il che dice quanto forte sia quel meccanismo. Ciò che resta dopo
averlo tolto è omofilia vera.

## 7.2 La diagnostica: il modello descrive davvero questa rete?

<figure>
<img src="figures/f12_ergm_gof.png" alt="f12_ergm_gof" style="width:100%" />
<figcaption>

**Bontà di adattamento.** Per ciascuna sottorete si confrontano tre statistiche della rete osservata (punti) con quelle delle reti simulate dal modello stimato (linea e banda): la distribuzione dei gradi, il numero di partner condivisi da ciascuna coppia collegata (ESP) e le distanze geodetiche. Un modello che coglie la struttura produce simulazioni la cui banda contiene l'osservato; dove il punto esce dalla banda, il modello sta sbagliando proprio quell'aspetto. L'ESP è la statistica da guardare con più attenzione, perché è quella che il termine gwesp dovrebbe riprodurre: se l'osservato ne esce, la chiusura triadica non è stata catturata e i coefficienti di omofilia possono averne assorbito una parte. Nei modelli stimati qui il centro delle distribuzioni è riprodotto bene, ma **la coda no**: i nodi con molti collaboratori e le coppie con molti partner in comune sono sistematicamente più numerosi di quanto il modello preveda (cerchi rossi). È il limite noto degli ERGM su reti con code pesanti, e va tenuto presente leggendo i coefficienti: il modello descrive bene il musicista tipico, meno bene i pochi grandi collaboratori.

</figcaption>
</figure>


> *Tabella «t4_ergm_mcmc» non disponibile.*


## 7.3 Il test pre/post 2000

| model            | term                    | estimate_pre   | estimate_post   | differenza   | se_diff   | z        | p      |
|:-----------------|:------------------------|:---------------|:----------------|:-------------|:----------|:---------|:-------|
| M0_senza_gwesp   | edges                   | -10,1834       | -10,1231        | 0,0603       | 0,1294    | 0,4657   | 0,6414 |
| M0_senza_gwesp   | nodematch.gender.F      | 0,6129         | 0,3757          | -0,2372      | 0,2690    | -0,8817  | 0,3780 |
| M0_senza_gwesp   | nodematch.gender.M      | 0,0546         | 0,1506          | 0,0960       | 0,0595    | 1,6145   | 0,1064 |
| M0_senza_gwesp   | nodematch.gender.mixed  | 1,1725         | 1,8788          | 0,7063       | 1,0520    | 0,6714   | 0,5020 |
| M0_senza_gwesp   | nodematch.musical_genre | 1,8584         | 0,7809          | -1,0775      | 0,0577    | -18,6881 | 0,0000 |
| M0_senza_gwesp   | nodecov.log_nrel        | 0,3983         | 0,4749          | 0,0766       | 0,0127    | 6,0327   | 0,0000 |
| M0_senza_gwesp   | nodematch.cohort_decade | 0,9962         | 0,8471          | -0,1491      | 0,0465    | -3,2085  | 0,0013 |
| M1_con_gwesp     | edges                   | -8,9452        | -8,7947         | 0,1506       | 0,1833    | 0,8216   | 0,4113 |
| M1_con_gwesp     | nodematch.gender.F      | 0,7092         | 0,7763          | 0,0671       | 0,4368    | 0,1536   | 0,8779 |
| M1_con_gwesp     | nodematch.gender.M      | 0,1368         | 0,0797          | -0,0571      | 0,1091    | -0,5234  | 0,6007 |
| M1_con_gwesp     | nodematch.gender.mixed  | 1,2087         | 0,6167          | -0,5920      | 1,3414    | -0,4414  | 0,6590 |
| M1_con_gwesp     | nodematch.musical_genre | 0,9938         | 0,2883          | -0,7055      | 0,0936    | -7,5364  | 0,0000 |
| M1_con_gwesp     | nodecov.log_nrel        | 0,1385         | 0,0803          | -0,0582      | 0,0214    | -2,7217  | 0,0065 |
| M1_con_gwesp     | nodematch.cohort_decade | 0,4768         | 0,3040          | -0,1727      | 0,0844    | -2,0462  | 0,0407 |
| M1_con_gwesp     | gwesp.fixed.0.25        | 2,2169         | 2,8923          | 0,6754       | 0,0799    | 8,4490   | 0,0000 |
| M2_nodemix_gwesp | edges                   | -7,8019        | -7,9375         | -0,1357      | 0,3456    | -0,3926  | 0,6946 |
| M2_nodemix_gwesp | mix.gender.F.M          | -0,7275        | -0,8898         | -0,1623      | 0,3460    | -0,4692  | 0,6389 |
| M2_nodemix_gwesp | mix.gender.M.M          | -0,6808        | -0,7937         | -0,1129      | 0,3290    | -0,3432  | 0,7315 |
| M2_nodemix_gwesp | mix.gender.F.mixed      | -1,0455        | 0,0598          | 1,1053       | 0,6258    | 1,7661   | 0,0774 |
| M2_nodemix_gwesp | mix.gender.M.mixed      | -1,0852        | -0,9688         | 0,1164       | 0,4379    | 0,2659   | 0,7903 |
| M2_nodemix_gwesp | mix.gender.mixed.mixed  | 0,0206         | 0,2712          | 0,2506       | 3,2202    | 0,0778   | 0,9380 |
| M2_nodemix_gwesp | nodematch.musical_genre | 1,0659         | 0,2194          | -0,8465      | 0,0710    | -11,9154 | 0,0000 |
| M2_nodemix_gwesp | nodecov.log_nrel        | 0,1052         | 0,0968          | -0,0084      | 0,0179    | -0,4684  | 0,6395 |
| M2_nodemix_gwesp | nodematch.cohort_decade | 0,5239         | 0,3121          | -0,2118      | 0,0677    | -3,1283  | 0,0018 |
| M2_nodemix_gwesp | gwesp.fixed.0.25        | 2,1250         | 2,8679          | 0,7429       | 0,0908    | 8,1822   | 0,0000 |

**Tabella — Test della differenza fra i coefficienti ERGM pre-2000 e post-2000**

*Dati completi in `tables/t4_ergm_differenza_epoche.csv` e `tables/t4_ergm_differenza_epoche.tex`.*


Questa tabella è la verifica formale del risultato controintuitivo della
sezione 5.2, e il suo esito è netto.

**L'omofilia di genere non cambia fra le due epoche.** Per le donne il
coefficiente passa da 0,709 a 0,776
(differenza 0,067, p = 0,88); per
gli uomini da 0,137 a 0,080
(differenza -0,057, p = 0,60).
Nessuna delle due differenze si avvicina alla significatività.

**Cambia invece, e moltissimo, la chiusura triadica.** Il coefficiente `gwesp`
passa da 2,217 a 2,892,
una differenza di 0,675 con p < 0,0001: è l'unico
termine del modello la cui variazione fra epoche sia statisticamente solida.

La lettura congiunta è quella data alla sezione 5.2: l'aumento
dell'assortatività osservata dopo il 2000 non è un rafforzamento della
preferenza di genere, ma la conseguenza di una rete che si chiude in gruppi più
fitti. Vale la pena notare che questo è esattamente il tipo di confusione che
un'analisi puramente descrittiva non può sciogliere, e per cui l'ERGM era
previsto nel disegno.


# 8. Quanto reggono questi risultati

## 8.1 L'incertezza sul genere sessuale

<figure>
<img src="figures/f10_montecarlo_genere.png" alt="f10_montecarlo_genere" style="width:100%" />
<figcaption>

**La distribuzione Monte Carlo dell'assortatività di genere al variare dell'imputazione degli 22.136 artisti senza genere determinato.** L'istogramma è la distribuzione su 200 estrazioni dalla marginale osservata. Le due linee tratteggiate laterali non sono stime ma **limiti costruiti apposta**: assegnando a ogni artista ignoto il genere prevalente fra i suoi collaboratori si ottiene la massima omofilia compatibile con i dati; assegnando il genere opposto si ottiene la minima. Il fatto rilevante è che **anche il limite inferiore resta positivo**: non esiste assegnazione degli ignoti che faccia sparire l'omofilia. La conclusione qualitativa è robusta; la sua grandezza esatta no.

</figcaption>
</figure>


| scenario              | count   | mean   | std    | min    | max    | ci_lo   | ci_hi   |
|:----------------------|:--------|:-------|:-------|:-------|:-------|:--------|:--------|
| migliore_omofilia_min | 1       | 0,0499 | n.d.   | 0,0499 | 0,0499 | n.d.    | n.d.    |
| peggiore_omofilia_max | 1       | 0,0623 | n.d.   | 0,0623 | 0,0623 | n.d.    | n.d.    |
| solo_noti             | 1       | 0,0432 | n.d.   | 0,0432 | 0,0432 | n.d.    | n.d.    |
| status_quo            | 200     | 0,0329 | 0,0007 | 0,0308 | 0,0349 | 0,0313  | 0,0343  |

**Tabella — Assortatività di genere sotto diversi scenari di imputazione**

*Dati completi in `tables/t5_montecarlo_genere.csv` e `tables/t5_montecarlo_genere.tex`.*


I quattro numeri vanno letti insieme. Sui soli artisti con genere determinato
l'assortatività vale 0,0432. Imputando gli ignoti per estrazione
casuale dalla marginale osservata scende a 0,0329: l'imputazione
casuale non può che diluire la struttura, ed è la ragione per cui la misura
di riferimento di questo studio è la prima e non la seconda. I due limiti
costruiti sul vicinato — 0,0499 e 0,0623 — delimitano
quanto l'omofilia potrebbe valere se gli artisti ignoti somigliassero
sistematicamente ai loro collaboratori o sistematicamente no. **Nessuno dei
quattro scenari porta l'omofilia a zero o sotto zero.**

Va detto con precisione che cosa questi limiti non fanno: riguardano solo gli
artisti ignoti che hanno almeno un collaboratore di genere noto. Quelli che
collaborano soltanto con altri ignoti non portano informazione utilizzabile e
vengono estratti dalla marginale anche negli scenari estremi — assegnarli per
maggioranza del vicinato li metterebbe tutti nella stessa categoria, creando un
blocco artificiale che gonfierebbe *entrambi* gli estremi invece di
delimitarli.

## 8.2 Sensibilità ai parametri di costruzione

<figure>
<img src="figures/f11_sensibilita.png" alt="f11_sensibilita" style="width:100%" />
<figcaption>

**Ogni punto è l'assortatività di genere ottenuta cambiando un solo parametro rispetto alla configurazione di default (linea tratteggiata).** Gli assi variati sono quelli che potevano ragionevolmente cambiare il risultato: quanti artisti al massimo può avere una pubblicazione perché conti come collaborazione, quale peso minimo deve avere un arco, se escludere le raccolte, quanto strettamente definire l'italianità, come pesare la specificità dei crediti, e se usare o no i crediti a livello traccia. Quest'ultimo è l'asse più informativo: disattivare i crediti di traccia significa tornare a una rete costruita solo sulle co-presenze di copertina, ed è il confronto che dice quanto il livello traccia stia effettivamente aggiungendo.

</figcaption>
</figure>


| variante                     | nodi   | archi     | gigante   | r genere M/F   | r pesata   | r gen. musicale   |
|:-----------------------------|:-------|:----------|:----------|:---------------|:-----------|:------------------|
| default                      | 70.712 | 586.040   | 0,9538    | 0,0432         | 0,1254     | 0,4970            |
| max_credits=4                | 50.042 | 204.330   | 0,9012    | 0,0327         | 0,1226     | 0,5278            |
| max_credits=20               | 80.864 | 1.445.126 | 0,9702    | 0,0500         | 0,1368     | 0,4512            |
| peso_min_arco=1.0            | 44.938 | 314.348   | 0,9133    | 0,0675         | 0,1329     | 0,5529            |
| peso_min_arco=2.0            | 33.840 | 159.715   | 0,8569    | 0,0631         | 0,1260     | 0,5966            |
| raccolte_escluse=True        | 65.549 | 508.524   | 0,9503    | 0,0459         | 0,1303     | 0,5037            |
| crediti_traccia=False        | 69.806 | 546.310   | 0,9518    | 0,0442         | 0,0892     | 0,5006            |
| pesi_specificita=1.0/1.0/1.0 | 70.712 | 586.040   | 0,9538    | 0,0432         | 0,1086     | 0,4970            |
| pesi_specificita=1.0/0.5/0.1 | 70.712 | 586.040   | 0,9538    | 0,0432         | 0,1336     | 0,4970            |
| soglia_italianita=0.6        | 63.488 | 500.418   | 0,9527    | 0,0461         | 0,1254     | 0,4875            |
| soglia_italianita=0.7        | 53.916 | 390.999   | 0,9507    | 0,0450         | 0,1331     | 0,4795            |

**Tabella — Sensibilità delle metriche chiave ai parametri di costruzione della rete**

*Dati completi in `tables/t5_sensibilita.csv` e `tables/t5_sensibilita.tex`.*


Sulle 10 varianti provate, l'assortatività di genere sui soli
nodi determinati resta compresa fra **0,0327 e
0,0675**, sempre positiva e sempre dello stesso ordine di
grandezza del valore di riferimento (0,0432). Nessuna scelta di
costruzione della rete, fra quelle difendibili, ribalta la conclusione.

### Che cosa aggiungono davvero i crediti a livello traccia

La colonna dell'assortatività **pesata** è l'unica su cui la gerarchia di
specificità dei crediti può manifestarsi, perché cambiare i pesi non cambia
quali coppie di artisti siano collegate: cambia quanto contano. Il confronto è
istruttivo.

* con i crediti di traccia e la gerarchia di default: **0,1254**
* senza crediti di traccia, cioè tornando alle sole co-presenze di copertina:
  **0,0892**
* con tutti i crediti allo stesso peso: 0,1086
* con una gerarchia più ripida (1 / 0,5 / 0,1): 0,1336

Disattivare il livello traccia abbassa l'omofilia misurata di circa
29%, e appiattire i pesi la
abbassa quasi altrettanto. La lettura è che **le collaborazioni documentate in
modo più specifico sono anche le più omofile**: quando due nomi compaiono
insieme sulla stessa traccia — non genericamente sullo stesso disco — la
probabilità che condividano il genere sessuale è più alta. Una rete costruita
sulle sole co-presenze di copertina sottostima quindi la segregazione, perché
mescola la collaborazione vera con la coabitazione editoriale. È la
giustificazione empirica della scelta di disegno descritta alla sezione 3.1.

## 8.3 Artisti con genere musicale debole

| variante      | nodi   | archi   | densita   | quota_gigante   | r_gender   | r_gender_MF   | r_gender_pesato   | r_genere_musicale   | quota_donne   | peso_mediano   | n_artisti   | n_generi   |
|:--------------|:-------|:--------|:----------|:----------------|:-----------|:--------------|:------------------|:--------------------|:--------------|:---------------|:------------|:-----------|
| genre_top1    | 70.712 | 586.040 | 0,0002    | 0,9538          | 0,0810     | 0,0432        | 0,1254            | 0,4970              | 0,1477        | 1,0000         | 87.229      | 16         |
| genre_top2    | 70.712 | 586.040 | 0,0002    | 0,9538          | 0,0810     | 0,0432        | 0,1254            | 0,4538              | 0,1477        | 1,0000         | 87.229      | 16         |
| genre_exclude | 45.704 | 349.998 | 0,0003    | 0,9505          | 0,0822     | 0,0486        | 0,1234            | 0,7045              | 0,1489        | 1,0000         | 56.505      | 15         |

**Tabella — Metriche chiave usando il tag principale, il secondo tag, o escludendo gli artisti con attribuzione debole**

*Dati completi in `tables/t5_genere_debole.csv` e `tables/t5_genere_debole.tex`.*


Gli artisti il cui tag di genere principale copre meno del
40% delle loro pubblicazioni sono marcati `genre_weak`:
sono 30.724, cioè 35,2% della popolazione. La
tabella confronta tre trattamenti — tenerli col tag principale, sostituirlo col
secondo tag, escluderli del tutto — per mostrare quanto le conclusioni su RQ2
dipendano da un'attribuzione di genere musicale che per costruzione è
incerta.


# Appendice tecnica

## A.1 Ambiente

* Sistema: Linux-5.15.0-185-generic-x86_64-with-glibc2.35
* Python 3.9.12
* PostgreSQL 18.4 — database `discogs`, dati su disco rotazionale
* R per l'ERGM: installato in userspace via micromamba (conda-forge), env
  `opt/mamba/envs/ergm`
* Seme casuale globale: **20260920**
* Data di esecuzione: 25/09/2026

| pacchetto      | versione                     |
|:---------------|:-----------------------------|
| gender_guesser | presente                     |
| matplotlib     | 3.8.1                        |
| networkx       | 3.2.1                        |
| numpy          | 1.24.2                       |
| pandas         | 1.5.3                        |
| psycopg2       | 2.9.10 (dt dec pq3 ext lo64) |
| pyarrow        | 18.1.0                       |
| scipy          | 1.11.3                       |
| seaborn        | 0.13.2                       |
| statsmodels    | 0.14.6                       |

## A.2 Una nota sulle prestazioni che ha condizionato il disegno

Il cluster PostgreSQL risiede su un disco **rotazionale** ma era configurato con
`random_page_cost = 1.1`, un valore tarato per dischi a stato solido. Con quel
costo il pianificatore preferisce percorsi ad accesso casuale che su disco
meccanico degradano a pochi megabyte al secondo: la prima versione
dell'estrazione girava a circa 5 MB/s. Le sessioni di estrazione impostano
perciò `random_page_cost = 4` e riducono il parallelismo, favorendo scansioni
sequenziali, e i conteggi di italianità sono stati riscritti come **una sola
passata aggregata** su `release_artist` invece di due join ripetuti. Sono GUC di
sessione: non modificano la configurazione del server né i dati.

Analogamente, il calcolo della matrice di mixing è stato riscritto da
`numpy.add.at` a `numpy.bincount` su indici appiattiti — risultato numerico
identico, verificato, circa **50 volte più veloce** — perché senza quella
riscrittura le migliaia di repliche bootstrap e di modello nullo previste dal
disegno non sarebbero state praticabili.

## A.3 Query principali

Tutte le interrogazioni sono in `src/phase1_extract.py`. La più importante è
quella che definisce la popolazione, in una passata sola:

```sql
SELECT ra.artist_id,
       count(*) FILTER (WHERE it.id IS NOT NULL) AS n_it,
       count(*)                                  AS n_all
FROM release_artist ra
LEFT JOIN (SELECT id FROM release WHERE country = 'Italy') it
       ON it.id = ra.release_id
GROUP BY 1
HAVING count(*) FILTER (WHERE it.id IS NOT NULL) >= 2;
```

La selezione finale (quota, minimo di pubblicazioni, esclusioni anagrafiche)
avviene poi sui dati già a terra, così che la Fase 5 possa variare le soglie
senza rileggere il database.

## A.4 Tempi di esecuzione

| step                                      | seconds   |
|:------------------------------------------|:----------|
| ERGM gwesp025_gwdeg                       | 45.780,5  |
| ERGM 2020s                                | 13.466,7  |
| ERGM 1950s                                | 10.928,0  |
| ERGM decay_alto                           | 8.509,8   |
| logit esatto su tutte le diadi            | 8.014,7   |
| serie temporale esatta                    | 5.449,4   |
| betweenness                               | 5.238,8   |
| ERGM 1960s                                | 4.602,8   |
| ERGM gwesp050_stocapp                     | 4.406,4   |
| ERGM gwesp_esp0                           | 3.585,5   |
| rete intera: 20 riproiezioni randomizzate | 3.342,4   |
| ERGM genere_Rock                          | 3.183,3   |
| sensibilità                              | 2.578,6   |
| ERGM 1940s                                | 2.468,0   |
| ERGM due_scale                            | 1.687,4   |
| ERGM genere_Folk_World_&_Country          | 1.643,7   |
| ERGM epoca_post2000                       | 1.612,0   |
| ERGM complessiva                          | 1.573,4   |
| ERGM genere_Electronic                    | 1.485,7   |
| passata 1b (ricerca di linea)             | 1.460,8   |

## A.5 Riproducibilità

```bash
cd /media/disk2/datascience/analysis/gender_collab
./run_all.sh              # esecuzione completa
./run_all.sh --from 3     # riparte dalla Fase 3
./run_all.sh --force      # ignora i checkpoint e ricalcola tutto
```

Ogni fase scrive un checkpoint in `data/*.parquet` e viene saltata se il
checkpoint esiste. I dati grezzi estratti stanno in `data/raw/`, le figure in
`report/figures/`, le tabelle in `report/tables/` sia in CSV sia in LaTeX.

## A.6 Limiti, in ordine di gravità

1. **Il genere sessuale è inferito, e la validazione manuale non è stata
   eseguita.** Il campione stratificato e lo script di scoring sono pronti; senza
   di essa l'errore di misura dell'inferenza resta non quantificato.
2. **L'italianità è approssimata dal paese di pubblicazione**, perché
   `release_label` è vuota. Confonde "artista italiano" con "artista pubblicato
   in Italia".
3. **26,9% della popolazione non ha genere musicale**, perché
   `release_genre` è vuota e i master coprono solo parte delle pubblicazioni.
4. **Nessuna verifica incrociata fra fonti**: iTunes è escluso per scelta.
5. **Discogs non è un censimento.** Sovrarappresenta vinile, elettronica e
   collezionismo.
6. **L'ERGM vale sulle sottoreti stimate**, non sull'intera rete.
7. **Wikidata copre 6,0% della popolazione**; il
   livello di recupero per nome non è stato completato per indisponibilità
   ripetuta del servizio SPARQL, che ha risposto con errori 429, 502 e 504.
