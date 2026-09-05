# Fase 1 sobre el corpus real — resumen

Generado por `scripts/make_summary.py` el 2026-09-05. Semilla 20260903, 1000 permutaciones para `todo` y `period` (100 para el resto), `rest_break = 0.0`, obras objetivo excluidas: osq-5108725, musedata_beethoven-bhl-orch-sym5. Entorno en `results/env.txt`.

## 1. Tamaño del corpus por estrato

Unidades primarias en análisis (fichero/movimiento; entre paréntesis, obras `work_id`).

| colección | <1750 | 1750–1800 | 1800–1830 | 1830–1900 | >1900 | unknown | total |
|---|---|---|---|---|---|---|---|
| dcml | 417 (214) | 164 (59) | 87 (22) | 206 (41) | 79 (17) | · | 953 (353) |
| dcml_abc | · | 16 (4) | 54 (12) | · | · | · | 70 (16) |
| dcml_mozart_sonatas | · | 54 (18) | · | · | · | · | 54 (18) |
| kern | 131 (118) | 254 (82) | 12 (5) | 142 (31) | 197 (143) | · | 736 (379) |
| musedata_bach | 1343 (424) | · | · | · | · | · | 1343 (424) |
| musedata_beethoven | · | 3 (1) | 49 (11) | · | · | · | 52 (12) |
| musedata_corelli | 294 (69) | · | · | · | · | · | 294 (69) |
| musedata_handel | 814 (38) | · | · | · | · | · | 814 (38) |
| musedata_mozart | · | 206 (56) | · | · | · | · | 206 (56) |
| musedata_telemann | 515 (108) | · | · | · | · | 45 (1) | 560 (109) |
| musedata_vivaldi | 232 (57) | · | · | · | · | · | 232 (57) |
| openscore_lieder | · | · | 64 (9) | 334 (64) | 60 (12) | 857 (161) | 1315 (246) |
| openscore_quartets | · | 18 (18) | 12 (12) | 44 (41) | 23 (23) | 1 (1) | 98 (95) |
| s3_symphonies | · | · | · | 8 (2) | · | · | 8 (2) |
| **total** | **3746 (1028)** | **715 (238)** | **278 (71)** | **734 (179)** | **359 (195)** | **903 (163)** | **6735 (1873)** |

Ventanas de 4 notas analizadas: **6,572,757** en 1,859 obras (7,736,142 notas); piloto: 302.414 ventanas en 601 obras. Unidades que no parsean: 30 (`results/extract_log.csv`).

| periodo | obras | ventanas | % ventanas |
|---|---|---|---|
| <1750 | 1,023 | 2,979,128 | 45.3 % |
| 1750–1800 | 237 | 1,121,403 | 17.1 % |
| 1800–1830 | 68 | 744,875 | 11.3 % |
| 1830–1900 | 178 | 863,972 | 13.1 % |
| >1900 | 190 | 375,353 | 5.7 % |
| unknown | 163 | 488,026 | 7.4 % |

## 2. Tasa base anidada D1–D5 por periodo (ocurrencias por 100k ventanas)

| estrato | obras | ventanas | D1 | D2 | D3 | D4 | D5 | obras con D4 |
|---|---|---|---|---|---|---|---|---|
| **todo** | 1,859 | 6,572,757 | 74.92 | 218.69 | 6,235 | 19.75 | 17.76 | 17.8 % |
| <1750 | 1,023 | 2,979,128 | 72.54 | 206.20 | 6,782 | 18.90 | 18.16 | 11.6 % |
| 1750–1800 | 237 | 1,121,403 | 70.80 | 247.81 | 6,490 | 22.74 | 17.83 | 31.6 % |
| 1800–1830 | 68 | 744,875 | 89.01 | 283.13 | 4,614 | 24.17 | 22.69 | 52.9 % |
| 1830–1900 | 178 | 863,972 | 85.88 | 221.19 | 5,706 | 18.75 | 16.55 | 30.3 % |
| >1900 | 190 | 375,353 | 44.76 | 94.31 | 5,941 | 3.46 | 2.93 | 4.2 % |
| unknown | 163 | 488,026 | 81.14 | 220.89 | 5,954 | 25.61 | 21.11 | 23.9 % |
| piloto (music21 art) | 601 | 302,414 | 77.71 | 275.78 | 6367 | 16.53 | 13.56 | 3.8 % |

**Estrato 1750–1830 (unión de los dos bins):** D4 = 435 en 1,866,278 ventanas → **23.31/100k**, frente a **16,53/100k** del piloto (todo el corpus art) y 8,69 (Beethoven), 6,05 (Mozart), 74,1 (Haydn, n=9) por colección en el piloto. La tasa del estrato clásico es **superior** a la global del piloto. Compárese sobre todo con las colecciones del piloto del mismo periodo (Beethoven, Mozart, Haydn).

## 3. Tasa base por colección (≥ 10.000 ventanas)

| colección | obras | ventanas | D1 | D2 | D3 | D4 | D5 | obras con D4 |
|---|---|---|---|---|---|---|---|---|
| musedata_bach | 420 | 1,422,596 | 48.78 | 162.52 | 7,027 | 10.61 | 10.26 | 7.9 % |
| openscore_quartets | 87 | 746,450 | 80.11 | 221.72 | 5,861 | 22.91 | 21.30 | 49.4 % |
| openscore_lieder | 246 | 690,154 | 76.94 | 207.49 | 5,979 | 22.02 | 18.40 | 24.8 % |
| musedata_handel | 38 | 582,302 | 99.26 | 255.02 | 6,682 | 27.48 | 25.93 | 39.5 % |
| musedata_mozart | 56 | 426,376 | 83.03 | 334.92 | 6,559 | 37.29 | 28.85 | 55.4 % |
| musedata_telemann | 109 | 346,120 | 102.85 | 319.83 | 6,972 | 29.18 | 27.45 | 28.4 % |
| musedata_beethoven | 11 | 323,556 | 101.68 | 317.72 | 3,853 | 9.89 | 9.27 | 72.7 % |
| musedata_vivaldi | 56 | 278,236 | 176.11 | 392.11 | 5,887 | 55.71 | 55.35 | 55.4 % |
| kern/humdrum-haydn-quartets | 59 | 247,377 | 80.44 | 251.44 | 7,027 | 19.81 | 14.55 | 40.7 % |
| dcml_abc | 16 | 168,074 | 68.42 | 300.46 | 5,667 | 20.82 | 16.66 | 56.2 % |
| dcml/beethoven_piano_sonatas | 28 | 151,606 | 32.98 | 82.45 | 4,888 | 5.94 | 5.94 | 14.3 % |
| musedata_corelli | 69 | 117,782 | 16.98 | 56.04 | 6,830 | 2.55 | 2.55 | 2.9 % |
| kern/humdrum-haydn-symphonies | 6 | 99,563 | 84.37 | 258.13 | 5,985 | 22.10 | 18.08 | 100.0 % |
| kern/scriabin | 65 | 95,472 | 55.51 | 95.32 | 5,526 | 6.28 | 4.19 | 6.2 % |
| dcml_mozart_sonatas | 18 | 69,297 | 30.30 | 77.93 | 5,924 | 1.44 | 1.44 | 5.6 % |
| s3_symphonies | 2 | 67,014 | 210.40 | 317.84 | 4,695 | 58.20 | 56.70 | 100.0 % |
| dcml/scarlatti_sonatas | 69 | 51,931 | 11.55 | 34.66 | 5,892 | 0.00 | 0.00 | 0.0 % |
| dcml/bach_en_fr_suites | 12 | 50,242 | 11.94 | 43.79 | 6,100 | 0.00 | 0.00 | 0.0 % |
| kern/scarlatti-keyboard-sonatas | 59 | 47,720 | 35.62 | 73.34 | 6,303 | 0.00 | 0.00 | 0.0 % |
| dcml/mendelssohn_quartets | 4 | 42,695 | 67.92 | 210.80 | 6,727 | 11.71 | 11.71 | 100.0 % |
| dcml/cpe_bach_keyboard | 34 | 40,182 | 24.89 | 89.59 | 6,209 | 2.49 | 2.49 | 2.9 % |
| kern/joplin | 47 | 35,241 | 34.05 | 110.67 | 7,077 | 0.00 | 0.00 | 0.0 % |
| dcml/bach_solo | 13 | 33,508 | 0.00 | 5.97 | 3,563 | 0.00 | 0.00 | 0.0 % |
| dcml/grieg_lyric_pieces | 10 | 32,431 | 40.09 | 77.09 | 6,318 | 0.00 | 0.00 | 0.0 % |
| dcml/couperin_concerts | 91 | 32,138 | 18.67 | 74.68 | 6,970 | 0.00 | 0.00 | 0.0 % |
| dcml/chopin_mazurkas | 20 | 29,178 | 85.68 | 157.65 | 3,938 | 10.28 | 0.00 | 15.0 % |
| dcml/jc_bach_sonatas | 2 | 28,047 | 10.70 | 71.31 | 5,348 | 3.57 | 3.57 | 50.0 % |
| dcml/kozeluh_sonatas | 8 | 26,997 | 62.97 | 144.46 | 6,938 | 18.52 | 11.11 | 25.0 % |
| dcml/liszt_pelerinage | 3 | 25,120 | 75.64 | 123.41 | 4,682 | 7.96 | 3.98 | 33.3 % |
| kern/haydn-piano-sonatas | 18 | 24,560 | 12.21 | 48.86 | 5,770 | 4.07 | 4.07 | 5.6 % |
| dcml/medtner_tales | 7 | 23,752 | 42.10 | 71.57 | 5,890 | 0.00 | 0.00 | 0.0 % |
| kern/vivaldi-op6 | 6 | 20,973 | 128.74 | 352.83 | 5,426 | 52.45 | 47.68 | 50.0 % |
| kern/bach-370-chorales | 105 | 19,200 | 26.04 | 104.17 | 6,917 | 0.00 | 0.00 | 0.0 % |
| kern/beethoven-piano-sonatas | 4 | 15,690 | 50.99 | 216.70 | 4,653 | 12.75 | 6.37 | 50.0 % |
| dcml/frescobaldi_fiori_musicali | 1 | 13,789 | 43.51 | 50.77 | 6,621 | 0.00 | 0.00 | 0.0 % |
| dcml/schubert_winterreise | 1 | 13,072 | 160.65 | 550.80 | 5,477 | 0.00 | 0.00 | 0.0 % |
| kern/chopin-preludes | 1 | 12,192 | 57.41 | 155.84 | 4,323 | 82.02 | 82.02 | 100.0 % |
| dcml/monteverdi_madrigals | 15 | 10,888 | 165.32 | 698.02 | 7,017 | 73.48 | 73.48 | 20.0 % |
| dcml/ravel_piano | 2 | 10,652 | 9.39 | 18.78 | 4,947 | 0.00 | 0.00 | 0.0 % |

Piloto (D4/100k): monteverdi 52.04, haydn 74.09, schumann_robert 20.84, beethoven 8.69, bach 7.91, mozart 6.05, oneills1850 7.15.

## 4. Tasa base por compositor (≥ 5 obras, ordenado por ventanas)

| compositor | obras | ventanas | D1 | D2 | D3 | D4 | D5 | obras con D4 |
|---|---|---|---|---|---|---|---|---|
| bach_js | 557 | 1,536,829 | 45.87 | 153.30 | 6,919 | 9.83 | 9.50 | 5.9 % |
| beethoven_l | 61 | 663,500 | 75.96 | 256.52 | 4,579 | 11.76 | 10.25 | 37.7 % |
| handel_gf | 39 | 583,655 | 99.03 | 254.43 | 6,678 | 27.41 | 25.87 | 38.5 % |
| mozart_wa | 74 | 495,673 | 75.65 | 298.99 | 6,470 | 32.28 | 25.02 | 43.2 % |
| haydn_fj | 90 | 402,567 | 75.76 | 235.99 | 6,762 | 18.88 | 14.66 | 37.8 % |
| telemann_gp | 109 | 346,120 | 102.85 | 319.83 | 6,972 | 29.18 | 27.45 | 28.4 % |
| vivaldi_a | 62 | 299,209 | 172.79 | 389.36 | 5,855 | 55.48 | 54.81 | 54.8 % |
| schubert_f | 17 | 129,840 | 130.16 | 354.28 | 5,290 | 75.48 | 74.71 | 58.8 % |
| corelli_a | 72 | 122,555 | 16.32 | 53.85 | 6,865 | 2.45 | 2.45 | 2.8 % |
| dvorak_a | 8 | 103,980 | 143.30 | 323.14 | 5,149 | 21.16 | 18.27 | 50.0 % |
| scarlatti_d | 128 | 99,651 | 23.08 | 53.19 | 6,089 | 0.00 | 0.00 | 0.0 % |
| scriabin_a | 65 | 95,472 | 55.51 | 95.32 | 5,526 | 6.28 | 4.19 | 6.2 % |
| brahms_j | 21 | 84,135 | 68.94 | 199.68 | 6,096 | 1.19 | 1.19 | 4.8 % |
| mendelssohn_f | 14 | 77,097 | 81.72 | 254.23 | 7,013 | 15.56 | 15.56 | 57.1 % |
| schumann_r | 9 | 52,106 | 99.80 | 282.12 | 4,491 | 7.68 | 5.76 | 33.3 % |
| holmes_a | 8 | 43,849 | 29.65 | 66.14 | 6,233 | 4.56 | 4.56 | 12.5 % |
| grieg_e | 11 | 43,139 | 71.86 | 141.40 | 6,148 | 6.95 | 6.95 | 9.1 % |
| chopin_f | 23 | 43,028 | 74.37 | 151.06 | 3,974 | 30.21 | 23.24 | 17.4 % |
| bach_cpe | 34 | 40,182 | 24.89 | 89.59 | 6,209 | 2.49 | 2.49 | 2.9 % |
| mayer_e | 7 | 36,997 | 13.51 | 121.63 | 8,236 | 5.41 | 5.41 | 28.6 % |
| joplin_s | 48 | 35,643 | 33.67 | 109.42 | 7,031 | 0.00 | 0.00 | 0.0 % |
| couperin_f | 91 | 32,138 | 18.67 | 74.68 | 6,970 | 0.00 | 0.00 | 0.0 % |
| debussy_c | 6 | 30,814 | 38.94 | 113.58 | 5,903 | 16.23 | 12.98 | 50.0 % |
| wolf_h | 5 | 30,319 | 56.07 | 171.51 | 5,746 | 46.18 | 46.18 | 60.0 % |
| lang_j | 12 | 27,504 | 79.99 | 203.61 | 6,214 | 43.63 | 39.99 | 50.0 % |

## 5. Observado frente al modelo nulo (D4; barajado intra-voz, obras con ≥ 150 notas)

| estrato | obras perm. | D4 obs | D4 nulo (media) | IC95 | ratio | p | perms |
|---|---|---|---|---|---|---|---|
| **todo** | 1825 | 1,298 | 981.0 | 925–1,043 | 1.32 | 0.001 | 1000 |
| <1750 | 994 | 563 | 371.9 | 337–411 | 1.51 | 0.001 | 1000 |
| 1750–1800 | 235 | 255 | 211.3 | 186–239 | 1.21 | 0.002 | 1000 |
| 1800–1830 | 68 | 180 | 168.9 | 142–194 | 1.07 | 0.195 | 1000 |
| 1830–1900 | 178 | 162 | 123.4 | 103–144 | 1.31 | 0.001 | 1000 |
| >1900 | 188 | 13 | 30.1 | 20–41 | 0.43 | 1.000 | 1000 |
| unknown | 162 | 125 | 75.3 | 59–92 | 1.66 | 0.001 | 1000 |
| musedata_bach | 407 | 151 | 141.2 | 122–162 | 1.07 | 0.208 | 100 |
| openscore_quartets | 87 | 171 | 124.3 | 104–147 | 1.38 | 0.010 | 100 |
| openscore_lieder | 245 | 152 | 93.1 | 76–110 | 1.63 | 0.010 | 100 |
| musedata_handel | 38 | 160 | 94.8 | 79–110 | 1.69 | 0.010 | 100 |
| musedata_mozart | 56 | 159 | 114.7 | 98–132 | 1.39 | 0.010 | 100 |
| musedata_telemann | 109 | 101 | 66.3 | 49–83 | 1.52 | 0.010 | 100 |
| musedata_beethoven | 11 | 32 | 94.5 | 76–113 | 0.34 | 1.000 | 100 |
| musedata_vivaldi | 56 | 155 | 66.1 | 52–81 | 2.34 | 0.010 | 100 |
| kern/humdrum-haydn-quartets | 59 | 49 | 41.9 | 32–57 | 1.17 | 0.158 | 100 |
| dcml_abc | 16 | 35 | 33.2 | 23–45 | 1.05 | 0.406 | 100 |
| dcml/beethoven_piano_sonatas | 28 | 9 | 9.9 | 4–17 | 0.90 | 0.663 | 100 |
| musedata_corelli | 69 | 3 | 4.3 | 1–9 | 0.70 | 0.782 | 100 |
| piloto (art) | 519 | 49 | 51.5 | 36–64 | 0.95 | 0.69 | 100 |

### 5b. D4 por rol de voz y posición cadencial (D-32)

Rol: voz de mediana MIDI más baja de cada movimiento = «bajo». Cadencial: la nota larga empieza en la última negra del compás o precede a silencio/fin de voz. El nulo conserva la clase de cada posición.

| estrato | clase | ventanas | D4 obs | D4/100k | nulo (media) | ratio | p |
|---|---|---|---|---|---|---|---|
| **todo** | bajo, cadencial | 514,891 | 80 | 15.54 | 51.2 | 1.56 | 0.001 |
| **todo** | bajo, otra | 893,959 | 127 | 14.21 | 81.4 | 1.56 | 0.001 |
| **todo** | otras voces, cadencial | 1,922,532 | 477 | 24.81 | 321.4 | 1.48 | 0.001 |
| **todo** | otras voces, otra | 3,241,375 | 614 | 18.94 | 527.0 | 1.17 | 0.001 |
| <1750 | bajo, cadencial | 202,906 | 25 | 12.32 | 14.5 | 1.72 | 0.010 |
| <1750 | bajo, otra | 375,525 | 15 | 3.99 | 23.7 | 0.63 | 0.979 |
| <1750 | otras voces, cadencial | 848,378 | 285 | 33.59 | 128.4 | 2.22 | 0.001 |
| <1750 | otras voces, otra | 1,552,319 | 238 | 15.33 | 205.4 | 1.16 | 0.013 |
| 1750–1800 | bajo, cadencial | 84,940 | 12 | 14.13 | 11.6 | 1.04 | 0.487 |
| 1750–1800 | bajo, otra | 123,021 | 22 | 17.88 | 16.6 | 1.33 | 0.116 |
| 1750–1800 | otras voces, cadencial | 366,664 | 70 | 19.09 | 70.6 | 0.99 | 0.545 |
| 1750–1800 | otras voces, otra | 546,778 | 151 | 27.62 | 112.5 | 1.34 | 0.001 |
| 1800–1830 | bajo, cadencial | 51,967 | 29 | 55.80 | 9.6 | 3.01 | 0.001 |
| 1800–1830 | bajo, otra | 83,384 | 38 | 45.57 | 12.0 | 3.16 | 0.001 |
| 1800–1830 | otras voces, cadencial | 232,622 | 47 | 20.20 | 53.5 | 0.88 | 0.846 |
| 1800–1830 | otras voces, otra | 376,902 | 66 | 17.51 | 93.6 | 0.70 | 1.000 |
| 1830–1900 | bajo, cadencial | 84,160 | 9 | 10.69 | 7.6 | 1.18 | 0.368 |
| 1830–1900 | bajo, otra | 149,671 | 32 | 21.38 | 14.4 | 2.22 | 0.002 |
| 1830–1900 | otras voces, cadencial | 242,679 | 32 | 13.19 | 37.2 | 0.86 | 0.829 |
| 1830–1900 | otras voces, otra | 387,462 | 89 | 22.97 | 64.2 | 1.39 | 0.002 |
| >1900 | bajo, cadencial | 43,735 | 1 | 2.29 | 2.7 | 0.37 | 0.933 |
| >1900 | bajo, otra | 69,086 | 1 | 1.45 | 3.8 | 0.26 | 0.978 |
| >1900 | otras voces, cadencial | 101,094 | 2 | 1.98 | 9.9 | 0.20 | 0.999 |
| >1900 | otras voces, otra | 161,438 | 9 | 5.57 | 13.7 | 0.66 | 0.922 |
| unknown | bajo, cadencial | 47,183 | 4 | 8.48 | 5.1 | 0.78 | 0.752 |
| unknown | bajo, otra | 93,272 | 19 | 20.37 | 10.9 | 1.74 | 0.014 |
| unknown | otras voces, cadencial | 131,095 | 41 | 31.28 | 21.8 | 1.88 | 0.002 |
| unknown | otras voces, otra | 216,476 | 61 | 28.18 | 37.5 | 1.63 | 0.001 |

Reparto del exceso observado − nulo (todo): bajo, cadencial +29 (9 %), bajo, otra +46 (14 %), otras voces, cadencial +156 (49 %), otras voces, otra +87 (27 %). Ventanas por clase: bajo, cadencial 7.8 %, bajo, otra 13.6 %, otras voces, cadencial 29.3 %, otras voces, otra 49.3 %.


D2: obs 14,371 vs nulo 17,729.4 (ratio 0.81, p=1.000); D3: obs 409,603 vs 383,701.5 (ratio 1.07, p=0.001); D4: ratio 1.32, p=0.001. Piloto: D2 0,88×, D3 1,14× (p=0,01), D4 0,95× (p=0,69).

## 6. Ranking del 3-grama de intervalos

3-gramas distintos: 47,959 (piloto 9.512). `(0, 0, -4)`: rango 186, n=4,924 (0.0749 %); `(0, 0, -3)`: rango 97, n=9,450 (0.1438 %). Piloto: (0,0,−4) rango 194, 0,078 %; (0,0,−3) rango 83, 0,198 %.

Top-10: `(0, 0, 0)` 396,965, `(-2, -2, -1)` 105,911, `(-1, -2, -2)` 105,376, `(-2, -1, -2)` 103,168, `(2, 2, 1)` 76,298, `(-2, -1, 1)` 70,673, `(2, 1, 2)` 64,995, `(1, 2, 2)` 58,340, `(-1, 1, 2)` 54,765, `(1, -1, 1)` 47,494.

## 7. Curva de unicidad P_cross(n)

1,859 obras. P_cross(n) = probabilidad de que una ventana de n notas aparezca idéntica en otra obra.

| n | IV tokens | IV tipos | IV P_cross | IV piloto | IV P_pair | IVR tokens | IVR tipos | IVR P_cross | IVR piloto | IVR P_pair |
|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 6,960,552 | 3,929 | 0.9998 |  | 0.76531 | 6,960,552 | 33,911 | 0.9979 |  | 0.48454 |
| 4 | 6,572,757 | 47,959 | 0.9962 | 0.9825 | 0.44930 | 6,572,757 | 364,502 | 0.9566 | 0.8719 | 0.18768 |
| 5 | 6,184,962 | 241,352 | 0.9719 |  | 0.21951 | 6,184,962 | 1,103,229 | 0.8090 |  | 0.07320 |
| 6 | 5,853,830 | 687,359 | 0.8943 | 0.7907 | 0.09984 | 5,853,830 | 1,823,670 | 0.6193 | 0.4646 | 0.03290 |
| 7 | 5,564,267 | 1,268,795 | 0.7584 |  | 0.04578 | 5,564,267 | 2,313,278 | 0.4608 |  | 0.01672 |
| 8 | 5,308,177 | 1,796,533 | 0.6046 | 0.4854 | 0.02273 | 5,308,177 | 2,603,407 | 0.3469 | 0.263 | 0.01003 |
| 9 | 5,079,577 | 2,190,789 | 0.4685 |  | 0.01271 | 5,079,577 | 2,762,516 | 0.2700 |  | 0.00662 |
| 10 | 4,873,692 | 2,455,034 | 0.3599 |  | 0.00831 | 4,873,692 | 2,845,814 | 0.2169 |  | 0.00505 |
| 11 | 4,685,448 | 2,615,298 | 0.2794 |  | 0.00616 | 4,685,448 | 2,881,720 | 0.1791 |  | 0.00409 |
| 12 | 4,511,979 | 2,702,251 | 0.2214 | 0.2066 | 0.00489 | 4,511,979 | 2,889,717 | 0.1508 | 0.1715 | 0.00336 |

`P_pair(n)` (D-33) = probabilidad de que una ventana de A aparezca en una obra B concreta del mismo estrato, promediada sobre pares; no depende del número de obras.

Aviso (D-33): `P_pair` pondera por ventanas, así que en los estratos orquestales (1750–1830) lo dominan n-gramas formularios de acompañamiento (notas repetidas, trémolos, escalas) que aparecen en casi todas las sinfonías; el diagnóstico por pares no encontró duplicados (contención máxima 5 % entre obras distintas). Para el E-value convendrá una versión ponderada por tipos o que excluya los n-gramas de nota repetida.

P_cross(n) y P_pair(n) por periodo (IVR = intervalos + ritmo), dentro de cada periodo:

| periodo | obras | P_cross n=4 | n=6 | n=8 | n=12 | P_pair n=4 | n=6 | n=8 | n=12 |
|---|---|---|---|---|---|---|---|---|---|
| <1750 | 1023 | 0.954 | 0.622 | 0.315 | 0.108 | 0.20457 | 0.02786 | 0.00485 | 0.00083 |
| 1750–1800 | 237 | 0.919 | 0.602 | 0.386 | 0.200 | 0.36656 | 0.12870 | 0.06022 | 0.02705 |
| 1800–1830 | 68 | 0.874 | 0.535 | 0.350 | 0.200 | 0.37224 | 0.13912 | 0.07463 | 0.03803 |
| 1830–1900 | 178 | 0.837 | 0.355 | 0.178 | 0.079 | 0.15937 | 0.03540 | 0.01638 | 0.00641 |
| >1900 | 190 | 0.731 | 0.239 | 0.109 | 0.041 | 0.08577 | 0.01286 | 0.00356 | 0.00079 |
| unknown | 163 | 0.782 | 0.270 | 0.127 | 0.060 | 0.12819 | 0.02169 | 0.00937 | 0.00362 |

## 8. Obras sin fecha

Origen de la fecha por obra: manual 1616, composer_lifespan 663, dcml_metadata 440, kern_ODT 286, kern_PDT_publication 65, missing 1. Asignación de periodo: year 1223, year_midpoint 1184, lifespan 499, none 165 (D-30: rangos por punto medio). Unidades en `unknown`: 903 de 6735 (13 %), casi todas Lieder cuyo compositor cruza un bin. `corpus/manual_dates.csv` ingerido (1962 obras); detalle en `results/missing_dates.md`.

## 9. Anomalías y avisos

- **Duplicados entre colecciones**: 2,152 unidades no primarias por clave de catálogo o por hash de secuencia (351 obras por hash, D-29: ediciones MuseData, kern vs MuseData, OpenScore vs kern/DCML); prioridad DCML > MuseData > kern > S3 > OpenScore. Lista en `results/seq_duplicates.md`.
- **Movimientos partidos**: el finale de la Novena está en 8 secciones MuseData (un solo `work_id`); WTC = pareja preludio+fuga; en OpenScore un fichero puede contener todos los movimientos (Beethoven op. 18) o uno (Dvořák).
- **OMR/transcripción**: OpenScore es transcripción humana desde IMSLP (sin OMR), pero 7 cuartetos no importan en music21 y 39 carpetas carecen de partitura. MuseData: 20 movimientos con datos corruptos. Instrumentos transpositores en altura escrita (sin efecto, D-14).
- **Voces dobladas**: colapsadas en el 20 % de las unidades (orquesta y continuo); ver `results/extract_summary.md`.
- **Unidad de obra**: prevalencia «obras con D4» no es comparable con el piloto (allí obra = fichero, aquí obra completa).
- **Test de regresión**: `results/regression_test.md` (m21_bach reproduce el piloto: D2 +1,2 %, D4 +1,9 %).

Figuras: `results/fig/base_rate_strata.png`, `results/fig/observed_vs_null.png`, `results/fig/p_cross.png`.
