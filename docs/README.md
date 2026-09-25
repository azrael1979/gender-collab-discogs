# Documentazione di processo

Questa cartella non documenta *che cosa fa* il codice — per quello ci sono i
docstring, che in questo progetto sono la documentazione primaria. Documenta
**come si è arrivati qui**: le decisioni prese, quelle rovesciate, gli errori
trovati e che cosa hanno cambiato, i test che non hanno deciso nulla.

Serve a due lettori diversi.

Al **referee**, per verificare che i risultati non siano il prodotto di scelte
convenienti fatte a posteriori. Ogni decisione metodologica ha un'alternativa
che è stata scartata, e la ragione dello scarto è scritta prima dei risultati
che ne dipendono.

A **chi riprende il lavoro fra sei mesi**, per non ripercorrere strade già
chiuse. Le strade chiuse sono documentate quanto quelle aperte, ed è il motivo
per cui questa cartella esiste: un vicolo cieco non documentato viene
riesplorato.

## Per riprendere il lavoro

**Leggere prima [`STATO.md`](STATO.md)**: dove siamo, che cosa resta, dove stanno le cose.

## Ordine di lettura

| file | che cosa contiene |
|---|---|
| [`01-percorso.md`](01-percorso.md) | la narrazione cronologica: dal mandato iniziale a oggi, con i punti in cui l'impostazione è cambiata e perché |
| [`02-decisioni.md`](02-decisioni.md) | registro delle decisioni metodologiche: alternativa scartata, ragione, conseguenza sui risultati |
| [`03-errori.md`](03-errori.md) | errori trovati e corretti, come sono emersi, quali numeri hanno cambiato |
| [`04-calcolo-esatto.md`](04-calcolo-esatto.md) | che cosa significa «esatto» qui, la matematica, e come è stata verificata |
| [`05-ergm.md`](05-ergm.md) | il verbale completo dei tentativi ERGM: ogni specifica, ogni fallimento, la diagnosi e il tentativo fallito di confermarla |
| [`06-risultati.md`](06-risultati.md) | lo stato dei risultati, con l'indicazione di quanto ciascuno sia solido |
| [`07-confronto-internazionale.md`](07-confronto-internazionale.md) | fattibilità del confronto con altri paesi: dimensioni, precisione del criterio di nazionalità, proposta |

## Convenzione

Le affermazioni sono etichettate per solidità, perché non hanno tutte lo stesso
statuto e mescolarle è il modo più rapido per perdere la fiducia di un lettore
attento:

* **misurato** — calcolato sui dati, senza modello. Cade solo se i dati sono
  sbagliati.
* **stimato** — dipende da un modello e dalle sue assunzioni. Cade se le
  assunzioni cadono.
* **interpretato** — una spiegazione proposta per un fatto osservato. Può
  essere sbagliata anche se il fatto è giusto.
