
## α = 1 (Laplace)

- pseudocuenta α = 1 (Laplace); N1/N (tipos únicos) = 0.291
- ventanas 200, obras B por ventana ≈ 247; ventanas cuyo tipo no aparece fuera de su compositor: 118
-   de esas 118: predicho 120.4 ocurrencias, observado 0 (por construcción 0)
- ocurrencias: predicho total 480697.4, observado 774792, ratio obs/pred 1.61
- obras con q: predicho total 7056.0, observado 4436, ratio 0.63
- ventanas con E_occ < 0.5: 0 (observadas 0 ocurrencias, predichas 0.0)
- correlación log(pred+0.05) vs log(obs+0.05): 0.970
- deciles (pred → obs): 0.96→0.00; 0.98→0.00; 0.98→0.00; 1.06→0.00; 1.08→0.00; 1.12→0.10; 3.31→3.55; 16.75→24.55; 216.82→331.80; 23791.81→38379.60

## α = 0.9609 (Good–Turing)_gt

- pseudocuenta α = 0.9609 (Good–Turing); N1/N (tipos únicos) = 0.291
- ventanas 200, obras B por ventana ≈ 247; ventanas cuyo tipo no aparece fuera de su compositor: 118
-   de esas 118: predicho 117.2 ocurrencias, observado 0 (por construcción 0)
- ocurrencias: predicho total 486723.1, observado 774792, ratio obs/pred 1.59
- obras con q: predicho total 7071.8, observado 4436, ratio 0.63
- ventanas con E_occ < 0.5: 0 (observadas 0 ocurrencias, predichas 0.0)
- correlación log(pred+0.05) vs log(obs+0.05): 0.971
- deciles (pred → obs): 0.93→0.00; 0.95→0.00; 0.95→0.00; 1.03→0.00; 1.05→0.00; 1.09→0.10; 3.32→3.55; 16.91→24.55; 219.52→331.80; 24090.40→38379.60

## Lectura (2026-09-09)

- **Tramo medio (E predicho 3–300 ocurrencias, 45 de las 82 ventanas vistas fuera de su compositor):** los puntos siguen la diagonal con sesgo obs/pred 1,3–1,5×; correlación log-log 0,97. El fondo ordena bien.
- **Tramo bajo (118 de 200 ventanas: el tipo no aparece en ningún otro compositor):** el modelo predice ≈1 ocurrencia en el resto del estrato y se observan 0. No es un problema de pseudocuenta (Good–Turing da α = 0,96, casi Laplace, porque el 29 % de las ventanas son tipos únicos): Laplace reparte la masa «no visto» entre V+1 cajones, pero el número de 8-gramas posibles es órdenes de magnitud mayor que V, así que p_q para un tipo concreto no visto está **sobreestimada** → E-values demasiado grandes → **conservador** para tipos raros (menos potencia, no más falsos positivos).
- **Tramo alto (fórmulas: notas repetidas, trémolos de octava, batidos de tercera):** obs/pred 1,5–1,6× de forma sistemática. La exclusión del compositor de B rebaja p_q justo para las B cuyo compositor abunda en esa fórmula (Beethoven, Haydn), y luego esas B la contienen. Es **anticonservador** para n-gramas formularios: el E-value los declara más raros de lo que son. Además, las ocurrencias se concentran en pocas obras (obras con q: obs/pred 0,63), así que 1 − e^{−E} sobreestima la presencia.
- Consecuencias para el preregistro: (1) restringir los candidatos a ventanas con estructura rítmica no uniforme (D3/D4 ya lo hacen) o excluir los tipos con p_q > 10⁻³ del estrato; (2) para tipos no vistos tratar el E-value como cota superior; (3) considerar un fondo mixto estrato + compositor de B (jerárquico) si hace falta corregir el tramo alto.
