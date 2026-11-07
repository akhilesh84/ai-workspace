#!/usr/bin/env python3
"""
resolve_scheme.py - Resilient Mutual Fund Scheme Resolver with Typo Tolerance
Resolves fund names or scheme codes into verified AMFI schemes on mfapi.in.
Auto-selects 'Direct Plan - Growth' and handles typos (e.g., 'HDFV midcap' -> 'HDFC Mid Cap').
"""

import sys
import json
import urllib.request
import urllib.parse
import urllib.error
import argparse
import re
from typing import Dict, Any, List, Optional, Tuple

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

KNOWN_AMCS = [
    "HDFC", "SBI", "ICICI", "Nippon", "Kotak", "Axis", "Quant", "UTI",
    "Tata", "DSP", "Mirae", "Motilal", "Parag Parikh", "PPFAS", "Bandhan",
    "Canara Robeco", "Edelweiss", "Invesco", "HSBC", "Sundaram", "Franklin"
]


def fetch_json(url: str, timeout: int = 8) -> Optional[Any]:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return None


def fetch_scheme_meta(scheme_code: int) -> Optional[Dict[str, Any]]:
    url = f"https://api.mfapi.in/mf/{scheme_code}"
    data = fetch_json(url)
    if data and "meta" in data:
        meta = data["meta"]
        latest_item = data.get("data", [{}])[0] if data.get("data") else {}
        return {
            "scheme_code": meta.get("scheme_code", scheme_code),
            "scheme_name": meta.get("scheme_name", ""),
            "fund_house": meta.get("fund_house", ""),
            "scheme_category": meta.get("scheme_category", ""),
            "scheme_type": meta.get("scheme_type", ""),
            "isin_growth": meta.get("isin_growth") or meta.get("isin_div_reinvestment") or "",
            "latest_nav": latest_item.get("nav"),
            "latest_nav_date": latest_item.get("date")
        }
    return None


def is_direct_growth(name: str) -> bool:
    nl = name.lower()
    has_direct = "direct" in nl or "dir " in nl or "dir." in nl
    has_growth = "growth" in nl or "gr" in nl
    has_idcw = "idcw" in nl or "dividend" in nl or "bonus" in nl
    return has_direct and has_growth and not has_idcw


def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            insert = prev[j + 1] + 1
            delete = curr[j] + 1
            sub = prev[j] + (0 if c1 == c2 else 1)
            curr.append(min(insert, delete, sub))
        prev = curr
    return prev[-1]


def correct_typos_in_query(query: str) -> Tuple[str, List[str]]:
    """
    Detects typos in query tokens against known AMCs and category keywords.
    E.g. 'HDFV' -> 'HDFC', 'flexicap' -> 'flexi cap', 'midcap' -> 'mid cap'.
    """
    tokens = query.strip().split()
    corrected_tokens = []
    corrections = []

    for t in tokens:
        clean_t = re.sub(r"[^\w]", "", t).strip()
        if not clean_t:
            continue
            
        # Check against known AMCs
        matched_amc = None
        for amc in KNOWN_AMCS:
            # If distance <= 1 for 4-letter words, or distance <= 2 for longer
            max_dist = 1 if len(clean_t) <= 4 else 2
            if levenshtein_distance(clean_t.upper(), amc.upper()) <= max_dist:
                matched_amc = amc
                break

        if matched_amc and matched_amc.upper() != clean_t.upper():
            corrected_tokens.append(matched_amc)
            corrections.append(f"'{t}' -> '{matched_amc}'")
        elif clean_t.lower() == "flexicap":
            corrected_tokens.append("flexi cap")
            corrections.append("'flexicap' -> 'flexi cap'")
        elif clean_t.lower() == "midcap":
            corrected_tokens.append("mid cap")
            corrections.append("'midcap' -> 'mid cap'")
        elif clean_t.lower() == "smallcap":
            corrected_tokens.append("small cap")
            corrections.append("'smallcap' -> 'small cap'")
        elif clean_t.lower() == "largecap":
            corrected_tokens.append("large cap")
            corrections.append("'largecap' -> 'large cap'")
        elif clean_t.lower() == "multicap":
            corrected_tokens.append("multi cap")
            corrections.append("'multicap' -> 'multi cap'")
        elif clean_t.lower() == "microcap":
            corrected_tokens.append("micro cap")
            corrections.append("'microcap' -> 'micro cap'")
        else:
            corrected_tokens.append(t)

    return " ".join(corrected_tokens), corrections


def search_api(q: str) -> List[Dict[str, Any]]:
    enc = urllib.parse.quote(q)
    url = f"https://api.mfapi.in/mf/search?q={enc}"
    results = fetch_json(url)
    if isinstance(results, list):
        return results
    return []


def score_candidate(candidate_name: str, query: str) -> float:
    base_cand = re.sub(r"\s*-\s*(Direct|Regular).*$", "", candidate_name, flags=re.I).strip()
    base_tokens = set(re.findall(r"\w+", base_cand.lower()))
    
    norm_q, _ = correct_typos_in_query(query)
    q_tokens = set(re.findall(r"\w+", norm_q.lower()))
    
    intersection = base_tokens.intersection(q_tokens)
    if not base_tokens or not q_tokens:
        return 0.0
        
    score = (len(intersection) / len(base_tokens.union(q_tokens))) * 100.0
    
    if q_tokens.issubset(base_tokens):
        score += 50.0
        
    if base_tokens == q_tokens:
        score += 100.0
        
    # Penalty if candidate has 'index', 'etf', 'fof' but query did not mention them
    for penalty_word in ["index", "etf", "fof"]:
        if penalty_word in base_tokens and penalty_word not in q_tokens:
            score -= 40.0
            
    return score


def resolve_fund(query: str, auto_direct_growth: bool = True) -> Dict[str, Any]:
    clean_q = query.strip()

    # 1. Direct scheme code passed
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

    corrected_q, corrections = correct_typos_in_query(clean_q)
    corrections_made = list(corrections)

    # 2. Gather results from raw and normalized queries
    results_map = {}
    queries_to_try = [corrected_q] if corrected_q != clean_q else []
    queries_to_try.append(clean_q)

    for q in queries_to_try:
        items = search_api(q)
        for it in items:
            code = it.get("schemeCode")
            if code and code not in results_map:
                results_map[code] = it

    # 3. If still empty, try individual category or AMC tokens
    if not results_map:
        tokens = [t for t in clean_q.split() if len(t) > 3]
        for t in tokens:
            sub_res = search_api(t)
            if sub_res:
                for it in sub_res:
                    code = it.get("schemeCode")
                    if code and code not in results_map:
                        results_map[code] = it
                corrections_made.append(f"Broadened query to token '{t}'")
                break

    if not results_map:
        return {
            "status": "NOT_FOUND",
            "query": clean_q,
            "message": f"No mutual fund schemes found matching '{clean_q}'"
        }

    # Normalize scheme list
    parsed = [{"scheme_code": int(x["schemeCode"]), "scheme_name": str(x["schemeName"])} for x in results_map.values() if "schemeCode" in x and "schemeName" in x]

    # Filter Direct Growth
    direct_growth = [s for s in parsed if is_direct_growth(s["scheme_name"])]
    candidates = direct_growth if (auto_direct_growth and direct_growth) else parsed

    # Sort candidates by relevance score
    candidates.sort(key=lambda c: score_candidate(c["scheme_name"], clean_q), reverse=True)

    # Check for single match
    if len(candidates) == 1:
        meta = fetch_scheme_meta(candidates[0]["scheme_code"])
        res = {
            "status": "RESOLVED",
            "selection_mode": "AUTO_DIRECT_GROWTH" if direct_growth else "SINGLE_MATCH",
            "selected": meta if meta else candidates[0],
            "matches": candidates
        }
        if corrections_made:
            res["typo_corrections"] = corrections_made
        return res

    # Check top candidate score
    top_score = score_candidate(candidates[0]["scheme_name"], clean_q)
    second_score = score_candidate(candidates[1]["scheme_name"], clean_q) if len(candidates) > 1 else -999.0

    if top_score >= 140.0 or (top_score >= 70.0 and (top_score - second_score) >= 35.0):
        meta = fetch_scheme_meta(candidates[0]["scheme_code"])
        res = {
            "status": "RESOLVED",
            "selection_mode": "AUTO_MATCH",
            "selected": meta if meta else candidates[0],
            "matches": candidates
        }
        if corrections_made:
            res["typo_corrections"] = corrections_made
        return res

    # Multiple candidates -> Ambiguous
    res = {
        "status": "AMBIGUOUS",
        "query": clean_q,
        "total_matches": len(candidates),
        "matches": candidates[:10],
        "message": f"Found {len(candidates)} matching funds. Please choose an option."
    }
    if corrections_made:
        res["typo_corrections"] = corrections_made
    return res


def main():
    parser = argparse.ArgumentParser(description="Resolve mutual fund schemes on mfapi.in with typo tolerance.")
    parser.add_argument("--query", "-q", type=str, required=True, help="Fund name or scheme code (e.g. 'HDFV midcap' or '118989')")
    parser.add_argument("--select", type=int, help="Option index to select from candidate list (1-based)")
    parser.add_argument("--all", action="store_true", help="Do not filter for Direct Growth plans")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    res = resolve_fund(args.query, auto_direct_growth=not args.all)

    if res["status"] == "AMBIGUOUS" and args.select:
        matches = res.get("matches", [])
        idx = args.select - 1
        if 0 <= idx < len(matches):
            chosen = matches[idx]
            meta = fetch_scheme_meta(chosen["scheme_code"])
            res = {
                "status": "RESOLVED",
                "selection_mode": "MANUAL_USER_SELECTION",
                "selected": meta if meta else chosen,
                "matches": matches
            }
            if "typo_corrections" in res:
                res["typo_corrections"] = res.get("typo_corrections", [])
        else:
            print(f"❌ Invalid selection index {args.select}. Valid range: 1 to {len(matches)}", file=sys.stderr)
            sys.exit(1)

    if args.json:
        print(json.dumps(res, indent=2))
        return

    if res["status"] == "RESOLVED":
        sel = res["selected"]
        print("✅ Fund Resolved Successfully:")
        if res.get("typo_corrections"):
            print(f"   ℹ️ Typo Correction : {', '.join(res['typo_corrections'])}")
        print(f"   • Scheme Name    : {sel.get('scheme_name')}")
        print(f"   • Scheme Code    : {sel.get('scheme_code')}")
        print(f"   • Fund House     : {sel.get('fund_house', 'N/A')}")
        print(f"   • Category       : {sel.get('scheme_category', 'N/A')}")
        print(f"   • Latest NAV     : ₹{sel.get('latest_nav')} ({sel.get('latest_nav_date')})")
    elif res["status"] == "AMBIGUOUS":
        if res.get("typo_corrections"):
            print(f"ℹ️ Typo Correction: {', '.join(res['typo_corrections'])}")
        print(f"⚠️ Ambiguous Search Query: '{res['query']}'")
        print(f"Found {res['total_matches']} matching funds. Please select an option:")
        for idx, m in enumerate(res["matches"], 1):
            print(f"   [{idx}] Scheme Code: {m['scheme_code']} | {m['scheme_name']}")
        print("\nPass --select <number> or provide the exact scheme code.")
    else:
        print(f"❌ {res.get('message', 'Resolution failed')}")
        sys.exit(1)


if __name__ == "__main__":
    main()

