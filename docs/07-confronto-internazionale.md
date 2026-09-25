# Fattibilità del confronto internazionale

Studio del 25 settembre 2026, per scegliere sui numeri i paesi da confrontare
con l'Italia in un secondo lavoro. Script: `src/fattibilita_paesi.py`; dati in
`data/fattibilita/`. Due passate sequenziali in sola lettura sul database, il
resto in locale.

**Controllo di validità dello script:** sull'Italia riproduce la pipeline —
100.202 voci contro 100.201, precisione del criterio di nazionalità 94,5%.

## I numeri

Stesso criterio di nazionalità dell'Italia (≥ 2 release nel paese, ≥ 3 in
totale, quota ≥ 0,50), gruppi esclusi come in D16.

| paese | artisti individuali | debutti anni '50 | precisione nazionalità (P27) | genere Wikidata | nome anagrafico |
|---|---|---|---|---|---|
| Italia | 87.230 | 1.553 | 94,5% | 6,0% | 16,7% |
| Spagna | 51.879 | 848 | 91,4% | 4,7% | 22,1% |
| Francia | 123.884 | 3.877 | 86,4% | 6,8% | 13,0% |
| Germania | 190.347 | 2.753 | **79,0%** | 6,8% | 17,4% |
| DDR | 3.382 | 339 | 94,2% | 17,9% | 12,0% |
| Svezia | 43.328 | 916 | 96,2% | 7,5% | 21,3% |
| Norvegia | 26.414 | 249 | 97,4% | 11,1% | 13,9% |
| Danimarca | 20.950 | 451 | 95,3% | 9,4% | 14,0% |
| Finlandia | 35.642 | 317 | 98,0% | 9,4% | 19,3% |
| Paesi Bassi | 58.080 | 755 | 89,5% | 6,0% | 20,9% |
| Portogallo | 12.419 | 182 | 88,6% | 5,2% | 16,4% |
| Grecia | 23.127 | 350 | 95,2% | 5,4% | 18,0% |
| Giappone | 98.661 | 725 | 95,0% | 6,0% | 20,1% |
| Brasile | 40.114 | 614 | 97,8% | 3,9% | 16,6% |
| Regno Unito | 184.552 | 2.347 | **81,6%** | 4,3% | 18,9% |
| Stati Uniti | 640.197 | 20.638 | 90,5% | 4,3% | 13,5% |

Debutti per decennio: `data/fattibilita/fattibilita_paesi_decenni.csv`.

## Che cosa dicono

**Il criterio di nazionalità regge dove il mercato coincide con il paese e
cede dove il mercato è linguistico.** In Germania gli errori sono soprattutto
austriaci (469) e svizzeri (241); in Francia belgi e svizzeri; nel Regno Unito
statunitensi, australiani e irlandesi. È un limite di sostanza, non di dati: in
quei casi l'unità naturale è forse il **campo linguistico** (Germania + Austria
+ Svizzera tedesca), non lo stato. Va deciso prima di pre-registrare.

**Due trappole di codifica trovate e corrette** (da ricordare): Wikidata
registra la cittadinanza come «Regno di Danimarca» (Q756617), «Regno dei Paesi
Bassi» (Q29999) e, per il passato, «Regno Unito di Gran Bretagna e Irlanda»
(Q174193); con i soli codici dei paesi costitutivi la precisione risultava zero.

**La DDR è piccola.** 3.382 artisti, quasi tutti con debutto fra il 1950 e il
1989. Basta per la permutazione per decennio, ma i legami donna–donna per
decennio saranno poche centinaia: il confronto con la Germania Ovest avrà poca
potenza, e va detto nel disegno.

**L'inferenza del genere è il collo di bottiglia ovunque.** Il genere Wikidata
copre il 4-11% degli artisti (18% nella DDR), come in Italia: la cascata
onomastica farà il grosso del lavoro, e ogni paese richiede il proprio
dizionario dei nomi e il proprio campione di validazione. Il Giappone resta il
caso più difficile per i nomi romanizzati.

**Calcolo.** Il logit esatto cresce con il quadrato degli artisti attivi: la
Germania richiederebbe circa dieci volte il tempo dell'Italia (un giorno di
macchina), gli Stati Uniti circa cento volte di più — fuori portata senza
campionare, cioè senza rinunciare a ciò che distingue questo metodo.

## Proposta

Primo confronto: **Italia, Spagna, Francia, Svezia** (o i paesi nordici
insieme, tutti sopra il 95% di precisione), più **Germania e DDR** se si
risolve l'unità d'analisi per i campi linguistici. Esclusi per ora Stati Uniti
(calcolo) e Regno Unito (criterio di nazionalità all'82%); Giappone solo con
una validazione del genere dedicata.
