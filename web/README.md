# Companion website — contract between W1 (data, page) and W2 (assets)

Static site, local preview only. No npm, no build, nothing deployed or published.
Libraries are loaded in the browser from `cdn.jsdelivr.net` with an exact pinned version.
Site language: English. Only aggregates are shown (no scores, caches, window interval
sequences or per-work rows: DCML is CC BY-NC-SA 4.0, decision D-12).
**The confirmatory case (Cherubini → Beethoven op. 67) has not been run.** Nothing on the
site may show or suggest a result for it.

## Files and ownership

| Path | Owner | Role |
|---|---|---|
| `web/index.html` | W1 | single page, sections and chart containers |
| `web/build_data.py` | W1 | writes `web/data/*.json` from versioned `results/**` |
| `web/data/*.json` | W1 (generated) | aggregates only |
| `web/assets/style.css` | W2 | styles |
| `web/assets/app.js` | W2 | ES module: number filling, charts, navigation behaviour |
| `web/assets/**` | W2 | anything else W2 needs |

Regenerate the data (from the repo root):

    /Users/cmorregof/Personal/Beethoven/.venv/bin/python web/build_data.py

Preview: `.claude/launch.json` → `python -m http.server 8765 --directory web`, then
`http://localhost:8765/`. JSON is loaded with `fetch("data/<name>.json")` (relative path).

## Page skeleton (`index.html`)

- `<link rel="stylesheet" href="assets/style.css">` and
  `<script type="module" src="assets/app.js"></script>`.
- Sections (`<section id=...>`), in order: `overview`, `question`, `method`, `corpus`,
  `chance`, `uniqueness`, `calibration`, `thresholds`, `protocol`, `reproducibility`,
  `licenses`. Navigation: `<nav id="site-nav">` with `<a href="#id">` links.
- Chart containers (empty `<div>`s, W2 renders into them). Each has `data-src` naming the JSON
  file it needs and a `<figcaption>` / fallback text written by W1:

| container id | section | data file | what to draw |
|---|---|---|---|
| `chart-corpus` | corpus | `corpus.json` | works and windows per period (bars); collections table optional |
| `chart-baserates` | chance | `base_rates.json` | D1–D5 rate per 100k windows by period |
| `chart-null` | chance | `observed_null.json` | D4 observed vs null mean with 95 % interval, by stratum |
| `chart-uniqueness` | uniqueness | `uniqueness.json` | P_cross(n) and P_pair(n), global and by period, IV and IVR |
| `chart-calibration` | calibration | `calibration.json` | observed vs predicted by bins of E (Laplace, KN, hierarchical) |
| `chart-lambda` | calibration | `lambda.json` | λ*(n) and log-likelihood profiles over the λ grid |
| `chart-rocpr` | thresholds | `thresholds.json` | ROC and PR curves (DF, E, DF→E), FPR = 5 % marker, prevalence line |
| `chart-literal` | thresholds | `literal.json` | literal-quotation sensitivity; **may be `status: "pending"`** → show a "not yet measured" note |

Each container keeps a text fallback inside it (W2 may replace it once the chart renders).

Other hooks used by app.js (agreed with W2's `assets/CONTRACT_NOTES.md`):
- `#method-content` (empty `<div>` at the end of `#method`): app.js injects `assets/content/method.html`.
- `#status-panel` (in `#protocol`, holds a static fallback list): app.js renders `status.json` into it.

## Numbers in the text: `data-num`

No result number is typed in the HTML. Every number is a placeholder:

    <span data-num="corpus_works">…</span>

`build_data.py` writes `web/data/numbers.json`, a flat object:

    { "generated_by": "...", "source": [...],
      "numbers": { "corpus_works": {"value": 1859, "text": "1,859", "source": "results/base_rate.json:strata.all.all.works"}, ... } }

`app.js` must, after `fetch("data/numbers.json")`, set `el.textContent = numbers[key].text` for
every `[data-num]` element, and if a key is missing write `[missing: key]` and add the class
`num-missing` (so gaps are visible, never silently blank). `text` is preformatted by
`build_data.py` (English thousands separators, fixed decimals), so app.js does no formatting.
Keys follow the paper's ledger prefixes: `corpus_`, `baserate_`, `null_`, `uniq_`, `calib_`,
`lambda_`, `thresh_`, `literal_`, plus `status_` for protocol status. The full key list is in
`numbers.json` itself; do not invent keys in app.js.

## Common fields of every JSON

    "source": ["results/...", ...]        # repo-relative paths read
    "generated_by": "web/build_data.py"
    "generated_at": "<ISO date>"           # informational only

Strings for periods use the repo labels: `"<1750"`, `"1750–1800"`, `"1800–1830"`,
`"1830–1900"`, `">1900"`, `"unknown"` (en dash). `period_order` lists them in display order.

## Schemas

### `corpus.json`
    totals: {units, works_catalog, works_missing_cache, works, windows, notes, collections}
    period_order: [str]
    by_period: [{period, units, works_catalog, works, windows, notes}]
    by_collection: [{collection, units, works_catalog, works, windows, notes, periods: [str], licenses: [str]}]
    windows_n: 4                                   # windows = 4-note windows (3 intervals)
`units` (movements / files) come from `corpus/works.csv` (in_analysis = 1, target and Cherubini
rows removed by the guard); `works`, `windows`, `notes` from `results/base_rate.json` strata.

### `base_rates.json`
    motifs: [{id: "D1".."D5", label}], window: "4 notes"   # nested motif definitions
    period_order: [str]
    by_period: [{period, works, windows, rate_per_100k: {D1..D5}, counts: {D1..D5},
                 prevalence_pct: {D1..D5}}]
    all: {same fields for the whole corpus}

### `observed_null.json`
    motif: "D4"  (also D2, D3 when present)
    n_perm: 1000, seed: 20260903, null: "within-voice shuffle"
    strata: [{stratum, kind: "all"|"period", works_perm, obs, null_mean, ci95: [lo, hi], ratio, p, n_perm}]
    other_motifs: {D2: [...same rows...], D3: [...]}

### `uniqueness.json`
    ns: [3..12], alphabet_labels, definitions: {p_cross, p_pair}, period_order
    alphabets: ["IV", "IVR"]                       # IV = intervals, IVR = intervals + rhythm class
    global: {IV: [{n, p_cross, p_pair, types, unique_types, tokens, works}], IVR: [...]}
    by_period: {IV: {period: [{n, p_cross, p_pair, ...}]}, IVR: {...}}
    works_by_period: {period: int}

### `calibration.json`
    lambda: 0.45, choice: "hier", stratum, n, design
    models: ["lap", "kn", "hier"]  labels: {lap, kn, hier}
    summary: {"<model>|todas": [slope, MAE_log, bias_log], "<model>|vistas": [...]}  # todas = all, vistas = seen
    summary_fields: ["slope", "mae_log", "bias_log"], summary_note      # 3 fields = 3 values per summary entry
    summary_named: {"<model>|todas": {slope, mae_log, bias_log}, ...}   # same values, named
    obs_pred_total: {lap, kn, hier}
    bin_by: "pred_occ_kn", bins_subset: "seen windows (obs_occ ≥ 1)"
    bins: [{lo, hi (null = open), k, obs_sum, obs_mean, pred_mean: {lap, kn, hier}, obs_pred: {lap, kn, hier}}]
    unseen: {k, obs: 0, pred_mean: {lap, kn, hier}}
    n_queries: int
Bin edges and counts are those of `results/kn_calibration.md` (checked by build_data.py).
No per-work or per-query rows are exported.

### `lambda.json`
    method
    by_n: [{n, lambda_star, slope, mae_log, bias_log, obs_pred, loglik_per_window, n_windows}]
    grid: {"<n>": [{lambda, loglik, slope, mae_log, bias_log, obs_pred}]}

### `thresholds.json`
    n: 8, lambda: 0.45, stratum: "1750-1830", prevalence
    n_instances: {pos, neg}
    pairs: {positives: [{id, A, B, basis}], negatives: [{id, A, B}]}   # human labels ("Composer, title"), no scores
    instance, rules: {DF, E, combined}
    DF: {threshold, FPR, sensitivity}, E: {...}, combined: {FPR, sensitivity}
    per_pair: {id: {shared_types, pass_DF, pass_E, pass_both}}
    curves: {"DF"|"E"|"DF→E": {AUC, AP, roc: [[fpr, tpr], ...], pr: [[recall, precision], ...]}}
Curves are recomputed from `results/thresholds_n8_windows.csv` with `roc()` of
`scripts/thresholds_n8.py`; AUC and AP are checked against `results/thresholds_n8.json`.

### `literal.json`
    status: "pending" | "measured"
    note: str
    -- when measured (from results/literal_sensitivity_n8.{json,csv}; aggregates only) --
    n, lambda, stratum, t_DF, t_E
    pairs: [{id: "L230"|..., work: "Vivaldi, RV 230", A, B, A_source, B_source}]   # A = Le Cène original, B = Dawson arrangement
    variants: {default: str, noBeethoven: str}
    LS1: {description, results: {default|noBeethoven: {global|L230|L265|L519|L567:
          {instances, DF: {k, n, rate, ci95: [lo, hi]}, E: {...}, combined: {...}, pass_DF_nonuniform}}}}
    LS2: {description, n_obs, n_null, alpha, seed, pool_works,
          results: {default|noBeethoven: {L230|...: [{length_bars, length_windows, power: {k, n, rate, ci95},
                                                     obs_mean, null_mean, null_q95}],
                                          all_pairs: [{length_bars, power: {k, n, rate, ci95}}]}}}
    caveats_en: [str]
`rate` and `ci95` are proportions (0–1); CIs are Wilson 95 %. build_data.py recomputes LS1 counts from the
CSV with the frozen thresholds and every Wilson interval with `wilson()` of `scripts/literal_sensitivity_n8.py`.
numbers.json keys: `literal_ls1_<default|nobeethoven>_<df|e|comb>[_lo|_hi]`, `literal_ls1_<v>_df_<l230..l567>`,
`literal_ls1_<v>_instances`, `literal_ls2_<v>_power_<10|15|20>bars[_lo]`, `literal_ls2_{n_obs,n_null,alpha,pool_works}`,
`literal_n_pairs`.

### `status.json`
    preregistration: {id: "D-41", file, frozen_commit, frozen_commit_short, frozen_date, registered}
    confirmatory_case: {hypothesis, executed: false, note}
    frozen_parameters: {n, lambda, stratum, n_null_pairs, seed, target_fpr, secondary_n}
    pending: [{item, state}]          # state starts with "done", "open" or "in progress"
                                      # includes literal sensitivity, D-43 (amendment) and OSF (registration),
                                      # Cherubini transcription and tests: app.js needs no EXTRA_PENDING text

### `numbers.json`
See above.

## Open requests for W2 (style.css)

1. **Mobile nav gutter.** `#site-nav` has no side padding: rule `header, main, footer { padding-inline: 16px; }`
   (style.css line ~110) does not include `nav`. Suggested fix: `header, nav, main, footer { padding-inline: 16px; }`
   and `#site-nav > ul { max-width: 72rem; margin-inline: auto; }`.
2. `index.html` now wraps the header content in `.site-header-inner` (already styled in style.css).
3. `calibration.json` already lists `models: ["lap", "kn", "hier"]`; `summary_named` added for convenience.
4. `literal.json` is now `status: "measured"` (schema above); `status.json.pending` carries D-43 and OSF.
