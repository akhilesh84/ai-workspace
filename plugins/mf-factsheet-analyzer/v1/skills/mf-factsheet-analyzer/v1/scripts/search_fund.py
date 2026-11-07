#!/usr/bin/env python3
"""
search_fund.py - Mutual Fund Search & Scheme Resolver
Searches mfapi.in for schemes by name or code, auto-selects 'Direct Plan - Growth',
and handles ambiguity with interactive selection or structured JSON output.
"""

import sys
import json
import urllib.request
import urllib.parse
import urllib.error
import argparse
import re
from typing import Dict, Any, List, Optional

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}


def fetch_json(url: str, timeout: int = 8) -> Optional[Any]:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"⚠️ Network error accessing {url}: {e}", file=sys.stderr)
        return None


def fetch_scheme_meta(scheme_code: int) -> Optional[Dict[str, Any]]:
    url = f"https://api.mfapi.in/mf/{scheme_code}"
    data = fetch_json(url)
    if data and "meta" in data:
        meta = data["meta"]
        return {
            "scheme_code": meta.get("scheme_code", scheme_code),
            "scheme_name": meta.get("scheme_name", ""),
            "fund_house": meta.get("fund_house", ""),
            "scheme_category": meta.get("scheme_category", ""),
            "scheme_type": meta.get("scheme_type", ""),
            "isin_growth": meta.get("isin_growth") or meta.get("isin_div_reinvestment") or "",
            "latest_nav": data.get("data", [{}])[0].get("nav") if data.get("data") else None,
            "latest_nav_date": data.get("data", [{}])[0].get("date") if data.get("data") else None
        }
    return None


def is_direct_growth(name: str) -> bool:
    nl = name.lower()
    has_direct = "direct" in nl or "dir " in nl or "dir." in nl
    has_growth = "growth" in nl or "gr" in nl
    # Avoid IDCW / Dividend
    has_idcw = "idcw" in nl or "dividend" in nl
    return has_direct and has_growth and not has_idcw


def search_schemes(query: str, auto_direct_growth: bool = True) -> Dict[str, Any]:
    clean_q = query.strip()
    
    # 1. If numeric scheme code passed
    if clean_q.isdigit():
        code = int(clean_q)
        meta = fetch_scheme_meta(code)
        if meta:
            return {
                "status": "RESOLVED",
                "selection_mode": "DIRECT_CODE",
                "selected": meta,
                "matches": [meta]
            }
        return {"status": "NOT_FOUND", "message": f"Scheme code {code} not found on mfapi.in"}

    # 2. Search via mfapi.in search endpoint
    encoded_q = urllib.parse.quote(clean_q)
    url = f"https://api.mfapi.in/mf/search?q={encoded_q}"
    results = fetch_json(url)

    if not results or not isinstance(results, list):
        return {"status": "NOT_FOUND", "message": f"No mutual fund schemes found matching '{query}'"}

    # Normalize result objects
    parsed_results = []
    for item in results:
        code = item.get("schemeCode")
        name = item.get("schemeName")
        if code and name:
            parsed_results.append({
                "scheme_code": int(code),
                "scheme_name": str(name)
            })

    if not parsed_results:
        return {"status": "NOT_FOUND", "message": f"No valid scheme records found for '{query}'"}

    # 3. Filter for Direct Plan - Growth if requested
    direct_growth_matches = [s for s in parsed_results if is_direct_growth(s["scheme_name"])]
    
    candidates = direct_growth_matches if direct_growth_matches else parsed_results

    # 4. Check for unambiguous exact/single match
    if len(candidates) == 1:
        chosen = candidates[0]
        meta = fetch_scheme_meta(chosen["scheme_code"])
        return {
            "status": "RESOLVED",
            "selection_mode": "AUTO_DIRECT_GROWTH" if direct_growth_matches else "SINGLE_MATCH",
            "selected": meta if meta else chosen,
            "matches": candidates
        }

    # If multiple candidates, check for an exact query match
    for cand in candidates:
        if clean_q.lower() == cand["scheme_name"].lower():
            meta = fetch_scheme_meta(cand["scheme_code"])
            return {
                "status": "RESOLVED",
                "selection_mode": "EXACT_NAME_MATCH",
                "selected": meta if meta else cand,
                "matches": candidates
            }

    # Multiple candidates found -> Ambiguity
    return {
        "status": "AMBIGUOUS",
        "query": clean_q,
        "total_matches": len(candidates),
        "matches": candidates[:10],
        "message": f"Found {len(candidates)} matching funds. Please choose an option."
    }


def main():
    parser = argparse.ArgumentParser(description="Search mutual funds on mfapi.in and select Direct Growth plan.")
    parser.add_argument("--query", "-q", type=str, required=True, help="Fund name or scheme code (e.g. 'parag parikh flexi' or '122639')")
    parser.add_argument("--all", action="store_true", help="Return all matches without Direct Growth filtering")
    parser.add_argument("--json", action="store_true", help="Output results strictly in JSON format")
    parser.add_argument("--select", type=int, help="Option index to select from candidate list (1-based)")
    args = parser.parse_args()

    result = search_schemes(args.query, auto_direct_growth=not args.all)

    # If ambiguous and user provided --select flag
    if result["status"] == "AMBIGUOUS" and args.select:
        matches = result.get("matches", [])
        idx = args.select - 1
        if 0 <= idx < len(matches):
            chosen = matches[idx]
            meta = fetch_scheme_meta(chosen["scheme_code"])
            result = {
                "status": "RESOLVED",
                "selection_mode": "MANUAL_USER_SELECTION",
                "selected": meta if meta else chosen,
                "matches": matches
            }
        else:
            print(f"❌ Invalid selection index {args.select}. Valid range: 1 to {len(matches)}", file=sys.stderr)
            sys.exit(1)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    # Formatted terminal output
    if result["status"] == "RESOLVED":
        sel = result["selected"]
        print(f"✅ Fund Identified Successfully:")
        print(f"   • Scheme Name : {sel.get('scheme_name')}")
        print(f"   • Scheme Code : {sel.get('scheme_code')}")
        print(f"   • Fund House  : {sel.get('fund_house', 'N/A')}")
        print(f"   • Category    : {sel.get('scheme_category', 'N/A')}")
        print(f"   • ISIN Growth : {sel.get('isin_growth', 'N/A')}")
        if sel.get("latest_nav"):
            print(f"   • Latest NAV  : ₹{sel['latest_nav']} (as of {sel.get('latest_nav_date', 'N/A')})")
    elif result["status"] == "AMBIGUOUS":
        print(f"⚠️ Ambiguous Search Query: '{result['query']}'")
        print(f"Found {result['total_matches']} matching funds. Please select an option:")
        for idx, m in enumerate(result["matches"], 1):
            print(f"   [{idx}] Scheme Code: {m['scheme_code']} | {m['scheme_name']}")
        print("\nPass --select <number> or provide the exact scheme code.")
    else:
        print(f"❌ {result.get('message', 'Search failed')}")
        sys.exit(1)


if __name__ == "__main__":
    main()

