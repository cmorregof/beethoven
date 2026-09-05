# Test de regresión (D-18)

Referencia piloto `bach` (music21): ventanas 101,162, obras 433, D2 148.28/100k, D4 7.91/100k, recuentos {'D1': 42, 'D2': 150, 'D3': 6667, 'D4': 8, 'D5': 4}

## m21_bach
obras 413 (sin caché: 0), ventanas 99,297, notas 109,206

| def | recuento | por 100k | piloto por 100k | desviación |
|---|---|---|---|---|
| D1 | 42 | 42.30 | 41.52 | +1.9% |
| D2 | 149 | 150.05 | 148.28 | +1.2% OK |
| D3 | 6521 | 6567.17 | 6590.42 | -0.4% |
| D4 | 8 | 8.06 | 7.91 | +1.9% OK |
| D5 | 4 | 4.03 | 3.95 | +1.9% |

## kern/bach-370-chorales
obras 370 (sin caché: 0), ventanas 78,026, notas 84,614

| def | recuento | por 100k | piloto por 100k | desviación |
|---|---|---|---|---|
| D1 | 33 | 42.29 | 41.52 | +1.9% |
| D2 | 94 | 120.47 | 148.28 | -18.8% (fuera de tolerancia: conjunto distinto) |
| D3 | 5043 | 6463.23 | 6590.42 | -1.9% |
| D4 | 1 | 1.28 | 7.91 | -83.8% (fuera de tolerancia: conjunto distinto) |
| D5 | 0 | 0.00 | 3.95 | -100.0% |

Notas: (1) el piloto contaba 433 «obras» en `bach` porque incluía 20 ficheros `.rntxt` (análisis en números romanos) que music21 parsea como acordes; la nueva canalización los excluye (413 ficheros), de ahí las ~1.900 ventanas de menos y la desviación de +1–2 %. (2) `bach-370-chorales` es un conjunto distinto (370 corales Riemenschneider frente a ~390 corales + obras instrumentales del corpus music21), así que sus tasas no tienen por qué coincidir; se listan como referencia.

**Resultado: PASA** (criterio: `m21_bach` D2 y D4 dentro de ±2 % del piloto).
