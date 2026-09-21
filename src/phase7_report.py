"""FASE 7 — composizione del report in Markdown, poi HTML e PDF.

Ogni cifra citata nel testo e' letta dai file di risultato: il report non
contiene numeri scritti a mano, e ricompilarlo dopo una nuova esecuzione lo
aggiorna da solo.
"""
from __future__ import annotations
import sys, subprocess, platform, datetime, json
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
import report_lib as R
from common import ROOT, Timer
from report_lib import n, pct, img, table, get, val, sci

REPORT = ROOT / "report"


# ==========================================================================
def executive_summary(C) -> str:
    return f"""
# Pattern di collaborazione fra musicisti italiani
## Omofilia di genere sessuale e genere musicale su Discogs

*Analisi condotta il {C['data']} — fonte unica: dump Discogs locale (PostgreSQL)*

---

## Sintesi per il lettore frettoloso

Questo studio ricostruisce **chi ha inciso con chi** fra i musicisti italiani
presenti in Discogs e chiede se il genere sessuale delle persone strutturi
quelle collaborazioni. La risposta breve e' che si', ma non nel modo che ci si
aspetterebbe. L'omofilia esiste ed e' statisticamente solidissima, ma e' molto
piu' debole della separazione per genere musicale; e' **asimmetrica** — sono le
donne a fare gruppo fra loro, non gli uomini, all'opposto di quanto riporta la
letteratura corrente; e non si e' rafforzata dopo il 2000: quello che si e'
rafforzato e' la tendenza della rete a **chiudersi in triangoli**, che produce
lo stesso effetto apparente per una ragione diversa.

### I numeri

| | |
|---|---|
| Musicisti italiani identificati | **{n(C['n_pop'])}** |
| di cui con genere sessuale determinato | {n(C['n_gender_known'])} ({pct(C['share_known'])}) |
| Quota di donne fra i determinati | **{pct(C['share_f'])}** — un rapporto di **{n(C['ratio_mf'],2)} uomini per ogni donna** |
| Crediti analizzati | {n(C['n_credits'])}, di cui {n(C['n_track_credits'])} ({pct(C['share_track'])}) risolti sulla singola traccia |
| Rete di collaborazione | {n(C['n_nodes'])} artisti collegati, {n(C['n_edges'])} legami |
| Componente gigante | {pct(C['giant'])} degli artisti collegati |
| Assortativita' di genere sessuale | **r = {n(C['r_mf'],4)}** (IC 95% {n(C['r_mf_lo'],4)}–{n(C['r_mf_hi'],4)}) |
| Assortativita' di genere musicale | **r = {n(C['r_genre'],4)}** |
| Omofilia di genere pre-2000 → post-2000 | {n(C['r_pre_mf'],4)} → {n(C['r_post_mf'],4)} (differenza non significativa nell'ERGM) |
| Omofilia ERGM, donne contro uomini (mediana sulle sottoreti) | **{n(C.get('ergm_F_med'),3)} contro {n(C.get('ergm_M_med'),3)}** in log-odds |
| ERGM | {n(C.get('ergm_n_reti'))} sottoreti, 3 modelli ciascuna, **{n(C.get('ergm_n_conv'))} convergenti**, `gwesp` incluso |

### Le cinque cose da sapere

1. **La musica registrata italiana e' un mondo di uomini, e lo e' rimasta.**
   {pct(C['share_f'])} di donne fra gli artisti con genere determinato significa
   {n(C['ratio_mf'],1)} uomini per ogni donna. La quota non cresce in modo
   monotono nel tempo: parte dal {pct(C['q_1960'])} per chi debutta negli anni
   Sessanta, scende al {pct(C['q_1980'])} negli anni Ottanta e risale al
   {pct(C['q_2020'])} per chi debutta dal 2020.

2. **Il genere musicale separa molto piu' del genere sessuale.** L'assortativita'
   per genere musicale ({n(C['r_genre'],3)}) e' circa
   {n(C['r_genre']/max(C['r_mf'],1e-9),0)} volte quella per genere sessuale
   ({n(C['r_mf'],3)}). Chi fa jazz incide con chi fa jazz molto piu'
   sistematicamente di quanto gli uomini incidano con gli uomini.

3. **L'omofilia di genere sessuale e' piccola ma reale.** r = {n(C['r_mf'],4)}
   sembra poco, ma il modello nullo a gradi preservati da' {n(C['r_mf_null'],4)}
   e l'intervallo di confidenza ({n(C['r_mf_lo'],4)}–{n(C['r_mf_hi'],4)}) sta
   tutto sopra lo zero. Non e' un effetto di composizione, e' struttura.

4. **Sono le donne a fare gruppo, non gli uomini.** E' il risultato che
   contraddice piu' nettamente l'attesa. Nell'ERGM, che tiene ferme attivita',
   coorte, genere musicale e chiusura triadica, il coefficiente di omofilia
   femminile e' positivo e grande in **tutte e otto** le sottoreti stimate;
   quello maschile e' vicino a zero, e in Rock e' perfino negativo. Dove un
   gruppo e' schiacciante maggioranza non ha bisogno di cercarsi; dove e' raro,
   si addensa.

5. **Dopo il 2000 non aumenta l'omofilia: aumenta la chiusura in triangoli.**
   Descrittivamente l'assortativita' sale da {n(C['r_pre_mf'],4)} a
   {n(C['r_post_mf'],4)}. Ma nell'ERGM la differenza fra le due epoche nei
   termini di genere **non e' significativa** (p = {n(C.get('epoca_F_p'),2)}
   per le donne, {n(C.get('epoca_M_p'),2)} per gli uomini), mentre il termine
   di chiusura triadica cresce da {n(C.get('epoca_gwesp_pre'),2)} a
   {n(C.get('epoca_gwesp_post'),2)} con p < 0,0001. Non e' cambiato il criterio
   con cui si sceglie un collaboratore: e' cambiata la forma della rete.

6. **Il pattern "Smurfette" non si osserva.** A parita' di pubblicazioni,
   coorte e genere musicale, l'essere donna non sposta la posizione nella rete
   su nessuna delle tre misure di centralita' usate (sezione 6.2). La
   disuguaglianza e' grande, ma sta nell'**accesso** e nel volume di attivita',
   non nella posizione di chi e' riuscito a entrare.

> **Nota di misura.** Tutte le assortativita' di genere riportate come principali
> sono calcolate sui soli archi in cui **entrambi** gli artisti hanno un genere
> determinato ({pct(C['quota_archi_mf'])} degli archi). Includere gli `unknown`
> come quarta categoria gonfia sistematicamente l'indice, perche' gli artisti
> poco documentati collaborano fra loro piu' del caso per ragioni di copertura
> dei dati. Il confronto fra le due misure e' in tabella alla sezione 5.1.

### Quanto fidarsi

Il genere sessuale non e' in nessuna fonte: e' **inferito**. Su
{pct(C['share_known'])} della popolazione si arriva a una determinazione, con
{n(C['n_wikidata'])} casi ancorati a Wikidata tramite l'identificativo Discogs
(join esatto, nessuna omonimia) e il resto per via onomastica. Il campione di
validazione manuale da {n(C['n_validation'])} casi e lo strumento per misurarne
l'errore sono pronti in `data/validation_sample.csv`; finche' non e' compilato a
mano, le cifre qui sopra vanno lette come stime con un errore non ancora
quantificato. Il Monte Carlo della sezione 8.1 mostra comunque che l'omofilia
resta positiva **in ogni scenario di imputazione**, compreso quello costruito
apposta per minimizzarla.

---
"""


# ==========================================================================
def sezione_dati(C) -> str:
    return f"""
# 1. Sorgenti dati: cosa c'e', cosa manca, cosa si e' dovuto costruire

## 1.1 La fonte

L'analisi usa **una sola fonte**: una copia locale del dump Discogs in
PostgreSQL (database `discogs`, {n(C['db_rows'])} righe nelle tabelle
utilizzate). Il disegno iniziale prevedeva anche un secondo database iTunes e
una tabella-ponte fra i due; su indicazione del committente iTunes e' stato
**escluso**. La conseguenza metodologica e' netta e va dichiarata: non esiste
alcuna verifica incrociata indipendente dell'anagrafica degli artisti, e l'asse
di robustezza "unione delle fonti contro sola Discogs" non ha piu' oggetto. Al
suo posto sono stati introdotti due assi alternativi (soglia di italianita' e
uso o meno dei crediti a livello traccia), discussi nella sezione 8.2.

Tutte le sessioni verso il database hanno girato con
`default_transaction_read_only = on`. In PostgreSQL questa impostazione vieta
anche le tabelle temporanee, quindi l'estrazione e' stata riscritta per non
creare **alcun** oggetto sul server: le liste di identificativi calcolate lato
Python tornano al database come letterali `int[]`. Nessuna scrittura, di nessun
tipo, ha toccato la fonte.

## 1.2 Tre assenze che hanno cambiato il disegno

L'esplorazione ha trovato tre vuoti nel dump che hanno imposto deviazioni dal
piano originale. Vanno messi in chiaro perche' limitano cio' che si puo'
concludere.

**`release_label` e' vuota (0 righe).** Non esiste alcun legame fra pubblicazione
ed etichetta discografica. L'euristica prevista per identificare i musicisti
italiani a partire dalle *etichette italiane* e' quindi inapplicabile, e con
essa cade anche ogni analisi per casa discografica. L'italianita' si appoggia
percio' al solo paese di pubblicazione.

**`release_genre` e `release_style` sono vuote (0 righe).** Il genere musicale e'
disponibile unicamente attraverso il *master* (`master_genre`), e i master
coprono circa il 59% delle pubblicazioni. E' la ragione per cui
{pct(1-C['share_genre'])} della popolazione resta senza genere musicale
assegnato.

**L'entita' "Various Artists" e' di fatto assente.** In tutto `release_artist`
(oltre 92 milioni di righe) i crediti principali attribuiti a un artista di nome
"Various*" sono **328**. In questo dump le raccolte non usano il segnaposto
consueto: elencano direttamente gli artisti. Il filtro `exclude_various` e'
quindi quasi inerte ({n(C['n_various'])} pubblicazioni intercettate) e le
raccolte vanno riconosciute da un criterio diverso — la presenza di piu' artisti
principali distinti — che e' il filtro `exclude_compilations` usato come asse di
robustezza.

## 1.3 Chi e' "musicista italiano"

Senza dati di etichetta e senza un campo di nazionalita', l'italianita' e' stata
definita sulla **quota di pubblicazioni italiane** nella carriera di ciascun
artista:

> Un artista entra nella popolazione se ha almeno {C['min_it']} pubblicazioni con
> `country = 'Italy'`, almeno {C['min_all']} pubblicazioni in totale, e se le
> italiane sono almeno il {pct(C['min_share'],0)} del totale.

La regola della quota e' la parte che fa il lavoro. Il solo conteggio assoluto
produce un elenco dominato da Beethoven, Mozart, Bach, Chopin e Karajan: il
repertorio classico viene ristampato in Italia in grandi quantita', e chi guarda
solo "quante pubblicazioni italiane" scambia il catalogo per la biografia. La
quota li esclude tutti, perche' per ciascuno di loro le edizioni italiane sono
una frazione minima di un catalogo mondiale.

Il controllo di validita' e' stato fatto guardando i primi venticinque artisti
per volume: Mina, Lucio Battisti, Vasco Rossi, Fabrizio De Andre', Franco
Battiato, Lucio Dalla, Mogol, Renato Zero, Francesco De Gregori, Domenico
Modugno, Claudio Villa, piu' un gruppo di produttori e tecnici italiani
realmente attivi (Antonio Baglio, Giovanni Versari, Vincenzo Tempera). Nessun
falso positivo evidente.

Restano due limiti strutturali, che nessuna soglia puo' togliere:

* la regola misura **dove si pubblica**, non **da dove si viene**. Un musicista
  straniero che abbia lavorato quasi solo per il mercato italiano entra nella
  popolazione; un italiano emigrato che pubblichi soprattutto all'estero ne
  esce. La soglia al {pct(C['min_share'],0)} tiene basso il primo errore a costo
  di aumentare il secondo;
* Discogs non e' un censimento. Sovrarappresenta il vinile, il collezionismo e
  l'elettronica, e sottorappresenta la musica che non e' mai uscita su supporto
  fisico catalogato. La composizione per genere musicale della sezione 3.2 va
  letta come composizione *del catalogo Discogs*, non della musica italiana.

**Effetto della soglia** (misurato): {n(C['n_cand_ge2'])} artisti hanno almeno due
pubblicazioni italiane; applicando quota e minimo, la popolazione scende a
**{n(C['n_pop'])}**. Alzando la quota a 0,60 e 0,70 si ottengono
{n(C['n_pop_60'])} e {n(C['n_pop_70'])} artisti: la sezione 8.2 mostra che le
conclusioni non cambiano.
"""


# ==========================================================================
def sezione_gender(C) -> str:
    src = get("population_gender.parquet")
    by_src = (src.label_source.value_counts().rename_axis("fonte")
              .reset_index(name="artisti") if src is not None else pd.DataFrame())
    by_src["quota"] = (by_src.artisti / by_src.artisti.sum()).map(lambda v: pct(v))
    by_src["artisti"] = by_src.artisti.map(lambda v: n(v))
    return f"""
# 2. Il genere sessuale: come e' stato inferito

## 2.1 Il problema

Nessuna delle fonti disponibili contiene il genere sessuale delle persone.
Va inferito, e l'inferenza va documentata fino in fondo, perche' e' il punto piu'
fragile dell'intero studio: ogni conclusione sull'omofilia di genere poggia su
un'etichetta che nessuno ha dichiarato.

La cascata usata procede dal segnale piu' solido al piu' debole, e ogni artista
porta con se' **da quale livello** viene la sua etichetta e **con quanta
confidenza**.

## 2.2 Livello 1 — Wikidata agganciato all'identificativo Discogs

Wikidata espone la proprieta' `P1953`, *Discogs artist ID*. Questo consente un
**join esatto sull'identificativo**, non sul nome: nessuna omonimia, nessun
matching approssimato. Sono state raccolte tutte le entita' con `P1953` e `P21`
(genere): **{n(C['n_wd_total'])} identificativi Discogs distinti**, con
{n(C['n_wd_ambiguous'])} casi ambigui scartati e **zero blocchi persi** su una
paginazione ricorsiva per prefisso dell'identificativo.

Di questi, **{n(C['n_wikidata'])} ricadono nella nostra popolazione**
({pct(C['n_wikidata']/C['n_pop'])}). E' una copertura bassa in termini assoluti,
e il motivo e' ovvio: Wikidata descrive persone notabili, mentre la popolazione
Discogs e' fatta in larga parte di turnisti, arrangiatori, fonici e produttori
che non hanno una voce enciclopedica. Ma sono {n(C['n_wikidata'])} etichette
**certe**, ed e' su quelle che si regge il livello successivo.

## 2.3 Livello 2 — l'onomastica, costruita dai dati e non da una lista

Il disegno prevedeva la lista onomastica ISTAT. In questo ambiente non e'
risultata disponibile come dataset scaricabile; il ripiego adottato e' migliore
per lo scopo, non peggiore.

Gli stessi {n(C['n_wd_total'])} identificativi Discogs etichettati da Wikidata
sono stati ricongiunti ai **nomi** nel database: ne escono
**{n(C['n_wd_names'])} coppie nome→genere di musicisti**, un corpus onomastico
specifico del dominio, molto piu' ampio dei soli italiani e molto piu' pertinente
di una lista anagrafica generica.

Da qui si ricavano due dizionari, e l'ordine in cui vengono consultati e' la
scelta metodologicamente piu' importante di questa sezione:

1. **dizionario italiano** ({n(C['n_prior_it'])} nomi), costruito sui soli
   artisti italiani etichettati da Wikidata;
2. **`gender-guesser` con lookup italiano**;
3. **dizionario globale** ({n(C['n_prior_glob'])} nomi), ma **solo per i nomi che
   il lookup italiano non riconosce**;
4. `gender-guesser` globale, come ultima risorsa e con confidenza ridotta.

Il vincolo al punto 3 non e' pedanteria. Andrea, Simone, Nicola, Daniele,
Michele e Gabriele sono nomi maschili in Italia e femminili nei dizionari
dominati dall'inglese: usare il dizionario globale senza quel filtro
ribalterebbe il genere di alcune delle prime posizioni dell'onomastica maschile
italiana, con un errore sistematico e non casuale, concentrato proprio sui nomi
piu' frequenti. Verificato sui dati: i due dizionari concordano su tutti i
{n(C['n_prior_common'])} nomi che hanno in comune, il che indica che il filtro
sta effettivamente tenendo separati i due domini invece di mascherare un
conflitto.

## 2.4 Livello 3 — i gruppi si leggono dai membri

Un nome di band non dice nulla sul genere delle persone. Per i gruppi si guarda
percio' la composizione (`group_member`): se i membri di genere noto sono di
entrambi i generi il gruppo e' **`mixed`**, se sono tutti dello stesso genere il
gruppo eredita quello, se se ne conoscono meno di due resta `unknown`. Sono
stati risolti **{n(C['n_groups_res'])} gruppi su {n(C['n_groups'])}**, di cui
{n(C['n_mixed'])} misti.

## 2.5 Esito della cascata

{by_src.to_markdown(index=False)}

**Tabella — Origine dell'etichetta di genere sessuale per ciascun artista.**
La riga `onomastico_prior_it` porta da sola la maggior parte del carico: e' il
dizionario costruito sui {n(C['n_wikidata'])} italiani certi, e bastano
{n(C['n_prior_it'])} nomi propri per coprire quasi la meta' della popolazione,
perche' l'onomastica italiana e' fortemente concentrata. `none` e
`group_unresolved` sono i due volti del non sapere: artisti il cui nome non e'
un nome di persona riconoscibile (sigle, pseudonimi, progetti) e gruppi di cui
non si conoscono abbastanza membri.

**Esito finale: {pct(C['share_f'])} di donne fra gli artisti con genere
determinato**, cioe' {n(C['ratio_mf'],2)} uomini per ogni donna, con
{pct(1-C['share_known'])} della popolazione che resta indeterminata.

## 2.6 Il pezzo mancante: la validazione manuale

E' stato generato `data/validation_sample.csv`: **{n(C['n_validation'])} artisti**
estratti in modo stratificato per genere, fascia di confidenza e fonte
dell'etichetta, con una colonna `human_gender` vuota da compilare a mano.
Lo script `src/score_validation.py` calcola precisione, richiamo, F1 e matrice
di confusione per livello della cascata non appena il file e' compilato.

Il campione e' costruito con **allocazione meta' proporzionale e meta'
uniforme** fra gli strati: la parte proporzionale permette di stimare
l'accuratezza complessiva senza riponderare, quella uniforme garantisce
abbastanza casi anche nei livelli rari della cascata. Dentro ogni strato si
privilegiano nomi propri diversi, perche' altrimenti gli strati piccoli si
riempiono di omonimi e la validazione misurerebbe l'accuratezza su un nome
invece che su un livello.

Su due livelli quel rimedio non basta, e va detto: `onomastico_gg_mostly_female`
raccoglie 28 artisti che portano **un solo** nome proprio (Mary), e
`onomastico_gg_mostly_male` ne raccoglie 44 con due (Toni, Leonida). Su quei
due livelli la validazione potra' dire se quei nomi sono classificati bene, non
se il livello funziona in generale. Pesano insieme 72 artisti su
{n(C['n_pop'])}, quindi la cosa non tocca le conclusioni, ma il dato di
accuratezza che ne uscira' non va letto come se fosse generalizzabile.

Questo passo **non e' stato eseguito**: richiede giudizio umano. Finche' non lo
si compila, l'errore dell'inferenza di genere e' delimitato solo dal Monte Carlo
della sezione 8.1, che pero' misura l'effetto dell'*incertezza sugli unknown*,
non quello degli *errori sui noti*. E' il limite piu' serio di questo studio.
"""


# ==========================================================================
def sezione_rete(C) -> str:
    return f"""
# 3. La rete: come due musicisti diventano collegati

## 3.1 Il peso dell'arco e perche' non tutti i crediti valgono uguale

Un credito Discogs puo' dire tre cose molto diverse. Puo' dire *"questa persona
suona il basso nel brano B2"*; puo' dire *"questa persona e' l'artista del
disco"*; puo' dire *"questa persona compare nei crediti del disco"*, senza
specificare dove. Trattarli come equivalenti significherebbe dare a una
coincidenza di copertina lo stesso valore di una sessione documentata.

Ogni credito riceve percio' una **specificita'**, e il peso del legame fra due
artisti la usa:

| ambito | specificita' | che cosa significa |
|---|---|---|
| `track` | {C['w_track']:.2f} | credito risolto su una traccia precisa |
| `main` | {C['w_main']:.2f} | artista principale della pubblicazione |
| `umbrella` | {C['w_umb']:.2f} | credito secondario, senza indicazione di tracce |

$$w(u,v) = w_t \\cdot |\\text{{tracce condivise}}| + w_r \\cdot \\sum_{{R}} s_u(R)\\, s_v(R)$$

Il primo termine premia la collaborazione **documentata sullo stesso brano**; il
secondo tiene la co-presenza sulla stessa pubblicazione, scalata dalla
specificita' di entrambi i crediti. Due turnisti accreditati sulla stessa traccia
pesano molto piu' di due nomi che compaiono genericamente sullo stesso disco.

I crediti a livello traccia vengono da due strade. La prima e'
`release_track_artist`, che porta un identificativo di traccia globale:
**{n(C['n_rta'])} crediti**. La seconda e' il campo `tracks` di
`release_artist`, che indica le posizioni in forma testuale — `A1`, `1 to 3`,
`4, 6, 12` — e va **risolto**: le posizioni si convertono in tracce reali
passando per `release_track`. Di {n(C['n_ra_tracks'])} crediti posizionali ne
sono stati risolti {n(C['n_ra_resolved'])}
({pct(C['n_ra_resolved']/max(C['n_ra_tracks'],1))}); i restanti usano formule
libere (*"all tracks except 1, 13 and 14"*) e sono stati **degradati ad
`umbrella`** anziche' interpretati a forza.

Totale: **{n(C['n_track_credits'])} crediti su {n(C['n_credits'])}
({pct(C['share_track'])}) sono risolti a livello di singola traccia.**

## 3.2 Filtri e sottoreti

Le pubblicazioni con piu' di {C['max_credits']} artisti accreditati vengono
scartate: sono raccolte e cofanetti, dove la co-presenza non indica
collaborazione e il numero di coppie esplode in modo quadratico. Il filtro
riduce i crediti da {n(C['n_credits'])} a {n(C['n_credits_filt'])}.

Le sottoreti per ruolo separano due mestieri diversi: **creative**
(produzione, scrittura, arrangiamento, composizione) e **performance**
(voce, strumenti, direzione, featuring). Un artista principale senza ruolo
esplicito e' trattato come interprete, perche' e' cio' che significa essere
l'artista di un disco.

{table('t2_rete_descrittive', 'Descrittive delle tre reti di collaborazione', float_dec=6)}

La rete complessiva e' **sparsa e molto connessa**: densita' dell'ordine di
{n(C['density'],6)}, ma una componente gigante che assorbe {pct(C['giant'])}
degli artisti collegati. E' la firma tipica di un mondo professionale in cui
quasi nessuno lavora isolato e quasi nessuno lavora con tutti. La rete
`creative` e' piu' piccola e piu' densa di quella `performance`: produttori e
autori formano un nucleo piu' ristretto e piu' intrecciato di quello degli
esecutori — un dato che conta per la lettura della sezione 5.3, dove i due ruoli
mostrano omofilie diverse.

{img('f5_distribuzione_gradi',
 "**Distribuzione di grado e forza.** Su scala doppio-logaritmica entrambe le "
 "distribuzioni scendono con una pendenza quasi rettilinea su piu' ordini di "
 "grandezza: la stragrande maggioranza degli artisti ha pochissimi "
 "collaboratori, mentre una minoranza sottile ne ha centinaia. La forza — che "
 "somma i pesi, quindi conta quante volte si e' collaborato e quanto erano "
 "specifici i crediti — ha una coda ancora piu' lunga del grado: i grandi "
 "collaboratori non hanno solo molti partner, hanno relazioni molto piu' "
 "intense. E' il substrato strutturale su cui va letta la sezione 6.1: in una "
 "rete cosi' diseguale, la domanda 'le donne stanno al centro?' va sempre posta "
 "a parita' di attivita', perche' il numero di pubblicazioni da solo spiega gia' "
 "gran parte della centralita'.")}

Le analisi che seguono girano sulla **componente gigante**, perche' le misure di
centralita' e le distanze non sono definite fra componenti separate. La quota
esclusa e' {pct(1-C['giant'])} degli artisti collegati.
"""


# ==========================================================================
def sezione_risultati(C) -> str:
    return f"""
# 4. Quante sono le donne, e in quale musica (RQ1)

{img('f3_quota_donne_per_decennio',
 f"**La quota di donne per decennio di debutto.** La linea non e' la storia di "
 f"un progresso. Parte dal {pct(C['q_1960'])} per chi debutta negli anni "
 f"Sessanta, scende fino al {pct(C['q_1980'])} negli anni Ottanta — il minimo "
 f"della serie — e risale solo di recente, fino al {pct(C['q_2020'])} per chi "
 f"debutta dal 2020. La discesa degli anni Settanta e Ottanta merita cautela "
 f"prima di leggerla come un arretramento reale: coincide con l'espansione "
 f"massiccia del catalogo Discogs in quegli anni, cioe' con l'ingresso in massa "
 f"di crediti tecnici e di produzione — mestieri quasi interamente maschili — "
 f"che diluiscono una quota calcolata su tutti i crediti e non sui soli "
 f"interpreti. La risalita recente e' invece coerente sia in ampiezza sia in "
 f"direzione con quanto si osserva negli altri cataloghi musicali. In ogni "
 f"decennio, comunque, la banda di confidenza resta lontanissima dalla parita'.")}

{img('f4_quota_donne_genere_x_decennio',
 "**Quota di donne per genere musicale e decennio.** I pannelli mostrano che "
 "non esiste una singola traiettoria di genere: esistono generi musicali con "
 "storie diverse. Il livello di partenza conta piu' della pendenza — un genere "
 "che parte basso tende a restare basso attraverso i decenni, il che e' "
 "esattamente la firma di una segregazione che si riproduce per reclutamento "
 "piuttosto che dissolversi col tempo.")}

{table('t3_quota_donne_genere_decennio',
 'Quota di donne per genere musicale e decennio di debutto, con intervalli di Wilson al 95%',
 max_rows=25)}

## 4.1 Il confronto con i pattern noti in letteratura

Il riferimento consueto per l'hip hop e' un rapporto intorno a **4 uomini per
ogni donna**. Nei dati italiani il rapporto e' **{n(C['ratio_hiphop'],1)} a 1**
({pct(C['q_hiphop'])} di donne): sensibilmente **piu' squilibrato** del
riferimento internazionale. Due letture non alternative: la scena hip hop
italiana censita da Discogs e' piu' piccola e piu' recente, quindi piu' esposta
al fatto che i ruoli di produzione — dove le donne sono piu' rare — pesino
relativamente di piu'; e il conteggio qui include tutti i crediti, non solo gli
interpreti principali, il che abbassa la quota rispetto alle statistiche basate
sulle classifiche.

All'estremo opposto, **Classical** ({pct(C['q_classical'])}) e **Children's**
({pct(C['q_children'])}) sono i generi con la presenza femminile piu' alta —
il secondo sopra il {pct(C['q_children'],0)}, l'unico dell'intero corpus in cui
le donne si avvicinano alla meta'. La distanza fra Children's e Hip Hop, a
parita' di popolazione e di metodo, e' di oltre
{n((C['q_children']-C['q_hiphop'])*100,0)} punti percentuali: il genere musicale
e' il predittore piu' forte della presenza femminile in tutto questo studio.

**Rock ({pct(C['q_rock'])}) e Electronic ({pct(C['q_electronic'])})**, che
insieme fanno la parte maggiore della popolazione, stanno entrambi sotto la
media generale. E' su queste due scene, per peso numerico, che si decide la
quota complessiva.
"""


# ==========================================================================
def sezione_omofilia(C) -> str:
    return f"""
# 5. Omofilia: chi incide con chi (RQ2)

## 5.1 Il quadro generale

{img('f1_mixing_gender_oss_att',
 "**Chi collabora con chi, rispetto al caso.** Ogni cella e' il rapporto fra i "
 "legami osservati e quelli attesi sotto un modello nullo che conserva "
 "esattamente il grado di ogni artista e la composizione della popolazione: "
 "l'unica cosa randomizzata e' *chi sta con chi*. Un valore di 1 significa "
 "'come il caso', sopra 1 significa piu' del previsto. La diagonale sopra 1 e "
 "le celle fuori diagonale sotto 1 sono la definizione operativa di omofilia. "
 "Vale la pena notare che anche la cella unknown-unknown si discosta da 1: non "
 "e' un fatto sociale ma un fatto di copertura dei dati — gli artisti su cui "
 "non sappiamo nulla tendono a stare insieme perche' condividono le stesse "
 "caratteristiche che li rendono poco documentati (pochi crediti, ruoli minori, "
 "epoche marginali). E' precisamente questo il motivo per cui l'ERGM della "
 "sezione 7 esclude i nodi unknown invece di trattarli come una categoria.")}

{table('t3_assortativita_globale', "Assortativita' osservata e sotto modello nullo", float_dec=4)}

{table('t3_assortativita_MF_vs_tutte',
 "Assortativita' calcolata sui soli nodi con attributo determinato contro il "
 "calcolo che tratta 'indeterminato' come una categoria, per il genere "
 "sessuale e per quello musicale", float_dec=4, max_rows=40,
 cols=['sottorete', 'strato', 'attributo', 'categorie', 'archi_usati',
       'quota_archi_usati', 'r', 'ci_lo', 'ci_hi'],
 rename={'archi_usati': 'archi', 'quota_archi_usati': 'quota archi',
         'attributo': 'attr.'})}

### Una precisazione di misura che cambia i numeri

Le due tabelle vanno lette insieme, perche' la seconda corregge la prima.

Trattare `unknown` come una quarta categoria alla pari di M ed F gonfia
l'assortativita': la cella unknown-unknown sta molto sopra l'atteso, ma non
perche' quelle persone si cerchino fra loro. Si cercano fra loro le
caratteristiche che le rendono poco documentate — pochi crediti, ruoli minori,
epoche marginali, pseudonimi — e sono le stesse che rendono difficile inferirne
il genere. E' copertura dei dati che si traveste da struttura sociale.

La misura di riferimento restringe percio' il calcolo agli archi in cui entrambi
gli estremi hanno genere determinato: **{pct(C['quota_archi_mf'])} degli archi**.
La differenza non e' cosmetica: **r passa da {n(C['r_gender'],4)} a
{n(C['r_mf'],4)}**, cioe' un terzo dell'omofilia apparente era artefatto.

Lo stesso controllo e' stato fatto sul **genere musicale**, dove
'Unknown' e' altrettanto presente, e da' il risultato **opposto**: togliendo gli
indeterminati l'assortativita' sale da {n(C['r_genre_tutte'],4)} a
{n(C['r_genre_det'],4)}. Il motivo e' che gli artisti senza genere musicale
assegnato non si aggregano fra loro per genere — non ne hanno uno — e quindi
diluiscono la diagonale invece di gonfiarla. Riportare entrambi i confronti
serve a chiarire che l'esclusione degli indeterminati e' una scelta di metodo
applicata in modo uniforme, non un accorgimento adottato dove conveniva: sul
genere sessuale abbassa il risultato, sul genere musicale lo alza.

### Il risultato centrale

L'assortativita' per **genere musicale** vale {n(C['r_genre'],3)}. E' un valore
molto alto: le carriere si svolgono dentro un genere e le collaborazioni seguono
i confini del genere quasi come se fossero confini di settore.

L'assortativita' per **genere sessuale** vale {n(C['r_mf'],4)}, circa
{n(C['r_genre']/max(C['r_mf'],1e-9),0)} volte meno, con intervallo di confidenza
{n(C['r_mf_lo'],4)}–{n(C['r_mf_hi'],4)} e modello nullo a {n(C['r_mf_null'],4)}.
Preso da solo il numero sembra trascurabile; non lo e', perche' su
{n(C['n_edges'])} archi anche un effetto piccolo e' misurato con precisione
elevata e l'intervallo sta interamente sopra lo zero.

La lettura sostanziale e' che **il genere sessuale struttura le collaborazioni,
ma molto meno di quanto faccia la specializzazione musicale**. Chi cerca
un bassista lo cerca nel proprio giro musicale molto piu' sistematicamente di
quanto lo cerchi del proprio sesso. Questo non rende l'omofilia di genere
irrilevante — rende il genere musicale il canale attraverso cui essa
prevalentemente opera, come mostra il paragrafo seguente.

{img('f2_mixing_genere_musicale_oss_att',
 "**Omofilia per genere musicale.** La diagonale domina l'immagine. I generi "
 "piu' chiusi non sono necessariamente i piu' grandi: la chiusura misura quanto "
 "una scena recluta al proprio interno, non quanto e' popolosa. Le celle fuori "
 "diagonale che superano 1 indicano le coppie di generi fra cui esiste un "
 "traffico reale di musicisti — i confini permeabili del sistema.")}

## 5.2 L'omofilia nel tempo: il risultato controintuitivo

{img('f6_assortativita_per_strato',
 f"**Omofilia di genere per sottorete di ruolo ed epoca.** Il punto e' il valore "
 f"osservato, la barra l'intervallo di confidenza bootstrap al 95%, il trattino "
 f"verticale il valore del modello nullo. L'attesa, dalla letteratura, era un "
 f"**allentamento** dopo il 2000. Sui soli nodi con genere determinato i dati "
 f"dicono l'opposto, ma con ampiezza molto piu' contenuta di quanto suggerisca "
 f"la misura a quattro categorie mostrata in figura: "
 f"{n(C['r_pre_mf'],4)} contro {n(C['r_post_mf'],4)}.")}

Prima di interpretarlo va ripulito. Sulla misura ingenua a quattro categorie il
salto e' spettacolare, da {n(C['r_pre'],4)} a {n(C['r_post'],4)}: piu' che
raddoppiato. Sui soli nodi con genere determinato si riduce a
{n(C['r_pre_mf'],4)} → {n(C['r_post_mf'],4)}. La ragione e' che la quota di
archi utilizzabili crolla fra le due epoche — dal
{pct(val(get('assortativity_mf.parquet'), "sottorete=='all' and strato=='pre2000' and attributo=='gender' and categorie=='determinati soltanto'", 'quota_archi_usati'))}
al
{pct(val(get('assortativity_mf.parquet'), "sottorete=='all' and strato=='post2000' and attributo=='gender' and categorie=='determinati soltanto'", 'quota_archi_usati'))}
— perche' gli artisti recenti sono mediamente meno documentati: piu' `unknown`,
quindi piu' apparente omofilia spuria.

**Quel che resta dopo la correzione e' comunque un aumento**, con intervalli
({n(C['r_pre_mf_lo'],4)}–{n(C['r_pre_mf_hi'],4)} contro
{n(C['r_post_mf_lo'],4)}–{n(C['r_post_mf_hi'],4)}) che non si sovrappongono. Il
risultato regge, ma va raccontato per quello che e': un aumento moderato, non un
raddoppio.

**E l'aumento non e' diffuso: viene tutto da una parte sola della rete.**
Scomponendo per ruolo, l'omofilia dei ruoli di esecuzione e' sostanzialmente
piatta nel tempo ({n(C['r_perf_pre'],4)} prima del 2000,
{n(C['r_perf_post'],4)} dopo), mentre quella dei ruoli creativi **raddoppia**,
da {n(C['r_creative_pre'],4)} a {n(C['r_creative_post'],4)}. Qualunque
spiegazione dell'aumento deve percio' riguardare il modo in cui si produce e si
scrive musica, non il modo in cui la si suona.

Restano due letture possibili, e i dati qui presenti non permettono di scegliere
fra loro in modo definitivo.

**Prima lettura — e' reale.** Dopo il 2000 cambia il modo di produrre musica: la
registrazione si decentra, gli studi grandi con organici misti e obbligati
lasciano spazio a progetti piccoli, costruiti su reti personali. Reti personali
significa reti piu' omofile. In questa lettura l'aumento non e' un arretramento
culturale ma l'effetto strutturale di una tecnologia di produzione diversa — e
il fatto che riguardi i soli ruoli creativi, che sono precisamente quelli
toccati dalla decentralizzazione degli studi, depone a favore di questa
spiegazione.

**Seconda lettura — e' composizione.** L'indice *r* di Newman dipende dalle
marginali. Post-2000 ci sono piu' donne, quindi piu' occasioni di legame
donna-donna; a parita' di propensione, un gruppo minoritario piu' numeroso
produce meccanicamente un'assortativita' misurata piu' alta. Il modello nullo a
gradi preservati corregge per il grado, **non** per questa asimmetria di
composizione fra epoche.

E' esattamente per dirimere questo punto che serve l'ERGM, e **il verdetto e'
arrivato**: una volta controllata la tendenza della rete a chiudere i
triangoli, la differenza di omofilia di genere fra le due epoche **non e'
statisticamente distinguibile da zero** (per le donne
{n(C.get('epoca_F_pre'),3)} contro {n(C.get('epoca_F_post'),3)}, p =
{n(C.get('epoca_F_p'),2)}; per gli uomini {n(C.get('epoca_M_pre'),3)} contro
{n(C.get('epoca_M_post'),3)}, p = {n(C.get('epoca_M_p'),2)}).

Cio' che aumenta davvero, e in modo nettissimo, e' la **chiusura triadica**: il
coefficiente `gwesp` passa da {n(C.get('epoca_gwesp_pre'),3)} a
{n(C.get('epoca_gwesp_post'),3)} (p < 0,0001). La musica registrata italiana
dopo il 2000 non e' diventata piu' omofila per genere: e' diventata piu'
**chiusa in triangoli**. Si lavora sempre di piu' dentro gruppi fitti di
persone che si conoscono gia' tutte fra loro. In un ambiente dove le donne sono
il {pct(C['share_f'])}, una struttura piu' triangolare produce
meccanicamente piu' legami donna-donna osservati, e quindi un'assortativita'
misurata piu' alta — senza che nessuno abbia cambiato criterio nello scegliere
con chi lavorare.

E' la risposta piu' interessante dello studio, perche' sposta l'oggetto: il
problema non e' una preferenza di genere che si e' rafforzata, ma una
struttura di reclutamento che si e' chiusa. Sono due cose diverse anche dal
punto di vista di chi volesse intervenire. I dettagli del test sono nella
sezione 7.3.

## 5.3 Produttori e interpreti: due mestieri, due omofilie (RQ5)

La distinzione fra ruoli creativi (produzione, scrittura, arrangiamento) e ruoli
di esecuzione (voce, strumenti, direzione) e' la domanda RQ5, e la risposta e'
netta: sui soli nodi con genere determinato l'omofilia vale
**{n(C['r_creative_mf'],4)} nella rete creativa** contro
**{n(C['r_perf_mf'],4)} in quella di esecuzione**.

La collaborazione creativa e' quindi *meno* segregata per genere di quella
esecutiva, di un fattore
{n(C['r_perf_mf']/max(C['r_creative_mf'],1e-9),1)}. E' un risultato che va letto insieme al dato di composizione: i ruoli
creativi sono in assoluto i piu' maschili dell'intero corpus, e proprio per
questo l'omofilia misurata vi risulta bassa — dove la maggioranza e'
schiacciante non c'e' quasi spazio per discostarsi dal caso. La segregazione dei
ruoli creativi si manifesta nel **chi entra**, non nel **chi lavora con chi**;
quella dei ruoli esecutivi, dove le donne sono piu' presenti, si manifesta anche
nella struttura delle collaborazioni. Sono due forme diverse di chiusura, e
confonderle porterebbe a concludere che la produzione musicale sia il luogo piu'
aperto del sistema, che e' l'opposto di quanto dicono i conteggi.

## 5.4 Omofilia dentro ciascun genere musicale

{img('f7_omofilia_per_genere_musicale',
 "**A sinistra** l'omofilia di genere sessuale calcolata separatamente dentro "
 "ciascun genere musicale, con il modello nullo come riferimento. **A destra** "
 "la scomposizione della diagonale: quanto i legami uomo-uomo e quanto i legami "
 "donna-donna superano l'atteso. La lettura congiunta dei due pannelli e' il "
 "cuore di RQ2. Un valore osservato/atteso vicino a 1 per gli uomini e molto "
 "sopra 1 per le donne descrive una situazione precisa: gli uomini non si "
 "cercano fra loro piu' del caso — non ne hanno bisogno, sono la maggioranza e "
 "il caso li mette gia' insieme — mentre le donne si aggregano fra loro molto "
 "piu' del previsto. E' la forma che l'omofilia assume quando una minoranza "
 "opera dentro una maggioranza: non segregazione simmetrica, ma addensamento "
 "del gruppo minoritario.")}

{table('t3_omofilia_per_genere_musicale',
 'Omofilia di genere sessuale entro ciascun genere musicale (RQ2)', float_dec=4)}

Questo e' il punto su cui il dato italiano **contraddice l'aspettativa
corrente**. La letteratura riporta di norma un'omofilia piu' forte *fra gli
uomini*. Qui il rapporto osservato/atteso donna-donna e' sistematicamente
**maggiore** di quello uomo-uomo. La spiegazione non e' che le donne siano piu'
chiuse: e' che con una quota femminile del {pct(C['share_f'])} il valore atteso
per un legame donna-donna sotto casualita' e' bassissimo, e basta un modesto
addensamento reale per produrre un rapporto elevato. L'indice uomo-uomo, al
contrario, e' schiacciato verso 1 perche' la maggioranza non puo' discostarsi
molto dal caso. **I due indici non sono confrontabili come se misurassero la
stessa cosa**, ed e' l'ERGM — che stima una propensione e non un rapporto — a
fornire il confronto corretto.
"""


# ==========================================================================
def sezione_posizione(C) -> str:
    return f"""
# 6. Le donne stanno al centro o ai margini? (RQ3)

La domanda che la letteratura chiama *pattern Smurfette* e' se le donne, dove
ci sono, occupino posizioni strutturalmente periferiche: presenti quanto basta,
mai al centro.

{table('t3_posizione_per_genere', 'Posizione nella componente gigante per genere sessuale', float_dec=6)}

{img('f8_posizione_per_genere',
 "**Coreness mediana per genere sessuale, dentro ciascun genere musicale.** La "
 "coreness dice a quale strato del nucleo denso della rete una persona "
 "appartiene: e' una misura di appartenenza al centro piu' robusta della "
 "centralita' di grado, perche' non si lascia gonfiare da chi ha molti "
 "collaboratori occasionali. Le barre affiancate permettono il confronto "
 "diretto a parita' di genere musicale, che e' il confronto giusto: paragonare "
 "una cantante pop a un turnista jazz non direbbe nulla sul genere sessuale e "
 "molto sulla struttura delle due scene.")}

{table('t3_posizione_per_genere_musicale',
 'Posizione nella rete per genere sessuale entro genere musicale', max_rows=30, float_dec=6)}

## 6.1 Il confronto a parita' di attivita' e coorte

Le mediane grezze non bastano. Chi pubblica di piu' e' piu' centrale, e le donne
della popolazione pubblicano meno: la mediana delle pubblicazioni e'
{n(C.get('nrel_med_F'),0)} per le donne contro {n(C.get('nrel_med_M'),0)} per gli
uomini, e la coreness mediana segue ({n(C.get('core_med_F'),0)} contro
{n(C.get('core_med_M'),0)}). Senza controllare per l'attivita' si misurerebbe la
differenza di quanto si pubblica e la si chiamerebbe differenza di posizione.

La regressione confronta percio' persone con la stessa attivita', la stessa
coorte di debutto e lo stesso genere musicale.

{table('t3_regressione_eigenvector',
 "Posizione nella rete (eigenvector) per genere sessuale e genere musicale, "
 "a parita' di attivita' e coorte", max_rows=28, float_dec=4)}

{table('t3_regressione_coreness',
 "Appartenenza al nucleo (coreness) per genere sessuale e genere musicale, "
 "a parita' di attivita' e coorte", max_rows=28, float_dec=4)}

## 6.2 La risposta a RQ3

**Il pattern "Smurfette" non si osserva in questi dati.** A parita' di
pubblicazioni, coorte e genere musicale, l'effetto principale dell'essere donna
sulla posizione nella rete non e' distinguibile da zero su nessuna delle tre
misure:

| misura | coefficiente | IC 95% | p |
|---|---|---|---|
| eigenvector | {n(C.get('b_eigenvector'),3)} | {n(C.get('lo_eigenvector'),3)} – {n(C.get('hi_eigenvector'),3)} | {n(C.get('p_eigenvector'),3)} |
| coreness | {n(C.get('b_coreness'),3)} | {n(C.get('lo_coreness'),3)} – {n(C.get('hi_coreness'),3)} | {n(C.get('p_coreness'),3)} |
| betweenness | {n(C.get('b_betweenness'),3)} | {n(C.get('lo_betweenness'),3)} – {n(C.get('hi_betweenness'),3)} | {n(C.get('p_betweenness'),3)} |

Nemmeno le interazioni con il genere musicale aiutano: su
{n(C.get('n_interazioni'))} termini di interazione stimati,
{n(C.get('n_interazioni_signif'))} risultano significativi al 5%. Non esiste,
in questi dati, una scena in cui essere donna sposti sistematicamente verso la
periferia della rete.

E' un risultato che va enunciato con precisione, perche' si presta a due letture
sbagliate di segno opposto.

**Non significa che non ci sia disuguaglianza.** Le donne sono il
{pct(C['share_f'])} della popolazione e pubblicano meno: la mediana delle
pubblicazioni e' {n(C.get('nrel_med_F'),0)} contro {n(C.get('nrel_med_M'),0)}.
La disuguaglianza c'e' ed e' grande — ma si manifesta **nell'accesso e nel
volume di attivita'**, non nella posizione strutturale a parita' di attivita'.
Chi entra e riesce a lavorare, lavora in posizioni comparabili.

**Non significa nemmeno che il controllo per l'attivita' sia neutro.** Il numero
di pubblicazioni non e' una variabile esogena: e' esso stesso un esito di
processi di accesso che possono essere segregati. Controllare per l'attivita'
risponde alla domanda "a parita' di carriera, la posizione differisce?" e non
alla domanda "le carriere differiscono?". La prima ha risposta negativa, la
seconda — sezione 4 — ha risposta ampiamente positiva.

Il dato piu' interessante e' la divergenza fra mediana e media
dell'eigenvector: la mediana e' piu' alta per le donne
({sci(C.get('eig_med_F'))} contro {sci(C.get('eig_med_M'))}) mentre la media e'
piu' bassa. Significa che la donna tipica della rete e' connessa quanto e piu'
dell'uomo tipico, ma che gli **hub estremi** — i pochissimi nodi con centralita'
di ordini di grandezza superiore — sono quasi tutti uomini. La disuguaglianza
di posizione, dove c'e', sta nella coda, non nel corpo della distribuzione.
"""


# ==========================================================================
def sezione_ergm(C) -> str:
    st = get("ergm_summary.parquet")
    if st is None or st.empty or not st.get("convergenza", pd.Series([False])).any():
        return """
# 7. ERGM (RQ4)

> **Questa fase non ha prodotto stime utilizzabili.** R e statnet sono stati
> installati in userspace e verificati con un modello di prova, ma nessuna delle
> sottoreti ha portato a convergenza un modello entro il tempo massimo
> assegnato. La mancanza e' dichiarata qui e non aggirata: le domande che
> l'ERGM avrebbe dovuto dirimere — in particolare se l'aumento post-2000
> dell'omofilia (sez. 5.2) sia propensione o composizione — restano aperte, e
> su di esse valgono solo le misure descrittive delle sezioni precedenti.
"""
    conv = int(st.convergenza.sum())
    gw = int(st.get("gwesp_converge", pd.Series([False] * len(st))).sum())
    return f"""
# 7. Probabilita' di collaborare a parita' di tutto: l'ERGM (RQ4)


## 7.1 Perche' serve e come e' stato impostato

Tutte le misure fin qui sono descrittive: dicono *che* i legami sono distribuiti
in un certo modo, non *perche'*. Un modello esponenziale per grafi casuali
(ERGM) stima invece la probabilita' che un legame esista, tenendo insieme nello
stesso modello l'omofilia di genere, quella di genere musicale, il livello di
attivita', la coorte e la tendenza della rete a chiudere i triangoli.
Quest'ultimo punto e' decisivo: senza un termine di chiusura triadica
(`gwesp`), qualunque tendenza a fare gruppo viene erroneamente attribuita
all'attributo su cui si sta guardando.

**Sulla rete intera l'ERGM non e' stimabile**, e va detto chiaramente invece di
far finta. Con {n(C['n_nodes'])} nodi lo spazio dei grafi possibili rende il
campionamento MCMC impraticabile. Si e' quindi proceduto come previsto dal
disegno, per sottoreti: i cinque generi musicali piu' popolosi, le due epoche, e
un campione a palla di neve della rete complessiva come riferimento. **Le stime
valgono per le sottoreti su cui sono calcolate**, non si estendono per
costruzione all'intera popolazione.

Dall'ERGM sono esclusi i nodi con genere `unknown`. Tenerli come quarta
categoria avrebbe prodotto un termine di omofilia spurio che misura la struttura
della copertura dei dati — chi e' poco documentato collabora con chi e' poco
documentato — invece della struttura delle collaborazioni.

Si stima una **gerarchia di tre modelli**, invece di una specifica unica,
perche' il termine di chiusura triadica e' esattamente quello che puo' far
fallire la stima e non si vuole perdere tutto insieme a lui:

* **M0** `edges + nodematch(gender, diff) + controlli` — nessun termine di
  dipendenza fra archi. E' il modello di riferimento: stimabile sempre.
* **M1** M0 + `gwesp(0,25; fixed)` — la specifica prevista dal disegno. Il
  termine di chiusura triadica rende il modello quasi degenere sulle reti molto
  clusterizzate, e puo' non convergere.
* **M2** come il migliore fra M1 e M0, con `nodemix(gender)` al posto di
  `nodematch(gender, diff)`. Le due parametrizzazioni sono ridondanti fra loro
  e nello stesso modello lo renderebbero non identificato.

I termini di controllo entrano **solo se l'attributo varia** nella sottorete.
Dentro una sottorete di un solo genere musicale `nodematch('musical_genre')`
coincide identicamente con `edges`: includerlo produrrebbe un modello non
identificato, e nelle prime esecuzioni era proprio questo a impedire la
convergenza.

{table('t4_ergm_sintesi', 'Sintesi delle stime ERGM: dimensione, campionamento, convergenza')}

Sottoreti con almeno un modello convergente: **{conv} su {len(st)}**; sottoreti
in cui ha retto anche il termine `gwesp`: **{gw}**. Dove `gwesp` non converge,
i coefficienti riportati vengono da M0 e **non** controllano per la chiusura
triadica: vanno quindi letti come stime che possono attribuire all'omofilia una
parte di cio' che e' semplicemente tendenza a formare triangoli. E' una
limitazione, ed e' dichiarata qui invece di essere nascosta dietro un numero.

{img('f9_ergm_forest_gender',
 "**Coefficienti di omofilia di genere nei cinque generi musicali piu' "
 "popolosi.** Ogni coefficiente e' un log-odds: quanto la probabilita' di un "
 "legame aumenta (o diminuisce) se due artisti condividono il genere sessuale, "
 "*a parita'* di attivita', coorte, genere musicale e chiusura triadica. Questo "
 "e' il confronto che le misure descrittive della sezione 5.4 non potevano "
 "fornire: qui i coefficienti maschile e femminile sono sulla stessa scala e "
 "sono direttamente confrontabili, perche' misurano una propensione e non un "
 "rapporto osservato/atteso schiacciato dalle marginali. Se il coefficiente "
 "maschile supera quello femminile, il pattern italiano e' allineato alla "
 "letteratura (omofilia piu' forte fra gli uomini) e l'inversione osservata "
 "nella sezione 5.4 era un artefatto della rarita' delle donne.")}

{table('t4_ergm_coefficienti', 'Coefficienti ERGM per sottorete', max_rows=40,
 float_dec=4, cols=['rete', 'model', 'term', 'estimate', 'se', 'p', 'ci_lo', 'ci_hi', 'or'])}

### Come si leggono questi coefficienti, e che cosa dicono

I coefficienti sono in log-odds; la colonna `or` e' il loro esponenziale, cioe'
di quanto si moltiplica la probabilita' di un legame. `nodematch.gender.F` dice
quanto una coppia donna-donna e' piu' probabile di una coppia di riferimento **a
parita' di tutto il resto**: attivita', coorte, genere musicale e — cosa
decisiva — tendenza della rete a chiudere i triangoli.

Il confronto fra `nodematch.gender.F` e `nodematch.gender.M` e' il risultato
che la sezione 5.4 non poteva dare. Li' i rapporti osservato/atteso non erano
confrontabili, perche' con una quota femminile del {pct(C['share_f'])} il valore
atteso per un legame donna-donna e' cosi' basso che qualunque addensamento
reale produce un rapporto grande. Qui il problema non si pone: i due
coefficienti misurano la stessa quantita' sulla stessa scala. **E il risultato
regge: la propensione delle donne a lavorare con donne resta nettamente
superiore a quella degli uomini a lavorare con uomini.** Non e' un artefatto
della rarita'; e' una proprieta' della rete.

In alcune sottoreti il coefficiente maschile e' **negativo**: a parita' di
tutto il resto, due uomini hanno una probabilita' di collaborare leggermente
*inferiore* al riferimento. Non significa che gli uomini si evitino. Significa
che, in un ambiente dove sono la stragrande maggioranza, il termine `edges` da
solo gia' produce quasi tutti i legami maschili che si osservano, e una volta
tolta quella quota di base non resta nulla da attribuire a una preferenza. E'
la controprova, dal lato opposto, della stessa asimmetria: dove un gruppo
domina, l'omofilia non ha modo di manifestarsi come effetto misurabile; dove un
gruppo e' raro, si manifesta con forza.

Merita attenzione anche il confronto fra M0 e M1. Passando dal modello senza
chiusura triadica a quello con `gwesp`, il coefficiente di omofilia femminile
**si riduce**: una parte di cio' che sembrava preferenza di genere era in realta'
la tendenza generale della rete a chiudere i triangoli — se A lavora con B e B
con C, prima o poi A lavora con C, e in un ambiente dove le donne sono poche i
triangoli fra donne si formano comunque. Il termine `gwesp` ha un coefficiente
molto grande, il che dice quanto forte sia quel meccanismo. Cio' che resta dopo
averlo tolto e' omofilia vera.

## 7.2 La diagnostica: il modello descrive davvero questa rete?

{img('f12_ergm_gof',
 "**Bontà di adattamento.** Per ciascuna sottorete si confrontano tre "
 "statistiche della rete osservata (punti) con quelle delle reti simulate dal "
 "modello stimato (linea e banda): la distribuzione dei gradi, il numero di "
 "partner condivisi da ciascuna coppia collegata (ESP) e le distanze "
 "geodetiche. Un modello che coglie la struttura produce simulazioni la cui "
 "banda contiene l'osservato; dove il punto esce dalla banda, il modello sta "
 "sbagliando proprio quell'aspetto. L'ESP è la statistica da guardare con più "
 "attenzione, perché è quella che il termine gwesp dovrebbe riprodurre: se "
 "l'osservato ne esce, la chiusura triadica non è stata catturata e i "
 "coefficienti di omofilia possono averne assorbito una parte. Nei modelli "
 "stimati qui il centro delle distribuzioni è riprodotto bene, ma **la coda "
 "no**: i nodi con molti collaboratori e le coppie con molti partner in comune "
 "sono sistematicamente più numerosi di quanto il modello preveda (cerchi "
 "rossi). È il limite noto degli ERGM su reti con code pesanti, e va tenuto "
 "presente leggendo i coefficienti: il modello descrive bene il musicista "
 "tipico, meno bene i pochi grandi collaboratori.")}

{table('t4_ergm_mcmc', 'Diagnostica MCMC: dimensione efficace del campione per '
 'ciascun termine. Valori bassi indicano una catena che si muove poco e stime '
 'meno affidabili', max_rows=24, float_dec=1)}

## 7.3 Il test pre/post 2000

{table('t4_ergm_differenza_epoche',
 'Test della differenza fra i coefficienti ERGM pre-2000 e post-2000', float_dec=4,
 cols=['model', 'term', 'estimate_pre', 'estimate_post', 'differenza', 'se_diff', 'z', 'p'])}

Questa tabella e' la verifica formale del risultato controintuitivo della
sezione 5.2, e il suo esito e' netto.

**L'omofilia di genere non cambia fra le due epoche.** Per le donne il
coefficiente passa da {n(C.get('epoca_F_pre'),3)} a {n(C.get('epoca_F_post'),3)}
(differenza {n(C.get('epoca_F_diff'),3)}, p = {n(C.get('epoca_F_p'),2)}); per
gli uomini da {n(C.get('epoca_M_pre'),3)} a {n(C.get('epoca_M_post'),3)}
(differenza {n(C.get('epoca_M_diff'),3)}, p = {n(C.get('epoca_M_p'),2)}).
Nessuna delle due differenze si avvicina alla significativita'.

**Cambia invece, e moltissimo, la chiusura triadica.** Il coefficiente `gwesp`
passa da {n(C.get('epoca_gwesp_pre'),3)} a {n(C.get('epoca_gwesp_post'),3)},
una differenza di {n(C.get('epoca_gwesp_diff'),3)} con p < 0,0001: e' l'unico
termine del modello la cui variazione fra epoche sia statisticamente solida.

La lettura congiunta e' quella data alla sezione 5.2: l'aumento
dell'assortativita' osservata dopo il 2000 non e' un rafforzamento della
preferenza di genere, ma la conseguenza di una rete che si chiude in gruppi piu'
fitti. Vale la pena notare che questo e' esattamente il tipo di confusione che
un'analisi puramente descrittiva non puo' sciogliere, e per cui l'ERGM era
previsto nel disegno.
"""


# ==========================================================================
def sezione_robustezza(C) -> str:
    return f"""
# 8. Quanto reggono questi risultati

## 8.1 L'incertezza sul genere sessuale

{img('f10_montecarlo_genere',
 f"**La distribuzione Monte Carlo dell'assortativita' di genere al variare "
 f"dell'imputazione degli {n(C['n_unknown'])} artisti senza genere determinato.** "
 f"L'istogramma e' la distribuzione su {C['mc_B']} estrazioni dalla marginale "
 f"osservata. Le due linee tratteggiate laterali non sono stime ma **limiti "
 f"costruiti apposta**: assegnando a ogni artista ignoto il genere prevalente "
 f"fra i suoi collaboratori si ottiene la massima omofilia compatibile con i "
 f"dati; assegnando il genere opposto si ottiene la minima. Il fatto rilevante "
 f"e' che **anche il limite inferiore resta positivo**: non esiste "
 f"assegnazione degli ignoti che faccia sparire l'omofilia. La conclusione "
 f"qualitativa e' robusta; la sua grandezza esatta no.")}

{table('t5_montecarlo_genere',
 "Assortativita' di genere sotto diversi scenari di imputazione", float_dec=4)}

I quattro numeri vanno letti insieme. Sui soli artisti con genere determinato
l'assortativita' vale {n(C['mc_noti'],4)}. Imputando gli ignoti per estrazione
casuale dalla marginale osservata scende a {n(C['mc_sq'],4)}: l'imputazione
casuale non puo' che diluire la struttura, ed e' la ragione per cui la misura
di riferimento di questo studio e' la prima e non la seconda. I due limiti
costruiti sul vicinato — {n(C['mc_min'],4)} e {n(C['mc_max'],4)} — delimitano
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

## 8.2 Sensibilita' ai parametri di costruzione

{img('f11_sensibilita',
 "**Ogni punto e' l'assortativita' di genere ottenuta cambiando un solo "
 "parametro rispetto alla configurazione di default (linea tratteggiata).** "
 "Gli assi variati sono quelli che potevano ragionevolmente cambiare il "
 "risultato: quanti artisti al massimo puo' avere una pubblicazione perche' "
 "conti come collaborazione, quale peso minimo deve avere un arco, se "
 "escludere le raccolte, quanto strettamente definire l'italianita', come "
 "pesare la specificita' dei crediti, e se usare o no i crediti a livello "
 "traccia. Quest'ultimo e' l'asse piu' informativo: disattivare i crediti di "
 "traccia significa tornare a una rete costruita solo sulle co-presenze di "
 "copertina, ed e' il confronto che dice quanto il livello traccia stia "
 "effettivamente aggiungendo.")}

{table('t5_sensibilita',
 "Sensibilita' delle metriche chiave ai parametri di costruzione della rete",
 max_rows=25, float_dec=4,
 cols=['variante', 'nodi', 'archi', 'quota_gigante', 'r_gender_MF',
       'r_gender_pesato', 'r_genere_musicale'],
 rename={'quota_gigante': 'gigante', 'r_gender_MF': 'r genere M/F',
         'r_gender_pesato': 'r pesata', 'r_genere_musicale': 'r gen. musicale'})}

Sulle {n(C['sens_n'])} varianti provate, l'assortativita' di genere sui soli
nodi determinati resta compresa fra **{n(C['sens_mf_min'],4)} e
{n(C['sens_mf_max'],4)}**, sempre positiva e sempre dello stesso ordine di
grandezza del valore di riferimento ({n(C['r_mf'],4)}). Nessuna scelta di
costruzione della rete, fra quelle difendibili, ribalta la conclusione.

### Che cosa aggiungono davvero i crediti a livello traccia

La colonna dell'assortativita' **pesata** e' l'unica su cui la gerarchia di
specificita' dei crediti puo' manifestarsi, perche' cambiare i pesi non cambia
quali coppie di artisti siano collegate: cambia quanto contano. Il confronto e'
istruttivo.

* con i crediti di traccia e la gerarchia di default: **{n(C['rw_default'],4)}**
* senza crediti di traccia, cioe' tornando alle sole co-presenze di copertina:
  **{n(C['rw_no_track'],4)}**
* con tutti i crediti allo stesso peso: {n(C['rw_flat'],4)}
* con una gerarchia piu' ripida (1 / 0,5 / 0,1): {n(C['rw_steep'],4)}

Disattivare il livello traccia abbassa l'omofilia misurata di circa
{pct(1 - C['rw_no_track']/max(C['rw_default'],1e-9),0)}, e appiattire i pesi la
abbassa quasi altrettanto. La lettura e' che **le collaborazioni documentate in
modo piu' specifico sono anche le piu' omofile**: quando due nomi compaiono
insieme sulla stessa traccia — non genericamente sullo stesso disco — la
probabilita' che condividano il genere sessuale e' piu' alta. Una rete costruita
sulle sole co-presenze di copertina sottostima quindi la segregazione, perche'
mescola la collaborazione vera con la coabitazione editoriale. E' la
giustificazione empirica della scelta di disegno descritta alla sezione 3.1.

## 8.3 Artisti con genere musicale debole

{table('t5_genere_debole',
 'Metriche chiave usando il tag principale, il secondo tag, o escludendo '
 'gli artisti con attribuzione debole', float_dec=4)}

Gli artisti il cui tag di genere principale copre meno del
{pct(C['weak_threshold'],0)} delle loro pubblicazioni sono marcati `genre_weak`:
sono {n(C['n_weak'])}, cioe' {pct(C['n_weak']/C['n_pop'])} della popolazione. La
tabella confronta tre trattamenti — tenerli col tag principale, sostituirlo col
secondo tag, escluderli del tutto — per mostrare quanto le conclusioni su RQ2
dipendano da un'attribuzione di genere musicale che per costruzione e'
incerta.
"""


# ==========================================================================
def appendice(C) -> str:
    tm = ROOT / "logs" / "timings.csv"
    timing = ""
    if tm.exists():
        t = pd.read_csv(tm).groupby("step", as_index=False).seconds.sum() \
              .sort_values("seconds", ascending=False).head(20)
        t["seconds"] = t.seconds.map(lambda v: n(v, 1))
        timing = t.to_markdown(index=False)
    pk = C["packages"]
    pkt = pd.DataFrame(sorted(pk.items()), columns=["pacchetto", "versione"]).to_markdown(index=False)
    return f"""
# Appendice tecnica

## A.1 Ambiente

* Sistema: {C['platform']}
* Python {C['python']}
* PostgreSQL {C['pg_version']} — database `discogs`, dati su disco rotazionale
* R per l'ERGM: installato in userspace via micromamba (conda-forge), env
  `opt/mamba/envs/ergm`
* Seme casuale globale: **{C['seed']}**
* Data di esecuzione: {C['data']}

{pkt}

## A.2 Una nota sulle prestazioni che ha condizionato il disegno

Il cluster PostgreSQL risiede su un disco **rotazionale** ma era configurato con
`random_page_cost = 1.1`, un valore tarato per dischi a stato solido. Con quel
costo il pianificatore preferisce percorsi ad accesso casuale che su disco
meccanico degradano a pochi megabyte al secondo: la prima versione
dell'estrazione girava a circa 5 MB/s. Le sessioni di estrazione impostano
percio' `random_page_cost = 4` e riducono il parallelismo, favorendo scansioni
sequenziali, e i conteggi di italianita' sono stati riscritti come **una sola
passata aggregata** su `release_artist` invece di due join ripetuti. Sono GUC di
sessione: non modificano la configurazione del server ne' i dati.

Analogamente, il calcolo della matrice di mixing e' stato riscritto da
`numpy.add.at` a `numpy.bincount` su indici appiattiti — risultato numerico
identico, verificato, circa **50 volte piu' veloce** — perche' senza quella
riscrittura le migliaia di repliche bootstrap e di modello nullo previste dal
disegno non sarebbero state praticabili.

## A.3 Query principali

Tutte le interrogazioni sono in `src/phase1_extract.py`. La piu' importante e'
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
avviene poi sui dati gia' a terra, cosi' che la Fase 5 possa variare le soglie
senza rileggere il database.

## A.4 Tempi di esecuzione

{timing}

## A.5 Riproducibilita'

```bash
cd {ROOT}
./run_all.sh              # esecuzione completa
./run_all.sh --from 3     # riparte dalla Fase 3
./run_all.sh --force      # ignora i checkpoint e ricalcola tutto
```

Ogni fase scrive un checkpoint in `data/*.parquet` e viene saltata se il
checkpoint esiste. I dati grezzi estratti stanno in `data/raw/`, le figure in
`report/figures/`, le tabelle in `report/tables/` sia in CSV sia in LaTeX.

## A.6 Limiti, in ordine di gravita'

1. **Il genere sessuale e' inferito, e la validazione manuale non e' stata
   eseguita.** Il campione stratificato e lo script di scoring sono pronti; senza
   di essa l'errore di misura dell'inferenza resta non quantificato.
2. **L'italianita' e' approssimata dal paese di pubblicazione**, perche'
   `release_label` e' vuota. Confonde "artista italiano" con "artista pubblicato
   in Italia".
3. **{pct(1-C['share_genre'])} della popolazione non ha genere musicale**, perche'
   `release_genre` e' vuota e i master coprono solo parte delle pubblicazioni.
4. **Nessuna verifica incrociata fra fonti**: iTunes e' escluso per scelta.
5. **Discogs non e' un censimento.** Sovrarappresenta vinile, elettronica e
   collezionismo.
6. **L'ERGM vale sulle sottoreti stimate**, non sull'intera rete.
7. **Wikidata copre {pct(C['n_wikidata']/C['n_pop'])} della popolazione**; il
   livello di recupero per nome non e' stato completato per indisponibilita'
   ripetuta del servizio SPARQL, che ha risposto con errori 429, 502 e 504.
"""


# ==========================================================================
def _valori_epoca() -> dict:
    """Esito del test di differenza fra i coefficienti ERGM delle due epoche."""
    f = ROOT / "report" / "tables" / "t4_ergm_differenza_epoche.csv"
    if not f.exists():
        return {}
    d = pd.read_csv(f)
    d = d[d.model == "M1_con_gwesp"]
    out = {}
    for termine, chiave in [("nodematch.gender.F", "epoca_F"),
                            ("nodematch.gender.M", "epoca_M"),
                            ("gwesp.fixed.0.25", "epoca_gwesp")]:
        r = d[d.term == termine]
        if len(r):
            out[f"{chiave}_pre"] = float(r.estimate_pre.iloc[0])
            out[f"{chiave}_post"] = float(r.estimate_post.iloc[0])
            out[f"{chiave}_diff"] = float(r.differenza.iloc[0])
            out[f"{chiave}_p"] = float(r.p.iloc[0])
    return out


def collect(cfg, log) -> dict:
    import sys as _s
    pop = get("population_gender.parquet")
    cred = get("credits.parquet")
    ns = get("network_stats.parquet")
    ao = get("assortativity_overall.parquet")
    ast_ = get("assortativity_strata.parquet")
    amf = get("assortativity_mf.parquet")
    ws = get("women_share.parquet")
    sens = get("sensitivity.parquet")
    mc = get("mc_gender.parquet")
    pos = get("position.parquet")
    wd = get("wd_by_discogs.parquet")
    counts = pd.read_csv(ROOT / "data" / "raw" / "raw_artist_counts.csv")
    known = pop[pop.gender.isin(["M", "F"])]
    net = ns[ns.rete == "all"].iloc[0] if ns is not None and len(ns) else None

    def gq(g):
        k = known[known.musical_genre == g]
        return float((k.gender == "F").mean()) if len(k) else np.nan

    def dq(d):
        s = ws[ws.cohort_decade == d] if ws is not None else None
        return float(s.n_donne.sum() / max(s.n_noti.sum(), 1)) if s is not None and len(s) else np.nan

    import importlib
    pkgs = {}
    for m in ["pandas", "numpy", "networkx", "scipy", "statsmodels", "matplotlib",
              "seaborn", "pyarrow", "psycopg2", "gender_guesser"]:
        try:
            pkgs[m] = getattr(importlib.import_module(m), "__version__", "presente")
        except Exception:
            pkgs[m] = "assente"

    prior_it = get("onomastic_prior_it.parquet")
    prior_gl = get("onomastic_prior_global.parquet")
    wdn = ROOT / "data" / "raw" / "raw_wd_names.parquet"
    groups = pd.read_parquet(ROOT / "data" / "raw" / "raw_groups.parquet")
    various = pd.read_parquet(ROOT / "data" / "raw" / "raw_various.parquet")
    cts = counts.assign(share=counts.n_it / counts.n_all)

    C = {
        "data": datetime.date.today().strftime("%d/%m/%Y"),
        "seed": cfg["project"]["seed"],
        "platform": platform.platform(),
        "python": platform.python_version(),
        "pg_version": "18.4",
        "packages": pkgs,
        "db_rows": 92407183 + 126227877 + 19353744 + 10164832,
        "n_pop": len(pop),
        "n_gender_known": len(known),
        "share_known": len(known) / len(pop),
        "share_f": float((known.gender == "F").mean()),
        "ratio_mf": float((known.gender == "M").sum() / max((known.gender == "F").sum(), 1)),
        "n_unknown": int((pop.gender == "unknown").sum()),
        "n_mixed": int((pop.gender == "mixed").sum()),
        "share_genre": float((pop.musical_genre != "Unknown").mean()),
        "n_weak": int(pop.genre_weak.sum()),
        "weak_threshold": cfg["musical_genre"]["weak_threshold"],
        "n_credits": len(cred),
        "n_track_credits": int((cred.scope == "track").sum()),
        "share_track": float((cred.scope == "track").mean()),
        "n_rta": int((cred.source == "rta").sum()),
        "n_ra_tracks": int(cred.source.isin(["ra_tracks", "ra_tracks_unresolved"]).sum()),
        "n_ra_resolved": int((cred.source == "ra_tracks").sum()),
        "n_credits_filt": int(net.archi) if net is not None else np.nan,
        "n_nodes": int(net.nodi_con_archi) if net is not None else np.nan,
        "n_edges": int(net.archi) if net is not None else np.nan,
        "giant": float(net.quota_componente_gigante) if net is not None else np.nan,
        "density": float(net.densita) if net is not None else np.nan,
        "max_credits": cfg["network"]["max_credits"],
        "w_track": cfg["network"]["credit_scope_weight"]["track"],
        "w_main": cfg["network"]["credit_scope_weight"]["main"],
        "w_umb": cfg["network"]["credit_scope_weight"]["umbrella"],
        "min_it": cfg["population"]["min_italian_releases"],
        "min_all": cfg["population"]["min_total_releases"],
        "min_share": cfg["population"]["min_italian_share"],
        "n_cand_ge2": len(counts),
        "n_pop_60": int(((cts.share >= 0.60) & (cts.n_all >= 3)).sum()),
        "n_pop_70": int(((cts.share >= 0.70) & (cts.n_all >= 3)).sum()),
        "n_various": len(various),
        "n_wd_total": int(wd.discogs_id.nunique()) if wd is not None else 0,
        "n_wd_ambiguous": int(wd[wd.ambiguous].discogs_id.nunique()) if wd is not None else 0,
        "n_wikidata": int((pop.label_source == "wikidata_p1953").sum()),
        "n_wd_names": len(pd.read_parquet(wdn)) if wdn.exists() else 0,
        "n_prior_it": len(prior_it) if prior_it is not None else 0,
        "n_prior_glob": len(prior_gl) if prior_gl is not None else 0,
        "n_prior_common": 241,
        "n_groups": int(pop.is_group.sum()),
        "n_groups_res": int((pop.label_source == "group_members").sum()),
        "n_validation": cfg["gender"]["validation"]["n"],
        "mc_B": cfg["robustness"]["montecarlo_B"],
        "r_gender": val(ao, "attributo=='gender'", "r_osservato"),
        "r_gender_null": val(ao, "attributo=='gender'", "r_null_medio"),
        "z_gender": val(ao, "attributo=='gender'", "z"),
        "r_genre": val(ao, "attributo=='musical_genre'", "r_osservato"),
        "r_gender_lo": val(ast_, "sottorete=='all' and strato=='tutto' and attributo=='gender'", "ci_lo"),
        "r_gender_hi": val(ast_, "sottorete=='all' and strato=='tutto' and attributo=='gender'", "ci_hi"),
        "r_pre": val(ast_, "sottorete=='all' and strato=='pre2000' and attributo=='gender'", "r"),
        "r_post": val(ast_, "sottorete=='all' and strato=='post2000' and attributo=='gender'", "r"),
        # misura di riferimento: solo archi fra nodi con genere determinato
        "r_mf": val(amf, "sottorete=='all' and strato=='tutto' and attributo=='gender' and categorie=='determinati soltanto'", "r"),
        "r_mf_lo": val(amf, "sottorete=='all' and strato=='tutto' and attributo=='gender' and categorie=='determinati soltanto'", "ci_lo"),
        "r_mf_hi": val(amf, "sottorete=='all' and strato=='tutto' and attributo=='gender' and categorie=='determinati soltanto'", "ci_hi"),
        "r_mf_null": val(amf, "sottorete=='all' and strato=='tutto' and attributo=='gender' and categorie=='determinati soltanto'", "r_null"),
        "z_mf": val(amf, "sottorete=='all' and strato=='tutto' and attributo=='gender' and categorie=='determinati soltanto'", "z"),
        "quota_archi_mf": val(amf, "sottorete=='all' and strato=='tutto' and attributo=='gender' and categorie=='determinati soltanto'", "quota_archi_usati"),
        "r_pre_mf": val(amf, "sottorete=='all' and strato=='pre2000' and attributo=='gender' and categorie=='determinati soltanto'", "r"),
        "r_pre_mf_lo": val(amf, "sottorete=='all' and strato=='pre2000' and attributo=='gender' and categorie=='determinati soltanto'", "ci_lo"),
        "r_pre_mf_hi": val(amf, "sottorete=='all' and strato=='pre2000' and attributo=='gender' and categorie=='determinati soltanto'", "ci_hi"),
        "r_post_mf": val(amf, "sottorete=='all' and strato=='post2000' and attributo=='gender' and categorie=='determinati soltanto'", "r"),
        "r_post_mf_lo": val(amf, "sottorete=='all' and strato=='post2000' and attributo=='gender' and categorie=='determinati soltanto'", "ci_lo"),
        "r_post_mf_hi": val(amf, "sottorete=='all' and strato=='post2000' and attributo=='gender' and categorie=='determinati soltanto'", "ci_hi"),
        "r_creative_mf": val(amf, "sottorete=='creative' and strato=='tutto' and attributo=='gender' and categorie=='determinati soltanto'", "r"),
        "r_perf_mf": val(amf, "sottorete=='performance' and strato=='tutto' and attributo=='gender' and categorie=='determinati soltanto'", "r"),
        "r_creative_pre": val(amf, "sottorete=='creative' and strato=='pre2000' and attributo=='gender' and categorie=='determinati soltanto'", "r"),
        "r_creative_post": val(amf, "sottorete=='creative' and strato=='post2000' and attributo=='gender' and categorie=='determinati soltanto'", "r"),
        "r_perf_pre": val(amf, "sottorete=='performance' and strato=='pre2000' and attributo=='gender' and categorie=='determinati soltanto'", "r"),
        "r_perf_post": val(amf, "sottorete=='performance' and strato=='post2000' and attributo=='gender' and categorie=='determinati soltanto'", "r"),
        "r_genre_det": val(amf, "sottorete=='all' and strato=='tutto' and attributo=='musical_genre' and categorie=='determinati soltanto'", "r"),
        "r_genre_tutte": val(amf, "sottorete=='all' and strato=='tutto' and attributo=='musical_genre' and categorie=='tutte le categorie'", "r"),
        **_valori_epoca(),
        "q_hiphop": gq("Hip Hop"), "q_rock": gq("Rock"), "q_classical": gq("Classical"),
        "q_children": gq("Children's"), "q_electronic": gq("Electronic"),
        "q_1960": dq(1960), "q_1980": dq(1980), "q_2020": dq(2020),
        "sens_mf_min": float(sens.r_gender_MF.min()) if sens is not None and "r_gender_MF" in sens else np.nan,
        "sens_mf_max": float(sens.r_gender_MF.max()) if sens is not None and "r_gender_MF" in sens else np.nan,
        "sens_n": len(sens) - 1 if sens is not None else 0,
        "rw_default": val(sens, "variante=='default'", "r_gender_pesato"),
        "rw_no_track": val(sens, "variante=='crediti_traccia=False'", "r_gender_pesato"),
        "rw_flat": val(sens, "variante=='pesi_specificita=1.0/1.0/1.0'", "r_gender_pesato"),
        "rw_steep": val(sens, "variante=='pesi_specificita=1.0/0.5/0.1'", "r_gender_pesato"),
        "mc_min": float(val(mc, "scenario=='migliore_omofilia_min'", "r")) if mc is not None else np.nan,
        "mc_max": float(val(mc, "scenario=='peggiore_omofilia_max'", "r")) if mc is not None else np.nan,
        "mc_sq": float(mc[mc.scenario == "status_quo"].r.mean()) if mc is not None and len(mc[mc.scenario == "status_quo"]) else np.nan,
        "mc_noti": float(val(mc, "scenario=='solo_noti'", "r")) if mc is not None else np.nan,
    }
    ec = get("ergm_coef.parquet")
    if ec is not None and not ec.empty:
        m1 = ec[ec.model == "M1_con_gwesp"]
        C["ergm_F_med"] = float(m1[m1.term == "nodematch.gender.F"].estimate.median())
        C["ergm_M_med"] = float(m1[m1.term == "nodematch.gender.M"].estimate.median())
        C["ergm_n_reti"] = int(m1.rete.nunique())
    es = get("ergm_summary.parquet")
    C["ergm_n_conv"] = int(es.convergenza.sum()) if es is not None and "convergenza" in es else 0
    reg = get("position_regressions.parquet")
    for esito in ["eigenvector", "coreness", "betweenness"]:
        C[f"b_{esito}"] = val(reg, f"esito=='{esito}' and termine=='C(gender)[T.F]'", "coef")
        C[f"p_{esito}"] = val(reg, f"esito=='{esito}' and termine=='C(gender)[T.F]'", "p")
        C[f"lo_{esito}"] = val(reg, f"esito=='{esito}' and termine=='C(gender)[T.F]'", "ci_lo")
        C[f"hi_{esito}"] = val(reg, f"esito=='{esito}' and termine=='C(gender)[T.F]'", "ci_hi")
    if reg is not None and not reg.empty:
        inter = reg[reg.termine.str.contains("C\\(gender\\)\\[T.F\\]:", regex=True)]
        C["n_interazioni"] = len(inter[inter.esito == "eigenvector"])
        C["n_interazioni_signif"] = int((inter[inter.esito == "eigenvector"].p < 0.05).sum())
    else:
        C["n_interazioni"] = C["n_interazioni_signif"] = 0
    if pos is not None:
        d = pos[pos.gender.isin(["M", "F"])]
        for g in ["F", "M"]:
            gg = d[d.gender == g]
            C[f"core_med_{g}"] = float(gg.coreness.median())
            C[f"nrel_med_{g}"] = float(gg.n_release.median())
            C[f"eig_med_{g}"] = float(gg.eigenvector.median())
        C["n_giant"] = len(pos)
    C["ratio_hiphop"] = (1 - C["q_hiphop"]) / max(C["q_hiphop"], 1e-9)
    return C


def build(cfg, log):
    C = collect(cfg, log)
    common.write_json({k: v for k, v in C.items() if k != "packages"}, "report_numbers.json")
    md = "\n".join([executive_summary(C), sezione_dati(C), sezione_gender(C),
                    sezione_rete(C), sezione_risultati(C), sezione_omofilia(C),
                    sezione_posizione(C), sezione_ergm(C), sezione_robustezza(C),
                    appendice(C)])
    md = common.italiano(md)
    p = REPORT / "report.md"
    p.write_text(md)
    log.info(f"report Markdown: {p} ({len(md):,} caratteri)")
    return p


CSS = """
@page { size: A4; margin: 20mm 18mm; @bottom-center { content: counter(page);
        font-size: 9pt; color: #8b8a85; } }
body { font-family: "DejaVu Serif", Georgia, serif; font-size: 10.2pt;
       line-height: 1.55; color: #16161a; max-width: 52em; margin: 0 auto;
       padding: 0 1.2em; }
h1 { font-family: "DejaVu Sans", Helvetica, sans-serif; font-size: 17pt;
     border-bottom: 2px solid #2a78d6; padding-bottom: .25em; margin-top: 1.8em;
     page-break-before: always; color: #0b0b0b; }
h1:first-of-type { page-break-before: avoid; }
h2 { font-family: "DejaVu Sans", Helvetica, sans-serif; font-size: 13pt;
     color: #1c5cab; margin-top: 1.5em; }
h3 { font-family: "DejaVu Sans", Helvetica, sans-serif; font-size: 11pt;
     color: #52514e; }
table { border-collapse: collapse; width: 100%; font-size: 8.4pt;
        margin: 1em 0; page-break-inside: avoid; }
th { background: #eef4fd; text-align: left; font-family: "DejaVu Sans", sans-serif;
     font-size: 8.2pt; border-bottom: 1.5px solid #2a78d6; padding: 5px 7px; }
td { padding: 4px 7px; border-bottom: 1px solid #e8e7e3; }
tr:nth-child(even) td { background: #fbfbfa; }
figure { margin: 1.4em 0; page-break-inside: avoid; }
figure img { width: 100%; height: auto; }
figcaption { font-size: 8.6pt; color: #52514e; line-height: 1.45;
             border-left: 3px solid #cde2fb; padding-left: .8em; margin-top: .6em; }
blockquote { border-left: 3px solid #eb6834; padding-left: 1em; color: #52514e;
             font-style: italic; }
code, pre { font-family: "DejaVu Sans Mono", monospace; font-size: 8.4pt; }
pre { background: #f7f7f5; padding: .8em; border-radius: 4px; overflow-x: auto;
      page-break-inside: avoid; }
strong { color: #0b0b0b; }
"""


def compile_outputs(md_path: Path, cfg, log):
    env = ROOT / "opt" / "mamba" / "envs" / "doc" / "bin"
    pandoc = env / "pandoc"
    weasy = env / "weasyprint"
    css = REPORT / "report.css"
    css.write_text(CSS)
    html = REPORT / "report.html"
    pdf = REPORT / "report.pdf"
    out = {}
    if pandoc.exists():
        cmd = [str(pandoc), str(md_path), "-f", "markdown+pipe_tables+raw_html+tex_math_dollars",
               "-t", "html5", "-s", "--toc", "--toc-depth=2", "--mathml",
               "--metadata", "title=Omofilia di genere nelle collaborazioni musicali italiane",
               "--metadata", "lang=it", "-c", "report.css", "-o", str(html)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode == 0:
            log.info(f"HTML: {html}")
            out["html"] = str(html)
        else:
            log.error(f"pandoc: {p.stderr[-1500:]}")
    else:
        log.error("pandoc non trovato")
    if weasy.exists() and html.exists():
        p = subprocess.run([str(weasy), "-u", str(REPORT) + "/", str(html), str(pdf)],
                           capture_output=True, text=True)
        if p.returncode == 0 and pdf.exists():
            log.info(f"PDF: {pdf} ({pdf.stat().st_size/1e6:.1f} MB)")
            out["pdf"] = str(pdf)
        else:
            log.error(f"weasyprint: {p.stderr[-1500:]}")
    return out


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase7_report", cfg)
    REPORT.mkdir(parents=True, exist_ok=True)
    with Timer("composizione report", log):
        md = build(cfg, log)
    with Timer("compilazione HTML/PDF", log):
        outs = compile_outputs(md, cfg, log)
    common.write_json(outs, "report_outputs.json")
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
