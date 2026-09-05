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
