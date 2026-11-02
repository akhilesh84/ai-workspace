#!/usr/bin/env bash
# rebalance_cron.sh
# Headless script for executing energy basket rebalancing via OS crontab or command line.
#
# Crontab schedule (10:15 AM Monday to Friday):
# 15 10 * * 1-5 /Users/akhilesh/MyDevArea/ai-workspace/scripts/rebalance_cron.sh >> /tmp/energy_basket_rebalance.log 2>&1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${WORKSPACE_ROOT}"

# Run evaluation script with ₹50,000 budget
"${WORKSPACE_ROOT}/.venv/bin/python" -c "
import sys, json
sys.path.insert(0, '${WORKSPACE_ROOT}/mcp-servers/nifty-energy-basket/latest/src/server')
from tools.energy_basket import evaluate_energy_basket

result = evaluate_energy_basket(monthly_budget=50000.0)
print(json.dumps(result, indent=2))
"

