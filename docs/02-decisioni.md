# Registro delle decisioni

Ogni riga è una scelta che avrebbe potuto essere fatta diversamente. Le
alternative sono indicate perché un referee le proporrà, e conviene che la
risposta sia già scritta.

---

## D1 — Estrazione senza oggetti lato server

**Scelta.** Nessuna tabella temporanea, nessuna vista, nessuna funzione: gli
elenchi di identificativi tornano al database come letterali `int[]`.

**Alternativa.** Tabelle temporanee, che è il modo naturale.

**Perché scartata.** Il vincolo di sola lettura le vieta. `CREATE TEMP TABLE`
fallisce sotto `default_transaction_read_only = on`, perché una tabella
temporanea è comunque una scrittura nel catalogo.

**Conseguenza.** Query più lunghe e meno leggibili, in cambio della garanzia
che i database sorgente non siano stati toccati. Verificabile: non esiste
alcun `INSERT`, `CREATE` o `UPDATE` in `src/`.

---

## D2 — L'italianità come euristica dichiarata, non come dato

**Scelta.** Un artista è italiano se almeno metà delle sue pubblicazioni ha
`country = 'Italy'`, con soglia di almeno due pubblicazioni italiane.

**Alternativa.** Usare `P27` di Wikidata come criterio.

**Perché scartata.** `P27` copre solo la frazione di artisti presenti in
Wikidata — 4.663 su 100.201, cioè il 4,7%. Usarlo come criterio avrebbe
ristretto la popolazione a chi è abbastanza noto da avere una voce, che è
esattamente il *bias* che si vuole evitare studiando una minoranza.

**Perché è difendibile comunque.** `P27` è stato usato non come criterio ma
come **validazione**: sui 4.663 verificabili l'euristica ha una precisione del
**94,5%**, che sale monotonamente con la soglia. La monotonia conta più del
livello: dice che la misura ordina correttamente, non solo che indovina spesso.

---

## D3 — L'ordine dei dizionari onomastici: italiano prima del globale

**Scelta.** Il prior italiano viene consultato per primo; quello globale solo
in mancanza.

**Alternativa.** Un dizionario globale, più ampio e apparentemente più neutro.

**Perché scartata.** Andrea, Simone, Nicola, Daniele, Michele, Gabriele sono
maschili in italiano e femminili nei dizionari a dominanza anglofona. Su una
popolazione italiana l'ordine inverso avrebbe classificato come donne migliaia
di uomini — e l'errore sarebbe stato **sistematico e orientato**, cioè avrebbe
gonfiato la quota femminile proprio nella direzione che rende l'articolo più
interessante. È il tipo di errore che non si vede nei totali.

---

## D4 — `unknown` escluso dal calcolo dell'assortatività

**Scelta.** L'assortatività si calcola sui soli casi determinati; la versione
con `unknown` come quarta categoria è riportata a parte.

**Alternativa.** Tenere `unknown` come categoria, che usa tutti gli archi.

**Perché scartata.** Il genere non determinato non è un genere: è assenza di
informazione. Trattarlo come categoria misura in parte la co-occorrenza di
artisti oscuri, non l'omofilia.

**Perché la scelta non è opportunistica.** Sul genere **sessuale** l'esclusione
*abbassa* il coefficiente (da 0,0735 a 0,0511), cioè indebolisce il risultato.
Sul genere **musicale** lo *alza* (da 0,5186 a 0,5865). Segni opposti, stessa
regola applicata: la regola non è stata scelta guardando l'esito.

---

## D5 — Tre livelli di specificità dei crediti

**Scelta.** Peso di un legame `w(u,v) = w_t·|tracce condivise| + w_r·Σ s_u·s_v`
con specificità traccia 1,0, release principale 0,7, ombrello 0,3.

**Alternativa.** Contare ogni co-presenza allo stesso modo.

**Perché scartata.** Due musicisti accreditati sulla stessa traccia hanno
collaborato; due nominati in fondo a una compilation possono non essersi mai
incontrati. Pesarli uguale confonde le due cose. Il campo `tracks` di Discogs è
testo libero e ciò che non si riesce a risolvere viene **degradato a ombrello,
non forzato** a una traccia: in caso di dubbio il legame pesa meno, mai di più.

---

## D6 — Datare i legami, non le persone

**Scelta.** Ogni arco è datato con l'anno della **prima pubblicazione
condivisa** dai due artisti.

**Alternativa.** Definire un arco «pre-2000» se entrambi gli estremi hanno
debuttato prima del 2000.

**Perché scartata.** Un legame nato nel 1975 fra un esordiente e un veterano è
un legame del 1975, non di due epoche. E la regola dell'accordo scarta proprio
le collaborazioni intergenerazionali, che sono fra le più interessanti.

**Conseguenza.** È la decisione che ha reso visibile il risultato centrale.
Con la definizione per coorti l'inversione non si vedeva.

---

## D7 — Sottoreti a valanga abbandonate

**Scelta.** Nessuna stima su sottorete campionata compare nei risultati finali.

**Alternativa.** Tenerle come approssimazione, dichiarandone i limiti.

**Perché scartata.** Di una stima su campione a valanga non si può dire di che
cosa sia stima: il campione non è rappresentativo di alcuna popolazione
definibile. Dichiarare il limite non lo rimuove.

**Sostituito da.** Il decennio come unità, che è una **popolazione completa**, e
il calcolo esatto sull'intera rete.

---

## D8 — Calcolare invece di stimare, ovunque sia possibile

**Scelta.** Logit diadico su tutte e 1.619.630.155 le diadi; momenti della
permutazione in forma chiusa; betweenness esatta su tutte le 79.013 sorgenti.

**Alternativa.** Campionamento caso-controllo, mille permutazioni, 400 sorgenti
— cioè quello che c'era prima.

**Perché scartata.** Non c'era una buona ragione per approssimare ciò che si
può calcolare, e due delle quattro approssimazioni **distorcevano i risultati**
(vedi [`03-errori.md`](03-errori.md)).

**Costo.** Circa tre ore di macchina per il logit esatto, un'ora per la
betweenness. Il resto è più veloce della versione campionata, perché una
formula chiusa costa meno di mille permutazioni.

---

## D9 — Un decennio come unità di analisi ERGM

**Scelta.** Dove l'ERGM si stima, lo si stima per decennio.

**Alternativa.** Sottoreti campionate della dimensione voluta.

**Perché scartata.** Vedi D7. Un decennio ha un difetto — non è indipendente
dagli altri — ma è un difetto dichiarabile, mentre l'assenza di riferimento di
un campione a valanga non lo è.

---

## D10 — La proiezione NON data al modello come covariata

**Scelta.** Non si è aggiunto un `edgecov` con la dimensione del cast condiviso.

**Alternativa.** Darla al modello, così che `gwesp` debba spiegare solo il
residuo.

**Perché scartata.** Se due artisti condividono una release hanno un arco **per
costruzione**: la covariata sarebbe non nulla esattamente sugli archi e nulla
altrove, cioè separerebbe perfettamente i dati. È un vicolo cieco, ed è
documentato perché sembra la strada ovvia.

---

## D11 — La bontà di adattamento attiva sui decenni, disattivata sulla rete intera

**Scelta.** GOF con 100 reti simulate per i decenni; nessuna GOF sulla rete
integrale.

**Perché.** Simulare una rete da 57.000 nodi costa quanto un'iterazione della
stima; cento simulazioni costerebbero più della stima stessa. Sui decenni costa
poco.

**Perché conta.** È la GOF ad aver smascherato una **convergenza apparente**
sulla rete integrale — una stima che dichiarava successo producendo reti con il
40% degli archi osservati e il 4% dei legami fra donne. Senza, quel risultato
sarebbe finito nell'articolo.

---

## D12 — Il nullo di riferimento condiziona sull'attività

**Scelta.** I rapporti osservato/atteso della serie temporale si calcolano
permutando le etichette **entro strati di grado** (Fase 4j). La permutazione
uniforme in forma chiusa resta riportata, come confronto.

**Alternativa.** La permutazione uniforme, che era il riferimento fino al 24
settembre ed è esatta.

**Perché scartata.** È esatta come calcolo ma risponde a un'altra domanda:
«le donne si legano fra loro più di quanto farebbero etichette assegnate a caso
a *qualunque* artista?». Le donne hanno meno legami, e quel nullo le confronta
con artisti più attivi di loro. La domanda dell'articolo è se le donne si
leghino fra loro più di quanto farebbero artisti *con la stessa attività*. Vedi
E13 in [`03-errori.md`](03-errori.md).

**Perché la scelta non è opportunistica.** Indebolisce il risultato più
spettacolare — l'inversione di segno scompare — e ne rafforza un altro: il
livello recente passa da 1,17-1,66 a un plateau stabile attorno a 1,7. E
concorda con i due strumenti già presenti che condizionavano sull'attività, il
mixing a grado preservato e il logit con `sum_lognrel`.

---

## D13 — Il paper sta in 8.000 parole di testo principale

**Scelta.** Dall'abstract alla conclusione, tabelle e didascalie comprese,
bibliografia e appendici escluse — la convenzione delle riviste Elsevier. Il
conteggio è in `paper.py` e finisce in `data/paper_status.json`; i separatori
delle tabelle Markdown e i percorsi delle immagini non contano come parole.

**Alternativa.** Il conteggio grezzo di tutto il file, che era quello riportato
prima (12.811) e che contava anche i `|` delle tabelle.

**Conseguenza.** La versione lunga è conservata in
`paper/versioni/2026-09-24_v2_12811-parole/` e nel tag git `paper-v2-12811`.

---

## D14 — Ipotesi dichiarate, e che cosa resta esplorativo

**Scelta.** Il paper formula una domanda di ricerca e sei ipotesi (H1-H6, con
un'ipotesi concorrente H2′). Le differenze fra generi musicali e la
sensibilità al nullo che tiene conto dell'attività sono dichiarate
**esplorative**.

**Alternativa.** Trasformare in ipotesi anche questi due risultati, che
rafforzerebbero l'articolo.

**Perché scartata.** Sono nati dall'analisi (Fasi 4j e 4k, 24 settembre), non
dalla teoria: presentarli come ipotesi sarebbe HARKing (formulare le ipotesi dopo
aver visto i risultati), e questa documentazione, che è pubblica, lo
mostrerebbe. Per lo stesso motivo **H3 non ha direzione**: nel mandato si
chiedeva *se* l'omofilia cambiasse nel tempo, non che salisse.

**Cautela sulle altre.** Il paper dice che le ipotesi derivano dalla
letteratura, non che furono registrate prima dell'analisi. Il mandato poneva le
domande di H1, H4 e H5 (genere musicale, ruoli, posizione), ma non la direzione
di H4, e H2 è stata messa per iscritto dopo le prime stime. Le formulazioni
seguono la letteratura citata, e H4 e H5 sono respinte: non sono state
aggiustate sui risultati. Ma nessuna è pre-registrata, e non va detto che lo
sia.

