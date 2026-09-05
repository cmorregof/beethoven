# Resumen de la extracción (tarea 4)

Unidades primarias procesadas: 7737 — ok 7705, fail 32. Caché: `corpus/cache/*.npz` (2688 obras).

| colección | unidades | ok | fail | partes | partes tras colapso | notas | colapso medio | colapso máx | seg |
|---|---|---|---|---|---|---|---|---|---|
| dcml | 955.0 | 955.0 | 0.0 | 2096 | 2090 | 869,917 | 0.002 | 0.25 | 8 |
| dcml_abc | 64.0 | 64.0 | 0.0 | 256 | 256 | 199,711 | 0.0 | 0.0 | 3 |
| dcml_mozart_sonatas | 54.0 | 54.0 | 0.0 | 108 | 108 | 88,463 | 0.0 | 0.0 | 1 |
| kern | 1578.0 | 1578.0 | 0.0 | 5825 | 5576 | 1,577,806 | 0.027 | 0.5 | 331 |
| m21_bach | 413.0 | 413.0 | 0.0 | 1779 | 1770 | 110,001 | 0.002 | 0.333 | 6 |
| musedata_bach | 1304.0 | 1293.0 | 11.0 | 7042 | 6359 | 1,656,604 | 0.065 | 0.714 | 365 |
| musedata_beethoven | 52.0 | 48.0 | 4.0 | 625 | 569 | 483,801 | 0.076 | 0.381 | 49 |
| musedata_corelli | 45.0 | 45.0 | 0.0 | 175 | 134 | 16,443 | 0.228 | 0.25 | 3 |
| musedata_handel | 877.0 | 872.0 | 5.0 | 4651 | 3712 | 824,202 | 0.197 | 0.75 | 136 |
| musedata_mozart | 105.0 | 104.0 | 1.0 | 1059 | 938 | 408,631 | 0.075 | 0.533 | 96 |
| musedata_telemann | 560.0 | 560.0 | 0.0 | 2575 | 2089 | 437,216 | 0.15 | 0.667 | 154 |
| musedata_vivaldi | 241.0 | 237.0 | 4.0 | 1356 | 1032 | 337,092 | 0.18 | 0.857 | 24 |
| openscore_lieder | 1356.0 | 1356.0 | 0.0 | 4266 | 4253 | 953,880 | 0.003 | 0.333 | 189 |
| openscore_quartets | 125.0 | 118.0 | 7.0 | 472 | 472 | 1,162,448 | 0.0 | 0.0 | 248 |
| s3_symphonies | 8.0 | 8.0 | 0.0 | 184 | 177 | 108,755 | 0.039 | 0.143 | 26 |
| **total** | 7737 | 7705 | 32 | 32469 | 29535 | 9,234,970 | 0.059 | 0.857 | 1633 |

## Colapso de voces dobladas (D-13)

Unidades con alguna voz colapsada: 1547 de 7705 (20.1 %). Por colección (nº unidades con colapso / total):
- dcml: 6/955
- dcml_abc: 0/64
- dcml_mozart_sonatas: 0/54
- kern: 171/1578
- m21_bach: 5/413
- musedata_bach: 319/1293
- musedata_beethoven: 35/48
- musedata_corelli: 41/45
- musedata_handel: 484/872
- musedata_mozart: 54/104
- musedata_telemann: 283/560
- musedata_vivaldi: 131/237
- openscore_lieder: 13/1356
- openscore_quartets: 0/118
- s3_symphonies: 5/8

Las 15 unidades con mayor colapso:

- `musedata_vivaldi-micro-op10-rv570_1B--02` 14.0→2.0 (0.857)
- `musedata_handel-best-rada--28` 4.0→1.0 (0.75)
- `musedata_handel-best-rada--55` 4.0→1.0 (0.75)
- `musedata_handel-best-rada--06` 4.0→1.0 (0.75)
- `musedata_handel-best-rada--48` 4.0→1.0 (0.75)
- `musedata_handel-best-rada--49` 4.0→1.0 (0.75)
- `musedata_handel-best-rada--08` 4.0→1.0 (0.75)
- `musedata_handel-hicks-ott--58a` 4.0→1.0 (0.75)
- `musedata_handel-hicks-ott--06b` 8.0→2.0 (0.75)
- `musedata_handel-best-rada--20` 4.0→1.0 (0.75)
- `musedata_handel-hicks-ott--04` 4.0→1.0 (0.75)
- `musedata_handel-hicks-ott--13` 4.0→1.0 (0.75)
- `musedata_handel-best-rada--10` 4.0→1.0 (0.75)
- `musedata_handel-best-rada--44` 4.0→1.0 (0.75)
- `musedata_handel-hicks-ott--50b` 8.0→2.0 (0.75)

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
