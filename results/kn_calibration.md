# Calibración de los tres fondos (D-40)

Estrato 1750-1830, n = 8, 200 ventanas muestreadas uniformemente sobre ventanas, leave-both-composers-out; λ = 0.45. Métricas sobre log(x + 0,05): pendiente OLS de log(obs) sobre log(pred), sesgo absoluto medio |log obs − log pred| (MAE), sesgo medio (log obs − log pred). «vistas» = ventanas con ≥ 1 ocurrencia en otro compositor.

| modelo | conjunto | n | pendiente | MAE log | sesgo log | obs/pred total |
|---|---|---|---|---|---|---|
| Laplace (cota superior) | todas | 200 | 1.422 | 1.963 | -1.696 | 1.61 |
| Laplace (cota superior) | vistas | 82 | 1.057 | 0.380 | +0.270 | 1.61 |
| Kneser-Ney | todas | 200 | 1.018 | 0.246 | -0.138 | 1.10 |
| Kneser-Ney | vistas | 82 | 0.977 | 0.171 | +0.091 | 1.10 |
| jerárquico | todas | 200 | 1.016 | 0.234 | -0.152 | 1.05 |
| jerárquico | vistas | 82 | 0.975 | 0.137 | +0.065 | 1.05 |

## obs/pred por tramo de E predicho (KN), ocurrencias, ventanas vistas

| tramo E (KN) | n | Laplace | KN | jerárquico |
|---|---|---|---|---|
| [0, 1) | 5 | 0.58 | 2.45 | 2.55 |
| [1, 3) | 9 | 1.00 | 1.19 | 1.12 |
| [3, 30) | 23 | 1.36 | 1.00 | 0.98 |
| [30, 300) | 16 | 1.50 | 0.99 | 0.98 |
| [300, 3000) | 15 | 1.48 | 0.99 | 0.97 |
| [3000, 1e+12) | 14 | 1.62 | 1.10 | 1.05 |

Ventanas no vistas en otro compositor: 118 (observado 0); E predicho medio: Laplace 1.021, KN 0.043, jerárquico 0.043.

## DF: presencia en B (pares ventana × obra B)

pares 49,362; presencia observada 0.0899; DF media 0.0875; 1−e^(−E) KN medio 0.1538; jerárquico 0.1539

| bin DF predicho | pares | DF medio | presencia observada | 1−e^(−E) KN | 1−e^(−E) hier |
|---|---|---|---|---|---|
| [0, 0.0001) | 24,271 | 0.0000 | 0.0004 | 0.0000 | 0.0003 |
| [0.0001, 0.001) | 4,249 | 0.0004 | 0.0026 | 0.0005 | 0.0035 |
| [0.001, 0.01) | 5,792 | 0.0048 | 0.0050 | 0.0115 | 0.0117 |
| [0.01, 0.05) | 3,882 | 0.0259 | 0.0307 | 0.0724 | 0.0715 |
| [0.05, 0.1) | 2,195 | 0.0703 | 0.0679 | 0.1612 | 0.1671 |
| [0.1, 0.2) | 1,637 | 0.1527 | 0.1863 | 0.4314 | 0.4376 |
| [0.2, 0.5) | 3,406 | 0.3166 | 0.3053 | 0.7119 | 0.7011 |
| [0.5, 1.01) | 3,930 | 0.6888 | 0.7059 | 0.9557 | 0.9568 |

A nivel de ventana (número de obras B que contienen q): DF pendiente 1.021, MAE log 0.192, sesgo -0.159; total predicho 4319.7 vs observado 4436.

## Regla de selección (D-40)

Menor MAE en log entre los modelos con pendiente en [0,9, 1,1] sobre las 200 ventanas → **hier**.
