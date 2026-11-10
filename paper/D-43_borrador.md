# D-43 — Enmienda al preregistro D-41: fragmentos, nulo de igual longitud y controles de cita literal (BORRADOR)

**Estado: PROPUESTA, PENDIENTE DE APROBACIÓN DEL USUARIO.** Borrador redactado por el agente A1 el
2026-11-09. No es vigente hasta que el usuario lo apruebe, se versione en `decisions/` y se registre
en OSF junto con D-41. **El caso Cherubini → Beethoven op. 67 NO se ha ejecutado.** Ningún número de
este documento proviene de la Quinta ni de ninguna obra de Cherubini; los recuentos de obras salen
solo de `corpus/works.csv` filtrado por `scripts/preregistration_guard.py`, sin caché ni parquet.

## Motivo

1. No hay en el corpus ninguna obra de Cherubini anterior a 1808. La única catalogada
   (`osq-5108725`, Cuarteto n.º 1, 1814) es posterior y está excluida (D-35). Las dos fuentes de la
   hipótesis, el incipit del *Hymne au Panthéon* y la coda de la obertura de *Eliza* (ambas de 1794),
   no tienen edición simbólica y deben transcribirse a mano (`corpus/raw/cherubini/README.md`, D-11).
   Con D-41 tal como está, el conjunto de obras A sería vacío.
2. El nulo de D-41 toma como A′ obras completas. Con A = fragmentos de 10–20 compases, A′ tendría
   órdenes de magnitud más ventanas y más tipos que A, y el recuento K(A′, B) del nulo sería mucho
   mayor que el de A por puro tamaño: el test quedaría sesgado hacia no detectar.
3. D-41 exige medir antes la sensibilidad a cita literal (punto 1 de «Pendiente») con P01–P06/P14,
   que no están codificados. Sí lo están cuatro arreglos literales para teclado de *L'estro armonico*.

## (a) Obras A elegibles y protocolo de codificación

**A = exactamente dos fragmentos, fijados aquí y no ampliables:**

| id | obra | límites del fragmento (regla objetiva) | edición |
|---|---|---|---|
| A1 | *Hymne au Panthéon* (1794), coro y orquesta | compases 1 a 12 de la edición E1, todas las partes | E1 = `[HUECO: edición, editor, año, signatura o URL de IMSLP; la rellena el usuario antes de registrar]` |
| A2 | Obertura de *Eliza, ou Le Voyage aux glaciers du Mont St-Bernard* (1794) | los últimos 20 compases de la obertura en la edición E2: compases `[HUECO: C_total − 19]` a `[HUECO: C_total]`, todas las partes | E2 = `[HUECO: edición; C_total = número del último compás de la obertura en E2]` |

Reglas de los límites (no dependen de juicio musical): se usa la numeración de compases de la
edición; si la edición no numera, se cuentan los compases completos desde el primero. Una anacrusa
inicial se codifica y no cuenta como compás. Si dentro del rango hay casillas de 1.ª/2.ª vez, se
codifica la última versión (la que se ejecuta al terminar); las repeticiones no se desarrollan. El
compás final con calderón cuenta. El usuario rellena los huecos **mirando solo la portada, el
catálogo de IMSLP y el número del último compás**, no el contenido musical, y los congela al
registrar. No se cambian después.

**Regla de elegibilidad (sustituye a «todas las obras de Cherubini presentes en el corpus con fecha
anterior a 1808»):** son elegibles los dos fragmentos anteriores, de composición anterior a 1808,
fijados antes de calcular cualquier ventana. No se añade ni se quita ningún fragmento a posteriori.
Si uno de los dos no puede codificarse (fuente ilegible o incompleta), se declara y el test se
hace con el otro, manteniendo α = 0,025 (la corrección no se relaja).

**Protocolo de codificación:**

1. Fuente: solo la edición fijada en la tabla. Si es una reducción y no una partitura completa, se
   declara antes de codificar y el fragmento se analiza igual, con esa limitación anotada.
2. Formato y reglas de `corpus/raw/cherubini/README.md` (MusicXML sin comprimir; una `<part>` por
   instrumento o voz real; acordes como `<chord/>`; ligaduras con `<tie>` y `<tied/>`; silencios
   explícitos; transpositores en altura escrita con `<transpose>` o en altura real, declarado; notas
   de adorno como `<grace/>`, tal como aparecen; trémolos abreviados como en la fuente, sin
   desarrollar; edición, páginas y compases en `<encoding-description>`).
3. **Dos codificaciones independientes** (C1 y C2). Preferiblemente por dos personas; si solo
   codifica el usuario, dos pasadas separadas al menos 7 días, sin abrir C1 al hacer C2.
4. Cotejo automático nota a nota (parte, compás, ataque, altura, duración, ligadura) con un script
   que solo compara los dos ficheros y no calcula ventanas ni consulta la Quinta. Cada discrepancia
   se resuelve contra la fuente y se registra en `corpus/raw/cherubini/discrepancias.csv`
   (fragmento, parte, compás, C1, C2, resolución, motivo). Se versiona el fichero final y su MD5.
5. Ningún agente transcribe, corrige ni hace OCR. El cotejo puede hacerlo un script.
6. Catálogo: las dos filas se añaden a `corpus/works.csv` con `is_target = 1`, `collection =
   cherubini`, `license = manual_transcription`, `year_source = manual`, mediante un cambio que solo
   añade filas (se verifica que el `diff` del catálogo no toca ninguna otra fila; no se relanza
   `build_catalog.py` completo, porque reejecuta la deduplicación sobre la caché). Las tablas de
   fondo, la calibración y los umbrales no se reconstruyen.

## (b) Nulo con fragmentos de igual longitud

**Sustituye** a «1000 pares (A′, B′) con A′ obra de otro compositor del estrato con la misma
instrumentación que A».

- **Longitud de A:** L(A) = número de ventanas de 8 notas de A (todas las voces, segmentos cortados
  por silencios, `rest_break = 0`, tras colapso de voces dobladas calculado sobre el propio
  fragmento). L(A) se calcula en la ejecución confirmatoria; no es un resultado sobre B.
- **Piscina de A′:** obras primarias del estrato 1750–1830 (`period ∈ {1750–1800, 1800–1830}`,
  `is_primary = 1`, `in_analysis = 1`), ni de Beethoven ni de Cherubini, de la clase de
  instrumentación de A. Como `works.csv` no tiene columna de instrumentación, la lista exacta de
  `work_id` queda fijada en **`paper/D-43_null_pool.csv`**, regenerable con `paper/make_null_pool.py` (reglas de clasificación explícitas en el código; recuentos en `paper/D-43_pool_counts.json`) (`work_id`, `composer_id`, año, periodo,
  instrumentación, fragmentos a los que sirve, regla), generada con
  `preregistration_guard.filter_catalog_rows` sobre `corpus/works.csv` (solo metadatos), y se
  versiona como `decisions/D-43_null_pool.csv` al aprobar. Es el argumento `--null-pool` de
  `scripts/confirmatory_n8.py`. A2 (*Eliza*) usa las filas `orchestra`; A1 (*Hymne*) usa las tres
  clases (`orchestra`, `orchestra_soloist`, `voices_orchestra`).
- **Fragmento A′:** un movimiento de una obra de la piscina; inicio en una barra de compás elegida
  uniformemente entre todas las barras de inicio admisibles de la piscina (equivale a ponderar por
  longitud); se añaden compases completos, todas las partes, hasta que L(A′) ∈ [0,95·L(A),
  1,05·L(A)]; si el primer compás que supera 0,95·L(A) pasa de 1,05·L(A), o el movimiento se acaba,
  se descarta y se vuelve a sortear (se informa la tasa de rechazo). Las barras se reconstruyen con
  `offset + bar_remaining` de la caché. Las ventanas que cruzan el borde no cuentan, igual que en A.
- **Colapso de voces dobladas a nivel de fragmento** (regla D-13 aplicada al fragmento) en A y en
  A′. Como la caché ya colapsó a nivel de movimiento, la versión principal reextrae los movimientos
  de la piscina desde `corpus/raw` sin colapso y colapsa por fragmento (análogo exacto de A); si su
  coste resulta prohibitivo, se aplica el colapso de fragmento sobre la caché y se declara la
  diferencia (ver huecos, punto 3).
- **Réplicas:** R = 1000 por fragmento; generador `numpy.random.default_rng([20260903, k])` con
  k = 1 para A1 y k = 2 para A2. B′ = op. 67 completa, como en D-41.
- **Estadístico:** K(X, B) = número de tipos de ventana de 8 notas de X presentes en B con
  DF₋XB ≤ t_DF, con la regla de exclusión de D-37 (para A: sin Cherubini ni Beethoven; para A′: sin
  el compositor de A′ ni Beethoven).
  Esto mantiene simétricos observado y nulo (Cherubini no está en el estrato; Mozart se excluye
  para una réplica de Mozart). **Aviso para el script:** la versión actual de
  `scripts/confirmatory_n8.py` calcula DF del nulo con la exclusión de A (solo Beethoven), es decir,
  la variante de exclusión común sin los compositores de la piscina, sesgada hacia detectar; debe
  calcular un conjunto S_B por compositor de la piscina antes de ejecutar (revisión de A2, punto 1).
- **p-valor** (como D-41): p = fracción de réplicas con K(A′, B) ≥ K(A, B). Se informa también
  (1 + #)/(1 + R).
- **Bonferroni sobre 2:** se rechaza para un fragmento si p ≤ 0,025.
- **Alternativa declarada** para el emparejamiento: duración del fragmento en negras (misma
  tolerancia), como análisis de sensibilidad.

**Recuento de la piscina** (`corpus/works.csv` filtrado por la guardia; clasificación por título y
colección hecha por A1, a revisar por el usuario antes de aprobar; que cada obra tenga caché no se
ha comprobado; las tres primeras filas son las de `D-43_null_pool.csv`):

| clase | obras | compositores | detalle |
|---|---|---|---|
| orquesta sin solista ni voces | 20 | 2 | Mozart 14 sinfonías (K. 16, 19, 22, 43, 45, 48, 73, 76, 385, 425, 504, 543, 550, 551), Haydn 6 (n.º 99–104) |
| orquesta con solista | 7 | 1 | Mozart K. 271, 450, 453, 459, 466, 467, 622 |
| voces y orquesta | 1 | 1 | Mozart, *Così fan tutte* K. 588 (5 números) |
| coro y orquesta | 0 | 0 | — |
| orquesta de cuerda | 3 | 1 | Mozart K. 136–138 |

**¿Basta?** Para A2 (*Eliza*, orquesta) hay 20 obras pero solo 2 compositores, con Mozart en 14:
el nulo representa «la escritura orquestal de Mozart y Haydn», no el estrato. Es utilizable con esa
limitación declarada. Para A1 (*Hymne*, coro y orquesta) **no basta**: no hay ninguna obra de coro y
orquesta.

**Propuesta para A1** (por orden de preferencia):

1. *Principal:* piscina «orquestal ampliada» = orquesta sin solista + orquesta con solista + voces y
   orquesta (28 obras, 2 compositores), declarando que el coro no está emparejado. Coste: nulo.
   Sesgo: de signo desconocido (las líneas corales silábicas pueden compartir menos o más tipos
   raros con op. 67 que las partes instrumentales).
2. *Sensibilidad 1 (exploratoria):* A1 sin las partes corales frente a la piscina orquestal (mide cuánto pesa el
   coro); exploratoria.
3. *Sensibilidad 2 (exploratoria):* piscina = todo el estrato salvo Beethoven y Cherubini, cualquier instrumentación,
   emparejando por L(A); y versión equilibrada por compositor (primero compositor uniforme, luego
   barra uniforme).
4. *Mejora futura (no bloquea; en `OPEN_ITEMS.md`):* codificar o descargar obras de coro y orquesta
   1750–1830 de otros compositores (misas de Haydn y Mozart, himnos revolucionarios de Gossec o
   Méhul). Coste: descargas con OK del usuario, licencias, catalogación y extracción, de días a
   semanas; esas obras solo entrarían en la piscina de A′, **nunca** en las tablas de fondo
   (congeladas). Retrasa el registro.

## (c) Controles de cita literal (sustituyen a P01–P06/P14 de D-41)

**Pares:** A = Le Cène (`musedata_vivaldi-lecene-op3-rv{230,265,519,567}`, *L'estro armonico*
op. 3 n.º 9, 12, 5 y 7, cuerdas), B = transcripción para teclado del *Anne Dawson's Book*
(`musedata_vivaldi-dawson-op3-rv{230,265,519,567}`). Son arreglos literales completos.

**Por qué sustituyen a P01–P06/P14:** son el mismo tipo de control (arreglo literal de una obra
ajena, como BWV 972/976 respecto de RV 230/265), ya están codificados por una fuente externa
(MuseData) y no exigen descargas ni transcripción. P05/P14 quedan como deseables, no como requisito.

**Cambio de dominio, declarado:** ambos son del estrato < 1750, y B es un arreglo para teclado; los
umbrales se calibraron con cuartetos de cuerda de 1750–1830. Además los fondos se calculan en el
estrato 1750–1830, donde la figuración barroca es rara, lo que abarata DF. La sensibilidad medida es
una **cota superior** de la sensibilidad a cita literal en el caso objetivo.

**Medida (especificación de la torre; A3 la implementa):**

- **LS-1 (principal, análogo de la «sensibilidad en positivos» de D-41).** Instancias = tipos de
  ventana de 8 notas (7-grama IVR, `rest_break = 0`) de A presentes en B. DF y E exactamente como
  `scripts/thresholds_n8.py`: `Models("1750-1830", 8, 0.45)`, exclusión de los compositores de A y B
  (Vivaldi en ambos: no excluye nada del estrato). t_DF y t_E leídos de
  `results/thresholds_n8.json`, sin recalcular. Sensibilidad = fracción de instancias con
  DF ≤ t_DF, IC de Wilson al 95 %, global y por par; también E ≤ t_E y ambas; y cuántos tipos que
  pasan tienen ritmo no uniforme. Variante secundaria: excluir además a Beethoven (el fondo del caso
  objetivo).
- **LS-2 (secundaria, potencia del test de (b)).** Fragmentos contiguos de A (todas las voces) de
  longitud equivalente a 10, 15 y 20 compases medida en ventanas (ventanas medias por compás de la
  obra A × número de compases), 200 por par y longitud, semilla 20260903. Estadístico = tipos del
  fragmento presentes en B con DF ≤ t_DF. Nulo = 1000 fragmentos de igual longitud (misma regla que
  (b)) de obras de cuerda (con o sin continuo) del estrato < 1750 de otros compositores (sin
  Vivaldi), mismo B. Potencia = fracción de fragmentos con p ≤ 0,025. Piscina según `works.csv`:
  Corelli 69 (sonatas en trío op. 1–4: 45; op. 5: 12; op. 6: 12), Handel op. 6: 12, Telemann sonatas
  para violín: 12; 93 obras, 3 compositores, dominada por Corelli (más obras de Telemann y Bach sin
  clasificar por título).
- La especificación quedó versionada antes de medir (commit `a240875`,
  `paper/research/LS_spec.md`); la piscina nula de LS-2 que usó A3 tiene 72 obras (Corelli op. 1–4
  y op. 6, Handel op. 6), más estrecha que la clasificación por título de A1 (93 obras con Corelli
  op. 5 y las sonatas para violín de Telemann); rige la de la especificación.
- **Propuestas de A1 (no bloquean):** (i) medir también LS-2 en una rejilla de longitudes absolutas
  en ventanas (p. ej. 250, 500, 1000, 2000), porque L(A1) y L(A2), orquestales, tendrán más
  ventanas por compás que un concierto de cuerda y la equivalencia «10–20 compases» no se traslada;
  (ii) colapso de dobladas por fragmento, como en (b).

**Resultados medidos** (A3, commit `4c00ffa`, `results/literal_sensitivity_n8.json`; antes de
cualquier contacto con el caso objetivo): LS-1, fracción de tipos compartidos con DF ≤ t_DF =
0,525 (IC de Wilson 95 %: 0,510–0,541; 3.847 instancias; 0,543 con Beethoven también excluido del
fondo). LS-2, potencia a α = 0,025: 0,978 (10 compases), 0,996 (15), 1,000 (20), es decir, 185, 278 y 370 ventanas de 8 notas del original de cuerda. Frente a 0,8 %
sobre modelado (D-41). El IC de LS-1 es por instancia y las instancias de un mismo par están
correlacionadas: es más estrecho de lo que correspondería a cuatro pares.

**Regla de lectura** (redactada **después** de medir LS-1 y LS-2 y antes de cualquier contacto con
el material objetivo; no figuraba en la especificación versionada antes de medir, `LS_spec.md`,
`a240875`, y así debe declararse en el paper y en OSF):

1. Con estos valores, un nulo del caso objetivo se lee como **«no se detecta en op. 67 cita literal
   de los fragmentos (≥ 8 notas consecutivas idénticas en una voz)»**; la potencia se midió en
   ventanas, no en compases (un compás orquestal tiene muchas más ventanas que uno de concierto de
   cuerda), así que se informa la potencia en L(A), con dos cautelas obligatorias: la sensibilidad es una **cota superior** (cambio de
   estrato y de instrumentación; arreglos completos y no citas aisladas) y su IC es por instancia.
   Si L(A) cae fuera del rango de longitudes medido en LS-2, la frase se acompaña de la potencia en
   la longitud más cercana y de esa salvedad.
2. Regla para una futura nueva medición de LS (propuesta de antemano solo para ese caso): si el límite superior de Wilson de LS-1 fuera < 5 %, el
   nulo sería no informativo; si no, potencia de LS-2 en L(A) ≥ 0,80 → lectura del punto 1;
   0,50–0,80 → «evidencia débil de ausencia de cita literal»; < 0,50 → «no informativo».
3. En ningún caso un nulo se lee como ausencia de modelado, alusión o influencia difusa (D-41:
   sensibilidad 0,8 % sobre modelado). La frase de D-41 «sensibilidad desconocida sobre cita literal»
   se sustituye por los valores de LS-1 y LS-2 con su IC.

## (d) Lo que no cambia

n = 8; λ = 0,45; t_DF y t_E de `results/thresholds_n8.json`; estrato 1750–1830; fondo jerárquico
(D-40) con la regla de exclusión de D-37 y DF de D-39/D-40b; dirección A → B (A = Cherubini,
anterior; B = op. 67 completa); estadístico K; R = 1000; semilla 20260903; Bonferroni sobre el
número de fragmentos (2); criterio de confirmación (al menos un fragmento con p corregido ≤ 0,05 y
al menos una ventana con DF ≤ t_DF y ritmo no uniforme); ranking por E solo para inspección. Los
archivos congelados (`scripts/{thresholds_n8,kn_background,lambda_by_n,background}.py`, parquet,
`results/**`) no se tocan.

**Aclaración (no es cambio):** D-41 escribe el término de compositor del fondo jerárquico como
«p_KN[obras de Cherubini sin la obra B]». D-39, D-40 y el código congelado (`Models.p_hier`) usan
las obras del **compositor de B** (Beethoven) en el estrato, sin la obra B. Rige el código
congelado. Solo afecta a E, que en el confirmatorio es un ranking informativo y no entra en la
decisión. Como op. 67 no está en las tablas de fondo, el término de compositor usa todas las obras
de Beethoven del estrato.

## (e) Análisis secundarios y huecos de diseño

**Secundarios declarados** (sin corrección; no deciden):

- n ∈ {6, 10}, como en D-41. **Hueco:** solo hay umbrales para n = 8. Antes de ejecutar hay que
  calcular t_DF(6) y t_DF(10) con el mismo procedimiento en un script nuevo (sin tocar
  `thresholds_n8.py`) y congelarlos; si no, n ∈ {6, 10} se informan solo de forma descriptiva.
  λ*(6) = λ*(10) = 0,45 ya está en `results/lambda_by_n.csv`.
- B por movimiento de op. 67: solo exploratorio.
- Piscinas alternativas de (b) y emparejamiento por duración.
- DF con un conjunto de exclusión común para A y A′ ({Beethoven} ∪ compositores de la piscina).

**Huecos encontrados:**

1. **Asimetría de la exclusión.** Para A se excluye solo a Beethoven (Cherubini no tiene obras en el
   estrato); para A′ de Mozart se excluye además a Mozart, una parte grande del estrato. Los tipos
   idiomáticos de Mozart obtienen DF menor en el nulo que en el observado: el nulo se infla y el test
   es conservador. Se mantiene la regla de D-37 como principal y la exclusión común queda como análisis secundario declarado: no puede ser principal porque t_DF se calibró con la regla congelada (exclusión de los compositores de A y B), y con otro conjunto de exclusión DF cambia de escala y el umbral dejaría de tener la tasa de falsos positivos medida.
2. **Solo 8 notas literales cuentan.** Con n = 8 la cita tiene que reproducir 8 notas seguidas de
   una voz (7 intervalos y 7 clases rítmicas). Una cita del motivo de 4 notas con continuación
   distinta es invisible. Lo que detecta el test es «cita literal de ≥ 8 notas», no «el motivo».
3. **Colapso de dobladas.** En A se calcula sobre el fragmento; en A′ sobre la caché, ya colapsada a
   nivel de movimiento. Una parte colapsada en el movimiento que en el fragmento no dobla se pierde en
   A′: A′ tiene menos tipos → nulo más bajo → test anticonservador. Por eso (b) propone reextraer.
   Al revés, sin colapso por fragmento A′ tendría más ventanas redundantes que A con el mismo número
   de tipos distintos.
4. **Silencios.** Todo silencio corta (`rest_break = 0`). En el coro, las respiraciones y silencios
   escritos cortan las líneas; se usa la misma regla en A y A′.
5. **Compases incompletos y bordes.** Anacrusa y compás final incompleto no afectan a las ventanas
   (no se usa métrica); las ventanas que cruzan el borde del fragmento no cuentan en A ni en A′. Una
   nota ligada desde antes del primer compás se codifica en A como nota; en A′ se excluyen los
   eventos con ataque anterior al primer compás. Diferencia menor, declarada.
6. **Transpositores.** Altura escrita o real, indiferente: todo es intra-voz (D-14), también el
   colapso de dobladas.
7. **Convenciones de codificación distintas** entre la transcripción y MuseData/kern (trémolos,
   adornos, divisi). Afectan sobre todo a tipos de notas repetidas o escalas, con DF alto, que no
   pasan t_DF. Se declaran.
8. **Errores de transcripción** solo pueden crear coincidencias con B por azar (el tipo erróneo
   tiene que estar en op. 67) o destruirlas; la doble codificación los acota.
9. **Coincidencias con DF ínfimo.** El back-off de DF para tipos no vistos puede dar valores
   minúsculos (saltos raros, notas de adorno); en los negativos de calibración aparecen. Las ventanas
   que pasan se listan con su contenido, para inspección, sin cambiar la decisión.
10. **Discreción del estadístico.** K es un entero pequeño con muchos empates en el nulo; con
    R = 1000 la resolución del p-valor es 0,001 y basta para α = 0,025.
11. **Guardia y catálogo.** Con las filas de Cherubini en `works.csv` (`is_target = 1`), la guardia
    aborta todo script nuevo; el script confirmatorio necesita una vía de excepción explícita, solo
    para A1, A2 y op. 67, probada con datos sintéticos.
12. **op. 67 no está en las tablas de fondo** (se construyeron sin obras objetivo): el término de
    compositor de E usa todas las obras de Beethoven del estrato (no hay que quitar B), y
    `Models.widx` no tiene índice para op. 67; el script confirmatorio debe tratarlo.
13. **Composición de la piscina.** Con 2 compositores, las 1000 réplicas no son independientes a
    nivel de obra; el nulo representa un idioma concreto. Se informa la composición de las réplicas.

## (f) Lo que falta antes de ejecutar

1. Rellenar los huecos de (a) (ediciones E1, E2 y C_total) sin mirar el contenido musical.
   **Cómo:** en IMSLP se elige la edición por los datos de catálogo (editor, año, tipo de partitura:
   partitura completa, no reducción) y se anota su identificador. Para C_total se abre solo la
   página final de la obertura en E2 y se lee el número impreso del último compás (o, si la edición
   no numera, se cuentan las barras de compás de la línea superior página a página, sin leer notas).
   E1 no requiere contar (compases 1–12). Los tres datos se escriben en D-43 y en el formulario de
   OSF **antes** de abrir la partitura para transcribir; si al transcribir se ve que el número era
   erróneo, se registra la corrección como desviación, sin mover el criterio.
2. Revisar y aprobar D-43 (usuario); versionar `decisions/D-43_*.md` y `decisions/D-43_null_pool.csv` (hoy `paper/D-43_null_pool.csv`).
3. Registrar D-41 + D-43 juntos en OSF, **con OK explícito del usuario y antes de empezar a
   transcribir**: la transcripción ya es contacto con los datos del caso objetivo.
4. Transcripción doble y cotejo según (a); versionar los MusicXML, su MD5 y `discrepancias.csv`.
5. LS-1 y LS-2: medidos (A3, `4c00ffa`); falta congelarlos en el mismo registro que D-43. Los
   cuatro Le Cène no estaban en la caché principal (son copias no primarias del catálogo; la copia
   primaria de RV 230/265/519/567 es la de Dawson) y A3 los extrajo a la caché del worktree.
6. Umbrales para n ∈ {6, 10} si se quieren como secundarios no descriptivos.
7. Script confirmatorio con tests sintéticos, en un commit congelado nuevo; ejecutar `tests/` en
   ese commit y anotar el hash en `docs/DECISIONES.md`.
8. Solo entonces, una única ejecución del caso objetivo.
