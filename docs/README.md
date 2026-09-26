# Process documentation

This folder does not document what the code does; that is the job of the
docstrings, which in this project are the primary documentation. It documents
how the work reached its present state: the decisions taken, those reversed,
the errors found and what they changed, and the tests that decided nothing.

It is written for two different readers.

For referees, it makes it possible to check that the results are not the
product of convenient choices made after the fact. Every methodological
decision has an alternative that was rejected, and the reason for rejecting it
is written down before the results that depend on it.

For anyone resuming the work six months from now, it avoids retracing paths
already closed. Dead ends are documented as fully as the paths that were
pursued, and that is the reason this folder exists: an undocumented dead end
gets explored again.

## Resuming the work

Read [`STATO.md`](STATO.md) first: where the project stands, what remains to
be done and where things are kept.

## Reading order

| file | contents |
|---|---|
| [`01-percorso.md`](01-percorso.md) | the chronological narrative, from the initial brief to the present, with the points where the approach changed and why |
| [`02-decisioni.md`](02-decisioni.md) | log of methodological decisions: rejected alternative, reason, consequence for the results |
| [`03-errori.md`](03-errori.md) | errors found and corrected, how they came to light, which numbers they changed |
| [`04-calcolo-esatto.md`](04-calcolo-esatto.md) | what "exact" means here, the mathematics, and how it was verified |
| [`05-ergm.md`](05-ergm.md) | the full record of the ERGM attempts: every specification, every failure, the diagnosis and the failed attempt to confirm it |
| [`06-risultati.md`](06-risultati.md) | the status of the results, with an indication of how solid each one is |
| [`07-confronto-internazionale.md`](07-confronto-internazionale.md) | feasibility of the comparison with other countries: sizes, precision of the nationality criterion, proposal |

## Convention

Claims are labeled by how solid they are, because they do not all have the
same status, and mixing them is the quickest way to lose the trust of a careful
reader:

* **measured**: computed on the data, without a model. It fails only if the
  data are wrong.
* **estimated**: depends on a model and its assumptions. It fails if the
  assumptions fail.
* **interpreted**: a proposed explanation for an observed fact. It can be
  wrong even if the fact is right.
