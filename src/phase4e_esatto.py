"""FASE 4e — gli stessi conti, ma esatti su tutte le diadi.

Perche' rifare cio' che la Fase 4c aveva gia' fatto
---------------------------------------------------
La Fase 4c aveva campionato: il logit diadico su tre milioni di diadi
caso-controllo invece che su tutte, il QAP su mille permutazioni invece che
sulla distribuzione esatta. Erano scorciatoie prese per comodita', non per
necessita'. La rete ha 56.915 nodi, cioe' **1.619.630.155 diadi**: sono molte,
non sono intrattabili.

Qui non si stima e non si simula nulla.

**A. Regressione logistica su tutte le diadi.**
Si percorre l'intero insieme delle diadi a blocchi, accumulando le quantita'
che servono a un passo di Newton — la matrice X'WX e il vettore X'(y-p) — e si
itera fino a convergenza. Ogni passata tocca tutte e 1,6 miliardi di coppie, in
memoria costante. Il risultato non e' una stima campionaria con un intervallo
di confidenza da bootstrap: e' il massimo esatto della verosimiglianza sul
dato completo, con gli errori standard che vengono dall'inversa
dell'informazione osservata.

**B. Momenti esatti della permutazione, invece di permutare.**
Il numero di archi interni a un genere, quando le etichette dei nodi vengono
permutate a caso, ha media e varianza in forma chiusa. Basta contare quante
coppie di archi condividono un nodo — cioe' la somma dei C(d,2) sui gradi — e
applicare le probabilita' ipergeometriche per tre e quattro nodi distinti.
Mille permutazioni davano una stima della distribuzione nulla con il suo errore
Monte Carlo; questo da' la distribuzione nulla.

**C. La serie temporale, esatta anch'essa.**
Le stesse due quantita' vengono ricalcolate decennio per decennio, sugli archi
datati con l'anno della prima pubblicazione condivisa. Per ogni periodo il
logit percorre tutte le diadi fra i nodi attivi in quegli anni, e la
permutazione usa i momenti in forma chiusa. La serie che ne esce non ha piu'
alcun errore Monte Carlo: le differenze fra decenni sono differenze nei dati.

Cio' che resta non calcolabile e' solo l'ERGM, e non per pigrizia: la sua
verosimiglianza contiene una somma su tutti i grafi possibili con 56.915 nodi,
che sono 2^1.619.630.155. E' quella intrattabilita' a rendere necessario
l'MCMC, ed e' per quello che su questa rete il metodo fallisce.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import networkx as nx
from scipy.special import expit
from scipy.sparse import csr_matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import ROOT, Timer

# Righe di diadi per blocco. Con 56.915 nodi un blocco da 400 righe tocca circa
# 23 milioni di coppie: qualche centinaio di megabyte per array temporaneo.
BLOCCO_RIGHE = 400
MAX_NEWTON = 40
# Frazioni del passo di Newton valutate a ogni iterazione. Newton su una
# verosimiglianza logistica ha un massimo unico, ma un passo intero preso
# lontano dall'ottimo puo' scavalcarlo: alla seconda iterazione la
# log-verosimiglianza era passata da -4,7 a -27,3 milioni. Valutarle tutte
# nella stessa passata costa cinque prodotti scalari sulla stessa matrice, cioe'
# quasi nulla rispetto al costruirla.
FRAZIONI = np.array([1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125])
# Soglia sul passo. Non puo' essere arbitrariamente piccola: la
# log-verosimiglianza e' una somma di 1,6 miliardi di termini in virgola mobile
# a doppia precisione, e l'errore di accumulo pone un pavimento intorno a 1e-7
# sul passo. Una tolleranza a 1e-9 non viene mai raggiunta e il programma gira
# a vuoto — e' successo: tre iterazioni con log-verosimiglianza identica e
# coefficienti stabili alla quarta decimale, con il passo fermo a 5e-8.
# A 1e-6 i coefficienti sono determinati tre ordini di grandezza meglio del
# loro errore standard piu' piccolo, che e' dell'ordine di 1e-3.
TOLLERANZA = 1e-6
# Secondo criterio, indipendente dal primo: se la verosimiglianza non migliora
# in modo misurabile, non c'e' piu' nulla da guadagnare qualunque sia il passo.
MIGLIORAMENTO_MINIMO = 1e-3

TERMINI = ["intercetta", "same_F", "same_M", "same_mixed",
           "same_genre", "same_cohort", "sum_lognrel"]


def termini_di(attrs) -> list[str]:
    """I termini stimabili su questa rete.

    `same_mixed` esiste solo se ci sono nodi 'mixed', cioe' gruppi misti. Con i
    gruppi esclusi dalla popolazione (D16) la colonna e' identicamente zero e
    renderebbe singolare l'informazione osservata: il termine esce.
    """
    return [t for t in TERMINI
            if t != "same_mixed" or bool((attrs["gender"] == "mixed").any())]


def carica(cfg, log):
    pop = common.load("population_gender.parquet")
    edges = common.load("edges_all.parquet")
    ids = set(pop[pop.gender.isin(["M", "F", "mixed"])].artist_id)
    E = edges[edges.u.isin(ids) & edges.v.isin(ids)]
    G = nx.Graph()
    G.add_nodes_from(ids)
    G.add_weighted_edges_from(E[["u", "v", "w"]].itertuples(index=False, name=None))
    G = G.subgraph([n for n, d in G.degree() if d > 0]).copy()
    G = G.subgraph(max(nx.connected_components(G), key=len)).copy()

    nodi = np.array(sorted(G.nodes()))
    pos = {a: i for i, a in enumerate(nodi)}
    a = pop.set_index("artist_id").reindex(nodi)
    n = len(nodi)
    attrs = {
        "gender": a.gender.values.astype(str),
        "genre": pd.factorize(a.musical_genre.fillna("Unknown"))[0].astype(np.int32),
        "cohort": pd.factorize(a.cohort_decade.astype("Int64").astype(str))[0].astype(np.int32),
        "lnr": np.log(a.n_release.fillna(1).clip(lower=1).values).astype(np.float64),
    }
    ii = np.array([pos[u] for u, _ in G.edges()], dtype=np.int32)
    jj = np.array([pos[v] for _, v in G.edges()], dtype=np.int32)
    A = csr_matrix((np.ones(len(ii), dtype=np.int8), (ii, jj)), shape=(n, n))
    A = A + A.T                              # simmetrica, serve per le righe
    log.info(f"rete: {n:,} nodi, {G.number_of_edges():,} archi, "
             f"{n*(n-1)//2:,} diadi da percorrere")
    return n, attrs, A, ii, jj, np.asarray(A.sum(1)).ravel()


def _blocco(r0, r1, n, attrs, A):
    """Design e risposta per tutte le diadi (i, j) con r0<=i<r1 e j>i."""
    g, gen, coh, lnr = (attrs["gender"], attrs["genre"],
                        attrs["cohort"], attrs["lnr"])
    righe, y_l = [], []
    for i in range(r0, r1):
        j = np.arange(i + 1, n)
        if not len(j):
            continue
        uno = np.ones(len(j))
        gi = g[i]
        M = np.column_stack([
            uno,
            ((gi == "F") & (g[j] == "F")).astype(np.float64),
            ((gi == "M") & (g[j] == "M")).astype(np.float64),
            ((gi == "mixed") & (g[j] == "mixed")).astype(np.float64),
            (gen[i] == gen[j]).astype(np.float64),
            (coh[i] == coh[j]).astype(np.float64),
            lnr[i] + lnr[j],
        ])
        sel = attrs.get("_sel")
        righe.append(M if sel is None else M[:, sel])
        riga = np.zeros(n, dtype=np.int8)
        s, e = A.indptr[i], A.indptr[i + 1]
        riga[A.indices[s:e]] = 1
        y_l.append(riga[i + 1:].astype(np.float64))
    if not righe:
        return None, None
    return np.vstack(righe), np.concatenate(y_l)


def _passata(b_list, n, attrs, A, servono_derivate: bool):
    """Una percorrenza di tutte le diadi.

    Restituisce la log-verosimiglianza di ciascun punto in `b_list` e, se
    richiesto, gradiente e informazione osservata nel PRIMO di quei punti.
    Costruire la matrice di disegno e' la parte cara; valutarci sopra piu'
    punti costa un prodotto scalare ciascuno, quindi conviene chiedere tutto
    cio' che serve in una volta sola.
    """
    B = np.vstack(b_list)
    k = B.shape[1]
    ll = np.zeros(len(B))
    XtWX = np.zeros((k, k))
    Xtr = np.zeros(k)
    for r0 in range(0, n, BLOCCO_RIGHE):
        X, y = _blocco(r0, min(r0 + BLOCCO_RIGHE, n), n, attrs, A)
        if X is None:
            continue
        ETA = X @ B.T
        # log(1+e^eta) calcolato con logaddexp: non trabocca per eta grandi
        ll += np.sum(y[:, None] * ETA - np.logaddexp(0.0, ETA), axis=0)
        if servono_derivate:
            p = expit(ETA[:, 0])
            w = p * (1.0 - p)
            XtWX += X.T @ (X * w[:, None])
            Xtr += X.T @ (y - p)
            del p, w
        del X, y, ETA
    return ll, XtWX, Xtr


def logit_esatto(n, attrs, A, log, avvio=None) -> pd.DataFrame:
    """Massimo esatto della verosimiglianza su tutte le diadi.

    Newton-Raphson con ricerca di linea. La verosimiglianza logistica ha un
    massimo unico, ma un passo intero preso lontano da quel massimo puo'
    scavalcarlo: in una prima versione senza ricerca di linea la
    log-verosimiglianza era peggiorata da -4,7 a -27,3 milioni fra la prima e
    la seconda iterazione. Ogni iterazione costa due percorrenze delle diadi —
    una per gradiente e informazione, una per scegliere quanto del passo
    adottare — e vicino all'ottimo il passo intero vince sempre, cosi' la
    convergenza resta quadratica.
    """
    termini = termini_di(attrs)
    attrs = {**attrs, "_sel": [TERMINI.index(t) for t in termini]}
    k = len(termini)
    m = int(A.nnz // 2)
    dens = m / (n * (n - 1) / 2)
    if avvio is not None:
        b = np.asarray(avvio, dtype=float).copy()
        log.info(f"avvio dai coefficienti gia' disponibili: "
                 + " ".join(f"{t}={v:+.3f}" for t, v in zip(termini, b)))
    else:
        b = np.zeros(k)
        b[0] = np.log(dens / (1 - dens))
        log.info(f"densita' osservata {dens:.3e}; intercetta iniziale {b[0]:.4f}")

    ll = None
    for it in range(MAX_NEWTON):
        with Timer(f"passata {it+1}a (derivate)", log):
            lls, XtWX, Xtr = _passata([b], n, attrs, A, True)
        ll = float(lls[0])
        passo = np.linalg.solve(XtWX, Xtr)
        proposto = float(np.max(np.abs(passo)))
        log.info(f"  iterazione {it+1}: logL={ll:,.2f}  passo proposto {proposto:.3e}")
        if proposto < TOLLERANZA:
            log.info(f"  convergenza esatta dopo {it+1} iterazioni")
            break

        cand = [b + f * passo for f in FRAZIONI]
        with Timer(f"passata {it+1}b (ricerca di linea)", log):
            ll_c, _, _ = _passata(cand, n, attrs, A, False)
        j = int(np.argmax(ll_c))
        if ll_c[j] <= ll + MIGLIORAMENTO_MINIMO:
            log.info(f"  nessuna frazione del passo migliora logL di piu' di "
                     f"{MIGLIORAMENTO_MINIMO}: massimo raggiunto "
                     f"(logL={ll:,.2f})")
            break
        f = FRAZIONI[j]
        b = cand[j]
        adottato = float(np.max(np.abs(f * passo)))
        log.info(f"    adottato x{f:g}: logL {ll:,.2f} -> {ll_c[j]:,.2f}, "
                 f"max|passo| {adottato:.3e}")
        log.info("    " + "  ".join(f"{t}={v:+.4f}" for t, v in zip(termini, b)))
        # Checkpoint a ogni iterazione: una passata costa quattordici minuti e
        # una stima interrotta non deve ricominciare dall'inizio.
        try:
            common.save(pd.DataFrame({"termine": termini, "coef": b}),
                        "logit_esatto_parziale.parquet")
        except Exception as e:
            log.warning(f"  checkpoint non salvato: {e!r}")
        if adottato < TOLLERANZA:
            log.info(f"  convergenza esatta dopo {it+1} iterazioni")
            ll = float(ll_c[j])
            break

    # informazione osservata nel punto finale, per gli errori standard
    with Timer("passata finale (errori standard)", log):
        lls, XtWX, _ = _passata([b], n, attrs, A, True)
    ll = float(lls[0])
    se = np.sqrt(np.diag(np.linalg.inv(XtWX)))
    out = pd.DataFrame({
        "termine": termini, "coef": b, "se": se,
        "z": b / se, "ci_lo": b - 1.96 * se, "ci_hi": b + 1.96 * se,
        "or": np.exp(b),
    })
    out["diadi"] = n * (n - 1) // 2
    out["logL"] = ll
    return out


def permutazione_esatta(n, attrs, ii, jj, gradi, log) -> pd.DataFrame:
    """Media e varianza esatte del numero di archi interni a un genere, sotto
    permutazione uniforme delle etichette dei nodi.

    Sia X il numero di archi con entrambi gli estremi di categoria c. Con m
    archi e n_c nodi di quella categoria su n:

        E[X]  = m * p2,   p2 = n_c(n_c-1) / (n(n-1))

    Per la varianza servono le probabilita' che DUE archi siano entrambi
    interni, e dipendono da quanti nodi distinti coinvolgono: tre se i due
    archi condividono un estremo, quattro se sono disgiunti. Il numero di
    coppie di archi adiacenti e' la somma dei C(d,2) sui gradi, e le restanti
    sono disgiunte. Non c'e' niente da simulare.
    """
    g = attrs["gender"]
    m = len(ii)
    # coppie ORDINATE di archi distinti che condividono un nodo
    adiacenti = int(np.sum(gradi * (gradi - 1)))          # = 2 * sum C(d,2)
    disgiunte = m * (m - 1) - adiacenti

    righe = []
    for c in ("F", "M", "mixed"):
        nc = int((g == c).sum())
        if nc < 4 or m < 2:
            continue
        p2 = nc * (nc - 1) / (n * (n - 1))
        p3 = p2 * (nc - 2) / (n - 2)
        p4 = p3 * (nc - 3) / (n - 3)
        oss = int(((g[ii] == c) & (g[jj] == c)).sum())
        media = m * p2
        # E[X^2] = E[X] + coppie_adiacenti*p3 + coppie_disgiunte*p4
        ex2 = media + adiacenti * p3 + disgiunte * p4
        var = ex2 - media ** 2
        sd = np.sqrt(var) if var > 0 else np.nan
        righe.append({
            "categoria": c, "nodi_categoria": nc,
            "archi_osservati": oss, "attesi": media, "sd_esatta": sd,
            "rapporto": oss / media if media else np.nan,
            "z": (oss - media) / sd if sd and np.isfinite(sd) else np.nan,
        })
    out = pd.DataFrame(righe)
    out["archi_totali"] = m
    out["nodi"] = n
    return out


def per_periodo(cfg, log) -> pd.DataFrame:
    """La serie temporale, calcolata esattamente decennio per decennio.

    Nessuna permutazione e nessun campionamento: per ogni periodo il logit
    percorre tutte le diadi fra i nodi attivi in quegli anni, e l'atteso sotto
    permutazione viene dalla forma chiusa. La Fase 4d aveva dato la stessa
    serie con mille permutazioni e un campione caso-controllo; questa la da'
    senza.
    """
    E = common.load("edges_datati.parquet")
    pop = common.load("population_gender.parquet").set_index("artist_id")
    gen_mappa = pop.gender

    righe = []
    for dec, g in E.groupby("decennio"):
        # gli stessi due estremi possono comparire in piu' decenni solo se il
        # legame e' ridatato, ma edges_datati tiene gia' il primo anno: qui
        # ogni arco appartiene a un solo periodo
        nodi = np.unique(np.concatenate([g.u.values, g.v.values]))
        nodi = nodi[pd.Index(nodi).isin(pop.index)]
        a = pop.reindex(nodi)
        a = a[a.gender.isin(["M", "F", "mixed"])]
        nodi = a.index.values
        pos = {x: i for i, x in enumerate(nodi)}
        gg = g[g.u.isin(pos) & g.v.isin(pos)]
        n = len(nodi)
        if n < 100 or len(gg) < 200:
            log.info(f"  {dec}s: {n} nodi, {len(gg)} archi — troppo pochi, saltato")
            continue

        attrs = {
            "gender": a.gender.values.astype(str),
            "genre": pd.factorize(a.musical_genre.fillna("Unknown"))[0].astype(np.int32),
            "cohort": pd.factorize(a.cohort_decade.astype("Int64").astype(str))[0].astype(np.int32),
            "lnr": np.log(a.n_release.fillna(1).clip(lower=1).values).astype(np.float64),
        }
        ii = gg.u.map(pos).values.astype(np.int32)
        jj = gg.v.map(pos).values.astype(np.int32)
        A = csr_matrix((np.ones(len(ii), dtype=np.int8), (ii, jj)), shape=(n, n))
        A = A + A.T
        gradi = np.asarray(A.sum(1)).ravel()

        r = {"decennio": int(dec), "nodi": n, "archi": len(gg),
             "diadi": n * (n - 1) // 2,
             "quota_donne": float((attrs["gender"] == "F").mean())}
        with Timer(f"periodo {dec}s ({n:,} nodi, {n*(n-1)//2:,} diadi)", log):
            perm = permutazione_esatta(n, attrs, ii, jj, gradi, log)
            for _, p in perm.iterrows():
                r[f"rapporto_{p.categoria}"] = p.rapporto
                r[f"z_{p.categoria}"] = p.z
            try:
                lo = logit_esatto(n, attrs, A, log)
                for _, x in lo.iterrows():
                    r[f"coef_{x.termine}"] = x.coef
                    r[f"se_{x.termine}"] = x.se
            except Exception as e:
                log.warning(f"  {dec}s: logit non risolvibile ({e!r})")
        righe.append(r)
        log.info(f"  {dec}s: donne {r['quota_donne']:.3f} | "
                 f"permutazione F {r.get('rapporto_F', float('nan')):.2f} "
                 f"(z={r.get('z_F', float('nan')):+.1f}) "
                 f"M {r.get('rapporto_M', float('nan')):.2f} | "
                 f"logit F {r.get('coef_same_F', float('nan')):+.3f} "
                 f"M {r.get('coef_same_M', float('nan')):+.3f}")
    return pd.DataFrame(righe)


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase4e_esatto", cfg)
    if common.exists("logit_esatto.parquet") and not force:
        log.info("Fase 4e gia' completata, salto")
        return
    n, attrs, A, ii, jj, gradi = carica(cfg, log)

    with Timer("permutazione esatta", log):
        perm = permutazione_esatta(n, attrs, ii, jj, gradi, log)
    log.info("\n" + perm.round(4).to_string(index=False))
    common.save(perm, "permutazione_esatta.parquet")
    common.save_table(perm, "t4_permutazione_esatta",
                      "Momenti esatti della distribuzione nulla per permutazione "
                      "delle etichette: media e deviazione in forma chiusa, non "
                      "stimate per simulazione")

    # I coefficienti caso-controllo della Fase 4c sono un ottimo punto di
    # partenza: stimano la stessa cosa su un campione. Non influiscono sul
    # risultato — la convergenza e' verificata sul passo, non sull'avvio — ma
    # risparmiano qualche percorrenza da cinque minuti l'una.
    # Se ne prendono le PENDENZE, non l'intercetta: quella del campione
    # caso-controllo dipende da una correzione esterna al modello, e un avvio
    # sbagliato di tredici unita' costa passate inutili. L'intercetta parte
    # dalla densita' osservata, che e' sempre nel giusto ordine di grandezza.
    avvio = None
    termini = termini_di(attrs)
    # un checkpoint di una stima interrotta ha la precedenza: e' gia' vicino
    if common.exists("logit_esatto_parziale.parquet"):
        c = common.load("logit_esatto_parziale.parquet").set_index("termine")
        if list(c.index) == termini:
            avvio = c.loc[termini, "coef"].values
            log.info("ripresa da checkpoint")
    if avvio is None and common.exists("dyadic_logit.parquet"):
        d = common.load("dyadic_logit.parquet").set_index("termine")
        if all(c in d.index for c in termini[1:]):
            dens = A.nnz / 2 / (n * (n - 1) / 2)
            avvio = np.concatenate([[np.log(dens / (1 - dens))],
                                    d.loc[termini[1:], "coef"].values])
    with Timer("logit esatto su tutte le diadi", log):
        out = logit_esatto(n, attrs, A, log, avvio=avvio)
    log.info("\n" + out.round(4).to_string(index=False))
    common.save(out, "logit_esatto.parquet")
    common.save_table(out, "t4_logit_esatto",
                      "Regressione logistica diadica calcolata su tutte le "
                      "1,62 miliardi di diadi della rete integrale, senza "
                      "campionamento")

    with Timer("serie temporale esatta", log):
        serie = per_periodo(cfg, log)
    log.info("\n" + serie.round(4).to_string(index=False))
    common.save(serie, "temporale_esatto.parquet")
    common.save_table(serie, "t4_temporale_esatto",
                      "Omofilia di genere per decennio di formazione del legame, "
                      "calcolata esattamente: tutte le diadi del periodo per il "
                      "logit, momenti in forma chiusa per la permutazione")
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
