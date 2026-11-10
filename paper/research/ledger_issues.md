# Incidencias del ledger de numeros

Generado por `paper/make_numbers.py` (no editar a mano). Nada se ha corregido: las claves en desajuste quedan fuera de `paper/numbers.tex` (usarlas da error de compilacion) hasta que la torre decida.

- Claves: 1266 (1264 validas, 2 con desajuste).
- Comprobaciones cruzadas: 632 (629 correctas, 3 fallidas).

## Desajustes

| clave | valor del ledger | documento y localizador | valor en el documento |
|---|---|---|---|
| corpus_extract_fail | 32 | docs/DECISIONES.md :: D-23 titulo 'Unidades que no parsean (N de 6.990)' | 27 |
| corpus_extract_fail | 32 | results/extract_log.csv :: recuento de status != ok (filas prohibidas omitidas) | 30 |
| corpus_parse_fail_units | 30 | docs/DECISIONES.md :: D-23 titulo 'Unidades que no parsean (N de 6.990)' | 27 |

## Avisos (no son desajustes numericos)

- summary.md §1 y PLAN.md §1 citan 1873 obras primarias, pero base_rate.json analiza 1871 (= 1873 - 2 obras objetivo excluidas; aritmetica, sin leer el catalogo). Clave corpus_works_total = 1873; corpus_works_catalog = 1871. La torre decide cual cita el paper.
- extract_log.csv: 7165 filas permitidas (5 omitidas por la guardia del preregistro, sin leer su contenido), 30 con status != ok. extract_summary.md: 32; summary.md §1: 30.
- Tres cifras distintas de unidades que no parsean: 27 (docs/DECISIONES.md D-23, de 6.990), 30 (summary.md §1) y 32 (extract_summary.md); extract_log.csv recuenta 30. El paper no cita ninguna hasta que el usuario lo resuelva (decision de la torre).
- lambda_by_n.csv contiene n = [4, 5, 6, 7, 8, 10, 12]; no hay n = 9 ni n = 11 (D-41 tampoco los incluye). No se inventan.

## Comprobaciones por documento

| documento | comprobaciones | correctas |
|---|---|---|
| (interno) | 17 | 17 |
| decisions/D-41_preregistro.md | 79 | 79 |
| docs/DECISIONES.md | 25 | 23 |
| paper/PLAN.md | 8 | 8 |
| results/background_calibration.md | 2 | 2 |
| results/extract_log.csv | 2 | 1 |
| results/kn_calibration.md | 57 | 57 |
| results/lambda_by_n_grid.csv | 5 | 5 |
| results/summary.md | 434 | 434 |
| results/uniqueness.json | 3 | 3 |

## Claves usadas en el texto sin resolver

Escaneo de `paper/sections`, `paper/tables`, `paper/figures/*.tex` y `main.tex` (no entra en `--check`).

- Claves distintas usadas: 192; resueltas directamente: 184.

### Con alias (la torre corrige el texto; 6)

- `thresh_comb_fpr` -> `thresh_comb_fpr_pct` (results.tex la usa seguida de \,\%; la clave existente incluye \%) [results.tex]
- `thresh_comb_sens` -> `thresh_comb_sens_pct` (results.tex la usa seguida de \,\%; la clave existente incluye \%) [results.tex]
- `thresh_df_fpr` -> `thresh_df_fpr_pct` (CONFLICTO: intro/discussion la usan sin \,\% (necesitan \%); results/protocol con \,\% (necesitan _pct)) [abstract.tex, captions.tex, intro.tex, protocol.tex, results.tex]
- `thresh_df_sens` -> `thresh_df_sens_pct` (CONFLICTO: intro/discussion la usan sin \,\% (necesitan \%); results/protocol con \,\% (necesitan _pct)) [abstract.tex, captions.tex, discussion.tex, intro.tex, protocol.tex, results.tex]
- `thresh_e_fpr` -> `thresh_e_fpr_pct` (results.tex la usa seguida de \,\%; la clave existente incluye \%) [results.tex]
- `thresh_e_sens` -> `thresh_e_sens_pct` (results.tex la usa seguida de \,\%; la clave existente incluye \%) [results.tex]

### Sin fuente versionada o con desajuste (2)

- `clave` [main.tex]: Marcador de ejemplo en main.tex, no es una clave.
- `key` [results.tex]: Marcador de ejemplo en results.tex, no es una clave.

### Notas de formato y nombres

- `calib_df_slope` y `calib_df_mae` existen con 3 decimales (1.021, 0.192; precision de kn_calibration.md); A2 esperaba 2 decimales. Lo mismo `calib_unseen_e_lap/kn` (1.021 / 0.043).
- `thresh_df_fpr`, `thresh_df_sens` incluyen `\%`: usadas con `\,\%` detras (results, protocol) darian `%%`. Para eso existen los gemelos `thresh_{df,e,comb}_{fpr,sens}_pct`.
- Las claves de porcentaje pedidas por A2 (`*_pct_*`, `uniq_p*_ivr_*`, `literal_*`) no llevan `%`; las del ledger original (`baserate_d4_prev_*`, `corpus_windows_pct_*`) si.
- `literal_spec_commit` = a240875...; el JSON de A3 y el mensaje de la torre mencionan 4c00ffa como commit del resultado; el ledger lee solo `spec_commit` y `head_commit` del JSON.
