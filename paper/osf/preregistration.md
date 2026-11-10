# OSF Preregistration — borrador para registrar D-41 + D-43 (NO REGISTRADO)

Preparado por A1 el 2026-11-09/10. **Nada de esto se ha subido ni registrado.** Lo registra el
usuario, en un único registro, cuando haya aprobado D-43 y **antes de empezar a transcribir** los
fragmentos de Cherubini. El formulario sigue la plantilla estándar «OSF Preregistration»; el
contenido va en inglés porque el registro es público. Los `[HUECO: …]` los rellena el usuario.

---

## Checklist de 10 minutos (usuario)

**Cómo fijar E1, E2 y C_total sin leer la música.** En IMSLP elige cada edición por sus datos de
catálogo (editor, año, partitura completa y no reducción) y anota su identificador. Para C_total
abre solo la última página de la obertura de *Eliza* en E2 y lee el número impreso del último compás;
si la edición no numera, cuenta las barras de compás de la línea superior página a página sin leer
notas. E1 no requiere contar (compases 1–12). Escribe los tres datos en D-43 y en este formulario
**antes** de abrir la partitura para transcribir; un error detectado después se registra como
desviación, sin cambiar la regla.

1. [ ] D-43 aprobada; rellenados en D-43 (a) los huecos E1, E2 y C_total **mirando solo portada,
       catálogo y número del último compás**; `decisions/D-43_*.md` y
       `decisions/D-43_null_pool.csv` versionados por la torre en la rama de trabajo.
2. [ ] Anotar los hashes completos de los commits de la tabla de adjuntos
       (`git rev-parse <corto>`), incluido el commit que versiona D-43.
3. [ ] Generar el PDF de D-43 (como el de D-41) y comprobar que D-41 PDF corresponde al commit
       `6c44aa9`.
4. [ ] En osf.io: *Create new project* (privado) → *Registrations* → *New registration* →
       plantilla **OSF Preregistration**.
5. [ ] Copiar cada sección de abajo en su campo (las cabeceras coinciden con la plantilla).
6. [ ] Adjuntar los archivos de la tabla «Attachments».
7. [ ] Elegir embargo (recomendado: sin embargo o hasta la publicación) y registrar.
8. [ ] Copiar el DOI del registro a `paper/OPEN_ITEMS.md` y pedir a la torre que sustituya
       `\tbd{OSF DOI}` en `paper/sections/protocol.tex`.
9. [ ] Solo después: empezar la transcripción doble (D-43 a).

---

## Study information

**Title.** A calibrated test for literal inter-composer borrowing: pre-specified application to
the Cherubini → Beethoven Op. 67 hypothesis.

**Authors.** [HUECO: autor(es) y afiliación].

**Description.** We built a statistical framework to decide whether a coincidence of short melodic
windows between two works exceeds what a stratified corpus background predicts: 8-note windows
represented by interval and rhythm-ratio class, a Kneser–Ney background of the 1750–1830 stratum
excluding the composers of both works, a document frequency (DF) of each window type, and decision
thresholds fixed on control pairs. The framework was frozen in commit `6c44aa9` (decision D-41)
before any contact with the target material, and amended by D-43 because no pre-1808 Cherubini work
exists in the corpus and the original null did not match fragment length. This registration covers
one confirmatory application: whether Beethoven's Fifth Symphony, Op. 67, shares with two 1794
passages by Cherubini (opening of the *Hymne au Panthéon*; coda of the overture to *Eliza*) more
rare 8-note windows than length-matched passages by other composers of the period.

**Hypotheses.** H1: for at least one of the two Cherubini fragments A, the number K(A, B) of
8-note window types of A present in B = Op. 67 with DF ≤ t_DF exceeds its distribution under a
length-matched null, at Bonferroni-corrected α = 0.05 (0.025 per fragment). Directional (excess).

## Design plan

**Study type.** Observational study on symbolic music data (no human participants).

**Blinding.** No analysis has computed any window of Op. 67 or of any Cherubini work. Op. 67 and the
only catalogued Cherubini work (String Quartet No. 1, 1814) are flagged as targets and excluded from
every background, calibration and threshold; every new script aborts if they are requested
(`scripts/preregistration_guard.py`). The Cherubini fragments do not exist yet in symbolic form.

**Study design.** One test per fragment: observed K(A, B) against R = 1000 null replicates
K(A′, B), with A′ a contiguous span of whole bars, all parts, of a movement by another composer of
the 1750–1830 stratum (neither Beethoven nor Cherubini) of the same instrumentation class, whose
number of 8-note windows is within ±5 % of that of A. B = Op. 67 (all movements) in every replicate.

**Randomization.** Null start bars drawn uniformly over the eligible bars of a fixed list of works
(`D-43_null_pool.csv`); generator `numpy.random.default_rng([20260903, k])`, k = 1 (*Hymne*),
k = 2 (*Eliza*).

## Sampling plan

**Existing data.** Registration prior to creation of data for A (the two fragments will be
transcribed after registration) and prior to analysis of the data for B (Op. 67 is in the corpus
but has never been analysed). The comparison works and the background were analysed for calibration
before D-41 was frozen.

**Explanation of existing data.** Calibration used only non-target works (results in
`results/kn_calibration.*`, `results/lambda_by_n.csv`, `results/thresholds_n8.json`). The
literal-quotation controls (Vivaldi Op. 3 in the Le Cène print vs the *Anne Dawson's Book*
keyboard arrangements) were measured after their specification was committed (`a240875`, results
`4c00ffa`), without target data.

**Data collection procedures.** A1 = bars 1–12 of the *Hymne au Panthéon* in edition
[HUECO: E1]; A2 = the last 20 bars of the overture to *Eliza* in edition [HUECO: E2], bars
[HUECO: C_total − 19]–[HUECO: C_total]; all parts. Boundaries fixed by these objective rules
before transcription. Each fragment is encoded twice independently in MusicXML (rules in
`corpus/raw/cherubini/README.md`), compared note by note by a script, and discrepancies resolved
against the source and logged in `corpus/raw/cherubini/discrepancias.csv`. Extraction with the
frozen pipeline (`scripts/extract.py`: top note of chords, ties merged, rests break sequences,
doubled parts collapsed).

**Sample size.** Two fragments; R = 1000 null replicates each; null pool of 20 orchestral works
(Mozart 14, Haydn 6) for *Eliza*, and 28 works with orchestra (adding 7 Mozart concertos and one
opera) for the *Hymne*, for which no work for chorus and orchestra exists in the stratum.

**Sample size rationale.** The sources are those named by the historical hypothesis. Power was
measured on literal controls: LS-2 power at α = 0.025 was 0.978, 0.996 and 1.000 for fragments of
10, 15 and 20 bars of a string concerto (185, 278 and 370 eight-note windows) (upper bounds; see Inference criteria).

**Stopping rule.** Single run after the frozen confirmatory script passes its synthetic tests at a
new frozen commit.

## Variables

**Manipulated variables.** None.

**Measured variables.** For each fragment: the set of 8-note window types (7 symbols of interval
in semitones and rhythm class of the duration ratio, thresholds 0.4/0.9/1.1/2.5), its number of
windows L(A), and for each type shared with B its DF in the 1750–1830 stratum without the composers
of A and B, and its E-value under the hierarchical background (λ = 0.45).

**Indices.** K(A, B) = |{q shared by A and B : DF(q) ≤ t_DF}|, t_DF = 1.82 × 10⁻⁴ (frozen,
`results/thresholds_n8.json`).

## Analysis plan

**Statistical models.** Monte Carlo test: p = (1/R)·#{r : K(A′_r, B) ≥ K(A, B)} (also reported as
(1 + #)/(1 + R)). E-values rank the passing windows for inspection only.

**Transformations.** None beyond the frozen representation.

**Inference criteria.** Confirmation: at least one fragment with p ≤ 0.025 **and** at least one
passing window with non-uniform rhythm. Otherwise not confirmed. Reading of a null result (written after the literal-quotation controls were measured and before
any contact with the target material; it was not part of the specification committed before that
measurement): literal-quotation sensitivity measured on the controls was 0.525 per shared type (Wilson
95 % CI 0.510–0.541; 3,847 instances) against 0.008 on documented modelling, so a null reads as
"no literal quotation of the fragments (a run of ≥ 8 notes in one part with the same intervals and
duration ratios, at any transposition) detected in
Op. 67" (power was measured at 185–370 windows; the power at each fragment's own window count is
reported), stated with two caveats: the controls are keyboard arrangements from
before 1750, so the sensitivity is an upper bound; and the interval is per instance, with correlated
instances. A null says nothing about modelling, allusion or diffuse influence.

**Data exclusion.** Primary copies only; units that fail to parse are excluded and logged; target
works excluded from all background quantities.

**Missing data.** If one fragment cannot be encoded from its fixed source, the test is run on the
other at α = 0.025.

**Exploratory analyses.** n ∈ {6, 10} (descriptive unless thresholds are fixed with the same
procedure before the run); B by movement; duration-matched null; composer-balanced and
all-instrumentation pools; common exclusion set for A and A′; *Hymne* without chorus parts.

## Other

Frozen elements: n = 8, λ = 0.45, t_DF, t_E, stratum, background, exclusion rule, direction,
statistic, R, seed. Clarification registered with D-43: the composer term of the hierarchical
background is that of B's composer, as in the frozen code (the text of D-41 names Cherubini); it
affects only the E ranking.

---

## Attachments

| archivo | identificador |
|---|---|
| `decisions/D-41_preregistro.pdf` (y `.md`) | commit D-41 `6c44aa98ed32ee691cc4140aec684414ef5691ba` |
| D-43 aprobada (`decisions/D-43_*.md` y PDF) | `[HUECO: commit que versiona D-43]` |
| `decisions/D-43_null_pool.csv` | mismo commit que D-43 |
| Código y decisiones D-39/D-40 | `c715141a6f3d805a6bd5a0afd38c841dd040c60f` |
| D-42 (memoria del fondo KN, resultados idénticos) | `160828deb43defe86395b787072904d6e5a69622` |
| Hash de D-41 anotado en `docs/DECISIONES.md` | `87bfa5d` `[HUECO: hash completo]` |
| Especificación LS (`paper/research/LS_spec.md`) | `a240875` `[HUECO: hash completo]` |
| Resultados LS (`results/literal_sensitivity_n8.json`) | `4c00ffa` `[HUECO: hash completo]` |
| `results/thresholds_n8.json` | presente en el commit D-41 (`6c44aa9`) |
| `results/lambda_by_n.csv` | presente en el commit D-41 (`6c44aa9`) |
| Script confirmatorio y tests sintéticos | `[HUECO: commit congelado nuevo]` |
| Hashes MD5 de los MusicXML de Cherubini | se añaden en una actualización posterior al registro (no forman parte de este) |
