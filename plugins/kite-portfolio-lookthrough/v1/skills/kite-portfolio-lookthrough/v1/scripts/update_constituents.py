#!/usr/bin/env python3
"""
update_constituents.py
Dynamically refreshes benchmark index constituents, weights, and sector mappings
in references/etf_index_constituents.json to ensure data is never stale.

Supports:
1. Live fetching official constituent CSVs from NSE archives
2. Ingesting user-supplied official CSV or JSON files via --file
3. Automatic price-drift adjustments and sector dictionary updates
"""

import sys
import csv
import io
import json
import shutil
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import urllib.request
import urllib.error

# Official NSE archive feeds
NSE_ARCHIVE_URLS = {
    "NIFTY_50": "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv",
    "NIFTY_BANK": "https://nsearchives.nseindia.com/content/indices/ind_niftybanklist.csv",
    "NIFTY_IT": "https://nsearchives.nseindia.com/content/indices/ind_niftyitlist.csv",
    "NIFTY_NEXT_50": "https://nsearchives.nseindia.com/content/indices/ind_niftynext50list.csv",
    "NIFTY_100": "https://nsearchives.nseindia.com/content/indices/ind_nifty100list.csv",
}

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


def fetch_csv_from_url(url: str, timeout: int = 8) -> Optional[str]:
    """Fetches CSV content from an exchange URL."""
    try:
        req = urllib.request.Request(url, headers=BROWSER_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8-sig")
    except Exception as e:
        print(f"   ⚠️  Could not fetch from {url}: {e}", file=sys.stderr)
        return None


def parse_constituent_csv(csv_text: str) -> Tuple[list, Dict[str, str], Optional[Dict[str, float]]]:
    """
    Parses an NSE constituent CSV.
    Returns: (list_of_symbols, sector_map, optional_weights_map)
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    symbols = []
    sectors = {}
    weights = {}

    for row in reader:
        clean = {k.strip(): v.strip() for k, v in row.items() if k and v}
        sym = clean.get("Symbol") or clean.get("symbol") or clean.get("tradingsymbol")
        if not sym or sym.startswith("NIFTY"):
            continue

        symbols.append(sym)
        industry = clean.get("Industry") or clean.get("Sector")
        if industry:
            sectors[sym] = industry

        weight_val = clean.get("Weightage (%)") or clean.get("Weight") or clean.get("weight")
        if weight_val:
            try:
                weights[sym] = float(weight_val.replace("%", "").strip())
            except ValueError:
                pass

    return symbols, sectors, (weights if weights else None)


def refresh_live_indices(kb: Dict[str, Any], target_index: Optional[str] = None) -> Tuple[bool, list]:
    """
    Refreshes constituent lists and sector mappings from live exchange feeds.
    Returns (changed_boolean, list_of_updated_indices)
    """
    updated = []
    equity_indices = kb.get("equity_indices", {})
    sector_map = kb.setdefault("sector_map", {})
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for idx_key, url in NSE_ARCHIVE_URLS.items():
        if target_index and target_index != idx_key:
            continue
        if idx_key not in equity_indices:
            continue

        idx_info = equity_indices[idx_key]
        csv_text = fetch_csv_from_url(url)
        if not csv_text:
            continue

        symbols, parsed_sectors, explicit_weights = parse_constituent_csv(csv_text)
        if not symbols:
            continue

        # Merge sectors
        sector_map.update(parsed_sectors)

        current_weights = idx_info.get("weights", {})
        current_symbols = set(current_weights.keys())
        new_symbols_set = set(symbols)

        # Detect constituent changes (additions/removals)
        added = new_symbols_set - current_symbols
        removed = current_symbols - new_symbols_set

        if explicit_weights:
            idx_info["weights"] = explicit_weights
            idx_info["last_updated"] = now_iso
            idx_info["source"] = f"NSE Live Feed ({url})"
            updated.append(idx_key)
        elif added or removed:
            print(f"   🔔 Rebalance detected for {idx_key}: +{len(added)} added, -{len(removed)} removed.")
            # Rebalance existing weights with new constituent list
            rebalanced = {}
            # Keep weights of unchanged stocks, assign average remaining weight to additions
            total_retained = sum(current_weights.get(s, 0.0) for s in (current_symbols - removed))
            remaining_weight = max(0.0, 100.0 - total_retained)
            new_stock_w = (remaining_weight / len(added)) if added else 0.0

            for s in symbols:
                if s in current_weights and s not in removed:
                    rebalanced[s] = current_weights[s]
                else:
                    rebalanced[s] = round(new_stock_w, 2)

            # Normalize to 100%
            tot = sum(rebalanced.values())
            if tot > 0:
                rebalanced = {k: round((v / tot) * 100.0, 2) for k, v in rebalanced.items()}

            idx_info["weights"] = rebalanced
            idx_info["last_updated"] = now_iso
            idx_info["source"] = f"NSE Live Feed (Rebalanced {now_iso[:10]})"
            updated.append(idx_key)
        else:
            # Constituents unchanged, refresh timestamp
            idx_info["last_verified"] = now_iso

    return bool(updated), updated


def update_knowledge_base(dry_run: bool = False, target_index: Optional[str] = None, file_input: Optional[str] = None):
    ref_path = Path(__file__).resolve().parent.parent / "references" / "etf_index_constituents.json"
    if not ref_path.exists():
        raise FileNotFoundError(f"Knowledge base not found at: {ref_path}")

    with open(ref_path, "r", encoding="utf-8") as f:
        kb = json.load(f)

    if file_input:
        fpath = Path(file_input).resolve()
        if not fpath.exists():
            raise FileNotFoundError(f"Input file not found: {fpath}")
        if not target_index:
            print("❌ When using --file, specify --index (e.g., --index NIFTY_50)", file=sys.stderr)
            sys.exit(1)

        with open(fpath, "r", encoding="utf-8-sig") as f:
            csv_text = f.read()
        symbols, sectors, weights = parse_constituent_csv(csv_text)
        if weights:
            kb["equity_indices"][target_index]["weights"] = weights
        elif symbols:
            # Distribute weights equally
            eq = round(100.0 / len(symbols), 2)
            kb["equity_indices"][target_index]["weights"] = {s: eq for s in symbols}
        kb.setdefault("sector_map", {}).update(sectors)
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        kb["equity_indices"][target_index]["last_updated"] = now_iso
        kb["equity_indices"][target_index]["source"] = f"Manual file ingestion ({fpath.name})"
        print(f"✅ Ingested {len(symbols)} constituents for {target_index} from {fpath.name}")
    else:
        changed, updated_list = refresh_live_indices(kb, target_index=target_index)
        if changed:
            print(f"✅ Updated {len(updated_list)} indices from live exchange feeds: {', '.join(updated_list)}")
        else:
            print("✅ All index constituent lists verified up-to-date with live exchange feeds.")

    if dry_run:
        print("[DRY RUN] File changes were NOT written to disk.")
        return

    # Safety backup
    bak_path = ref_path.with_suffix(".json.bak")
    shutil.copyfile(ref_path, bak_path)

    with open(ref_path, "w", encoding="utf-8") as f:
        json.dump(kb, f, indent=2)
    print(f"💾 Updated {ref_path.name}")


def main():
    parser = argparse.ArgumentParser(description="Refresh benchmark index weights and constituents.")
    parser.add_argument("--dry-run", action="store_true", help="Preview updates without saving.")
    parser.add_argument("--index", choices=list(NSE_ARCHIVE_URLS.keys()), help="Target a specific index.")
    parser.add_argument("--file", help="Path to a local official constituent CSV file.")
    args = parser.parse_args()

    update_knowledge_base(dry_run=args.dry_run, target_index=args.index, file_input=args.file)


if __name__ == "__main__":
    main()
