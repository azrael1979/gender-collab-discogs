#!/usr/bin/env Rscript
# ===========================================================================
# FASE 4 — ERGM sulle reti di collaborazione (statnet)
#
# Uso:  Rscript ergm_models.R <dir_modello> [seed]
# La cartella contiene nodes.csv, edges.csv, control.json prodotti dal driver
# Python; i risultati tornano in coef.csv, gof.csv, mcmc.csv, stato_modelli.csv
# e summary.json.
#
# Si stima una GERARCHIA di modelli, dal piu' robusto al piu' ambizioso:
#
#   M0  edges + nodematch(gender, diff) + controlli
#       Nessun termine di dipendenza: stimabile sempre, e' il riferimento.
#   M1  M0 + gwesp(decay, fixed)
#       La specifica richiesta dal disegno. Il termine di chiusura triadica
#       rende il modello quasi degenere su reti molto clusterizzate e puo'
#       non convergere: in tal caso lo si dichiara e resta valido M0.
#   M2  come il migliore fra M1 e M0, ma con nodemix(gender) al posto di
#       nodematch(gender, diff): le due parametrizzazioni sono ridondanti fra
#       loro e messe insieme renderebbero il modello non identificato.
#
# I termini di controllo entrano solo se l'attributo VARIA nella sottorete:
# dentro una sottorete di un solo genere musicale nodematch('musical_genre')
# coincide con edges, e il modello non sarebbe identificato.
# ===========================================================================
suppressPackageStartupMessages({
  library(ergm); library(network); library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
dir  <- args[1]
seed <- if (length(args) > 1) as.integer(args[2]) else 20260920
set.seed(seed)

nodes <- read.csv(file.path(dir, "nodes.csv"), stringsAsFactors = FALSE)
edges <- read.csv(file.path(dir, "edges.csv"), stringsAsFactors = FALSE)
ctrl  <- fromJSON(file.path(dir, "control.json"))

cat(sprintf("[%s] nodi=%d archi=%d\n", basename(dir), nrow(nodes), nrow(edges)))

idx <- setNames(seq_len(nrow(nodes)), as.character(nodes$artist_id))
el  <- cbind(idx[as.character(edges$u)], idx[as.character(edges$v)])
el  <- el[!is.na(el[, 1]) & !is.na(el[, 2]), , drop = FALSE]

net <- network.initialize(nrow(nodes), directed = FALSE)
net <- network.edgelist(el, net)
set.vertex.attribute(net, "gender",        as.character(nodes$gender))
set.vertex.attribute(net, "musical_genre", as.character(nodes$musical_genre))
set.vertex.attribute(net, "cohort_decade", as.character(nodes$cohort_decade))
set.vertex.attribute(net, "log_nrel",      as.numeric(nodes$log_nrel))

parti <- c("nodecov('log_nrel')")
if (isTRUE(ctrl$usa_genere)) parti <- c("nodematch('musical_genre')", parti)
if (isTRUE(ctrl$usa_coorte)) parti <- c(parti, "nodematch('cohort_decade')")
base_rhs <- paste(parti, collapse = " + ")
gw <- sprintf("gwesp(%s, fixed = TRUE)", ctrl$gwesp_decay)
cat(sprintf("  controlli: %s\n", base_rhs))

# NOTA sul controllo MCMC, che e' stata la differenza fra convergere e non
# convergere. ergm 4.x usa per default `MCMLE.effectiveSize = 64`: la
# dimensione del campione MCMC viene aumentata automaticamente finche' la
# catena non raggiunge quella dimensione efficace. Su una catena appiccicosa
# — ed e' il caso quando c'e' un termine gwesp su una rete clusterizzata — il
# campione cresce senza limite e la prima iterazione non termina mai. Fissando
# la dimensione del campione (effectiveSize = NULL) e usando la terminazione
# di Hummel, ogni iterazione costa un tempo prevedibile e la stima arriva a
# convergenza in una decina di minuti.
ctl <- control.ergm(
  MCMLE.effectiveSize = NULL,
  MCMLE.termination   = "Hummel",
  MCMC.samplesize     = ctrl$samplesize,
  MCMC.burnin         = ctrl$burnin,
  MCMC.interval       = ctrl$interval,
  MCMLE.maxit         = if (!is.null(ctrl$maxit)) ctrl$maxit else 20,
  seed                = seed,
  parallel            = 0
)

fit_one <- function(rhs, label) {
  cat(sprintf("  -> %s : %s\n", label, rhs))
  t0 <- Sys.time()
  f  <- as.formula(paste("net ~", rhs))
  m  <- try(suppressWarnings(ergm(f, control = ctl, verbose = FALSE)), silent = TRUE)
  dt <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
  if (inherits(m, "try-error")) {
    cat(sprintf("     NON CONVERGE dopo %.0fs\n", dt))
    return(list(ok = FALSE, label = label, secondi = dt,
                error = paste(as.character(m), collapse = " ")))
  }
  s  <- summary(m)
  cf <- as.data.frame(s$coefficients)
  names(cf)[1:4] <- c("estimate", "se", "mcmc_se", "p")
  cf$term  <- rownames(cf)
  cf$model <- label
  ci <- tryCatch(suppressWarnings(confint(m)),
                 error = function(e) matrix(NA_real_, nrow(cf), 2))
  cf$ci_lo <- ci[, 1]; cf$ci_hi <- ci[, 2]
  cf$or    <- exp(cf$estimate)
  mc <- data.frame()
  if (!is.null(m$sample)) {
    sm  <- as.matrix(m$sample)
    ess <- tryCatch(coda::effectiveSize(m$sample),
                    error = function(e) rep(NA_real_, ncol(sm)))
    mc  <- data.frame(term = colnames(sm), model = label,
                      mcmc_mean = colMeans(sm), mcmc_sd = apply(sm, 2, sd),
                      ess = as.numeric(ess))
  }
  cat(sprintf("     ok in %.0fs (%s)\n", dt,
              if (is.null(m$sample)) "solo MPLE" else "MCMLE"))
  list(ok = TRUE, label = label, coef = cf, mcmc = mc, model = m,
       aic = AIC(m), bic = BIC(m), secondi = dt, mple = is.null(m$sample))
}

gender_match <- "edges + nodematch('gender', diff = TRUE)"
gender_mix   <- "edges + nodemix('gender', base = 1)"

# I risultati si scrivono DOPO OGNI MODELLO, non alla fine. Se il processo
# venisse interrotto dal tempo massimo mentre stima il modello piu' pesante,
# quelli gia' conclusi resterebbero comunque su disco: senza questa scrittura
# incrementale un timeout su M1 porterebbe via anche M0, che converge in
# pochi secondi ed e' il modello di riferimento.
salva_incrementale <- function(res) {
  ok <- Filter(function(x) isTRUE(x$ok), res)
  if (length(ok)) {
    write.csv(do.call(rbind, lapply(ok, `[[`, "coef")),
              file.path(dir, "coef.csv"), row.names = FALSE)
    mc <- do.call(rbind, lapply(ok, `[[`, "mcmc"))
    if (!is.null(mc) && nrow(mc)) {
      write.csv(mc, file.path(dir, "mcmc.csv"), row.names = FALSE)
    }
  }
  write.csv(data.frame(modello     = unname(sapply(res, `[[`, "label")),
                       convergenza = unname(sapply(res, function(x) isTRUE(x$ok))),
                       secondi     = unname(sapply(res, `[[`, "secondi"))),
            file.path(dir, "stato_modelli.csv"), row.names = FALSE)
  # summary.json provvisorio: reso definitivo in fondo
  write(toJSON(list(converged = length(ok) > 0,
                    parziale  = TRUE,
                    modelli   = unname(sapply(ok, `[[`, "label")),
                    aic       = unname(sapply(ok, `[[`, "aic")),
                    bic       = unname(sapply(ok, `[[`, "bic")),
                    secondi   = unname(sapply(ok, `[[`, "secondi")),
                    solo_mple = unname(sapply(ok, `[[`, "mple")),
                    gwesp_ok  = any(sapply(ok, function(x) grepl("gwesp", x$label))),
                    n_nodi    = nrow(nodes), n_archi = nrow(el),
                    gof       = FALSE),
               auto_unbox = TRUE), file.path(dir, "summary.json"))
  invisible(ok)
}

res <- list()
res$M0 <- fit_one(paste(gender_match, base_rhs, sep = " + "), "M0_senza_gwesp")
salva_incrementale(res)
res$M1 <- fit_one(paste(gender_match, base_rhs, gw, sep = " + "), "M1_con_gwesp")
salva_incrementale(res)
usa_gw <- isTRUE(res$M1$ok)
res$M2 <- fit_one(paste(c(gender_mix, base_rhs, if (usa_gw) gw), collapse = " + "),
                  if (usa_gw) "M2_nodemix_gwesp" else "M2_nodemix")
ok <- salva_incrementale(res)

if (length(ok) == 0) {
  write(toJSON(list(converged = FALSE,
                    errori = unname(sapply(res, function(x)
                      if (is.null(x$error)) "" else substr(x$error, 1, 400)))),
               auto_unbox = TRUE), file.path(dir, "summary.json"))
  cat("  nessun modello converge\n")
  quit(status = 0)
}

# ---- bonta' di adattamento sul modello piu' ricco che ha retto
best <- ok[[length(ok)]]
gof_df <- tryCatch({
  g <- gof(best$model, GOF = ~ degree + espartners + distance)
  rbind(
    data.frame(statistica = "grado",    valore = rownames(g$summary.deg),    g$summary.deg),
    data.frame(statistica = "esp",      valore = rownames(g$summary.espart), g$summary.espart),
    data.frame(statistica = "distanza", valore = rownames(g$summary.dist),   g$summary.dist))
}, error = function(e) { cat("     GOF fallita:", conditionMessage(e), "\n"); NULL })
if (!is.null(gof_df)) write.csv(gof_df, file.path(dir, "gof.csv"), row.names = FALSE)

write(toJSON(list(converged = TRUE,
                  parziale  = FALSE,
                  modelli   = unname(sapply(ok, `[[`, "label")),
                  aic       = unname(sapply(ok, `[[`, "aic")),
                  bic       = unname(sapply(ok, `[[`, "bic")),
                  secondi   = unname(sapply(ok, `[[`, "secondi")),
                  solo_mple = unname(sapply(ok, `[[`, "mple")),
                  gwesp_ok  = usa_gw,
                  n_nodi    = nrow(nodes), n_archi = nrow(el),
                  gof       = !is.null(gof_df)),
             auto_unbox = TRUE), file.path(dir, "summary.json"))
cat("  fatto\n")
