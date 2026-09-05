# Brief — Fase 1 sobre corpus real (2026-09-05)

## Contexto del proyecto
Paper de musicología computacional. Tratamos las partituras como lenguaje y queremos un marco
estadísticamente calibrado para decidir si una coincidencia motívica entre obras de distintos
compositores excede la tasa base esperada, más una herramienta de recuperación de variantes
inexactas de un motivo con matriz de sustitución aprendida (análogo a BLAST/BLOSUM). Caso de
estudio insignia: el motivo inicial de la Quinta de Beethoven (intervalos `0,0,−4`, ritmo
corta-corta-corta-larga) y la hipótesis de que deriva de Cherubini (Hymne au Panthéon, 1794;
coda de la obertura de Eliza).

Piloto de Fase 1 sobre el corpus interno de music21 (601 obras, 302k ventanas). Referencia:

* Definiciones anidadas del motivo (ventana de 4 notas): D1 alturas exactas `(0,0,−4)`;
  D2 alturas generalizadas `(0,0,−3|−4)`; D3 solo ritmo (tres duraciones iguales + una ≥2×);
  D4 = D2∧D3; D5 = D4 + ataque en posición métrica débil.
* Prevalencia por obra: D2 31,4 %, D3 99,5 %, D4 3,8 %, D5 3,0 %.
* Nulo (barajado independiente de intervalos y duraciones intra-voz, 100 permutaciones):
  D4 observado 49 vs esperado 51,5, ratio 0,95, p = 0,69.
* Tasa base D4 por colección (por 100k ventanas): Monteverdi 52, Haydn 74 (n=9), Schumann 21,
  Beethoven 8,7, Bach 7,9, Mozart 6,0, O'Neill's 7,2. Varía un orden de magnitud → estratificar.
* Curva de unicidad `P_cross(n)`. Solo intervalos: n=4 → 0,98; n=8 → 0,49; n=12 → 0,21.
  Intervalos+ritmo: n=4 → 0,87; n=6 → 0,46; n=8 → 0,26; suelo ~0,17. Codo en n=6–7 con ritmo.

Scripts del piloto: `scripts/pilot/` (`base_rate2.py`, `uniqueness.py`) con sus JSON.

## Objetivo de la sesión
Construir el corpus clásico real, con metadatos cronológicos fiables, y repetir la Fase 1 sobre
él, estratificada por colección y periodo. NO hacer todavía ninguna comparación
Cherubini–Quinta ni buscar el motivo en obras concretas: eso va después del preregistro en OSF.

## Tareas
1. Estructura del repo (`corpus/raw`, `corpus/cache`, `corpus/works.csv`, `scripts/`,
   `results/`, `docs/`); piloto a `scripts/pilot/`; decisiones a `docs/DECISIONES.md`.
2. Descarga de corpus con licencia y commit/fecha en `docs/CORPUS.md`: OpenScore String
   Quartets, OpenScore Lieder, S3 symphony dataset, DCML (ABC, Mozart, otros clásicos),
   KernScores (craigsapp: Beethoven, Mozart, Haydn, Clementi, Scarlatti…; usar `!!!CDT`/`!!!COM`),
   Quinta de Beethoven op. 67 movs. I y IV (PDMX, MuseScore, KernScores; si no, bloqueante),
   Cherubini (README + plantilla MusicXML, sin transcribir), BPS-Motif (ISMIR 2023).
3. Catálogo maestro `corpus/works.csv`: `work_id, collection, composer, title, movement,
   composition_year, year_source, year_certainty, format, path, license`.
   `year_source` ∈ {`kern_CDT`, `openscore_metadata`, `dcml_metadata`, `manual`, `missing`};
   `year_certainty` ∈ {`exact`, `approx`, `range`, `unknown`}. Fechas de publicación marcadas
   explícitamente. `results/missing_dates.md`.
4. `scripts/extract.py` → `corpus/cache/<work_id>.npz` con `midi, quarter_length, offset,
   voice_id`. Todas las voces; acordes → nota superior + flag `from_chord`; fusionar ligaduras;
   silencios cortan (`--rest-break`, defecto 0); streaming; `results/extract_log.csv`.
   Los análisis leen solo de la caché.
5. `scripts/base_rate.py` y `scripts/uniqueness.py` sobre la caché, estratificados por
   `collection`, `period` (`<1750`, `1750–1800`, `1800–1830`, `1830–1900`, `>1900`, `unknown`)
   y `composer` (≥5 obras). Salidas: `results/base_rate.json`, `results/uniqueness.json`,
   `results/summary.md`, tres figuras en `results/fig/`, semilla fija, `results/env.txt`.
   Mismas D1–D5, mismo `rclass`, mismo nulo que el piloto.
6. Informe de una página en `results/summary.md`: tamaño por estrato, D1–D5 por periodo,
   comparación con el piloto, obras sin fecha, anomalías; señalar si D4 en `1750–1830` difiere
   del piloto.

## Restricciones
Python 3.12, music21 ≥ 10, `requirements.txt`. No modificar D1–D5 ni el nulo sin documentarlo.
Ninguna búsqueda del motivo en obras concretas ni comparación Cherubini–Beethoven. Cada decisión
no trivial a `docs/DECISIONES.md` con fecha. Paralelizar la extracción con `multiprocessing` si
tarda > 20 min.
