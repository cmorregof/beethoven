# Fase 1 sobre el corpus real — resumen

Generado por `scripts/make_summary.py` el 2026-09-05. Semilla 20260903, 100 permutaciones, `rest_break = 0.0`, obra objetivo (op. 67) excluida. Entorno en `results/env.txt`.

## 1. Tamaño del corpus por estrato

Unidades primarias en análisis (fichero/movimiento; entre paréntesis, obras `work_id`).

| colección | <1750 | 1750–1800 | 1800–1830 | 1830–1900 | >1900 | unknown | total |
|---|---|---|---|---|---|---|---|
| dcml | 417 (214) | 164 (59) | 87 (22) | 202 (40) | 85 (20) | · | 955 (355) |
| dcml_abc | · | 16 (4) | 54 (12) | · | · | · | 70 (16) |
| dcml_mozart_sonatas | · | 54 (18) | · | · | · | · | 54 (18) |
| kern | 781 (499) | 131 (51) | 4 (2) | 189 (42) | 197 (143) | 216 (64) | 1518 (801) |
| musedata_bach | 1304 (390) | · | · | · | · | · | 1304 (390) |
| musedata_beethoven | · | · | · | · | · | 52 (12) | 52 (12) |
| musedata_corelli | 45 (13) | · | · | · | · | · | 45 (13) |
| musedata_handel | · | · | · | · | · | 877 (50) | 877 (50) |
| musedata_mozart | · | 105 (29) | · | · | · | · | 105 (29) |
| musedata_telemann | · | · | · | · | · | 560 (109) | 560 (109) |
| musedata_vivaldi | 241 (60) | · | · | · | · | · | 241 (60) |
| openscore_lieder | · | · | 64 (9) | 334 (64) | 60 (12) | 874 (163) | 1332 (248) |
| openscore_quartets | · | 8 (8) | 10 (10) | 11 (11) | 2 (2) | 94 (91) | 125 (122) |
| s3_symphonies | · | · | · | 4 (1) | · | 4 (1) | 8 (2) |
| **total** | **2788 (1176)** | **478 (169)** | **219 (55)** | **740 (158)** | **344 (177)** | **2677 (490)** | **7246 (2224)** |

Ventanas de 4 notas analizadas: **6,995,048** en 2,211 obras (8,228,165 notas); piloto: 302.414 ventanas en 601 obras. Unidades que no parsean: 32 (`results/extract_log.csv`).

| periodo | obras | ventanas | % ventanas |
|---|---|---|---|
| <1750 | 1,171 | 2,276,286 | 32.5 % |
| 1750–1800 | 169 | 807,639 | 11.5 % |
| 1800–1830 | 54 | 416,428 | 6.0 % |
| 1830–1900 | 158 | 562,651 | 8.0 % |
| >1900 | 177 | 218,823 | 3.1 % |
| unknown | 482 | 2,713,221 | 38.8 % |

## 2. Tasa base anidada D1–D5 por periodo (ocurrencias por 100k ventanas)

| estrato | obras | ventanas | D1 | D2 | D3 | D4 | D5 | obras con D4 |
|---|---|---|---|---|---|---|---|---|
| **todo** | 2,211 | 6,995,048 | 73.29 | 216.04 | 6,280 | 19.13 | 17.04 | 16.0 % |
| <1750 | 1,171 | 2,276,286 | 60.05 | 180.51 | 6,776 | 15.16 | 14.80 | 7.1 % |
| 1750–1800 | 169 | 807,639 | 68.72 | 248.63 | 6,252 | 23.90 | 18.70 | 26.0 % |
| 1800–1830 | 54 | 416,428 | 79.49 | 258.87 | 5,231 | 35.78 | 33.62 | 51.9 % |
| 1830–1900 | 158 | 562,651 | 76.07 | 190.53 | 5,599 | 17.95 | 15.46 | 24.1 % |
| >1900 | 177 | 218,823 | 37.93 | 79.97 | 6,013 | 2.74 | 1.83 | 2.3 % |
| unknown | 482 | 2,713,221 | 87.09 | 245.83 | 6,195 | 20.05 | 17.43 | 32.4 % |
| piloto (music21 art) | 601 | 302,414 | 77.71 | 275.78 | 6367 | 16.53 | 13.56 | 3.8 % |

**Estrato 1750–1830 (unión de los dos bins):** D4 = 342 en 1,224,067 ventanas → **27.94/100k**, frente a **16,53/100k** del piloto (todo el corpus art) y 8,69 (Beethoven), 6,05 (Mozart), 74,1 (Haydn, n=9) por colección en el piloto. La tasa del estrato clásico es **superior** a la global del piloto. Compárese sobre todo con las colecciones del piloto del mismo periodo (Beethoven, Mozart, Haydn).

## 3. Tasa base por colección (≥ 10.000 ventanas)

| colección | obras | ventanas | D1 | D2 | D3 | D4 | D5 | obras con D4 |
|---|---|---|---|---|---|---|---|---|
| musedata_bach | 386 | 1,373,572 | 48.85 | 167.37 | 7,139 | 11.07 | 10.70 | 9.6 % |
| openscore_quartets | 115 | 899,159 | 74.18 | 215.53 | 6,114 | 21.91 | 19.24 | 47.0 % |
| openscore_lieder | 248 | 698,986 | 76.11 | 206.58 | 5,986 | 21.75 | 18.17 | 24.6 % |
| musedata_handel | 50 | 653,748 | 95.76 | 244.28 | 6,689 | 24.93 | 23.56 | 34.0 % |
| musedata_telemann | 109 | 346,120 | 102.85 | 319.83 | 6,972 | 29.18 | 27.45 | 28.4 % |
| musedata_beethoven | 11 | 323,556 | 101.68 | 317.72 | 3,853 | 9.89 | 9.27 | 72.7 % |
| musedata_mozart | 29 | 294,855 | 86.82 | 370.69 | 6,204 | 45.11 | 34.25 | 62.1 % |
| musedata_vivaldi | 59 | 284,702 | 172.81 | 384.26 | 5,924 | 54.79 | 54.44 | 54.2 % |
| kern/humdrum-haydn-quartets | 59 | 247,377 | 80.44 | 251.44 | 7,027 | 19.81 | 14.55 | 40.7 % |
| dcml_abc | 16 | 168,074 | 68.42 | 300.46 | 5,667 | 20.82 | 16.66 | 56.2 % |
| dcml/beethoven_piano_sonatas | 28 | 151,606 | 32.98 | 82.45 | 4,888 | 5.94 | 5.94 | 14.3 % |
| kern/humdrum-mozart-quartets | 27 | 107,519 | 76.27 | 259.49 | 7,334 | 17.67 | 13.95 | 37.0 % |
| kern/humdrum-corelli | 59 | 101,395 | 9.86 | 51.28 | 6,918 | 1.97 | 1.97 | 3.4 % |
| kern/humdrum-haydn-symphonies | 6 | 99,563 | 84.37 | 258.13 | 5,985 | 22.10 | 18.08 | 100.0 % |
| kern/scriabin | 65 | 95,472 | 55.51 | 95.32 | 5,526 | 6.28 | 4.19 | 6.2 % |
| kern/bach-370-chorales | 370 | 78,026 | 42.29 | 120.47 | 6,463 | 1.28 | 0.00 | 0.3 % |
| kern/humdrum-bach-brandenburg | 6 | 75,953 | 79.00 | 176.42 | 5,272 | 17.12 | 17.12 | 50.0 % |
| kern/bach-wtc | 48 | 70,073 | 2.85 | 17.12 | 7,384 | 0.00 | 0.00 | 0.0 % |
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
| kern/chopin-mazurkas | 16 | 28,717 | 90.54 | 156.70 | 3,733 | 10.45 | 3.48 | 18.8 % |
| dcml/jc_bach_sonatas | 2 | 28,047 | 10.70 | 71.31 | 5,348 | 3.57 | 3.57 | 50.0 % |
| dcml/kozeluh_sonatas | 8 | 26,997 | 62.97 | 144.46 | 6,938 | 18.52 | 11.11 | 25.0 % |
| kern/art-of-the-fugue | 5 | 26,996 | 44.45 | 518.60 | 8,590 | 0.00 | 0.00 | 0.0 % |
| dcml/liszt_pelerinage | 3 | 25,120 | 75.64 | 123.41 | 4,682 | 7.96 | 3.98 | 33.3 % |
| kern/haydn-piano-sonatas | 18 | 24,560 | 12.21 | 48.86 | 5,770 | 4.07 | 4.07 | 5.6 % |
| dcml/medtner_tales | 7 | 23,752 | 42.10 | 71.57 | 5,890 | 0.00 | 0.00 | 0.0 % |
| kern/vivaldi-op6 | 6 | 20,973 | 128.74 | 352.83 | 5,426 | 52.45 | 47.68 | 50.0 % |
| kern/beethoven-piano-sonatas | 4 | 15,690 | 50.99 | 216.70 | 4,653 | 12.75 | 6.37 | 50.0 % |
| musedata_corelli | 13 | 13,866 | 28.85 | 43.27 | 5,719 | 0.00 | 0.00 | 0.0 % |
| dcml/frescobaldi_fiori_musicali | 1 | 13,789 | 43.51 | 50.77 | 6,621 | 0.00 | 0.00 | 0.0 % |
| dcml/schubert_winterreise | 1 | 13,072 | 160.65 | 550.80 | 5,477 | 0.00 | 0.00 | 0.0 % |
| kern/chopin-preludes | 1 | 12,192 | 57.41 | 155.84 | 4,323 | 82.02 | 82.02 | 100.0 % |
| dcml/monteverdi_madrigals | 15 | 10,888 | 165.32 | 698.02 | 7,017 | 73.48 | 73.48 | 20.0 % |
| dcml/ravel_piano | 2 | 10,652 | 9.39 | 18.78 | 4,947 | 0.00 | 0.00 | 0.0 % |

Piloto (D4/100k): monteverdi 52.04, haydn 74.09, schumann_robert 20.84, beethoven 8.69, bach 7.91, mozart 6.05, oneills1850 7.15.

## 4. Tasa base por compositor (≥ 5 obras, ordenado por ventanas)

| compositor | obras | ventanas | D1 | D2 | D3 | D4 | D5 | obras con D4 |
|---|---|---|---|---|---|---|---|---|
| bach_js | 845 | 1,717,597 | 45.65 | 157.37 | 6,957 | 9.66 | 9.32 | 4.9 % |
| beethoven_l | 61 | 663,500 | 75.96 | 256.52 | 4,579 | 11.76 | 10.25 | 37.7 % |
| handel_gf | 51 | 655,101 | 95.56 | 243.78 | 6,686 | 24.88 | 23.51 | 33.3 % |
| haydn_fj | 116 | 531,259 | 70.02 | 227.01 | 6,946 | 19.01 | 13.55 | 37.9 % |
| mozart_wa | 74 | 471,671 | 76.11 | 302.33 | 6,420 | 32.44 | 24.81 | 39.2 % |
| telemann_gp | 109 | 346,120 | 102.85 | 319.83 | 6,972 | 29.18 | 27.45 | 28.4 % |
| vivaldi_a | 65 | 305,675 | 169.79 | 382.11 | 5,890 | 54.63 | 53.98 | 53.8 % |
| schubert_f | 17 | 129,840 | 130.16 | 354.28 | 5,290 | 75.48 | 74.71 | 58.8 % |
| corelli_a | 75 | 120,034 | 11.66 | 48.32 | 6,811 | 1.67 | 1.67 | 2.7 % |
| dvorak_a | 8 | 103,980 | 143.30 | 323.14 | 5,149 | 21.16 | 18.27 | 50.0 % |
| scarlatti_d | 128 | 99,651 | 23.08 | 53.19 | 6,089 | 0.00 | 0.00 | 0.0 % |
| scriabin_a | 65 | 95,472 | 55.51 | 95.32 | 5,526 | 6.28 | 4.19 | 6.2 % |
| mendelssohn_f | 15 | 89,206 | 72.87 | 236.53 | 7,065 | 14.57 | 14.57 | 60.0 % |
| brahms_j | 21 | 84,135 | 68.94 | 199.68 | 6,096 | 1.19 | 1.19 | 4.8 % |
| chopin_f | 37 | 70,087 | 82.75 | 156.95 | 3,921 | 22.83 | 15.69 | 18.9 % |
| schumann_r | 10 | 56,762 | 93.37 | 280.12 | 4,494 | 7.05 | 5.29 | 30.0 % |
| holmes_a | 8 | 43,849 | 29.65 | 66.14 | 6,233 | 4.56 | 4.56 | 12.5 % |
| grieg_e | 11 | 43,139 | 71.86 | 141.40 | 6,148 | 6.95 | 6.95 | 9.1 % |
| bach_cpe | 34 | 40,182 | 24.89 | 89.59 | 6,209 | 2.49 | 2.49 | 2.9 % |
| mayer_e | 7 | 36,997 | 13.51 | 121.63 | 8,236 | 5.41 | 5.41 | 28.6 % |
| joplin_s | 48 | 35,643 | 33.67 | 109.42 | 7,031 | 0.00 | 0.00 | 0.0 % |
| couperin_f | 91 | 32,138 | 18.67 | 74.68 | 6,970 | 0.00 | 0.00 | 0.0 % |
| debussy_c | 6 | 30,814 | 38.94 | 113.58 | 5,903 | 16.23 | 12.98 | 50.0 % |
| wolf_h | 5 | 30,319 | 56.07 | 171.51 | 5,746 | 46.18 | 46.18 | 60.0 % |
| lang_j | 12 | 27,504 | 79.99 | 203.61 | 6,214 | 43.63 | 39.99 | 50.0 % |

## 5. Observado frente al modelo nulo (D4; barajado intra-voz, obras con ≥ 150 notas)

| estrato | obras perm. | D4 obs | D4 nulo (media) | IC95 | ratio | p |
|---|---|---|---|---|---|---|
| **todo** | 2159 | 1,338 | 1,020.2 | 952–1,081 | 1.31 | 0.010 |
| <1750 | 1124 | 345 | 241.3 | 217–269 | 1.43 | 0.010 |
| 1750–1800 | 167 | 193 | 153.8 | 130–177 | 1.25 | 0.010 |
| 1800–1830 | 54 | 149 | 77.0 | 60–93 | 1.94 | 0.010 |
| 1830–1900 | 158 | 101 | 66.3 | 51–84 | 1.52 | 0.010 |
| >1900 | 175 | 6 | 15.9 | 9–24 | 0.38 | 1.000 |
| unknown | 481 | 544 | 465.8 | 427–507 | 1.17 | 0.010 |
| musedata_bach | 373 | 152 | 135.2 | 112–159 | 1.12 | 0.050 |
| openscore_quartets | 115 | 197 | 143.5 | 122–164 | 1.37 | 0.010 |
| openscore_lieder | 247 | 152 | 93.5 | 76–112 | 1.63 | 0.010 |
| musedata_handel | 50 | 163 | 105.5 | 80–125 | 1.54 | 0.010 |
| musedata_telemann | 109 | 101 | 64.5 | 50–79 | 1.57 | 0.010 |
| musedata_beethoven | 11 | 32 | 94.5 | 72–117 | 0.34 | 1.000 |
| musedata_mozart | 29 | 133 | 90.4 | 73–110 | 1.47 | 0.010 |
| musedata_vivaldi | 59 | 156 | 67.3 | 54–81 | 2.32 | 0.010 |
| kern/humdrum-haydn-quartets | 59 | 49 | 41.9 | 31–54 | 1.17 | 0.149 |
| dcml_abc | 16 | 35 | 33.1 | 23–43 | 1.06 | 0.396 |
| dcml/beethoven_piano_sonatas | 28 | 9 | 9.3 | 4–16 | 0.97 | 0.584 |
| kern/humdrum-mozart-quartets | 27 | 19 | 19.8 | 9–28 | 0.96 | 0.574 |
| piloto (art) | 519 | 49 | 51.5 | 36–64 | 0.95 | 0.69 |

D2: obs 15,103 vs nulo 18,453.2 (ratio 0.82, p=1.000); D3: obs 438,889 vs 408,872.0 (ratio 1.07, p=0.010); D4: ratio 1.31, p=0.010. Piloto: D2 0,88×, D3 1,14× (p=0,01), D4 0,95× (p=0,69).

## 6. Ranking del 3-grama de intervalos

3-gramas distintos: 50,155 (piloto 9.512). `(0, 0, -4)`: rango 189, n=5,127 (0.0733 %); `(0, 0, -3)`: rango 97, n=9,985 (0.1427 %). Piloto: (0,0,−4) rango 194, 0,078 %; (0,0,−3) rango 83, 0,198 %.

Top-10: `(0, 0, 0)` 412,834, `(-2, -2, -1)` 114,740, `(-1, -2, -2)` 113,690, `(-2, -1, -2)` 111,840, `(2, 2, 1)` 82,402, `(-2, -1, 1)` 77,003, `(2, 1, 2)` 70,385, `(1, 2, 2)` 63,129, `(-1, 1, 2)` 59,532, `(1, -1, 1)` 50,835.

## 7. Curva de unicidad P_cross(n)

2,211 obras. P_cross(n) = probabilidad de que una ventana de n notas aparezca idéntica en otra obra.

| n | IV tokens | IV tipos | IV P_cross | IV piloto | IVR tokens | IVR tipos | IVR P_cross | IVR piloto |
|---|---|---|---|---|---|---|---|---|
| 3 | 7,406,087 | 4,027 | 0.9999 |  | 7,406,087 | 34,727 | 0.9981 |  |
| 4 | 6,995,048 | 50,155 | 0.9963 | 0.9825 | 6,995,048 | 370,832 | 0.9600 | 0.8719 |
| 5 | 6,584,009 | 247,806 | 0.9735 |  | 6,584,009 | 1,119,008 | 0.8266 |  |
| 6 | 6,232,540 | 698,604 | 0.9025 | 0.7907 | 6,232,540 | 1,848,647 | 0.6574 | 0.4646 |
| 7 | 5,925,063 | 1,285,791 | 0.7802 |  | 5,925,063 | 2,345,051 | 0.5168 |  |
| 8 | 5,652,821 | 1,819,180 | 0.6429 | 0.4854 | 5,652,821 | 2,639,293 | 0.4155 | 0.263 |
| 9 | 5,409,418 | 2,218,416 | 0.5222 |  | 5,409,418 | 2,800,662 | 0.3467 |  |
| 10 | 5,189,989 | 2,486,427 | 0.4259 |  | 5,189,989 | 2,885,240 | 0.2988 |  |
| 11 | 4,989,281 | 2,649,428 | 0.3543 |  | 4,989,281 | 2,921,934 | 0.2644 |  |
| 12 | 4,804,340 | 2,738,088 | 0.3025 | 0.2066 | 4,804,340 | 2,930,399 | 0.2384 | 0.1715 |

P_cross(n) por periodo (IVR = intervalos + ritmo), dentro de cada periodo:

| periodo | obras | n=4 | n=6 | n=8 | n=10 | n=12 |
|---|---|---|---|---|---|---|
| <1750 | 1171 | 0.948 | 0.656 | 0.405 | 0.289 | 0.233 |
| 1750–1800 | 169 | 0.901 | 0.587 | 0.381 | 0.266 | 0.199 |
| 1800–1830 | 54 | 0.824 | 0.427 | 0.242 | 0.153 | 0.107 |
| 1830–1900 | 158 | 0.799 | 0.333 | 0.192 | 0.141 | 0.117 |
| >1900 | 177 | 0.659 | 0.203 | 0.094 | 0.053 | 0.036 |
| unknown | 482 | 0.936 | 0.584 | 0.371 | 0.281 | 0.235 |

## 8. Obras sin fecha

Origen de la fecha por obra: composer_lifespan 2279, dcml_metadata 440, kern_ODT 286, kern_PDT_publication 65, missing 1. Unidades en `unknown`: 2677 de 7246 (37 %), sobre todo Handel, Telemann, Lieder cuyo compositor cruza un bin, cuartetos de Haydn (kern) y Beethoven MuseData. Lista para rellenar: `corpus/manual_dates.csv` (1962 obras); detalle en `results/missing_dates.md`.

## 9. Anomalías y avisos

- **Duplicados entre colecciones**: 1.563 unidades no primarias (Beethoven sonatas/cuartetos en kern, DCML, MuseData y OpenScore; Chopin, Corelli, Scarlatti, Bach BWV); se conserva una copia por obra (prioridad DCML > kern > MuseData > S3 > OpenScore). Los corales no se deduplican por BWV (D-24).
- **Movimientos partidos**: el finale de la Novena está en 8 secciones MuseData (un solo `work_id`); WTC = pareja preludio+fuga; en OpenScore un fichero puede contener todos los movimientos (Beethoven op. 18) o uno (Dvořák).
- **OMR/transcripción**: OpenScore es transcripción humana desde IMSLP (sin OMR), pero 7 cuartetos no importan en music21 y 39 carpetas carecen de partitura. MuseData: 20 movimientos con datos corruptos. Instrumentos transpositores en altura escrita (sin efecto, D-14).
- **Voces dobladas**: colapsadas en el 20 % de las unidades (orquesta y continuo); ver `results/extract_summary.md`.
- **Unidad de obra**: prevalencia «obras con D4» no es comparable con el piloto (allí obra = fichero, aquí obra completa).
- **Test de regresión**: `results/regression_test.md` (m21_bach reproduce el piloto: D2 +1,2 %, D4 +1,9 %).

Figuras: `results/fig/base_rate_strata.png`, `results/fig/observed_vs_null.png`, `results/fig/p_cross.png`.
