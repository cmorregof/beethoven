#!/bin/zsh
# Calibración por n (D-41, punto 1); reejecutable: salta los n ya cacheados.
# UN solo proceso: Tables se carga una vez y se comparte entre los n (~2-3 GB en total).
cd "$(dirname "$0")/.."
mkdir -p results/lambda_by_n/logs
.venv/bin/python -u scripts/lambda_by_n.py 4 5 6 7 8 10 12 --only-cache > results/lambda_by_n/logs/cache.log 2>&1
.venv/bin/python scripts/lambda_by_n.py > results/lambda_by_n/logs/summary.log 2>&1
echo "LAMBDA_BY_N_DONE"
