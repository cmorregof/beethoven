# Decisiones metodológicas

Registro cronológico. Cada entrada: fecha, decisión, motivo, efecto sobre la comparabilidad con el piloto.

## 2026-09-05 — Sesión de infraestructura (tareas 1–2)

### D-01 Ubicación de los scripts del piloto
El brief situaba el piloto en `fase1/`, pero en el repo los ficheros estaban en la raíz
(`base_rate2.py`, `uniqueness.py`, `br_*.json`, `uniq_art.json`, `resultados_*.txt`).
Se han movido tal cual a `scripts/pilot/` sin modificar una sola línea, para que sigan
siendo la referencia exacta de los números del piloto.

### D-02 Repositorio git
La carpeta del proyecto estaba dentro de un repo git cuya raíz era el `$HOME` del usuario
(remoto `neural_ode`), sin que los ficheros del proyecto estuviesen trackeados. Se ha
inicializado un repo propio en `Personal/Beethoven` con remoto
`https://github.com/cmorregof/beethoven` (repo nuevo, vacío, indicado por el usuario).
`corpus/raw/`, `corpus/cache/` y `.venv/` van en `.gitignore`: se regeneran con
`scripts/download_corpus.sh` y `scripts/extract.py`. Los commits exactos de cada clon
quedan en `docs/CORPUS.md`.

### D-03 Entorno
Python 3.12.13 en `.venv` (uv), music21 10.5.0. Versiones en `results/env.txt`.
La instalación de sistema (miniforge, Python 3.13) no se toca.

### D-04 Clones superficiales
Todos los repos se clonan con `--depth 1`. Se registra commit y fecha del commit en
`docs/CORPUS.md`; con eso la descarga es reproducible (`git fetch --depth 1 origin <sha>`).

### D-05 Fecha de composición en ficheros kern: `!!!ODT`, no `!!!CDT`
El brief indicaba usar `!!!CDT`. En los ficheros reales `!!!CDT` son las fechas de
**nacimiento y muerte del compositor** (p. ej. `1770///-1827///`), no la fecha de
composición. La fecha de composición está en `!!!ODT` (original date) y a veces en
`!!!MPD`; `!!!PDT` es fecha de publicación. Regla para el catálogo (tarea 3):
1. `ODT` → `year_source = kern_ODT`; 2. si no hay `ODT` pero hay `MPD` → `kern_MPD`;
3. si solo hay `PDT` → se usa con `year_source = kern_PDT_publication` y
`year_certainty = approx` (fecha de publicación, marcada explícitamente);
4. si no hay nada → `missing` y va a `results/missing_dates.md`.
Rangos (`1798///-1800///`) → `composition_year` = año final, `year_certainty = range`,
y se guardan inicio y fin en columnas auxiliares.

### D-06 Metadatos de fecha en OpenScore
OpenScore (cuartetos y Lieder) no trae fecha de composición por obra: solo
`workNumber`, `composer` y fechas de nacimiento/muerte del compositor
(`data/composers.tsv`). Se dejará `year_source = missing` salvo que el usuario complete
`corpus/manual_dates.csv`. No se infieren fechas desde el número de opus automáticamente.

### D-07 DCML: se usa `notes.tsv`, no el parseo `.mscx` con music21
Todos los subcorpus DCML clonados traen `notes.tsv` (columnas `midi`, `duration_qb`,
`quarterbeats`, `staff`, `voice`, `tied`, `chord_id`) y `metadata.tsv` con
`composed_start`/`composed_end` completos (100 % de las piezas en los 38 subcorpus
clonados, con la excepción de fechas abiertas tipo `..-1720`). music21 no parsea
`.mscx` de MuseScore 3 de forma nativa (necesitaría MuseScore instalado para convertir, y
no lo está). Decisión: la vía TSV es la fiable; `extract.py` tendrá un lector específico
que reconstruya voces por `staff`+`voice` y fusione ligaduras con la columna `tied`.
Nota: los `.mscx` aparecen duplicados (`MS3/` y `reviewed/`); no se usan.

### D-08 Selección de subcorpus DCML
Además de ABC y sonatas de Mozart (pedidos), se han clonado 38 subcorpus DCML con
`notes.tsv` para poblar los estratos `<1750`, `1830–1900` y `>1900`, que de otro modo
quedarían muy pobres. Se ha excluido `debussy_piano` (repo legacy sin tablas) y se han
tomado en su lugar `debussy_preludes` y `debussy_suite_bergamasque`.
Consecuencia: hay obras duplicadas entre colecciones (ver D-09).

### D-09 Duplicados entre colecciones (pendiente de resolver en tarea 3)
Mismas obras en dos fuentes: sonatas de Beethoven (kern craigsapp vs DCML), mazurcas de
Chopin (kern vs DCML), sonatas de Scarlatti (kern Longo vs DCML, subconjunto), cuartetos
de Beethoven (kern craigsapp vs DCML ABC vs OpenScore, parcial), cuartetos de Haydn y
Mozart (kern musedata vs OpenScore, parcial), Corelli (kern musedata vs DCML), Bach
(chorales/WTC kern vs music21 corpus del piloto). El catálogo llevará una columna
`duplicate_group` y los análisis por defecto conservarán **una** copia por obra
(prioridad: DCML notes.tsv > kern > OpenScore, por fiabilidad de metadatos y ausencia de
OMR). Se documentará la elección en `results/summary.md`.

### D-10 Quinta de Beethoven: resuelto vía MuseData (CCARH)
GitHub, PDMX (gated) y kern.humdrum.org (503) no la tenían. El índice de musedata.org
(hoja de cálculo) apunta a `bitbucket.org/musedata/beethoven`, MuseData Stage 2 de la
edición Breitkopf & Härtel. Se clona el repo completo (nueve sinfonías, dos conciertos,
14 cuartetos) y no solo op. 67, porque es la única fuente orquestal del estrato
`1800–1830` y el coste es un clon de 1,3 GB. Se usan únicamente los ficheros
`editions/public/score/*.md2` (partitura completa); se ignoran partes sueltas y
`private/`. Pendiente en tarea 4: verificar transposición de clarinetes/trompas al
parsear con music21, y decidir sobre la parte duplicada «Violoncello e Contrabasso».
La Quinta llevará `is_target = 1` en `works.csv` para poder excluirla de las tasas base.
No se usará ningún MIDI de procedencia desconocida.

### D-11 Cherubini
Sin fuente simbólica. `corpus/raw/cherubini/README.md` + plantilla MusicXML mínima
(validada con music21). Transcripción manual a cargo del equipo.

### D-12 Licencias no comerciales
Los subcorpus DCML son CC BY-NC-SA 4.0. Es compatible con uso académico pero obliga a
(a) citar cada subcorpus y (b) no redistribuir derivados con licencia más permisiva. Los
ficheros de caché derivados (`corpus/cache/`) no se suben al repo público.

## 2026-09-05 — Cambios pedidos por el usuario antes de la extracción

### D-13 Voces dobladas: colapso intra-obra
Dentro de cada unidad (obra+movimiento), dos partes se consideran dobladas si sus
secuencias de tokens `(offset, intervalo_siguiente, rclass_siguiente)` coinciden en más del
95 % de la longitud de la más corta (comparación por offset absoluto, transposición-invariante:
colapsa dobles de octava, instrumentos transpositores que doblan y la parte «Violoncello e
Contrabasso» de MuseData). Se conserva la primera parte en orden de partitura y se descartan
las demás del grupo. `results/extract_log.csv` registra `n_parts_raw`, `n_parts_kept` y
`collapse_ratio = 1 − kept/raw` por unidad. Esto **no** estaba en el piloto: en corales SATB
no debería activarse (test de regresión D-18); en orquesta reduce la inflación de recuentos
por dobles. Implementado en `scripts/extract.py`.

### D-14 Instrumentos transpositores: cerrado, sin efecto
music21 devuelve las partes MuseData en altura escrita (clarinete en B♭ de la Quinta:
`A A A F` frente a `G G G E♭` de las cuerdas). Todas las definiciones D1–D5 y la curva de
unicidad usan intervalos intra-voz, invariantes a transposición, y D3/D5 usan solo ritmo y
posición métrica. No se corrige nada. (Las alturas MIDI de la caché para esas partes están
en altura escrita; no se usan en Fase 1.)

### D-15 Unidad de análisis: `work_id` = obra completa, `movement` = subunidad
`works.csv` tiene una fila por fichero/unidad (`unit_id`), pero `work_id` es común a todos los
movimientos de una obra (las ocho secciones del finale de la Novena comparten `work_id`).
La caché se guarda por `work_id` (`corpus/cache/<work_id>.npz`, con array `movement_idx`), y
los análisis cuentan prevalencia, permutaciones y `P_cross` por `work_id`. Diferencia con el
piloto: allí «obra» = fichero de music21 (a menudo un movimiento), así que los porcentajes
de prevalencia por obra no son directamente comparables; las tasas por 100k ventanas sí.
Se añade `composer_id` (slug canónico) y `corpus/composers.csv` con nombre, nacimiento y muerte.

### D-16 MuseData completo
Además de `musedata/beethoven`, se han clonado todos los repos del workspace Bitbucket
`musedata`: `mozart` (15 sinfonías NMA + 3 BH, concierto K. 467, cuartetos/quintetos/…),
`bach` (808 movs. stage2 + 80 cantatas solo stage1), `handel` (974 movs. stage2), `vivaldi`
(566), `corelli` (245), `telemann` (178); `haydn`, `dvorak`, `marcello`, `rovetta` están vacíos.
Regla de selección por obra: `editions/public/score/*.md2` si existe; si no, los directorios
`stage2/<mov>/`; si no, `stage1/<mov>/` (music21 parsea los tres; verificado). Los
ficheros `stage2` con etiqueta «sound» duplicada quedan cubiertos por D-13.
Las sinfonías de Mozart entran en `1750–1800` (por `manual_dates.csv` o, mientras esté
vacío, por la regla D-17: Mozart 1771–1791 cae entero en el bin).

### D-17 Fechas: `manual_dates.csv` y periodo activo del compositor
`corpus/manual_dates.csv` lista, una fila por `work_id`, las obras canónicas sin fecha en su
fuente (cuartetos de Haydn/Mozart/Beethoven en kern y OpenScore, sinfonías y conciertos
MuseData, etc.) para que el equipo rellene `year_start`, `year_end`, `year_certainty`, `source`.
Al reconstruir el catálogo, las filas rellenas entran con `year_source = manual`.
Para las obras sin fecha (Lieder y cualquier otra), `period` se asigna por el periodo activo
del compositor `[nacimiento + 15, muerte − 1]` **solo si cae entero en un bin** (el año de muerte no cuenta: Bach, †1750, queda en `<1750`)
(`year_certainty = range`, `year_source = composer_lifespan`, `composition_year` vacío);
si cruza un bin, `period = unknown`. El +15 es conservador (opus 1 juveniles); ajustable en
`build_catalog.py` (`ACTIVE_START_AGE`).

### D-18 Test de regresión antes de los análisis
`scripts/regression_test.py` extrae `bach-370-chorales` (kern) y el subconjunto `bach` del
corpus interno de music21 (los mismos 433 ficheros del piloto, marcados
`collection = m21_bach`, `in_analysis = 0`), corre el recuento D1–D5 sobre la caché y
compara con el piloto: `bach` D2 = 148,28/100k, D4 = 7,91/100k, tolerancia 2 %. Si falla,
la sesión se detiene antes de `base_rate.py`/`uniqueness.py`.

### D-19 Emulación del aplanado de music21 en el lector de `notes.tsv` (DCML)
El piloto usa `part.flatten().notesAndRests`: una secuencia por pentagrama con las voces
intercaladas por offset (acorde = objeto único → nota superior; notas simultáneas de voces
distintas = eventos consecutivos con el mismo offset). El lector TSV reproduce eso: agrupa
por `staff`, dentro de cada `(quarterbeats, voice)` reduce a la nota más aguda
(`from_chord = 1` si había más de una), ordena por `(offset, voice)`, y sintetiza silencios a
partir de huecos: en la voz 1 cualquier hueco es silencio; en voces 2–4 solo los huecos
dentro de un mismo compás (`mc`), porque MuseScore no escribe silencios para voces ausentes.
Ligaduras: filas con `tied ∈ {0, −1}` y mismo `midi` que la anterior en la misma voz se
funden sumando `duration_qb`. Notas de adorno (`gracenote`) se conservan con duración 0,
como hace music21.

## 2026-09-05 — Decisiones tomadas durante catálogo, extracción y análisis

### D-20 Generador aleatorio del nulo sembrado por obra
El piloto usaba un único `random.Random(20260903)` recorrido en orden de fichero; el
resultado dependía del orden. Ahora cada obra usa `numpy.random.default_rng(20260903 +
crc32(work_id) % 1e6)`: reproducible obra a obra e independiente del orden y del número
de workers. El barajado es el mismo (permutación independiente de intervalos y duraciones
dentro de cada voz, 100 permutaciones, obras con ≥ 150 notas), vectorizado con numpy.

### D-21 La Quinta (obra objetivo) no entra en las tasas base
`base_rate.py` y `uniqueness.py` excluyen `is_target = 1` (op. 67, 4 movimientos) por
defecto (`--include-target` para incluirla). Evita que la obra cuya hipótesis se va a
contrastar contribuya a su propio nulo. Efecto numérico despreciable (4 de ~6.500 unidades).

### D-22 Curva de unicidad con hashes de 64 bits
Con ~10× más ventanas que el piloto, las tablas de tuplas de Python no caben en memoria.
Cada n-grama se codifica con un hash polinómico de 64 bits (numpy) y se cuentan obras
distintas por hash ordenando la tabla. Probabilidad de colisión con ~10⁷ tipos: < 10⁻⁵.
Además de la curva global se calcula `P_cross(n)` dentro de cada periodo.

### D-23 Unidades que no parsean (27 de 6.990)
20 movimientos MuseData con datos corruptos (`cannot process bar data`, enteros
inválidos) en `musedata_bach` (6), `_beethoven` (4: piano2 mvt 1–3 en `stage2s`, sym9 —
ninguno de op. 67), `_handel` (5), `_vivaldi` (4), `_mozart` (1); 7 cuartetos OpenScore
(errores de importación MusicXML de music21: elementos desconocidos, `NoneType.style`).
Quedan registrados en `results/extract_log.csv` con `status = fail`; no se corrigen a mano.
Los 24 ficheros de sinfonías de Haydn fallaban por un registro `!!!commission` que
music21 rechaza: `extract.py` reintenta sin las líneas `!!!` (solo metadatos).

### D-24 Corales de Bach: sin deduplicación por BWV; explicación del piloto
Varios corales del mismo BWV (cantata) compartían clave de catálogo y el primer intento
descartó 68 de 370 como «duplicados». Los corales no se deduplican por BWV (solo pierden
la clave de catálogo). Por otro lado, la colección `bach` del piloto sumaba 433 «obras»
porque incluía 20 ficheros `.rntxt` (análisis armónicos) que music21 parsea como acordes;
la nueva canalización los excluye. Test de regresión: `results/regression_test.md`.

### D-25 OpenScore Lieder: 106 `.mxl` sin fila en `scores.tsv`
Se ignoran (no hay metadatos de compositor). Las 1.356 filas del catálogo se localizan
por el id numérico del fichero, no por la ruta de `scores.tsv` (274 rutas no coincidían).

### D-26 Validación del nulo vectorizado (2026-09-05)
Sobre 25 obras de `musedata_vivaldi`, `openscore_lieder` y `kern/humdrum-haydn-quartets`
se ejecutó el `process()` original del piloto (Python puro, `random.Random`) y
`base_rate.analyse_work` (numpy) sobre las mismas secuencias de la caché: recuentos
observados D1–D5 y número de ventanas idénticos; medias del nulo D4 34,1 vs 33,5, 9,0 vs 8,8
y 20,4 vs 20,5 (desviaciones típicas ~5, ~3, ~5). El ratio obs/nulo > 1 del corpus real no es
un artefacto de la reimplementación.

### D-27 P_cross depende del tamaño del corpus
`P_cross(n)` mide «aparece en otra obra del corpus»: con 2.274 obras frente a 601 sube en
todas las n (IVR n=6: 0,67 vs 0,46; suelo n=12: 0,27 vs 0,17). Para el E-value de Fase 2
habrá que normalizar por número de obras/ventanas del estrato de referencia, no usar la
curva global como constante.

### D-28 Corrección del agrupamiento de ABC y de la clave Deutsch (2026-09-05)
La curva `P_cross` del estrato `1800–1830` tenía un suelo anómalo (0,44 a n=12). Causa: la
rama de `build_catalog.py` para el Annotated Beethoven Corpus comprobaba el nombre `ABC`
pero el directorio es `dcml_abc`, así que cada movimiento quedó como obra suelta sin clave
de catálogo y los 16 cuartetos de kern no se marcaron como duplicados (lo mismo con las
sonatas de Mozart). Corregido: ABC = 16 obras con clave `op18/1 … op135`, kern y OpenScore
no primarias. Además, para Schubert la clave prefiere el número Deutsch (`d911`) al opus,
para que Winterreise (DCML) y Winterreise (OpenScore Lieder) formen un mismo grupo.
Lección: el diagnóstico por pares de obras que comparten 12-gramas es una buena prueba de
duplicados residuales; queda en `results/summary.md` §9.

## 2026-09-05 (tarde) — Ingesta de fechas manuales y segunda ronda de análisis

### D-29 Deduplicación por hash de secuencia y nueva prioridad de ediciones
Además de la clave de catálogo, `build_catalog.py` marca como no primarias las obras cuyo
conjunto de 12-gramas IVR está contenido en otra obra del mismo compositor (tipos
compartidos ≥ 50 y compartidos / min(tipos) ≥ 0,5; se ignoran los tipos presentes en > 40
obras). Se ejecuta sobre la caché, por lo que la cadena es catálogo → extracción → catálogo.
Resuelve las ediciones múltiples de MuseData (Handel op. 6 en `brit`/`chry`/`haa`, Vivaldi
op. 3 y op. 8 en `dawson`/`dover`/`lecene`/`micro`), WTC, corales y Corelli entre kern y
MuseData, y absorbe los corales kern dentro de sus cantatas MuseData. Prioridad para elegir
la copia primaria: **dcml > musedata > kern > s3 > openscore** (antes kern iba delante de
musedata); dentro de una misma colección gana la copia con más notas (edición más
completa) y, a igualdad, la ruta alfabética. Los grupos quedan listados en
`results/seq_duplicates.md`. Riesgo asumido: autopréstamos masivos (Handel) podrían
fundir obras distintas; el umbral de contención 0,5 sobre la obra entera lo hace improbable.

### D-30 Ingesta de `corpus/manual_dates.csv` y regla del punto medio
Se ingieren las 1.960 filas rellenadas por el equipo (`year_start`, `year_end`,
`year_certainty`, `source`, `note`; años aceptados como `1742` o `1742.0`).
Regla de bin: `year_certainty = range` → periodo por el **punto medio**
`round((year_start + year_end)/2)` (`period_source = year_midpoint`); `exact`/`approx` → por
el año (`period_source = year`). Se aplica a todas las fuentes de fecha (manual, kern ODT,
DCML), no solo a las manuales, para que un rango como Bach 1707–1750 caiga en `<1750`.
La regla del periodo activo (D-17) sigue vigente solo para obras sin ninguna fecha.

### D-31 La Quinta ya estaba excluida del 0,34× de las sinfonías de Beethoven
`base_rate.py` carga el catálogo con `exclude_target=True`; `musedata_beethoven` contaba 11
obras (8 sinfonías sin la Quinta, dos conciertos, op. 133). No hace falta recalcular; la
salida ahora lista explícitamente `targets_excluded` en `results/base_rate.json`.

### D-32 Desgloses de D4 por rol de voz y posición cadencial
Rol: en cada movimiento, la voz de mediana MIDI más baja es «bajo» (solo si hay ≥ 2 voces;
instrumentos transpositores en altura escrita, así que el contrabajo escrito una octava
arriba puede no ser el «bajo» en MuseData). Posición cadencial: la nota larga (4.ª de la
ventana) empieza en la última negra de su compás (`bar_remaining ≤ 1`, campo nuevo de la
caché, versión 1.1) o precede a un silencio o al final de la voz. Cuatro clases:
`bass_cad`, `bass_other`, `other_cad`, `other_other`, con tasa por 100k y nulo propio. En el
nulo la clase queda ligada a la posición original de la ventana (las duraciones barajadas
cambian los compases, pero preserva «cuántas ventanas de esa posición son D4 por azar»).

### D-33 `P_pair(n)`: unicidad invariante al tamaño del corpus
`P_pair(n)` = probabilidad de que una ventana de n notas de la obra A aparezca en otra obra
B concreta del mismo estrato, promediada sobre pares ordenados (A, B). Se calcula en cerrado
a partir de la tabla (hash, obra): para A, Σ_h t_A(h)·(|W_h| − 1) / (T_A·(N − 1)). A
diferencia de `P_cross`, no crece con N. Está en `results/uniqueness.json` (`p_pair`).

### D-34 1000 permutaciones para la tabla por estrato
`base_rate.py` corre 1000 permutaciones por obra; las tablas `all` y `period` usan las
1000 (IC95 = percentiles 2,5–97,5; p mínima 0,001); `collection`, `composer` y
`collection_x_period` usan las primeras 100, como el piloto.

### D-35 Cuarteto n.º 1 de Cherubini (OpenScore) marcado `is_target = 1`
`osq-5108725` (set 5108725) queda fuera de las tasas base y de la curva de unicidad, como
la Quinta, por ser material del caso de estudio.

### D-36 Resultado del desglose de D4 (D-32) y lectura de `P_pair` (2026-09-05, tarde)
La hipótesis «el exceso 1,31× está en el bajo cadencial» **no se sostiene**: el bajo aporta el
23 % del exceso (29 + 46 de 318) con un 21 % de las ventanas; las voces superiores en posición
cadencial aportan el 49 % (ratio 1,48) y en posición no cadencial el 27 % (ratio 1,17). El
exceso es transversal a las voces y algo mayor en posición cadencial. Por periodo sí hay
estructura: en `<1750` está en las voces superiores cadenciales (2,22×), en `1800–1830` en el
bajo (3,0×, 68 obras) y en `1750–1800` no hay exceso cadencial (0,99–1,04×). Los pares de
obras con más 12-gramas compartidos en 1750–1830 son sinfonías distintas con contención ≤ 5 %
(figuras de acompañamiento), no duplicados; por eso `P_pair` sube en los estratos
orquestales. Queda pendiente una variante de `P_pair` ponderada por tipos o sin n-gramas de
nota repetida.

## 2026-09-09 — Modelo de fondo por tipo

### D-37 Fondo por tipo de n-grama y regla de exclusión por compositor
Sustituye la idea de un `P_pair` ponderado (D-36, descartada). Para cada estrato (los cinco
bins de periodo y la unión `1750-1830`) y n = 4..12, `scripts/background.py build` guarda la
tabla de frecuencias de n-gramas IVR (intervalos + clase rítmica) de las obras primarias del
estrato, sin obras objetivo, en `results/background/<estrato>_n<n>.parquet`, con una fila por
(hash, `composer_id`, count). Reutiliza los hashes de `uniqueness.py` sobre la caché.
Probabilidad de fondo con suavizado de Laplace:
`p_q = (count_q + 1) / (N + V + 1)`, con N ventanas y V tipos observados del estrato;
tipo no visto: `p_unseen = 1 / (N + V + 1)`.
**Regla de exclusión:** en el confirmatorio, para todo par de obras (A, B) el fondo se estima
**sin los compositores de A ni de B** (`Background.p(hashes, exclude=(cA, cB))`): se restan
las ventanas de los excluidos de N, sus tipos exclusivos de V (aproximación: los tipos
compartidos solo entre los dos excluidos no se descuentan) y sus recuentos de count_q. Así
ni la obra consultada ni la candidata contribuyen a su propio fondo, y un compositor con
muchas obras no se «autocalibra».
E-value de una ventana q contra una obra B: `E = windows_B × p_q`; probabilidad de aparecer
al menos una vez ≈ `1 − exp(−E)`.
Calibración (`scripts/background.py calibrate`): 200 ventanas de 8 notas muestreadas
uniformemente sobre las ventanas de `1750-1830` (semilla 20260903), E predicho frente a
frecuencia empírica en las demás obras del estrato con compositor distinto, leave-both-
composers-out; `results/fig/background_calibration.png`, `results/background_calibration.md`.
Los parquet (217 MB) no se suben al repo; `meta.json` sí.

### D-38 Resultado de la calibración del fondo (2026-09-09)
`results/fig/background_calibration.png`, `results/background_calibration.md`. Tramo medio
(E 3–300) calibrado con sesgo 1,3–1,5× y correlación 0,97; tramo bajo (59 % de las ventanas
muestreadas son tipos que no aparecen en otro compositor) sobrepredicho (E ≈ 1 frente a 0),
conservador; tramo alto (fórmulas de acompañamiento) infrapredicho 1,5–1,6× por la exclusión
del compositor de B, anticonservador. Good–Turing (α = 0,96) no cambia nada porque el 29 % de
las ventanas del estrato son tipos únicos. Decisiones para el preregistro: candidatos con
ritmo no uniforme, E-value de tipos no vistos como cota superior, y evaluar un fondo
jerárquico estrato + compositor si el tramo alto importa. No se ha calculado nada de la
Quinta ni de Cherubini.
