# W2 → W1: notas sobre el contrato (web/assets)

W2 sigue `web/README.md`. Lo que `app.js` hace con el HTML de W1 y lo que pide a W1:

## Qué hace app.js en tiempo de ejecución (sin tocar index.html)

- `[data-num]`: rellena con `numbers[key].text`; si falta → `[missing: key]` + clase `num-missing`.
  Pone `title="Source: …"` con el campo `source`.
- Contenedores `chart-*`: al dibujar, borra el fallback y **quita `role="img"` y `aria-label` del
  `<div>`**, porque `role=img` oculta a los lectores de pantalla los controles y puntos enfocables
  de dentro; el `<svg>` lleva su propio `role="img"` + `aria-label` y cada gráfico tiene tabla de datos.
  Si el JSON no carga, deja un aviso «Data not available».
- Textos del método: carga `assets/content/method.html` en `#method-content`; si no existe, crea
  `<div id="method-content">` al final de `#method`.
- Estado: crea `<div class="status-summary" id="status-panel">` tras el `<h2>` de `#protocol`
  (tarjetas «Preregistration: Frozen» y «Confirmatory case: Not run») y reemplaza el contenido de
  `#status-pending` con tarjetas de `status.json.pending`. Añade, solo si no aparecen ya en
  `status.json`, tres pendientes de texto (sin números): transcripción de Cherubini, enmienda D-43,
  registro en OSF.

## Peticiones a W1 (opcionales)

1. Añadir `<div id="method-content"></div>` donde queráis el texto largo del método (si no, va al
   final de `#method`), y `<div id="status-panel"></div>` si queréis otra posición.
2. `status.json.pending`: añadir los ítems D-43 (enmienda) y OSF (registro); entonces app.js deja
   de añadir los suyos (los detecta por `/D-43/` y `/OSF/`).
3. `calibration.json`: `models` = `["lap","kn"]` pero `choice` = `"hier"` y `bins[].pred_mean`
   trae `hier`; app.js dibuja los modelos presentes en `pred_mean` (los tres). `summary_fields`
   tiene 2 nombres y cada `summary[...]` 3 valores (pendiente, MAE, sesgo, según `summary_note`):
   app.js muestra las tres columnas. Conviene alinear `models` y `summary_fields`.
4. `observed_null.json`: el campo es `works_perm` (README dice `works`); app.js acepta ambos.
