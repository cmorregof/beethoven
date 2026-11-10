# Especificación de la sensibilidad a cita literal (LS-1, LS-2), fijada antes de medir

Torre de control, 2026-11-10. Se versiona en un commit antes de ejecutar
`scripts/literal_sensitivity_n8.py`. Forma parte del borrador de enmienda D-43 (pendiente de
aprobación del usuario). No toca la obra objetivo ni a Cherubini, y no cambia nada de lo congelado
en D-41: n = 8, λ = 0,45, t_DF y t_E (se leen de `results/thresholds_n8.json`), estrato 1750-1830
y fondo.

## Pares de control (cita literal)

A = edición Le Cène de *L'estro armonico* op. 3 (`musedata_vivaldi-lecene-op3-rvX`) y
B = transcripción para teclado del *Anne Dawson's Book* (`musedata_vivaldi-dawson-op3-rvX`),
X ∈ {230, 265, 519, 567}. Las obras Le Cène son no primarias (D-29: duplicados de las de Dawson)
y no tienen caché en el checkout principal; se extraen con `scripts/extract.py::extract_work` sin
cambios hacia la caché del worktree (ignorada por git), con rest_break 0.

## LS-1 (principal)

Análogo exacto de la «sensibilidad en positivos» de D-41. Instancias: tipos de ventana de 8 notas
(7-grama IVR, rest_break 0, misma simbolización que `thresholds_n8.windows_with_movement`) de A
presentes en B. DF = `Models.df(s, cA, cB)` y E = ventanas_B · `Models.p_hier(s, cA, cB, wB)` con
`Models("1750-1830", 8, 0.45)`, exactamente como `scripts/thresholds_n8.py`. Métricas: fracción de
instancias con DF ≤ t_DF, con E ≤ t_E y con ambas, global y por par, con IC de Wilson al 95 %; y
tipos que pasan con ritmo no uniforme. Variante secundaria etiquetada: excluir además a Beethoven
del fondo (el fondo que tendrá el caso objetivo). Cherubini no tiene obras en las tablas de fondo
(su única obra es objetivo y está excluida), así que excluirlo no cambia nada.

## LS-2 (secundaria)

Potencia del test de fragmentos propuesto en D-43. Fragmentos contiguos de A (todas las voces) de
longitud equivalente a 10, 15 y 20 compases, medida en número total de ventanas de 8 notas;
200 fragmentos por par y longitud, semilla 20260903. Estadístico: tipos del fragmento presentes en B
con DF ≤ t_DF. Nulo: 1000 fragmentos de igual longitud de obras primarias del estrato <1750 con
instrumentación de cuerda, de compositores distintos de Vivaldi (Corelli op. 1–4 y op. 6, Handel
op. 6). p = fracción de nulos con recuento ≥ observado. Potencia = fracción de fragmentos con
p ≤ 0,025 (Bonferroni sobre los dos fragmentos de Cherubini).

## Comprobación de humo

Antes de medir, se recalculan DF y E de 20 filas del par P07 y se comparan con
`results/thresholds_n8_windows.csv` (tolerancia relativa 1e-9). Si no coinciden, el script aborta.

## Lectura

La sensibilidad medida es una cota superior para cita literal: los controles son arreglos para
teclado de un repertorio anterior (<1750), con otra instrumentación que los cuartetos 1750–1830
con los que se calibraron los umbrales.

## Nota sobre D-41

D-41 escribe el término de compositor del fondo jerárquico como «p_KN[obras de Cherubini sin la
obra B]». D-39, D-40 y el código congelado (`Models.p_hier`) usan el compositor de B. Se sigue el
código congelado. Solo afecta a E, que en el confirmatorio es un ranking informativo, no la
decisión. D-43 debe registrarlo como aclaración.
