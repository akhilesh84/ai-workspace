#!/usr/bin/env python3
"""
fetch_factsheet.py - Multi-Tier Mutual Fund Factsheet & Disclosure Acquisition Engine
Coordinates retrieval across:
  Tier 1: Pre-indexed Curated 36-Month Store
  Tier 2: Live AMC Statutory Portal Scraper (.xlsx/.xls)
  Tier 3: Local User Directory/File Ingestion
  Tier 4: Live 36-Month Daily NAV Series from mfapi.in
"""

import sys
import os
import json
import urllib.request
import urllib.parse
import urllib.error
import re
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

from parse_portfolio import parse_xlsx_portfolio

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

CACHE_DIR = Path.home() / ".cache" / "mf-factsheets"


def load_amc_sources() -> Dict[str, Any]:
    sources_file = Path(__file__).resolve().parent.parent / "references" / "amc_sources.json"
    if sources_file.exists():
        try:
            with open(sources_file, "r", encoding="utf-8") as f:
                return json.load(f).get("amcs", {})
        except Exception:
            pass
    return {}


def check_tier1_store(scheme_code: int) -> Optional[Dict[str, Any]]:
    store_dir = Path(__file__).resolve().parent.parent / "references" / "historical_store"
    # Find matching file starting with scheme code
    matches = list(store_dir.glob(f"{scheme_code}*.json"))
    if matches:
        try:
            with open(matches[0], "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error reading local historical store: {e}", file=sys.stderr)
    return None


def fetch_live_nav_history(scheme_code: int) -> Dict[str, Any]:
    url = f"https://api.mfapi.in/mf/{scheme_code}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except Exception as e:
        print(f"⚠️ Could not fetch live NAV history for {scheme_code}: {e}", file=sys.stderr)
        return {}


def download_amc_disclosure(file_url: str, dest_path: Path) -> bool:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(file_url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            dest_path.write_bytes(resp.read())
            return True
    except Exception as e:
        print(f"⚠️ Failed to download {file_url}: {e}", file=sys.stderr)
        return False


def scrape_ppfas_disclosures(scheme_code: int, max_files: int = 36) -> List[Dict[str, Any]]:
    url = "https://amc.ppfas.com/downloads/portfolio-disclosure/"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"⚠️ Failed to access PPFAS disclosure portal: {e}", file=sys.stderr)
        return []

    # Map scheme code to prefix
    prefix = "PPFCF" if scheme_code == 122639 else "PPTSF"
    matches = re.findall(rf'href=[\"\'](/downloads/portfolio-disclosure/(\d{{4}})/({prefix}_[^\"\'\s]+\.xlsx?)[^\"\'\s]*)[\"\']', html, re.I)
    
    # Filter unique
    unique_files = {}
    for link, yr, fname in matches:
        if fname not in unique_files:
            unique_files[fname] = (link, yr)

    parsed_snapshots = []
    scheme_cache = CACHE_DIR / str(scheme_code)

    for fname, (link, yr) in list(unique_files.items())[:max_files]:
        if not fname.endswith(".xlsx"):
            # openpyxl handles xlsx; skip legacy xls binary if not convertible
            continue

        full_url = f"https://amc.ppfas.com{link}"
        cached_file = scheme_cache / fname
        if not cached_file.exists():
            print(f"📥 Downloading live disclosure: {fname}...", file=sys.stderr)
            success = download_amc_disclosure(full_url, cached_file)
            if not success:
                continue

        try:
            res = parse_xlsx_portfolio(cached_file)
            parsed_snapshots.append(res)
        except Exception as e:
            print(f"⚠️ Parsing failed for {fname}: {e}", file=sys.stderr)

    return parsed_snapshots


def acquire_factsheet_data(
    scheme_code: int,
    local_dir: Optional[str] = None,
    force_live: bool = False
) -> Dict[str, Any]:
    """
    Acquires 36-month portfolio and factsheet data for a scheme.
    """
    # 1. Check local directory if provided
    if local_dir:
        ld = Path(local_dir).resolve()
        if ld.exists() and ld.is_dir():
            xlsx_files = sorted(ld.glob("*.xlsx"))
            snapshots = []
            for f in xlsx_files:
                try:
                    snapshots.append(parse_xlsx_portfolio(f))
                except Exception as e:
                    print(f"⚠️ Error parsing {f.name}: {e}", file=sys.stderr)
            if snapshots:
                return {
                    "source": "LOCAL_USER_DIRECTORY",
                    "scheme_code": scheme_code,
                    "snapshots": snapshots,
                    "count": len(snapshots)
                }

    # 2. Check Tier 1 Curated Store (unless force_live is requested)
    if not force_live:
        t1 = check_tier1_store(scheme_code)
        if t1:
            # Also attach latest live NAV (up to ~5 years / 1300 trading days)
            nav_data = fetch_live_nav_history(scheme_code)
            if nav_data and "data" in nav_data:
                t1["live_nav_series"] = nav_data["data"][:1300]
                t1["source"] = "CURATED_HISTORICAL_STORE_WITH_LIVE_NAV"
            return t1

    # 3. Dynamic AMC Scraper (for supported AMCs like PPFAS)
    if scheme_code in [122639, 148885, 149842, 151838, 152285, 152744]:
        live_snapshots = scrape_ppfas_disclosures(scheme_code)
        nav_data = fetch_live_nav_history(scheme_code)
        if live_snapshots:
            return {
                "source": "AMC_STATUTORY_PORTAL_SCRAPE",
                "scheme_code": scheme_code,
                "monthly_snapshots": live_snapshots,
                "history_months_count": len(live_snapshots),
                "live_nav_series": nav_data.get("data", [])[:750]
            }

    # 4. Fallback: If no factsheet documents available, fetch NAV time series
    nav_data = fetch_live_nav_history(scheme_code)
    meta = nav_data.get("meta", {})
    return {
        "source": "NAV_SERIES_ONLY",
        "scheme_code": scheme_code,
        "scheme_name": meta.get("scheme_name", f"Scheme {scheme_code}"),
        "fund_house": meta.get("fund_house", "Unknown"),
        "scheme_category": meta.get("scheme_category", "Unknown"),
        "history_months_count": 0,
        "monthly_snapshots": [],
        "live_nav_series": nav_data.get("data", [])[:750]
    }


def main():
    parser = argparse.ArgumentParser(description="Acquire 36-month factsheet and portfolio disclosures.")
    parser.add_argument("--scheme-code", "-s", type=int, required=True, help="AMFI scheme code (e.g. 122639)")
    parser.add_argument("--local-dir", "-d", type=str, help="Local directory containing monthly portfolio .xlsx files")
    parser.add_argument("--force-live", action="store_true", help="Force live statutory scraping, bypassing local store")
    parser.add_argument("--json", action="store_true", help="Output raw acquired dataset as JSON")
    args = parser.parse_args()

    data = acquire_factsheet_data(args.scheme_code, local_dir=args.local_dir, force_live=args.force_live)

    if args.json:
        # Avoid dumping huge NAV array to stdout
        summary_copy = dict(data)
        if "live_nav_series" in summary_copy:
            summary_copy["live_nav_records_count"] = len(summary_copy["live_nav_series"])
            summary_copy["live_nav_series"] = summary_copy["live_nav_series"][:5]
        print(json.dumps(summary_copy, indent=2))
        return

    print(f"✅ Factsheet Acquisition Result:")
    print(f"   • Scheme Code : {data.get('scheme_code')}")
    print(f"   • Scheme Name : {data.get('scheme_name')}")
    print(f"   • Data Source : {data.get('source')}")
    print(f"   • Snapshots   : {data.get('history_months_count', len(data.get('monthly_snapshots', [])))} months acquired")
    if "live_nav_series" in data:
        print(f"   • NAV Records : {len(data['live_nav_series'])} daily historical records loaded")


if __name__ == "__main__":
    main()

