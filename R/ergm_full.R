#!/usr/bin/env Rscript
# ===========================================================================
# ERGM sulla rete INTEGRALE, per scala crescente.
#
# Uso:  Rscript ergm_full.R <dir> <seed>
#
# La cartella contiene nodes.csv, edges.csv e control.json. A differenza di
# ergm_models.R, che stimava sottoreti campionate di 1.500 nodi, qui si punta
# alla rete intera: circa 59.000 nodi e 524.000 archi, cioe' 1,7 miliardi di
# diadi.
#
# Strategia
# ---------
# Non si lancia direttamente il modello piu' grande. Si stima la stessa
# specifica su reti di dimensione crescente, salvando dopo ognuna. Questo
# serve a tre cose:
#   1. se il modello integrale non converge, restano le stime intermedie;
#   2. la sequenza dei coefficienti al crescere di n dice se le stime su
#      sottorete erano rappresentative — che e' esattamente il limite
#      dichiarato nella versione precedente dell'articolo;
#   3. i tempi misurati a ogni scala permettono di prevedere la successiva
#      invece di indovinarla.
#
# Su ogni rete si stima anche la MPLE, che e' sempre calcolabile e fa da
# riferimento: se MCMLE e MPLE divergono molto, il termine di dipendenza sta
# facendo un lavoro importante; se coincidono, meno.
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

n_nodi <- nrow(nodes)
cat(sprintf("[%s] nodi=%s archi=%s diadi=%.2e\n", basename(dir),
            format(n_nodi, big.mark = "."), format(nrow(edges), big.mark = "."),
            n_nodi * (n_nodi - 1) / 2))

idx <- setNames(seq_len(n_nodi), as.character(nodes$artist_id))
el  <- cbind(idx[as.character(edges$u)], idx[as.character(edges$v)])
el  <- el[!is.na(el[, 1]) & !is.na(el[, 2]), , drop = FALSE]

net <- network.initialize(n_nodi, directed = FALSE)
net <- network.edgelist(el, net)
set.vertex.attribute(net, "gender",        as.character(nodes$gender))
set.vertex.attribute(net, "musical_genre", as.character(nodes$musical_genre))
set.vertex.attribute(net, "cohort_decade", as.character(nodes$cohort_decade))
set.vertex.attribute(net, "log_nrel",      as.numeric(nodes$log_nrel))

parti <- c("nodecov('log_nrel')")
if (length(unique(nodes$musical_genre)) > 1)
  parti <- c("nodematch('musical_genre')", parti)
if (length(unique(nodes$cohort_decade)) > 1)
  parti <- c(parti, "nodematch('cohort_decade')")
# Il termine di dipendenza arriva dal control.json: e' la variante che si sta
# provando. Su questa rete gwesp(0.25) non converge — lo step dell'ottimizzatore
# crolla di due ordini di grandezza alla seconda iterazione, che e' la firma
# della quasi-degenerazione — quindi si prova una sequenza di specifiche
# alternative, ognuna con la propria cartella.
rhs <- paste(c("edges", "nodematch('gender', diff = TRUE)", parti,
               ctrl$dipendenza),
             collapse = " + ")
cat(sprintf("  formula: net ~ %s\n", rhs))
cat(sprintf("  metodo: %s\n", if (!is.null(ctrl$metodo)) ctrl$metodo else "MCMLE"))
f <- as.formula(paste("net ~", rhs))

estrai <- function(m, etichetta, secondi, metodo) {
  s  <- summary(m)
  cf <- as.data.frame(s$coefficients)
  names(cf)[1:4] <- c("estimate", "se", "mcmc_se", "p")
  cf$term <- rownames(cf)
  ci <- tryCatch(suppressWarnings(confint(m)),
                 error = function(e) matrix(NA_real_, nrow(cf), 2))
  cf$ci_lo <- ci[, 1]; cf$ci_hi <- ci[, 2]
  cf$or <- exp(cf$estimate)
  cf$model <- etichetta; cf$metodo <- metodo
  cf$n_nodi <- n_nodi; cf$n_archi <- nrow(el); cf$secondi <- secondi
  cf
}

risultati <- list()

# ---- 1. MPLE: sempre calcolabile, e' il riferimento -----------------------
cat("  -> MPLE\n")
t0 <- Sys.time()
mple <- try(suppressWarnings(ergm(
  f, estimate = "MPLE",
  control = control.ergm(MPLE.samplesize = ctrl$mple_samplesize,
                         seed = seed))), silent = TRUE)
dt <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
if (!inherits(mple, "try-error")) {
  cat(sprintf("     MPLE ok in %.0fs\n", dt))
  risultati[["MPLE"]] <- estrai(mple, "MPLE", dt, "MPLE")
  write.csv(do.call(rbind, risultati), file.path(dir, "coef.csv"), row.names = FALSE)
} else {
  cat(sprintf("     MPLE FALLITA in %.0fs\n", dt))
}

# ---- 2. MCMLE: la stima vera ---------------------------------------------
cat("  -> MCMLE\n")
metodo <- if (!is.null(ctrl$metodo)) ctrl$metodo else "MCMLE"
ctl <- control.ergm(
  main.method         = metodo,
  MCMLE.effectiveSize = NULL,
  MCMLE.termination   = "Hummel",
  MCMC.samplesize     = ctrl$samplesize,
  MCMC.burnin         = ctrl$burnin,
  MCMC.interval       = ctrl$interval,
  MCMLE.maxit         = ctrl$maxit,
  MPLE.samplesize     = ctrl$mple_samplesize,
  parallel            = ctrl$parallel,
  parallel.type       = "PSOCK",
  seed                = seed
)
t0 <- Sys.time()
m <- try(suppressWarnings(ergm(f, control = ctl, verbose = FALSE)), silent = TRUE)
dt <- as.numeric(difftime(Sys.time(), t0, units = "secs"))

if (inherits(m, "try-error")) {
  cat(sprintf("     MCMLE NON CONVERGE dopo %.0fs\n", dt))
  write(toJSON(list(converged = length(risultati) > 0, mcmle = FALSE,
                    n_nodi = n_nodi, n_archi = nrow(el), secondi = dt,
                    errore = substr(paste(as.character(m), collapse = " "), 1, 500)),
               auto_unbox = TRUE), file.path(dir, "summary.json"))
  quit(status = 0)
}

cat(sprintf("     MCMLE ok in %.0fs (%.1f ore)\n", dt, dt / 3600))
risultati[["MCMLE"]] <- estrai(m, "M1_con_gwesp", dt, "MCMLE")
write.csv(do.call(rbind, risultati), file.path(dir, "coef.csv"), row.names = FALSE)

if (!is.null(m$sample)) {
  sm  <- as.matrix(m$sample)
  ess <- tryCatch(coda::effectiveSize(m$sample),
                  error = function(e) rep(NA_real_, ncol(sm)))
  write.csv(data.frame(term = colnames(sm), mcmc_mean = colMeans(sm),
                       mcmc_sd = apply(sm, 2, sd), ess = as.numeric(ess),
                       n_nodi = n_nodi),
            file.path(dir, "mcmc.csv"), row.names = FALSE)
}

# ---- 3. bonta' di adattamento, se la rete lo consente --------------------
gof_fatta <- FALSE
if (isTRUE(ctrl$gof)) {
  cat("  -> GOF\n")
  g <- try(gof(m, GOF = ~ degree + espartners + distance,
               control = control.gof.ergm(nsim = ctrl$gof_nsim)), silent = TRUE)
  if (!inherits(g, "try-error")) {
    write.csv(rbind(
      data.frame(statistica = "grado",    valore = rownames(g$summary.deg),    g$summary.deg),
      data.frame(statistica = "esp",      valore = rownames(g$summary.espart), g$summary.espart),
      data.frame(statistica = "distanza", valore = rownames(g$summary.dist),   g$summary.dist)),
      file.path(dir, "gof.csv"), row.names = FALSE)
    gof_fatta <- TRUE
  } else cat("     GOF fallita\n")
}

write(toJSON(list(converged = TRUE, mcmle = TRUE, n_nodi = n_nodi,
                  n_archi = nrow(el), secondi = dt, ore = dt / 3600,
                  aic = AIC(m), bic = BIC(m), gof = gof_fatta),
             auto_unbox = TRUE), file.path(dir, "summary.json"))
cat("  fatto\n")
