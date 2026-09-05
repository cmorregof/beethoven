# Corpus — fuentes, licencias y estado de descarga

Sesión: 2026-09-05. Todo está en `corpus/raw/` (ignorado por git; se regenera con
`bash scripts/download_corpus.sh`). Clones superficiales (`--depth 1`); la columna *commit*
es el HEAD clonado y *fecha* la de ese commit. Los tamaños son de disco tras el clon.

Total en disco: ~11 GB (tras clonar todo el workspace MuseData). Ficheros de partitura utilizables: ~4.400 (ver inventario).

## 1. Resumen por colección

| Colección (`collection`) | Fuente | Formato que usaremos | Obras/movs. | Fechas de composición | Licencia | Estado |
|---|---|---|---|---|---|---|
| `openscore_quartets` | [OpenScore/StringQuartets](https://github.com/OpenScore/StringQuartets) `4e3240e` (2026-09-04) | `.mxl` (MusicXML comprimido, exportado de MuseScore) | 158 movimientos con `.mxl` de 197 listados en `data/scores.tsv` (39 carpetas solo tienen README: aún no transcritas) | **No** por obra; solo nacimiento/muerte del compositor (`data/composers.tsv`) | CC0-1.0 | OK |
| `openscore_lieder` | [OpenScore/Lieder](https://github.com/OpenScore/Lieder) `6b2dc54` (2026-04-07) | `.mxl` | 1.462 canciones | **No** por obra; solo fechas del compositor | CC0-1.0 | OK |
| `s3_symphonies` | [iis-mctl/mctl-symphony-dataset](https://github.com/iis-mctl/mctl-symphony-dataset) `f845a46` (2024-11-16) | `sheet.xml` (MusicXML) + `annotations/*.csv` | 16 movimientos: Mozart 41, Beethoven 9, Chaikovski 6, Dvořák 9 (4 sinfonías completas) | No en el dataset; son obras canónicas de fecha conocida → `manual` | MIT | OK. **Ojo:** es mucho más pequeño de lo que sugería el brief (4 sinfonías, no un corpus orquestal amplio) |
| `dcml_abc` | [DCMLab/ABC](https://github.com/DCMLab/ABC) `b6b7d38` (2025-04-27) | `notes.tsv` + `metadata.tsv` | 70 movimientos (16 cuartetos de Beethoven, op. 18–135) | Sí: `composed_start`/`composed_end` en `metadata.tsv` | CC BY-NC-SA 4.0 | OK |
| `dcml_mozart_sonatas` | [DCMLab/mozart_piano_sonatas](https://github.com/DCMLab/mozart_piano_sonatas) `5337257` (2025-04-27) | `notes.tsv` + `metadata.tsv` | 54 movimientos (18 sonatas) | Sí (`composed_end`) | CC BY-NC-SA 4.0 | OK |
| `dcml/<sub>` (38 subcorpus) | [DCMLab](https://github.com/DCMLab) — lista en §2 | `notes.tsv` + `metadata.tsv` | 1.316 piezas/movimientos | Sí, 100 % (`composed_start`/`end`; algunos abiertos `..-1720`) | CC BY-NC-SA 4.0 (LICENSE en 11 repos; el resto lo declara en README con badge) | OK |
| `kern/<repo>` (19 repos) | KernScores en GitHub: [craigsapp](https://github.com/craigsapp), [musedata](https://github.com/musedata), [humdrum-tools](https://github.com/humdrum-tools) — lista en §3 | `.krn` (Humdrum) | 1.760 ficheros | Parcial: `!!!ODT` en 7 de 19 repos; `!!!CDT` **no sirve** (son fechas del compositor, ver `DECISIONES.md` D-05) | Variada (CC BY-SA / CC BY-NC-SA / sin fichero LICENSE; ver §3) | OK. `kern.humdrum.org` daba 503 durante toda la sesión; todo vía GitHub |
| `musedata_beethoven` | MuseData Stage 2, CCARH: [bitbucket.org/musedata/beethoven](https://bitbucket.org/musedata/beethoven) `76a94a6` (2022-10-23), 1,3 GB | `.md2` (MuseData); music21 lo parsea (`format='musedata'`) | **9 sinfonías completas** (44 ficheros de movimiento; la 9.ª tiene el IV en 8 secciones), conciertos op. 19 y op. 61, 14 cuartetos (op. 18/1–6, 59/1–2, 127, 130–133, 135) — solo `editions/public/score/*.md2` | No en fichero; obras canónicas → `manual` | CCARH (uso académico; ver §4) | OK. **Incluye la Quinta, op. 67 (movs. I–IV)** |
| `musedata_mozart` | Bitbucket `musedata/mozart` (2023-05-20) | `.md2` (57 partituras públicas) y `stage2/` | 15 sinfonías NMA (K. 16–76, 550) + 3 BH (K. 385, 504, 543), concierto K. 467, cuartetos/quintetos/tríos/divertimenti en `stage2` (63 obras, 227 unidades) | `manual` / periodo activo (1771–1790 → `1750–1800`) | CCARH | OK |
| `musedata_bach` | Bitbucket `musedata/bach` (2022-10-20) | `stage2/` (y `stage1/` donde no hay stage2) | 439 obras, 1.408 movimientos: cantatas BG, WTC, inventions, suites, órgano… | periodo activo (1700–1749 → `<1750`) | CCARH | OK; 6 movimientos no parsean |
| `musedata_handel` | Bitbucket `musedata/handel` (2023-10-27) | `stage2/` | 85 obras, 1.249 números (óperas, oratorios, op. 3/6, teclado) | **sin fecha** (Handel 1700–1758 cruza 1750) → `manual_dates.csv` | CCARH | OK; 5 no parsean |
| `musedata_vivaldi` | Bitbucket `musedata/vivaldi` (2025-12-16) | `stage2/` | 161 obras, 453 movimientos (op. 3–9, RV varios) | periodo activo → `<1750` | CCARH | OK; 4 no parsean |
| `musedata_corelli` | Bitbucket `musedata/corelli` (2024-05-03) | `stage2/` | 72 obras (op. 1–6), 305 movimientos | periodo activo → `<1750` | CCARH | OK; duplica `dcml/corelli` y `kern/humdrum-corelli` (no primaria) |
| `musedata_telemann` | Bitbucket `musedata/telemann` (2020-12-19) | `stage2/` y `stage1/` | 109 obras, 560 movimientos | **sin fecha** (1696–1766 cruza 1750) → `manual_dates.csv` | CCARH | OK |
| `bps_motif` | [Wiilly07/Beethoven_motif](https://github.com/Wiilly07/Beethoven_motif) `bd40b77` (2023-04-17) | `csv_notes/*.csv` (eventos con etiqueta de motivo), `csv_label/`, `motif_midi/` | 32 primeros movimientos de las sonatas de Beethoven; 263 motivos, 4.944 ocurrencias | n/a (Fase 2) | Sin LICENSE en el repo; el paper en Zenodo ([10.5281/zenodo.10265277](https://zenodo.org/records/10265277)) es CC BY 4.0 → pedir confirmación a los autores antes de redistribuir | OK |
| `cherubini` | — | MusicXML manual | 0 (pendiente) | 1794 → `manual` | transcripción propia | **Pendiente de transcripción manual**: `corpus/raw/cherubini/README.md` + `template_minimal.musicxml` |

## 2. Subcorpus DCML clonados (`corpus/raw/dcml/`)

Todos con `notes.tsv` (una tabla por pieza: `mc, mn, quarterbeats, duration_qb, staff, voice, tied, midi, chord_id…`), `measures.tsv` y `metadata.tsv` con `composed_start/composed_end`. Commit `2025-04-27` salvo `corelli` (`65608a1`, 2025-11-18).

| Periodo previsto | Subcorpus (n piezas) |
|---|---|
| `<1750` | monteverdi_madrigals (19), peri_euridice (6), sweelinck_keyboard (1), frescobaldi_fiori_musicali (47), corelli (149), couperin_concerts (91), bach_solo (68), bach_en_fr_suites (89), handel_keyboard (6), pergolesi_stabat_mater (12), scarlatti_sonatas (69) |
| `1750–1800` | cpe_bach_keyboard (66), wf_bach_sonatas (9), jc_bach_sonatas (29), kozeluh_sonatas (49), pleyel_quartets (6) |
| `1800–1830` | beethoven_piano_sonatas (91), schubert_winterreise (48), mendelssohn_quartets (24, 1829–47: a caballo) |
| `1830–1900` | chopin_mazurkas (56), schumann_kinderszenen (13), schumann_liederkreis (12), c_schumann_lieder (12), liszt_pelerinage (19), wagner_overtures (2), grieg_lyric_pieces (66), tchaikovsky_seasons (12), dvorak_silhouettes (12), debussy_suite_bergamasque (4) |
| `>1900` | mahler_kindertotenlieder (5), debussy_preludes (24), ravel_piano (5), medtner_tales (19), bartok_bagatelles (14), poulenc_mouvements_perpetuels (3), rachmaninoff_piano (22), schulhoff_suite_dansante_en_jazz (6) |

Descartado: `debussy_piano` (repo legacy sin tablas; sustituido por `debussy_preludes` y `debussy_suite_bergamasque`).
No clonados aún (existen en DCMLab, por si hacen falta): `bach_chorales`, `couperin_clavecin`, `haydn`? (no existe), `debussy_*` restantes, `romantic_piano_corpus`, `distant_listening_corpus` (metacorpus, duplicaría todo lo anterior).

## 3. KernScores clonados (`corpus/raw/kern/`)

| Repo | Commit (fecha) | `.krn` | `!!!ODT` (fecha comp.) | LICENSE | Notas |
|---|---|---|---|---|---|
| craigsapp/beethoven-piano-sonatas | `2d6627b` (2025-02-28) | 103 | sí (rangos) | no | Durand 1915 (Dukas). Duplica `dcml/beethoven_piano_sonatas` |
| craigsapp/beethoven-string-quartets | `1b0a3d9` (2014-06-04) | 71 | sí | no | Duplica `dcml_abc` y parte de OpenScore |
| craigsapp/haydn-piano-sonatas | `299abc8` (2024-08-19) | 25 | sí | sí | Universal Edition 1901 |
| craigsapp/mozart-piano-sonatas | `0f1f49d` (2025-07-18) | 69 | sí | sí | AMA. Duplica `dcml_mozart_sonatas` |
| craigsapp/scarlatti-keyboard-sonatas | `567731b` (2026-02-03) | 65 | **no** (solo `PDT` 1906–13, publicación de Longo) | sí | Solapa parcialmente con `dcml/scarlatti_sonatas` |
| craigsapp/chopin-mazurkas | `fc3a8fb` (2024-01-20) | 52 | no | no | Duplica `dcml/chopin_mazurkas` |
| craigsapp/chopin-preludes | `f8fb01f` (2014-06-03) | 24 | sí | no | |
| craigsapp/bach-370-chorales | `0fd9e00` (2026-01-20) | 370 | no | sí | Mismo material que `bach` del corpus music21 del piloto |
| craigsapp/art-of-the-fugue | `c970eb9` (2025-02-04) | 20 | no | no | |
| craigsapp/bach-musical-offering | `2487a50` (2024-04-02) | 6 | no | no | |
| humdrum-tools/bach-wtc | `0b4f4d8` (2023-12-10) | 96 | no | no | |
| craigsapp/vivaldi-op6 | `084329b` (2024-10-03) | 18 | no | no | |
| craigsapp/scriabin | `7daa113` (2023-05-18) | 207 | sí | no | Estrato `>1900` |
| craigsapp/joplin | `ad0840e` (2024-08-15) | 47 | sí | sí | Estrato `>1900`; ragtime (no clásico: decidir si entra) |
| musedata/humdrum-haydn-quartets | `3047e99` (2014-06-04) | 210 | no | no | Resuelve el n=9 de Haydn del piloto |
| musedata/humdrum-mozart-quartets | `a56fda4` (2024-08-17) | 82 | no | no | |
| musedata/humdrum-haydn-symphonies | `fa453a2` (2024-02-29) | 24 | sí | sí | Sinfonías 99–104: estrato orquestal `1750–1800` |
| musedata/humdrum-bach-brandenburg | `ec7aa22` (2014-06-04) | 21 | sí | sí | |
| musedata/humdrum-corelli | `5931c5d` (2024-08-19) | 250 | no | sí | Duplica `dcml/corelli` |

No encontrado: Clementi (ningún repo Humdrum/MusicXML en GitHub). Existen además en la
org `musedata`: `beethoven-quartets` (MuseData), `vivaldi`, `corelli` (MuseData) — no clonados.

## 4. Quinta de Beethoven, op. 67

**Resuelto.** El índice de MuseData (hoja de cálculo enlazada desde musedata.org) lista
las nueve sinfonías de Beethoven en MuseData *Stage 2*, edición Breitkopf & Härtel
(Serie 1, n.º 5), codificada por E. Correia (1993, rev. 2005/2008), CCARH. El repo Bitbucket
`musedata/beethoven` se ha clonado entero (`corpus/raw/musedata_beethoven`, commit `76a94a6`,
2022-10-23). La Quinta está en `bhl/orch/sym5/editions/public/score/mvt{1,2,3,4}.md2`
(MD5: `ef0fa0c2…`, `8dd3c580…`, `825e070c…`, `ee2bbe0b…`), y con ella las otras ocho sinfonías,
que pasan a formar el estrato orquestal `1800–1830`.

Verificación con music21 10.5 (`converter.parse(p, format='musedata')`), mov. I:
13 partes, 502 compases, Violín I comienza `R G4 G4 G4 E♭4 | R F4 F4 F4 D4 D4 R`
(corchea de silencio entre los dos grupos, como anticipaba el brief para `--rest-break`).

Pendiente para la extracción (tarea 4): (a) comprobar si music21 devuelve los
clarinetes en B♭ y trompas en E♭ en altura escrita o real (`atSoundingPitch`);
(b) hay una parte con nombre corrupto («First Movement», probablemente timbales) y una
parte «Violoncello e Contrabasso» que duplica el contrabajo: decidir si se excluye
la duplicada; (c) la Quinta debe marcarse en `works.csv` como obra objetivo
(`is_target = 1`) para poder excluirla de las tasas base cuando toque.

Alternativas evaluadas y descartadas: PDMX en Hugging Face (`pnlong/PDMX`) está *gated*
(HTTP 401 sin login); `kern.humdrum.org` en 503 toda la sesión; GitHub no tiene ninguna
edición orquestal completa en MusicXML/kern; MuseScore.com exige cuenta para descargar.

Licencia: CCARH publica MuseData para uso académico ("free for research and educational
use"); confirmar en <https://musedata.org/about> antes de redistribuir derivados.


## 5. Disponible y NO descargado (recomendaciones)

* (Hecho el 2026-09-05, a petición del usuario: todo el workspace Bitbucket `musedata`, ver §1.)
* PDMX (HF, gated): requiere login del usuario; útil solo si queremos un estrato
  MuseScore masivo, que trae OMR y arreglos → probablemente no.

## 6. Anomalías detectadas

* OpenScore Quartets: 39 carpetas de `scores/` sin partitura (solo README), entre ellas
  Beethoven op. 135, Haydn op. 76/3, Mozart K. 499. `data/scores.tsv` las lista igual.
* OpenScore no trae fecha de composición → estrato `unknown` salvo relleno manual.
* S3 contiene solo 4 sinfonías (16 movimientos), no un corpus orquestal amplio.
* DCML: cada pieza aparece dos veces como `.mscx` (`MS3/` y `reviewed/`); las tablas
  `notes.tsv` son únicas. No se usan los `.mscx`.
* Duplicados entre colecciones (kern vs DCML vs OpenScore): ver `DECISIONES.md` D-09.
* `bps_motif` sin fichero de licencia.
