#!/usr/bin/env python3
"""
date_parser.py - Date Range & Horizon Parser for Mutual Fund NAV Queries
Converts natural language expressions (e.g., 'last 15 months', '3 years', 'since inception')
or explicit dates into ISO 8601 (YYYY-MM-DD) start and end dates.
"""

import sys
import re
import argparse
from datetime import datetime, timedelta
from typing import Tuple, Optional


def parse_horizon_or_dates(
    period_str: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    ref_date: Optional[datetime] = None
) -> Tuple[Optional[str], Optional[str], str]:
    """
    Returns (start_date_iso, end_date_iso, label_description).
    Dates are formatted as 'YYYY-MM-DD' or None (for inception).
    """
    if ref_date is None:
        ref_date = datetime.now()

    today_str = ref_date.strftime("%Y-%m-%d")

    # 1. If explicit dates are provided
    if start_date or end_date:
        s_clean = normalize_iso_date(start_date) if start_date else None
        e_clean = normalize_iso_date(end_date) if end_date else today_str
        
        if s_clean and e_clean and s_clean > e_clean:
            raise ValueError(f"Start date ({s_clean}) cannot be after end date ({e_clean})")
            
        label = f"{s_clean or 'Inception'} to {e_clean}"
        return s_clean, e_clean, label

    # 2. If no period string or period specifies inception/all
    if not period_str:
        return None, None, "Since Inception"

    p_clean = period_str.strip().lower()

    # Inception keywords
    if any(k in p_clean for k in ["inception", "all time", "all", "entire", "full history", "max"]):
        return None, None, "Since Inception"

    # Year to date (YTD)
    if p_clean in ["ytd", "year to date", "this year"]:
        ytd_start = f"{ref_date.year}-01-01"
        return ytd_start, today_str, f"Year to Date ({ref_date.year})"

    # Match patterns like: "last 15 months", "15m", "15 months", "3 years", "3y", "30 days"
    # Months pattern
    m_match = re.search(r"(\d+)\s*(?:month|m)", p_clean)
    if m_match and "day" not in p_clean:
        num_months = int(m_match.group(1))
        start_dt = subtract_months(ref_date, num_months)
        s_iso = start_dt.strftime("%Y-%m-%d")
        return s_iso, today_str, f"Last {num_months} Months ({s_iso} to {today_str})"

    # Years pattern
    y_match = re.search(r"(\d+)\s*(?:year|yr|y)", p_clean)
    if y_match:
        num_years = int(y_match.group(1))
        start_dt = subtract_months(ref_date, num_years * 12)
        s_iso = start_dt.strftime("%Y-%m-%d")
        return s_iso, today_str, f"Last {num_years} Years ({s_iso} to {today_str})"

    # Weeks pattern
    w_match = re.search(r"(\d+)\s*(?:week|w)", p_clean)
    if w_match:
        num_weeks = int(w_match.group(1))
        start_dt = ref_date - timedelta(weeks=num_weeks)
        s_iso = start_dt.strftime("%Y-%m-%d")
        return s_iso, today_str, f"Last {num_weeks} Weeks ({s_iso} to {today_str})"

    # Days pattern
    d_match = re.search(r"(\d+)\s*(?:day|d)", p_clean)
    if d_match:
        num_days = int(d_match.group(1))
        start_dt = ref_date - timedelta(days=num_days)
        s_iso = start_dt.strftime("%Y-%m-%d")
        return s_iso, today_str, f"Last {num_days} Days ({s_iso} to {today_str})"

    # Fallback: check if period_str itself is a single date or range
    dates_found = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", p_clean)
    if len(dates_found) == 2:
        return dates_found[0], dates_found[1], f"{dates_found[0]} to {dates_found[1]}"
    elif len(dates_found) == 1:
        return dates_found[0], today_str, f"{dates_found[0]} to {today_str}"

    # Default to inception if unrecognized
    return None, None, f"Since Inception (Unrecognized period '{period_str}')"


def subtract_months(dt: datetime, months: int) -> datetime:
    """Accurately subtracts N months from a datetime."""
    year = dt.year - (months // 12)
    month = dt.month - (months % 12)
    if month <= 0:
        month += 12
        year -= 1
    # Handle day overflow (e.g. Feb 30)
    day = min(dt.day, days_in_month(year, month))
    return dt.replace(year=year, month=month, day=day)


def days_in_month(year: int, month: int) -> int:
    if month in [1, 3, 5, 7, 8, 10, 12]:
        return 31
    if month in [4, 6, 9, 11]:
        return 30
    if month == 2:
        # Leap year check
        if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
            return 29
        return 28
    return 30


def normalize_iso_date(date_str: str) -> str:
    """Validates and normalizes date string to YYYY-MM-DD."""
    clean = date_str.strip()
    # Check YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", clean):
        datetime.strptime(clean, "%Y-%m-%d")
        return clean
    # Check DD-MM-YYYY
    if re.match(r"^\d{2}-\d{2}-\d{4}$", clean):
        dt = datetime.strptime(clean, "%d-%m-%Y")
        return dt.strftime("%Y-%m-%d")
    # Check ISO format with T
    if "T" in clean:
        dt = datetime.fromisoformat(clean.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    raise ValueError(f"Invalid date format '{date_str}'. Expected ISO 8601 (YYYY-MM-DD).")


def main():
    parser = argparse.ArgumentParser(description="Test date range parsing for NAV queries.")
    parser.add_argument("--period", "-p", type=str, help="Natural language period (e.g. 'last 15 months', 'since inception', '3y')")
    parser.add_argument("--start-date", "-s", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", "-e", type=str, help="End date (YYYY-MM-DD)")
    args = parser.parse_args()

    s, e, label = parse_horizon_or_dates(period_str=args.period, start_date=args.start_date, end_date=args.end_date)
    print(f"Horizon Label : {label}")
    print(f"startDate     : {s}")
    print(f"endDate       : {e}")


if __name__ == "__main__":
    main()

