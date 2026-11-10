# A3: código confirmatorio y sensibilidad a cita literal (notas de implementación)

Archivos: `scripts/confirmatory_n8.py`, `scripts/literal_sensitivity_n8.py`,
`tests/test_confirmatory_n8.py`, `tests/test_literal_sensitivity_n8.py`,
`results/literal_sensitivity_n8.{json,csv}`.

## Advertencia principal (va también en el JSON, campo `caveats`)

La sensibilidad de LS-1 y LS-2 con los pares Dawson/Le Cène es una **cota superior para la cita
literal con cambio de dominio**. Son arreglos literales para teclado de conciertos de cuerda del
estrato <1750, y se miden contra umbrales (t_DF, t_E) calibrados en cuartetos de cuerda de 1750–1830.

## Decisiones de implementación

- **Ventanas.** Uso la misma simbolización que `thresholds_n8.windows_with_movement`:
  `seqlib.sequences_ex(d, 0.0)`, `kn_background.symbols_of` y `kn_background.order_hashes`, con
  m = 7. El hash rodante sobre la secuencia entera da el mismo valor que el hash de cada ventana
  por separado; lo he comprobado en 50 secuencias aleatorias. Las copias locales sin dependencias,
  usadas en los tests (`symbols_from_arr`, `rolling_hashes_local`), coinciden con el pipeline.
- **Vivaldi fuera del estrato.** `M.widx[wB]` existe, porque las obras Dawson son primarias y están
  en `meta.json`. En cambio, `comp_works["vivaldi_a"]` está vacío. Por eso `excl_of(cA, cB)` = ∅ y
  DF se calcula sobre el estrato completo. Además, `p_comp` devuelve `None` y `p_hier` cae en p_KN
  del estrato: λ no interviene. No cambio ninguna fórmula; el script comprueba todo esto y lo anota
  en `vivaldi_check`.
- **Variante noBeethoven.** Pongo `cA = "beethoven_l"` en la ranura de exclusión y dejo
  `cB = "vivaldi_a"`, para que `p_comp` mantenga su significado. No excluye a Cherubini: la API solo
  tiene dos ranuras. El fondo del caso objetivo excluye a ambos.
- **Le Cène no está en la caché.** Las cuatro obras rv230/265/519/567 tienen `is_primary = 0`. Las
  extraigo con `extract.extract_work` sin cambios, redirigiendo `CACHE` a `W/corpus/cache`, que git
  ignora. No se escribe nada en M.
- **Compases (LS-2).** El número de compases de A es el de finales de compás distintos
  (`offset + bar_remaining`) por movimiento. La longitud en ventanas es L compases × (ventanas de A /
  compases de A). El nulo usa el mismo número de ventanas.
- **Fragmentos.** Son tramos contiguos de L ventanas en orden (movimiento, ataque, voz), sin cruzar
  de movimiento. Los inicios se eligen de forma uniforme. En el nulo, el sorteo es uniforme sobre
  todos los pares (obra, inicio) válidos de la piscina.
- **Piscina del nulo de LS-2.** Obras de conjunto de cuerda <1750, primarias y en análisis, sin
  Vivaldi y sin obras prohibidas, con estos prefijos de `work_id`: `musedata_corelli-chry-concerto-`,
  `musedata_corelli-chry-trio-`, `dcml-corelli-op-` (Corelli op. 1–4 y 6), y
  `musedata_handel-brit-orch-op06-`, `musedata_handel-haa-op6n` (Handel op. 6). El catálogo no tiene
  campo de instrumentación, así que la lista es un juicio explícito. Como las obras de la piscina son
  <1750, DF no cambia con el compositor de A′, y S_B se calcula una sola vez por par y variante.
  Fragmentos observados y nulos: un único `default_rng(20260903)` en orden pares × longitudes; las
  dos variantes comparten los mismos fragmentos.
- **Confirmatorio (corregido el 2026-11-10 tras la revisión de A2, hallazgos altos 1 y 2).**
  - *Exclusión por réplica (D-37/D-41; principal en D-43).* Se precalcula
    S_B[c] = {q ∈ tipos(B) : M.df(q, c, cB) ≤ t_DF} para el compositor de A y para cada compositor de
    la piscina. K(A) se cuenta contra S_B[compositor de A] y cada réplica A′, contra
    S_B[compositor de A′]. La versión anterior aplicaba a todas las réplicas la exclusión fija
    (Cherubini, Beethoven): desinflaba el nulo y el test era anticonservador. La exclusión común
    ({B} ∪ compositores de la piscina, D-43 e) va como secundario etiquetado
    (`secondary_common_exclusion`). Se implementa con una segunda instancia de `Models` que comparte
    `Tables` y sustituye `excl_of` por el conjunto común; `df` no cambia.
  - *Piscina.* `--null-pool` lee `paper/D-43_null_pool.csv` con `csv.DictReader`, separa por la
    columna `fragments` (A2 → `orchestra`; A1 → las tres clases) y aplica la guardia a cada fila y a
    su fila del catálogo (`is_target`). Rechaza el formato antiguo, una lista de ids.
  - *Fragmentos A′ (D-43 b).* La barra de inicio se sortea uniformemente entre todas las barras de la
    piscina; se añaden compases completos, con todas las partes, hasta que L(A′) ∈ [0,95, 1,05]·L(A)
    en ventanas. Si no se consigue, se resortea; se informan los sorteos y la tasa de rechazo. Hay
    colapso de dobladas (regla D-13) por fragmento, en A y en A′, y las ventanas que cruzan el borde
    no cuentan. `--measure quarters` es la alternativa declarada: duración en negras.
  - *Colapso y caché.* Aplico el colapso de fragmento sobre la caché, que ya colapsó por movimiento.
    No reextraigo desde `corpus/raw`, la versión principal de D-43 b. Es el hueco 3 de D-43, que
    queda declarado.
  - *Semilla y p.* `default_rng([20260903, k])` con k = número de la etiqueta (A1 → 1, A2 → 2), así
    que el resultado no depende del orden. Se informan p (D-41) y (1 + #)/(1 + R), con Bonferroni
    sobre el número de fragmentos.
  - Uso: `--A A1=<work_id> A2=<work_id> --null-pool paper/D-43_null_pool.csv`. El caso no se ha
    ejecutado; 10 tests sintéticos nuevos fallan con el código anterior y pasan con el nuevo
    (suite: 52 pasan, 2 se saltan).
- **LS-2 no se ve afectado.** Su piscina (Corelli 72, Handel 39 en `meta.json`) es entera del
  periodo <1750; ninguna de esas obras está en las tablas de 1750-1830. Por eso
  `comp_works[corelli_a]` y `comp_works[handel_gf]` están vacíos, y la exclusión por réplica coincide
  con la fija (∅, Vivaldi). S_B es el mismo y los resultados no cambian.
- **Bloqueo.** `authorize()` aborta con la guardia (código 3) ante cualquier identificador objetivo,
  salvo que se den a la vez `--run-confirmatory`, un `--d43-commit` con forma de hash que exista en
  git (`git cat-file -e`, solo lectura) y `D41_CONFIRMATORY_UNLOCK=user-approved`. Un test comprueba
  que `main()` aborta antes de cargar ningún dato.

## Incidencias para la torre (no arregladas)

1. D-41 («Modelo nulo») escribe el término de compositor como `p_KN[obras de Cherubini sin la obra
   B]`. D-39 y `Models.p_hier` usan el compositor de B (Beethoven, B = op. 67). `confirmatory_n8.py`
   sigue a `p_hier`. Solo afecta al ranking por E, que es informativo.
2. Op. 67 no está en las tablas (`is_target`). En el confirmatorio se usa `wB = -1`, así que el
   término de compositor usa todas las obras de Beethoven del estrato.

Respuesta de la torre: (1) se sigue el código congelado, y la discrepancia se registra como
aclaración en D-43. (2) Cherubini no tiene obras en las tablas de fondo, así que noBeethoven
coincide con el fondo del caso objetivo; está anotado en las caveats.

## Ejecución (2026-11-10)

- Especificación: commit `a240875ef21dc0a7982c4c456f4cc71d5db37918` (= HEAD; ambos anotados en el
  JSON, `spec_commit` y `head_commit`). Diferencia del script respecto a ese commit: solo metadatos
  de salida (campos `spec_commit`/`head_commit`/`beethoven_root` y el texto de una caveat). No cambia
  ningún cálculo.
- Comando: `BEETHOVEN_ROOT=M /usr/bin/time -l M/.venv/bin/python scripts/literal_sensitivity_n8.py
  --out-dir results --spec-commit a240875…`, con un vigilante que mataba el proceso por encima de 8 GB.
- **Coste:** 14,2 s de reloj. Pico de RAM: 1,59 GB (`maximum resident set size` 1 593 589 760 B;
  `peak memory footprint` 1,63 GB). Carga de Models 2,7 s, LS-1 4,0 s, LS-2 1,4 s.
- Extracción de Le Cène: 12 movimientos, todos `ok`, a `W/corpus/cache`. Nada escrito en M.
- **Humo P07:** 20 de 20 filas coinciden en DF, E y ventanas_B (rel 1e-9) con
  `results/thresholds_n8_windows.csv`.
- `vivaldi_check`: `comp_works_vivaldi` = 0, `excl_default` = 0, `p_comp_is_None` = true;
  306 obras en el estrato; noBeethoven excluye 59.

## Resultados (`results/literal_sensitivity_n8.json`; instancias en `.csv`)

LS-1, variante por defecto. Instancias = tipos de 8 notas de Le Cène presentes en Dawson.
Umbrales: t_DF = 1,82e-4, t_E = 4,09e-4.

| par | instancias | pasa DF | sens. DF | pasa E | combinada | DF y ritmo no uniforme |
|---|---|---|---|---|---|---|
| rv230 | 1300 | 663 | 0,510 | 745 | 663 | 467 |
| rv265 | 1094 | 647 | 0,591 | 708 | 647 | 332 |
| rv519 | 823 | 386 | 0,469 | 423 | 386 | 128 |
| rv567 | 630 | 325 | 0,516 | 380 | 325 | 241 |
| **global** | **3847** | **2021** | **0,525 [0,510, 0,541]** | **2256 (0,586 [0,571, 0,602])** | **2021 (0,525)** | **1168** |

Variante noBeethoven, global: DF 0,543 [0,527, 0,558], E 0,597 [0,581, 0,612], combinada 0,543;
1173 pasan DF con ritmo no uniforme. En los dos casos, todo tipo que pasa DF pasa también E.

LS-2, variante por defecto. Potencia = fracción de los 800 fragmentos (4 pares × 200) con
p ≤ 0,025. Piscina: 72 obras, 140 368 ventanas.

| longitud | potencia global [Wilson 95 %] | rango por par | recuento medio obs. / nulo |
|---|---|---|---|
| 10 compases | 0,978 [0,965, 0,986] | 0,935–1,0 | 18,6–40,5 / 0,02–0,15 |
| 15 compases | 0,996 [0,989, 0,999] | 0,985–1,0 | 24,8–57,8 / 0,05–0,22 |
| 20 compases | 1,000 [0,995, 1,0] | 1,0 | 31,7–77,0 / 0,05–0,26 |

noBeethoven: 0,979, 1,000 y 1,000.

**Lectura (con la caveat principal).** En cita literal, la mitad de los tipos compartidos tiene
DF ≤ t_DF, frente a ≈ 1 % en modelado (D-41) y a un FPR del 5 % en negativos de cuarteto. Parte de
ese 52 % se debe con seguridad al cambio de dominio: el idioma barroco no aparece en el estrato
1750-1830, así que DF lo trata como raro. El nulo de LS-2, con fragmentos de Corelli y Handel
frente al mismo B (Dawson), controla ese efecto dentro del dominio: los recuentos nulos son casi
cero y la potencia, ≈ 98–100 %. Sigue siendo una cota superior para fragmentos de 10–20 compases
con cita literal.
