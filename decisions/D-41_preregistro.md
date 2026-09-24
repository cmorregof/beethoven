# D-41 — Preregistro del caso confirmatorio (2026-09-21)

**Estado: el caso Cherubini → Beethoven op. 67 NO se ha ejecutado.** Ningún número de este
documento proviene de la Quinta ni de ninguna obra de Cherubini. El pipeline queda congelado
en el commit indicado abajo; cualquier cambio posterior a los umbrales, a λ o al modelo nulo
debe registrarse como nueva decisión antes de correr el caso objetivo.

## Hipótesis

H1: la Quinta de Beethoven (op. 67) comparte con las obras de Cherubini disponibles en el
corpus más ventanas de 8 notas de baja frecuencia documental (DF ≤ t_DF) de las que predice el
fondo jerárquico del estrato 1750-1830 sin Beethoven ni Cherubini.

## Commit congelado

- Código y decisiones: `c715141a6f3d805a6bd5a0afd38c841dd040c60f` (D-39/D-40), el commit D-42
  `160828deb43defe86395b787072904d6e5a69622` (memoria del fondo KN con resultados idénticos;
  introduce `scripts/lambda_by_n.py`) y el commit `D-41:` que introduce este documento,
  `scripts/thresholds_n8.py` y `tests/test_kn_background.py`. El hash del commit D-41 se anota en
  el mensaje de commit y en `docs/DECISIONES.md` (no puede escribirse dentro del propio commit).
- Tablas de fondo: `results/background_kn/meta.json` (semilla 20260903, órdenes 1..11).
- Corpus: `corpus/works.csv` con `is_target = 1` para la Quinta (D-21/D-31) y el cuarteto n.º 1
  de Cherubini (D-35); ambos fuera de todo fondo, calibración y umbral.

## Longitud de ventana y λ(n)

- n usado en el confirmatorio: **8** (7-grama de símbolos intervalo + clase rítmica, D-39).
- Análisis secundarios declarados: n ∈ {6, 10}. Cualquier otro n es exploratorio.
- λ(n) por interpolación borrada (D-39; 20 % de obras de reserva, semilla 20260903), regla de
  D-40 sobre la calibración leave-both-composers-out (200 ventanas del estrato 1750-1830):

| n | λ* (interpolación borrada) | log-verosimilitud por ventana en λ* | ventanas de reserva | pendiente en λ* | MAE log en λ* | sesgo log en λ* | obs/pred en λ* | λ de menor sesgo absoluto con pendiente en [0,9, 1,1] | MAE log en ese λ |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 0,50 | −9,2387 | 9000 | 1,0222 | 0,1096 | −0,0337 | 1,0311 | 1,00 | 0,1112 |
| 5 | 0,50 | −12,1674 | 9000 | 1,0433 | 0,2635 | −0,1468 | 1,0322 | 1,00 | 0,2836 |
| 6 | 0,45 | −14,7142 | 9000 | 1,0198 | 0,1979 | −0,1050 | 1,0418 | 0,00 | 0,2092 |
| 7 | 0,45 | −17,0797 | 9000 | 1,0188 | 0,2499 | −0,1736 | 1,0515 | 0,00 | 0,2606 |
| 8 | 0,45 | −19,9810 | 9000 | 1,0157 | 0,2342 | −0,1517 | 1,0496 | 0,00 | 0,2455 |
| 10 | 0,45 | −25,0260 | 8984 | 1,0067 | 0,0931 | −0,0555 | 1,0484 | 0,00 | 0,0951 |
| 12 | 0,45 | −29,3896 | 8948 | 1,0023 | 0,0588 | −0,0257 | 1,0530 | 1,00 | 0,0537 |

Fuente: `results/lambda_by_n.csv`, generado por `scripts/lambda_by_n.py`; rejilla completa por
(n, λ) en `results/lambda_by_n_grid.csv` y perfiles en `figures/lambda_profile_by_n.png`.

## Umbrales (fijados sin la Quinta, `results/thresholds_n8.json`, `figures/roc_pr_n8.png`)

Conjunto de calibración (`scripts/thresholds_n8.py`): positivos = tipos de ventana de 8 notas
compartidos entre A y B en los cuatro pares con préstamo/modelado documentado cuyas dos obras
están en el corpus (`controls_positive_candidates.csv`, P07–P10: Mozart K.464 → Beethoven
op. 18/5, Kerman 1967; Beethoven op. 132 y op. 95 → Mendelssohn op. 13, Todd 2003 / Krummacher
1978; Beethoven op. 74 → Mendelssohn op. 12, Todd 2003). Negativos = tipos compartidos en cuatro
pares sin relación documentada, cada uno con el mismo B, misma instrumentación (cuarteto de
cuerda) y A de la misma franja temporal (Haydn op. 64/5 → op. 18/5; Schubert D.804 y Arriaga
n.º 1 → Mendelssohn op. 13; Schubert D.810 → Mendelssohn op. 12). 360 instancias positivas y
273 negativas. Ningún par incluye Beethoven op. 67 ni Cherubini (el script aborta si aparecen).

| cantidad | umbral | regla | FPR en negativos | sensibilidad en positivos |
|---|---|---|---|---|
| DF | 1,82 × 10⁻⁴ | mayor DF con FPR ≤ 5 % | 4,8 % | 0,8 % (3/360) |
| E (jerárquico, λ = 0,45) | 4,09 × 10⁻⁴ | percentil 5 de E en el nulo estratificado (= percentil 95 de −log E) | 5,1 % | 1,1 % (4/360) |
| DF y E | ambos | presencia por DF, después ranking por E | 4,8 % | 0,8 % |

AUC: DF 0,47; E 0,46; DF→E 0,48. Precisión media ≈ prevalencia (0,57).

**Lectura, que forma parte del preregistro:** con los positivos disponibles (cuatro casos de
*modelado* formal y temático, no de cita literal), las ventanas de 8 notas compartidas no se
distinguen de las compartidas por azar entre cuartetos de la misma franja: los umbrales
controlan el FPR como se pidió, pero la sensibilidad es ≈ 1 %. Esto significa que **un
resultado nulo en el caso objetivo no será informativo** sobre el modelado en sentido amplio;
solo un exceso de ventanas con DF ≤ t_DF sería evidencia. La sensibilidad del método frente a
préstamo literal (arreglos, sujetos de fuga: P01–P06, P11, P14) no se ha medido porque esas obras
no están codificadas; queda como requisito previo (véase «Pendiente»).

## Modelo nulo y estrato de comparación

- Fondo: jerárquico (D-40), p_q = λ·p_KN[obras de Cherubini sin la obra B](q) + (1 − λ)·p_KN[estrato
  1750-1830 sin Beethoven ni Cherubini](q); E = ventanas_B · p_q; Laplace (D-37) solo como cota
  superior. DF_q = fracción de obras del estrato sin Beethoven ni Cherubini que contienen q;
  para tipos no vistos, back-off KN documental acotado por 1/(N_obras + 1) (D-40b).
- Estrato de comparación: 1750-1830 (unión de los bins 1750–1800 y 1800–1830), obras primarias,
  sin obras objetivo.
- Dirección: A = obra de Cherubini (anterior), B = op. 67. Se evalúan todas las obras de
  Cherubini presentes en el corpus con fecha anterior a 1808; no se elige ninguna a posteriori.
- Estadístico confirmatorio: número de tipos de ventana de 8 notas de A presentes en B con
  DF ≤ t_DF, comparado con su distribución bajo el nulo: 1000 pares (A', B') con A' obra de otro
  compositor del estrato con la misma instrumentación que A y B' = op. 67 (mismo B, como en la
  calibración de umbrales), semilla 20260903. p-valor = fracción de pares nulos con recuento ≥ al
  observado; se corrige por Bonferroni sobre el número de obras de Cherubini evaluadas.
- Ranking de las ventanas que pasan DF por E (menor primero) solo para inspección; no entra en
  la decisión.

## Confirmación y refutación

- **Confirmación:** al menos una obra de Cherubini con p corregido ≤ 0,05 y al menos una ventana
  con DF ≤ t_DF y ritmo no uniforme (D-38: los candidatos de ritmo uniforme son fórmulas de
  acompañamiento).
- **Refutación de H1 en el sentido fuerte (cita literal):** ninguna obra con p corregido ≤ 0,05.
  Por la lectura anterior, esto no refuta el modelado difuso; se declarará como «no detectado
  con sensibilidad ≈ 1 % sobre modelado y sensibilidad desconocida sobre cita literal».
- No se moverán umbrales, n, λ ni estrato después de ver el caso objetivo.

## Limitaciones ya anotadas

- D-39: el término de compositor solo captura el idioma propio de B; no detecta influencia
  difusa de época o de escuela compartida por A y B, que el término de estrato absorbe como azar.
- D-38/D-40: tramo E < 3 sobrepredicho (conservador); tipos no vistos con E ≈ 0,04.
- Positivos escasos (4 pares, todos de modelado) y negativos elegidos por juicio del autor
  (sin relación documentada conocida), no por muestreo.
- La instancia de calibración es el tipo compartido, no el par: un par aporta muchas instancias
  correlacionadas, así que el FPR del 5 % es por ventana, no por par.

## Pendiente antes de correr el caso objetivo

1. Codificar al menos los positivos de cita literal P05 (Corelli op. 3/4 → BWV 579) y P14
   (Clementi op. 24/2 → Zauberflöte) o los arreglos P01–P04, y medir la sensibilidad de
   DF ≤ t_DF sobre ellos; sin esa medida el resultado del caso objetivo no tiene lectura.
2. Confirmar la lista de obras de Cherubini anteriores a 1808 presentes en el corpus (sin
   mirar sus ventanas).
3. Ejecutar la suite `tests/` en el commit congelado.
