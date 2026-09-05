# Resumen de la extracción (tarea 4)

Unidades primarias procesadas: 7659 — ok 7573, fail 32. Caché: `corpus/cache/*.npz` (2704 obras, incluye duplicados extraídos antes de la deduplicación final).

| colección | unidades | ok | fail | partes | partes tras colapso | notas | colapso medio | colapso máx | seg |
|---|---|---|---|---|---|---|---|---|---|
| dcml | 955 | 955 | 0 | 2096 | 2090 | 869,917 | 0.002 | 0.25 | 7 |
| dcml_abc | 70 | 70 | 0 | 280 | 280 | 221,655 | 0.000 | 0.0 | 4 |
| dcml_mozart_sonatas | 54 | 0 | 0 | 0 | 0 | 0 | nan | nan | 0 |
| kern | 1518 | 1518 | 0 | 5585 | 5336 | 1,391,185 | 0.028 | 0.5 | 283 |
| m21_bach | 413 | 413 | 0 | 1779 | 1770 | 110,001 | 0.002 | 0.333 | 5 |
| musedata_bach | 1304 | 1293 | 11 | 7042 | 6359 | 1,656,604 | 0.065 | 0.714 | 364 |
| musedata_beethoven | 52 | 48 | 4 | 625 | 569 | 483,801 | 0.076 | 0.381 | 49 |
| musedata_corelli | 45 | 45 | 0 | 175 | 134 | 16,443 | 0.228 | 0.25 | 2 |
| musedata_handel | 877 | 872 | 5 | 4651 | 3712 | 824,202 | 0.197 | 0.75 | 136 |
| musedata_mozart | 105 | 104 | 1 | 1059 | 938 | 408,631 | 0.075 | 0.533 | 96 |
| musedata_telemann | 560 | 560 | 0 | 2575 | 2089 | 437,216 | 0.150 | 0.667 | 154 |
| musedata_vivaldi | 241 | 237 | 4 | 1356 | 1032 | 337,092 | 0.180 | 0.857 | 24 |
| openscore_lieder | 1332 | 1332 | 0 | 4194 | 4181 | 936,152 | 0.003 | 0.333 | 185 |
| openscore_quartets | 125 | 118 | 7 | 472 | 472 | 1,162,448 | 0.000 | 0.0 | 247 |
| s3_symphonies | 8 | 8 | 0 | 184 | 177 | 108,755 | 0.039 | 0.143 | 25 |
| **total** | 7659 | 7573 | 32 | 32073 | 29139 | 8,964,102 | 0.060 | 0.857 | 1582 |

## Colapso de voces dobladas (D-13)

Unidades con alguna voz colapsada: 1547 de 7573 (20.4 %).
- dcml: 6/955
- dcml_abc: 0/70
- kern: 171/1518
- m21_bach: 5/413
- musedata_bach: 319/1293
- musedata_beethoven: 35/48
- musedata_corelli: 41/45
- musedata_handel: 484/872
- musedata_mozart: 54/104
- musedata_telemann: 283/560
- musedata_vivaldi: 131/237
- openscore_lieder: 13/1332
- openscore_quartets: 0/118
- s3_symphonies: 5/8

Las 15 unidades con mayor colapso:

- `musedata_vivaldi-micro-op10-rv570_1B--02` 14→2 (0.857)
- `musedata_handel-hicks-ott--26b` 4→1 (0.75)
- `musedata_handel-hicks-ott--59a` 4→1 (0.75)
- `musedata_handel-hicks-ott--10a` 4→1 (0.75)
- `musedata_handel-best-rada--55` 4→1 (0.75)
- `musedata_handel-hicks-ott--38` 4→1 (0.75)
- `musedata_handel-best-rada--20` 4→1 (0.75)
- `musedata_handel-hicks-ott--34a` 4→1 (0.75)
- `musedata_handel-hicks-ott--31` 4→1 (0.75)
- `musedata_handel-best-rada--67` 4→1 (0.75)
- `musedata_handel-hicks-ott--41` 4→1 (0.75)
- `musedata_handel-best-rada--26` 4→1 (0.75)
- `musedata_handel-best-rada--28` 4→1 (0.75)
- `musedata_handel-best-rada--65` 4→1 (0.75)
- `musedata_handel-hicks-ott--19c` 4→1 (0.75)

## Fallos

- `musedata_bach-bg-cant-0043--11`: ValueError: invalid literal for int() with base 10: 'vt.'
- `musedata_bach-bg-cant-0118--01`: ValueError: invalid literal for int() with base 10: '  '
- `musedata_bach-bg-orch-1043--01`: ValueError: invalid literal for int() with base 10: 'sen'
- `musedata_bach-bg-vocal-0245--14`: ValueError: invalid literal for int() with base 10: 'cat'
- `musedata_bach-bg-vocal-0245--32`: ValueError: invalid literal for int() with base 10: 'sen'
- `musedata_bach-bg-vocal-0245--34`: ValueError: invalid literal for int() with base 10: 'sen'
- `musedata_bach-bg-vocal-0245--37`: ValueError: invalid literal for int() with base 10: 'sen'
- `musedata_bach-rasmuss-inventio-0773--01`: MuseDataException: cannot process bar data definition: . 23, 
- `musedata_bach-rasmuss-inventio-0774--01`: MuseDataException: cannot process bar data definition: isinte
- `musedata_bach-rasmuss-inventio-0775--01`: ValueError: invalid literal for int() with base 10: 's "'
- `musedata_bach-s1-data-organ-0528--01a`: IndexError: list index out of range
- `musedata_beethoven-bhl-orch-sym9--mvt3`: MuseDataException: cannot process bar data definition: dasure
- `musedata_beethoven-bhl-orch-sym9--mvt4d`: MuseDataException: ('cannot determine clef from:', '0')
- `musedata_beethoven-bhl-orch-sym9--mvt4f`: ValueError: invalid literal for int() with base 10: ''
- `musedata_beethoven-bhl-orch-sym9--mvt4h`: ValueError: invalid literal for int() with base 10: ''
- `musedata_handel-arnold-semele--34`: IndexError: list index out of range
- `musedata_handel-chry-opera-atalan--213b`: ValueError: not enough values to unpack (expected 2, got 1)
- `musedata_handel-chry-orch-hwv382--01`: MuseDataException: cannot process bar data definition: eassur
- `musedata_handel-hicks-jmac--38`: ValueError: invalid literal for int() with base 10: '! 4'
- `musedata_handel-hicks-ott--65a`: ValueError: invalid literal for int() with base 10: ' !1'
- `musedata_mozart-bhl-sym-k550--02`: MuseDataException: cannot process bar data definition: easrue
- `musedata_vivaldi-lecene-op09-no09--02`: ValueError: invalid literal for int() with base 10: '\r'
- `musedata_vivaldi-lecene-op11-01rv207--02xx`: ValueError: invalid literal for int() with base 10: ''
- `musedata_vivaldi-micro-op10-rv101_6A--01`: MuseDataException: cannot process bar data definition:  asure
- `musedata_vivaldi-micro-op10-rv101_6A--03`: MuseDataException: cannot process bar data definition: 3asure
- `osq-22779031`: AttributeError: 'NoneType' object has no attribute 'style'
- `osq-25403263`: MusicXMLImportException: In part (Violin 1), measure (5): found unknown MusicXML type: None
- `osq-26269501`: MusicXMLImportException: In part (Violin 1), measure (138): found unknown MusicXML type: None
- `osq-31320671`: MusicXMLImportException: In part (Violin 1), measure (150): found unknown MusicXML type: None
- `osq-7158117`: MusicXMLImportException: In part (Violin 1), measure (102): found unknown MusicXML type: None
- `osq-7267316`: MusicXMLImportException: In part (Violin 1), measure (88): found unknown MusicXML type: None
- `osq-7643891`: AttributeError: 'NoneType' object has no attribute 'style'
