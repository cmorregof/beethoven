# Figuras del paper

Todas se generan con `/Users/cmorregof/Personal/Beethoven/.venv/bin/python paper/figures/make_figures.py [nombre ...]`
(sin argumentos: todas) desde la raíz del worktree. Estilo en `style.py` (perfil `default`: 3,35 / 7,0 in,
STIXGeneral, 8–9 pt, Okabe–Ito, fuentes embebidas tipo 42; para otra revista añadir un perfil a `PROFILES`
y usar `FIG_PROFILE=<perfil>`). Sin títulos dentro de la figura. Guardia D-41 en cada lectura.

| Figura | Fuente (versionada) | Comando |
|---|---|---|
| `fig_method_schema.pdf` | solo diseño (texto; n = 8 y FPR 5 % son constantes de diseño) | `make_figures.py fig_method_schema` |
| `fig_corpus.pdf` | `results/base_rate.json` (strata.period, strata.collection) | `make_figures.py fig_corpus` |
| `fig_base_rates.pdf` | `results/base_rate.json` (strata.all/period: rate_per_100k, prevalence_pct) | `make_figures.py fig_base_rates` |
| `fig_observed_vs_null.pdf` | `results/base_rate.json` (null.D4: obs, mean, ci95, ratio) | `make_figures.py fig_observed_vs_null` |
| `fig_uniqueness.pdf` | `results/uniqueness.json` (curve, curve_by_period) | `make_figures.py fig_uniqueness` |
| `fig_calibration.pdf` | `results/kn_calibration.csv`, `results/kn_calibration_pairs.csv`, `results/kn_calibration.json` | `make_figures.py fig_calibration` |
| `fig_lambda_profile.pdf` | `results/lambda_by_n_grid.csv`, `results/lambda_by_n.csv` | `make_figures.py fig_lambda_profile` |
| `fig_roc_pr.pdf` | `results/thresholds_n8_windows.csv`, `results/thresholds_n8.json` | `make_figures.py fig_roc_pr` |
| `fig_literal_sensitivity.pdf` | `results/literal_sensitivity_n8.json` (A3); función preparada, se omite si no existe | `make_figures.py fig_literal_sensitivity` |

Comprobaciones internas (el script aborta si fallan): métricas de calibración idénticas a
`kn_calibration.json`; AUC, AP, FPR y sensibilidad de `fig_roc_pr` idénticos a `thresholds_n8.json`
(`roc()` copiada literalmente de `scripts/thresholds_n8.py`).

Notas: la curva DF→E de `fig_roc_pr` es escalonada por construcción (la puerta DF deja el resto empatado
en −1e9, como en el script original). `fig_lambda_profile` muestra la log-verosimilitud relativa al máximo
de la rejilla de cada n (el archivo da valores absolutos); los puntos son λ* de `lambda_by_n.csv`.
`fig_corpus` usa `base_rate.json` (1859 obras analizadas, 4-gramas), no la tabla de unidades de `summary.md`.

## Ronda final (revista: Musicae Scientiae, SAGE)

- Tamaños sin cambios (3,35 / 7,0 in); un PDF por figura, numeración en el pie (LaTeX).
- `fig_method_schema`: la caja 7 rotula el nulo de fragmentos de igual longitud como propuesta D-43 (borrador), sin atribuirlo a D-41.
- Escala de grises: cada serie se distingue por marcador y/o estilo de línea además del color (comprobado con
  `gs -sDEVICE=pnggray`). Perfil de curvas de λ: orden por luminosidad (n creciente = más claro) y leyenda.
- Fuentes: todas embebidas (TrueType tipo 42, sin Type 3; comprobado en los PDF). `save()` aborta si algún texto visible
  mide < 7 pt; los subíndices/superíndices de mathtext (p. ej. P_cross) se reducen por construcción a ~70 %.
- Regenerar todo: `/Users/cmorregof/Personal/Beethoven/.venv/bin/python paper/figures/make_figures.py`.
