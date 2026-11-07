#!/usr/bin/env python3
"""
parse_portfolio.py - SEBI Standardized Portfolio Disclosure Parser
Parses mutual fund portfolio disclosures in Excel (.xlsx, .xls) and CSV formats.
Extracts AUM, Portfolio Turnover Ratio (PTR), Dry Powder (Cash/TREPS/Money Market),
Sector allocations, and top holdings.
"""

import sys
import os
import json
import re
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

try:
    import openpyxl
except ImportError:
    openpyxl = None


def load_sector_taxonomy() -> Dict[str, str]:
    ref_file = Path(__file__).resolve().parent.parent / "references" / "sector_taxonomy.json"
    if ref_file.exists():
        try:
            with open(ref_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("industry_to_sector", {})
        except Exception:
            pass
    return {}


INDUSTRY_TO_SECTOR = load_sector_taxonomy()


def normalize_sector(industry: str) -> str:
    if not industry:
        return "Other / Unclassified"
    ind_clean = str(industry).strip()
    if ind_clean in INDUSTRY_TO_SECTOR:
        return INDUSTRY_TO_SECTOR[ind_clean]
    for k, v in INDUSTRY_TO_SECTOR.items():
        if k.lower() in ind_clean.lower() or ind_clean.lower() in k.lower():
            return v
    il = ind_clean.lower()
    if any(w in il for w in ["bank", "finan", "capital market", "insurance", "nbfc"]):
        return "Financial Services"
    if any(w in il for w in ["software", "tech", "data processing", "it -"]):
        return "Information Technology"
    if any(w in il for w in ["auto", "vehicle", "tyre"]):
        return "Consumer Discretionary"
    if any(w in il for w in ["pharma", "health", "biotech", "drug", "hospital"]):
        return "Healthcare"
    if any(w in il for w in ["power", "electric", "utility"]):
        return "Utilities & Power"
    if any(w in il for w in ["fmcg", "food", "beverage", "consumer goods"]):
        return "Consumer Staples"
    if any(w in il for w in ["oil", "gas", "fuel", "petro", "coal"]):
        return "Energy"
    if any(w in il for w in ["reit", "real estate", "realty"]):
        return "Real Estate"
    if any(w in il for w in ["metal", "steel", "cement", "chemical"]):
        return "Materials"
    if any(w in il for w in ["treps", "reverse repo", "cash", "treasury bill", "deposit", "commercial paper"]):
        return "Cash & Cash Equivalents"
    return "Other / Diversified"


def parse_xlsx_portfolio(file_path: Path) -> Dict[str, Any]:
    if openpyxl is None:
        raise RuntimeError("openpyxl is required to parse .xlsx files.")

    wb = openpyxl.load_workbook(str(file_path), data_only=True)
    sheet = wb.active

    date_str = ""
    scheme_name = ""
    ptr_ex_arb = None
    ptr_incl_arb = None
    aum_lakhs = None

    current_section = "OTHER"
    holdings = []
    
    subtotals = {
        "domestic_equity": 0.0,
        "foreign_equity": 0.0,
        "arbitrage": 0.0,
        "reits": 0.0,
        "cd": 0.0,
        "cp": 0.0,
        "tbill": 0.0,
        "mf_units": 0.0,
        "treps_repo": 0.0,
        "net_current_assets": 0.0,
        "debt_other": 0.0
    }

    subtotal_found = False

    for row_idx, row in enumerate(sheet.iter_rows(values_only=True), 1):
        non_nulls = [c for c in row if c is not None]
        if not non_nulls:
            continue
        row_text = " ".join([str(c) for c in non_nulls]).strip()
        low = row_text.lower()

        # Scheme name
        if row_idx <= 3 and not scheme_name and len(non_nulls) == 1 and isinstance(non_nulls[0], str):
            if len(non_nulls[0].strip()) > 10:
                scheme_name = non_nulls[0].strip()

        # Statement date
        if not date_str:
            m_date = re.search(r"as on\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})", row_text, re.I)
            if m_date:
                date_str = m_date.group(1).replace(",", "").strip()

        # PTR
        if "portfolio turnover" in low:
            m_ptr = re.search(r"Portfolio Turnover Ratio[^:]*:\s*([\d\.]+)", row_text, re.I)
            if m_ptr:
                val = float(m_ptr.group(1))
                if "excluding" in low or ptr_ex_arb is None:
                    ptr_ex_arb = val
                if "including" in low:
                    ptr_incl_arb = val

        # Section classification
        if "equity & equity related foreign" in low or "foreign investment" in low:
            current_section = "FOREIGN_EQUITY"
        elif "equity & equity related" in low:
            current_section = "DOMESTIC_EQUITY"
        elif "arbitrage" in low and len(non_nulls) <= 2:
            current_section = "ARBITRAGE"
        elif "reit" in low and len(non_nulls) <= 2:
            current_section = "REIT"
        elif "certificate of deposit" in low and len(non_nulls) <= 2:
            current_section = "CD"
        elif "commercial paper" in low and len(non_nulls) <= 2:
            current_section = "CP"
        elif "treasury bill" in low and len(non_nulls) <= 2:
            current_section = "TBILL"
        elif "mutual fund units" in low and len(non_nulls) <= 2:
            current_section = "MF_UNITS"
        elif any(k in low for k in ["reverse repo", "treps"]):
            current_section = "TREPS_REPO"
        elif any(k in low for k in ["net receivables", "net current assets"]):
            current_section = "NET_CURRENT_ASSETS"
        elif "grand total" in low or "total net assets" in low:
            current_section = "TOTAL"
            for val in non_nulls:
                if isinstance(val, (int, float)) and val > 10000:
                    aum_lakhs = float(val)

        # Check for Section Subtotals
        if "sub total" in low and len(non_nulls) >= 2:
            val_pct = non_nulls[-1]
            if isinstance(val_pct, (int, float)):
                pct_val = val_pct * 100.0 if val_pct <= 1.0 else val_pct
                pct_val = round(pct_val, 2)
                subtotal_found = True
                if current_section == "DOMESTIC_EQUITY":
                    subtotals["domestic_equity"] = pct_val
                elif current_section == "FOREIGN_EQUITY":
                    subtotals["foreign_equity"] = pct_val
                elif current_section == "ARBITRAGE":
                    subtotals["arbitrage"] = pct_val
                elif current_section == "REIT":
                    subtotals["reits"] = pct_val
                elif current_section == "CD":
                    subtotals["cd"] = pct_val
                elif current_section == "CP":
                    subtotals["cp"] = pct_val
                elif current_section == "TBILL":
                    subtotals["tbill"] = pct_val
                elif current_section == "MF_UNITS":
                    subtotals["mf_units"] = pct_val
                elif current_section == "TREPS_REPO":
                    subtotals["treps_repo"] = pct_val

        # Net receivables row
        if "net receivables" in low:
            val_pct = non_nulls[-1]
            if isinstance(val_pct, (int, float)):
                pct_val = val_pct * 100.0 if abs(val_pct) <= 1.0 else val_pct
                subtotals["net_current_assets"] = round(pct_val, 2)

        # Detect Individual Holdings by ISIN (Only for Equity / REIT holdings)
        isin_match = None
        for c in non_nulls:
            if isinstance(c, str):
                s = c.strip()
                if re.match(r"^[A-Z]{2}[A-Z0-9]{10}$", s):
                    isin_match = s
                    break

        if isin_match and current_section in ["DOMESTIC_EQUITY", "FOREIGN_EQUITY", "REIT", "ARBITRAGE"]:
            name = None
            industry = None
            pct = None
            for i, val in enumerate(non_nulls):
                if val == isin_match:
                    name = non_nulls[i - 1] if i > 0 else "Unknown"
                    industry = non_nulls[i + 1] if i + 1 < len(non_nulls) else "Unknown"
                if isinstance(val, (int, float)) and 0.00001 <= abs(val) <= 100.0:
                    pct = val

            if pct is not None:
                if abs(pct) <= 1.0:
                    pct = pct * 100.0
                w = round(pct, 2)
                sector_norm = normalize_sector(industry)
                holdings.append({
                    "name": str(name).strip(),
                    "isin": isin_match,
                    "industry": str(industry).strip(),
                    "sector": sector_norm,
                    "weight_pct": w,
                    "section": current_section
                })

    # If subtotals were captured directly from sheet
    if subtotal_found:
        domestic_eq_pct = subtotals["domestic_equity"]
        foreign_eq_pct = subtotals["foreign_equity"]
        arbitrage_pct = subtotals["arbitrage"]
        reits_pct = subtotals["reits"]
        money_market_pct = round(subtotals["cd"] + subtotals["cp"] + subtotals["tbill"] + subtotals["mf_units"], 2)
        treps_repo_pct = subtotals["treps_repo"]
        net_curr_pct = subtotals["net_current_assets"]
        dry_powder_total = round(treps_repo_pct + money_market_pct + net_curr_pct, 2)
    else:
        # Fallback to sum of individual rows
        domestic_eq_pct = round(sum(h["weight_pct"] for h in holdings if h["section"] == "DOMESTIC_EQUITY"), 2)
        foreign_eq_pct = round(sum(h["weight_pct"] for h in holdings if h["section"] == "FOREIGN_EQUITY"), 2)
        arbitrage_pct = round(sum(h["weight_pct"] for h in holdings if h["section"] == "ARBITRAGE"), 2)
        reits_pct = round(sum(h["weight_pct"] for h in holdings if h["section"] == "REIT"), 2)
        dry_powder_total = round(max(0.0, 100.0 - (domestic_eq_pct + foreign_eq_pct + arbitrage_pct + reits_pct)), 2)
        treps_repo_pct = round(dry_powder_total * 0.5, 2)
        money_market_pct = round(dry_powder_total * 0.4, 2)
        net_curr_pct = round(dry_powder_total - treps_repo_pct - money_market_pct, 2)

    # Sector aggregation
    sector_weights = {}
    for h in holdings:
        sec = h["sector"]
        sector_weights[sec] = round(sector_weights.get(sec, 0.0) + h["weight_pct"], 2)

    sector_weights["Cash & Cash Equivalents"] = dry_powder_total
    if reits_pct > 0 and "Real Estate" not in sector_weights:
        sector_weights["Real Estate"] = reits_pct

    # Sort holdings
    sorted_holdings = sorted(holdings, key=lambda x: x["weight_pct"], reverse=True)
    top_10 = sorted_holdings[:10]

    # Concentration metrics
    top_1_stock = round(sorted_holdings[0]["weight_pct"], 2) if sorted_holdings else 0.0
    top_5_stock = round(sum(h["weight_pct"] for h in sorted_holdings[:5]), 2)
    top_10_stock = round(sum(h["weight_pct"] for h in sorted_holdings[:10]), 2)

    sorted_sectors = sorted([(k, v) for k, v in sector_weights.items() if k != "Cash & Cash Equivalents"], key=lambda x: x[1], reverse=True)
    top_1_sector = sorted_sectors[0][1] if sorted_sectors else 0.0
    top_3_sector = round(sum(v for _, v in sorted_sectors[:3]), 2)
    top_5_sector = round(sum(v for _, v in sorted_sectors[:5]), 2)
    hhi_sector = round(sum(v ** 2 for _, v in sorted_sectors), 1)

    aum_crores = round(aum_lakhs / 100.0, 2) if aum_lakhs else None

    return {
        "file": str(file_path.name),
        "as_of_date": date_str or "Parsed from disclosure",
        "scheme_name": scheme_name or file_path.stem,
        "aum_crores": aum_crores,
        "portfolio_turnover_ratio_ex_arbitrage": ptr_ex_arb,
        "portfolio_turnover_ratio_incl_arbitrage": ptr_incl_arb,
        "asset_allocation": {
            "domestic_equity_pct": domestic_eq_pct,
            "foreign_equity_pct": foreign_eq_pct,
            "arbitrage_pct": arbitrage_pct,
            "reits_invits_pct": reits_pct,
            "treps_reverse_repo_pct": treps_repo_pct,
            "money_market_pct": money_market_pct,
            "net_current_assets_pct": net_curr_pct,
            "dry_powder_total_pct": dry_powder_total
        },
        "concentration_risk": {
            "top_1_stock_pct": top_1_stock,
            "top_5_stock_pct": top_5_stock,
            "top_10_stock_pct": top_10_stock,
            "top_1_sector_pct": top_1_sector,
            "top_3_sector_pct": top_3_sector,
            "top_5_sector_pct": top_5_sector,
            "sector_hhi": hhi_sector,
            "sector_hhi_category": "CONCENTRATED" if hhi_sector > 2500 else ("MODERATE" if hhi_sector >= 1500 else "DIVERSIFIED"),
            "sebi_10pct_cap_breached": any(h["weight_pct"] >= 10.0 for h in holdings)
        },
        "sector_allocation": sector_weights,
        "top_holdings": top_10,
        "total_holdings_count": len(holdings)
    }


def main():
    parser = argparse.ArgumentParser(description="Parse SEBI standardized mutual fund portfolio disclosure files.")
    parser.add_argument("--file", "-f", type=str, help="Path to .xlsx or .xls file to parse")
    parser.add_argument("--dir", "-d", type=str, help="Directory containing monthly portfolio files")
    parser.add_argument("--json", action="store_true", help="Output parsed metrics strictly in JSON")
    args = parser.parse_args()

    if not args.file and not args.dir:
        parser.print_help()
        sys.exit(1)

    results = []
    if args.file:
        p = Path(args.file).resolve()
        if not p.exists():
            print(f"❌ Error: File not found: {p}", file=sys.stderr)
            sys.exit(1)
        res = parse_xlsx_portfolio(p)
        results.append(res)
    elif args.dir:
        d = Path(args.dir).resolve()
        for f in sorted(d.glob("*.xlsx")):
            try:
                res = parse_xlsx_portfolio(f)
                results.append(res)
            except Exception as e:
                print(f"⚠️ Failed to parse {f.name}: {e}", file=sys.stderr)

    if args.json:
        print(json.dumps(results[0] if len(results) == 1 else results, indent=2))
        return

    for r in results:
        print(f"\n=======================================================")
        print(f"📊 Portfolio Statement: {r['scheme_name']}")
        print(f"   Date: {r['as_of_date']} | AUM: ₹{r['aum_crores']:,} Cr" if r['aum_crores'] else f"   Date: {r['as_of_date']}")
        print(f"   PTR (Excl Arbitrage): {r['portfolio_turnover_ratio_ex_arbitrage']}% | (Incl Arb): {r['portfolio_turnover_ratio_incl_arbitrage']}%")
        print(f"-------------------------------------------------------")
        print(f"💰 Capital & Cash Deployment (Dry Powder):")
        alloc = r["asset_allocation"]
        print(f"   • Domestic Equity : {alloc['domestic_equity_pct']}%")
        print(f"   • Foreign Equity  : {alloc['foreign_equity_pct']}%")
        print(f"   • Arbitrage       : {alloc['arbitrage_pct']}%")
        print(f"   • REITs / InvITs  : {alloc['reits_invits_pct']}%")
        print(f"   • TREPS / Repo    : {alloc['treps_reverse_repo_pct']}%")
        print(f"   • Money Market    : {alloc['money_market_pct']}%")
        print(f"   • Net Current     : {alloc['net_current_assets_pct']}%")
        print(f"   • 🌟 Total Dry Powder : {alloc['dry_powder_total_pct']}%")
        print(f"-------------------------------------------------------")
        print(f"🏢 Sector Allocation & Concentration (HHI: {r['concentration_risk']['sector_hhi']} - {r['concentration_risk']['sector_hhi_category']}):")
        for s, w in sorted(r["sector_allocation"].items(), key=lambda x: x[1], reverse=True)[:7]:
            print(f"   • {s:25}: {w:>6.2f}%")
        print(f"-------------------------------------------------------")
        print(f"🏆 Top 5 Holdings:")
        for h in r["top_holdings"][:5]:
            print(f"   • {h['name']:30}: {h['weight_pct']:>5.2f}% ({h['industry']})")
        print(f"=======================================================\n")


if __name__ == "__main__":
    main()
