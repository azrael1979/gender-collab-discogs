# Project status: Italian study (paper for *Poetics*)

Updated: 26 September 2026. Status of the project, for anyone
resuming the work. The full history of the work is in `01-percorso.md`,
decisions in `02-decisioni.md` (D1–D17), errors in `03-errori.md` (E1–E18),
results in `06-risultati.md`.

---

## 1. The paper

- Title: *Finding each other: the emergence of gender homophily in Italian
  recorded music, 1950–2026.*
- Thesis: emergence. Among equally active artists, women did not form ties
  with each other more than chance in the 1950s and 1960s; the excess appears
  in the 1970s and from 2000 onward stabilizes at around 1.55 times chance.
  Men remain at chance, the female share does not grow, and the emergence
  concerns pop, rock and electronic music, not classical. Hypotheses H1–H6 in
  §2.7; the differences by musical genre and the choice of null are declared
  exploratory (D14).
- Length: 7,989 words of main text (limit 8,000, set by the author). The count
  is in `data/paper_status.json` and in the log of `src/paper.py`; every
  addition must be offset by a cut.
- The manuscript is not in the repository (D15): `paper/`, `src/paper.py`
  (which contains the text) and `src/paper_figures.py` are in `.gitignore` and
  have been removed from the entire git history. They remain local only. The
  earlier long version is in `paper/versioni/`.
- To regenerate: `python3 src/paper_figures.py && python3 src/paper.py`. No
  number is typed by hand: everything is read from the result files (declared
  exception: the external USC/Goodreau data).

## 2. Recent decisions

- Groups are excluded (D16): unit of analysis = person; 87,229 individual
  artists out of 100,201 entries. Pipeline rerun on 24–25 September.
- Reference null by degree strata (D12, Phase 4j): the uniform null produced
  a false sign reversal (E13).
- Gender validation completed (25 September): 200 cases coded blind by the
  author, 94.6% agreement on the M/F labels, 97.5% on determinable cases, 4
  reversals. Reported in §3.2 and in the limitations. Single annotated file
  (also used for the comparison): `data/validation_ITALIA_unico_ANNOTATO.csv`.
- Entries that are not persons (D17, Phase 4l): a sensitivity analysis, not a
  new definition. Removing them (3.6% of entries) changes nothing.
- The "Wikidata by name" level of the cascade became active again in the
  rerun (E18): 145 labels changed out of 87,229.

## 3. Remaining items before submission

From `paper/NOTE_PER_AUTORE.md` (local only), in order:

1. Date of the Discogs dump: not recorded in the database or in the logs; it
   is also needed for the OSF form of the comparison study.
2. Authors, affiliations, declarations (conflicts of interest, funding,
   CRediT, use of AI, data availability).
3. Citations: checked on 24 September (`paper/VERIFICA_CITAZIONI.md`). Still
   to be checked by hand: the NYT page for Pollitt and the wording of Blau's
   formulation; the reference style must be compared with the Guide for
   Authors.
4. Automatic report (`report/`, Phase 7): translated into English on 26
   September and declared superseded by a notice at the top; its text still
   reflects the withdrawn thesis and is not being revised further.
5. Reviewer package (`export/`, Phase 8): regenerated in English on 26
   September, after the validation and Phase 4l. Rerun
   `python3 src/phase8_export.py --force` after any further change. The
   package contains the manuscript, so it must not be uploaded to Zenodo as
   it stands until the article is published.
6. Old commits on GitHub: the history was cleaned and force-pushed (D15), but
   GitHub still serves the removed commits to anyone who knows the hash. This
   can be resolved by a request to GitHub support or by recreating the
   repository. The author has not yet said which option to take.

## 4. Where things are

| | |
|---|---|
| `run_all.sh` | full pipeline; phase 9 (paper) runs only if the paper files are present |
| `data/con_gruppi_2026-09-24/` | snapshot of the results before D16, for comparison |
| `data/validation_sample.csv` | validation sample (without groups), with `human_gender` filled in |
| `data/validation_sample_con_gruppi_2026-09-20.csv` | earlier sample, never annotated |
| `data/validazione_ia/` | blind AI annotation of the **earlier** sample (with groups): not used |
| `docs/07-confronto-internazionale.md` | feasibility of the comparison with other countries, from which the second project originated |
| `tests/` | 5 verification tests, all passing as of 25 September |

## 5. Related project

The international comparison is in `../gender_collab_comparativo/` (private
repository), pre-registered on OSF. Its status is in
`../gender_collab_comparativo/docs/STATO.md`. Italy appears there as the
reference case, with the same code but without the "Wikidata by name" level;
the acceptance test reproduces this study to the third digit.
