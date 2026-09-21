
\set ON_ERROR_STOP on
SET default_transaction_read_only = on;
SET work_mem = '2GB';
SET max_parallel_workers_per_gather = 8;
SET jit = off;

-- ===================================================================
-- Popolazione candidata: euristica share-based su release.country.
-- (release_label e' vuota nel dump: l'euristica "etichette italiane"
--  non e' applicabile, cfr. report sezione Sorgenti dati.)
-- ===================================================================
CREATE TEMP TABLE it_rel AS
  SELECT id FROM release WHERE country = 'Italy';
CREATE INDEX ON it_rel(id);
ANALYZE it_rel;

CREATE TEMP TABLE cand AS
WITH c AS (
  SELECT ra.artist_id, count(*) AS n_it
  FROM release_artist ra JOIN it_rel ON it_rel.id = ra.release_id
  GROUP BY 1 HAVING count(*) >= 2
), t AS (
  SELECT ra.artist_id, count(*) AS n_all
  FROM release_artist ra JOIN c ON c.artist_id = ra.artist_id
  GROUP BY 1
)
SELECT c.artist_id, c.n_it, t.n_all, c.n_it::float8 / t.n_all AS italian_share
FROM c JOIN t USING (artist_id)
WHERE c.n_it::float8 / t.n_all >= 0.5
  AND t.n_all >= 3
  AND NOT EXISTS (SELECT 1 FROM artist a WHERE a.id = c.artist_id AND (a.name ~* '^various( artists?)?( \(\d+\))?$' OR a.name ~* '^unknown artist' OR a.name ~* '^no artist' OR a.name ~* '^traditional$'));
CREATE INDEX ON cand(artist_id);
ANALYZE cand;

\echo '--- popolazione candidata ---'
SELECT count(*) AS artisti_candidati FROM cand;

\copy (SELECT c.artist_id, a.name, a.realname, a.profile, a.data_quality, c.n_it, c.n_all, c.italian_share FROM cand c JOIN artist a ON a.id = c.artist_id) TO '/media/disk2/datascience/analysis/gender_collab/data/raw/raw_artists.csv' WITH (FORMAT csv, HEADER true)

-- ===================================================================
-- Crediti a livello RELEASE
-- ===================================================================
CREATE TEMP TABLE ra_c AS
SELECT ra.artist_id, ra.release_id, ra.extra,
       NULLIF(btrim(ra.role), '')   AS role,
       NULLIF(btrim(ra.tracks), '') AS tracks
FROM release_artist ra JOIN cand USING (artist_id);
CREATE INDEX ON ra_c(release_id);
ANALYZE ra_c;
\echo '--- crediti release ---'
SELECT count(*) AS ra_totali,
       count(*) FILTER (WHERE extra = 0) AS ra_main,
       count(*) FILTER (WHERE extra <> 0 AND tracks IS NOT NULL) AS ra_con_tracce,
       count(*) FILTER (WHERE extra <> 0 AND tracks IS NULL) AS ra_ombrello
FROM ra_c;
\copy (SELECT * FROM ra_c) TO '/media/disk2/datascience/analysis/gender_collab/data/raw/raw_ra.csv' WITH (FORMAT csv, HEADER true)

-- ===================================================================
-- Crediti a livello TRACCIA  (passata unica sulla tabella da 25 GB)
-- ===================================================================
CREATE TEMP TABLE rta_c AS
SELECT rta.artist_id, rta.release_id,
       NULLIF(btrim(rta.track_id), '')       AS track_id,
       NULLIF(btrim(rta.track_sequence), '') AS track_sequence,
       rta.extra,
       NULLIF(btrim(rta.role), '')           AS role
FROM release_track_artist rta JOIN cand USING (artist_id);
CREATE INDEX ON rta_c(release_id);
ANALYZE rta_c;
\echo '--- crediti traccia ---'
SELECT count(*) AS rta_totali,
       count(track_id) AS con_track_id,
       count(track_sequence) AS con_sequence,
       count(DISTINCT artist_id) AS artisti_coinvolti
FROM rta_c;
\copy (SELECT * FROM rta_c) TO '/media/disk2/datascience/analysis/gender_collab/data/raw/raw_rta.csv' WITH (FORMAT csv, HEADER true)

-- ===================================================================
-- Release coinvolte: anagrafica, anno, master
-- ===================================================================
CREATE TEMP TABLE rel_ids AS
  SELECT release_id FROM ra_c UNION SELECT release_id FROM rta_c;
CREATE INDEX ON rel_ids(release_id);
ANALYZE rel_ids;
\echo '--- release coinvolte ---'
SELECT count(*) AS release_coinvolte FROM rel_ids;

CREATE TEMP TABLE rel_meta AS
SELECT r.id AS release_id,
       substring(r.released FROM '^[0-9]{4}')::int AS year,
       r.country,
       NULLIF(r.master_id, 0) AS master_id,
       r.status,
       r.title
FROM release r JOIN rel_ids ri ON ri.release_id = r.id;
CREATE INDEX ON rel_meta(release_id);
CREATE INDEX ON rel_meta(master_id);
ANALYZE rel_meta;
\copy (SELECT * FROM rel_meta) TO '/media/disk2/datascience/analysis/gender_collab/data/raw/raw_releases.csv' WITH (FORMAT csv, HEADER true)

-- numero di artisti (qualsiasi, non solo candidati) accreditati sulla release:
-- serve per il filtro max_credits e per riconoscere le compilation
\copy (SELECT ra.release_id, count(DISTINCT ra.artist_id) AS n_credited, count(DISTINCT ra.artist_id) FILTER (WHERE ra.extra = 0) AS n_main FROM release_artist ra JOIN rel_ids ri ON ri.release_id = ra.release_id GROUP BY 1) TO '/media/disk2/datascience/analysis/gender_collab/data/raw/raw_relsize.csv' WITH (FORMAT csv, HEADER true)

-- release attribuite a "Various Artists" (compilation)
\copy (SELECT DISTINCT ra.release_id FROM release_artist ra JOIN rel_ids ri ON ri.release_id = ra.release_id JOIN artist a ON a.id = ra.artist_id WHERE ra.extra = 0 AND a.name ~* '^various( artists?)?( \(\d+\))?$') TO '/media/disk2/datascience/analysis/gender_collab/data/raw/raw_various.csv' WITH (FORMAT csv, HEADER true)

-- generi e stili (solo via master: release_genre/release_style sono vuote)
\copy (SELECT rm.release_id, mg.genre FROM rel_meta rm JOIN master_genre mg ON mg.master_id = rm.master_id WHERE mg.genre IS NOT NULL) TO '/media/disk2/datascience/analysis/gender_collab/data/raw/raw_relgenre.csv' WITH (FORMAT csv, HEADER true)
\copy (SELECT rm.release_id, ms.style FROM rel_meta rm JOIN master_style ms ON ms.master_id = rm.master_id WHERE ms.style IS NOT NULL) TO '/media/disk2/datascience/analysis/gender_collab/data/raw/raw_relstyle.csv' WITH (FORMAT csv, HEADER true)

-- ===================================================================
-- Mappa posizione -> traccia, solo per le release che ne hanno bisogno
-- (quelle con almeno un credito release con campo `tracks` valorizzato)
-- ===================================================================
CREATE TEMP TABLE need_pos AS
  SELECT DISTINCT release_id FROM ra_c WHERE tracks IS NOT NULL;
CREATE INDEX ON need_pos(release_id);
ANALYZE need_pos;
\echo '--- release con crediti posizionali da risolvere ---'
SELECT count(*) AS release_da_risolvere FROM need_pos;

\copy (SELECT rt.release_id, rt.sequence, NULLIF(btrim(rt.position),'') AS position, NULLIF(btrim(rt.track_id),'') AS track_id FROM release_track rt JOIN need_pos np ON np.release_id = rt.release_id) TO '/media/disk2/datascience/analysis/gender_collab/data/raw/raw_reltracks.csv' WITH (FORMAT csv, HEADER true)

-- ===================================================================
-- Gruppi: composizione (per l'inferenza "mixed")
-- ===================================================================
\copy (SELECT g.group_artist_id, g.member_artist_id, g.member_name FROM group_member g WHERE g.group_artist_id IN (SELECT artist_id FROM cand) OR g.member_artist_id IN (SELECT artist_id FROM cand)) TO '/media/disk2/datascience/analysis/gender_collab/data/raw/raw_groups.csv' WITH (FORMAT csv, HEADER true)

-- alias e varianti di nome (utili al matching onomastico / Wikidata)
\copy (SELECT av.artist_id, av.name FROM artist_namevariation av JOIN cand USING (artist_id)) TO '/media/disk2/datascience/analysis/gender_collab/data/raw/raw_namevar.csv' WITH (FORMAT csv, HEADER true)

\echo '=== ESTRAZIONE COMPLETATA ==='
