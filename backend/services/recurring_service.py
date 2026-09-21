"""
Recurring Subscription & Payment Detection Engine (Task 18)
Analyzes user transactions to detect recurring payments, subscriptions, utility bills,
calculates normalized monthly/annual costs, and projects upcoming payment obligations.
"""

import re
import math
import statistics
import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from models.transaction import Transaction
from models.recurring_payment import RecurringPayment

# Known recurring merchant patterns and typical categories
KNOWN_SUBSCRIPTION_PATTERNS = [
    # Entertainment & Streaming
    (r"\b(netflix|spotify|disney|hotstar|prime video|youtube premium|apple music|audible|hulu|hbo|max|paramount|crunchyroll)\b", "Entertainment", "monthly"),
    # Cloud & SaaS
    (r"\b(aws|amazon web services|google cloud|gcp|azure|github|openai|chatgpt|claude|notion|dropbox|canva|figma|adobe|slack|zoom|atlassian|digitalocean|heroku)\b", "Bills & Utilities", "monthly"),
    # Telecom & Internet
    (r"\b(airtel|jio|vodafone|vi post|act fibernet|tata play|hathway|spectranet|broadband|wifi)\b", "Bills & Utilities", "monthly"),
    # Utilities
    (r"\b(bescom|tata power|adani electricity|electricity bill|water board|piped gas|mahanagar gas|indraprastha gas)\b", "Bills & Utilities", "monthly"),
    # Living & Rent
    (r"\b(rent|house rent|flat rent|society maintenance|apartment maintenance|maintenance charge)\b", "Rent", "monthly"),
    # Health & Fitness
    (r"\b(gym|cult\.fit|cultfit|fitness center|anytime fitness|gold's gym|yoga class|swimming club)\b", "Healthcare", "monthly"),
    # Insurance
    (r"\b(lic|hdfc life|icici prudential|icici lombard|star health|max life|tata aia|insurance premium|policy premium)\b", "Bills & Utilities", "annual"),
    # Education
    (r"\b(coursera|udemy|duolingo|chegg|skillshare|masterclass|tuition fee)\b", "Education", "monthly"),
]


def normalize_merchant_name(raw_desc: Optional[str]) -> str:
    """
    Strips transient transaction identifiers (dates, UPI references, card digits,
    order IDs, POS terminals) to extract canonical merchant/payment identifiers.
    """
    if not raw_desc:
        return "Unknown Payment"

    desc = raw_desc.strip()

    # 1. Check known subscription patterns first for high-quality canonical name
    desc_lower = f" {desc.lower()} "
    for pattern, _, _ in KNOWN_SUBSCRIPTION_PATTERNS:
        match = re.search(pattern, desc_lower, re.IGNORECASE)
        if match:
            matched_text = match.group(0).strip().title()
            # Clean common names
            if "Netflix" in matched_text: return "Netflix"
            if "Spotify" in matched_text: return "Spotify"
            if "Prime Video" in matched_text: return "Amazon Prime"
            if "Youtube" in matched_text: return "YouTube Premium"
            if "Aws" in matched_text or "Amazon Web" in matched_text: return "AWS Cloud"
            if "Github" in matched_text: return "GitHub"
            if "Openai" in matched_text or "Chatgpt" in matched_text: return "OpenAI / ChatGPT"
            if "Airtel" in matched_text: return "Airtel"
            if "Jio" in matched_text: return "Jio"
            if "Bescom" in matched_text: return "BESCOM Electricity"
            if "Rent" in matched_text: return "Rent"
            if "Cult" in matched_text: return "Cult.fit"
            return matched_text

    # 2. General cleansing for unmapped merchants
    cleaned = desc
    # Strip common prefixes like UPI, POS, IMPS, ACH, Direct Debit, Autopay
    cleaned = re.sub(r"^(upi|pos|imps|neft|ach|dr|cr|txn|ref)[\s/:-]+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(autopay|mandate|standing instruction|si|billdesk|razorpay|payu|cashfree)\b", "", cleaned, flags=re.IGNORECASE)
    # Strip dates (e.g. 2026-09-01, 12/09/2026, Sep 2026)
    cleaned = re.sub(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b", "", cleaned)
    cleaned = re.sub(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s-]*\d{2,4}\b", "", cleaned, flags=re.IGNORECASE)
    # Strip transaction IDs, reference numbers, alphanumeric hashes
    cleaned = re.sub(r"\b[A-Za-z0-9]*\d{4,}[A-Za-z0-9]*\b", "", cleaned)
    # Strip card masking e.g. **1234 or XX9812
    cleaned = re.sub(r"[*xX]+\d{2,4}", "", cleaned)
    # Strip symbols and extra whitespaces
    cleaned = re.sub(r"[-_/\\#,.:;@()]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if len(cleaned) < 3:
        # Fallback to alphanumeric portion of original description
        words = re.findall(r"[A-Za-z]{3,}", desc)
        return " ".join(words[:2]).title() if words else desc[:20].strip().title()

    # Return clean title-cased token
    return cleaned.title()


def calculate_next_payment_date(last_date: datetime.date, frequency: str) -> Optional[datetime.date]:
    """Projects next expected payment date based on detected frequency."""
    if not last_date:
        return None

    try:
        if frequency == "weekly":
            return last_date + datetime.timedelta(days=7)
        elif frequency == "biweekly":
            return last_date + datetime.timedelta(days=14)
        elif frequency == "monthly":
            # Add ~1 calendar month preserving day where possible
            year = last_date.year
            month = last_date.month + 1
            if month > 12:
                year += 1
                month = 1
            # Adjust day if target month has fewer days
            import calendar
            _, max_days = calendar.monthrange(year, month)
            day = min(last_date.day, max_days)
            return datetime.date(year, month, day)
        elif frequency == "quarterly":
            year = last_date.year
            month = last_date.month + 3
            if month > 12:
                year += 1
                month -= 12
            import calendar
            _, max_days = calendar.monthrange(year, month)
            day = min(last_date.day, max_days)
            return datetime.date(year, month, day)
        elif frequency == "annual":
            try:
                return datetime.date(last_date.year + 1, last_date.month, last_date.day)
            except ValueError:
                # Leap day handling (Feb 29)
                return datetime.date(last_date.year + 1, 2, 28)
    except Exception:
        return None

    return None


def calculate_normalized_costs(amount: float, frequency: str) -> Tuple[float, float]:
    """
    Normalizes a recurring payment amount into monthly and annual expenditures.
    Returns (monthly_cost, annual_cost).
    """
    amt = max(0.0, float(amount))
    if frequency == "weekly":
        monthly = round(amt * 52.0 / 12.0, 2)
        annual = round(amt * 52.0, 2)
    elif frequency == "biweekly":
        monthly = round(amt * 26.0 / 12.0, 2)
        annual = round(amt * 26.0, 2)
    elif frequency == "monthly":
        monthly = round(amt, 2)
        annual = round(amt * 12.0, 2)
    elif frequency == "quarterly":
        monthly = round(amt / 3.0, 2)
        annual = round(amt * 4.0, 2)
    elif frequency == "annual":
        monthly = round(amt / 12.0, 2)
        annual = round(amt, 2)
    else:
        monthly = round(amt, 2)
        annual = round(amt * 12.0, 2)

    return monthly, annual


class RecurringPaymentDetector:
    """
    Engine for identifying subscriptions and recurring bill commitments from user ledger transactions.
    """

    def analyze_transactions(self, transactions: List[Transaction]) -> List[Dict[str, Any]]:
        """
        Groups transactions by normalized merchant, evaluates temporal intervals
        and amount variances, and outputs detected recurring patterns.
        """
        # Filter valid expenses: exclude Income and Transfers
        expense_txs = [
            t for t in transactions
            if t.type == "Expense"
            and t.category not in ("Transfers",)
            and t.amount > 0
            and t.transaction_date is not None
        ]

        if len(expense_txs) < 2:
            return []

        # Group by normalized merchant name
        grouped: Dict[str, List[Transaction]] = {}
        for tx in expense_txs:
            norm_name = normalize_merchant_name(tx.description or tx.category)
            if norm_name not in grouped:
                grouped[norm_name] = []
            grouped[norm_name].append(tx)

        detected_patterns = []

        for norm_name, tx_list in grouped.items():
            # Need at least 2 transactions to form any interval
            if len(tx_list) < 2:
                continue

            pattern = self._evaluate_group(norm_name, tx_list)
            if pattern:
                detected_patterns.append(pattern)

        return detected_patterns

    def _evaluate_group(self, norm_name: str, tx_list: List[Transaction]) -> Optional[Dict[str, Any]]:
        """Evaluates a single merchant group for periodic cadence and amount stability."""
        # Sort chronologically
        sorted_txs = sorted(tx_list, key=lambda t: t.transaction_date)
        dates = [t.transaction_date for t in sorted_txs]
        amounts = [float(t.amount) for t in sorted_txs]

        # Deduplicate transactions on the exact same date (e.g. accidental double billing or two coffees on same day)
        unique_date_txs = []
        seen_dates = set()
        for t in sorted_txs:
            if t.transaction_date not in seen_dates:
                seen_dates.add(t.transaction_date)
                unique_date_txs.append(t)

        if len(unique_date_txs) < 2:
            return None

        unique_dates = [t.transaction_date for t in unique_date_txs]
        unique_amounts = [float(t.amount) for t in unique_date_txs]

        # Calculate consecutive day intervals
        intervals = [(unique_dates[i] - unique_dates[i - 1]).days for i in range(1, len(unique_dates))]
        if not intervals:
            return None

        median_interval = statistics.median(intervals)
        avg_amount = sum(unique_amounts) / len(unique_amounts)
        last_amount = unique_amounts[-1]
        last_date = unique_dates[-1]

        # Check amount variation: CV = standard deviation / mean
        if len(unique_amounts) > 1:
            stdev_amount = statistics.stdev(unique_amounts)
            amount_cv = stdev_amount / avg_amount if avg_amount > 0 else 0.0
            max_spread = (max(unique_amounts) - min(unique_amounts)) / avg_amount if avg_amount > 0 else 0.0
        else:
            amount_cv = 0.0
            max_spread = 0.0

        # High amount variation (> 35% CV) with irregular dates indicates random purchases, not a subscription
        if amount_cv > 0.35 and max_spread > 0.45:
            return None

        # Check known subscription pattern
        is_known = False
        default_cat = unique_date_txs[-1].category or "Other"
        for pattern, matched_cat, _ in KNOWN_SUBSCRIPTION_PATTERNS:
            if re.search(pattern, norm_name, re.IGNORECASE) or any(re.search(pattern, t.description or "", re.IGNORECASE) for t in unique_date_txs):
                is_known = True
                if default_cat in ("Other", "Needs Review"):
                    default_cat = matched_cat
                break

        # Classify Cadence Frequency
        frequency = None
        interval_stdev = statistics.stdev(intervals) if len(intervals) > 1 else 0.0

        # 1. Weekly: 6 to 9 days interval, requires >= 3 transactions
        if 5 <= median_interval <= 9 and len(unique_date_txs) >= 3 and interval_stdev <= 3.5:
            frequency = "weekly"

        # 2. Biweekly: 12 to 16 days interval, requires >= 3 transactions
        elif 12 <= median_interval <= 16 and len(unique_date_txs) >= 3 and interval_stdev <= 4.0:
            frequency = "biweekly"

        # 3. Monthly: 26 to 34 days interval
        elif 25 <= median_interval <= 35:
            # Check calendar day-of-month consistency (e.g. 5th of each month ± 3 days)
            days_of_month = [d.day for d in unique_dates]
            day_spread = max(days_of_month) - min(days_of_month)
            if interval_stdev <= 7.0 or day_spread <= 6:
                frequency = "monthly"

        # 4. Quarterly: 80 to 100 days (~3 months)
        elif 75 <= median_interval <= 105 and interval_stdev <= 14.0:
            frequency = "quarterly"

        # 5. Annual: 345 to 385 days (~1 year)
        elif 340 <= median_interval <= 390 and interval_stdev <= 25.0:
            frequency = "annual"

        # Fallback for known subscriptions: if known and monthly-like spacing exists
        if not frequency and is_known:
            if 20 <= median_interval <= 40:
                frequency = "monthly"
            elif 330 <= median_interval <= 400:
                frequency = "annual"

        # If no recognized frequency could be determined, reject
        if not frequency:
            return None

        # Compute Confidence Score (0.0 to 1.0)
        confidence = 0.70

        # Amount consistency contribution
        if amount_cv <= 0.03:
            confidence += 0.15 # Exact fixed subscription price
        elif amount_cv <= 0.15:
            confidence += 0.08 # Minor price variation (e.g. tax/fx)
        elif amount_cv <= 0.28:
            confidence += 0.02 # Utility bill variation
        else:
            confidence -= 0.10

        # Cadence consistency contribution
        if len(intervals) > 1 and interval_stdev <= 2.0:
            confidence += 0.10
        elif len(intervals) > 1 and interval_stdev <= 4.0:
            confidence += 0.05
        elif interval_stdev > 6.0:
            confidence -= 0.08

        # Sample count contribution
        if len(unique_date_txs) >= 4:
            confidence += 0.08
        elif len(unique_date_txs) >= 3:
            confidence += 0.04

        # Known merchant boost
        if is_known:
            confidence += 0.10

        confidence = max(0.40, min(0.98, round(confidence, 2)))

        # Calculate normalized costs
        monthly_cost, annual_cost = calculate_normalized_costs(last_amount, frequency)

        # Predict next date
        next_date = calculate_next_payment_date(last_date, frequency)

        return {
            "merchant_name": norm_name,
            "normalized_name": norm_name.lower(),
            "category": default_cat,
            "frequency": frequency,
            "average_amount": round(avg_amount, 2),
            "last_amount": round(last_amount, 2),
            "estimated_monthly_cost": monthly_cost,
            "estimated_annual_cost": annual_cost,
            "confidence": confidence,
            "status": "detected" if confidence < 0.85 else "confirmed",
            "last_payment_date": last_date,
            "next_estimated_date": next_date,
            "transaction_count": len(unique_date_txs),
            "notes": f"Detected {frequency} payment pattern based on {len(unique_date_txs)} transactions.",
        }


# Global detector instance
recurring_detector = RecurringPaymentDetector()


def scan_user_recurring_payments(db: Session, user_id: str) -> Dict[str, Any]:
    """
    Runs the recurring payment detector on the user's historical transactions.
    Safely updates or creates records in `recurring_payments`, preserving user confirmation
    and dismissal statuses. Returns scan metrics and the refreshed list of records.
    """
    transactions = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.type == "Expense"
    ).order_by(Transaction.transaction_date.asc()).all()

    detected_items = recurring_detector.analyze_transactions(transactions)

    # Fetch current recurring records for this user
    existing_records = db.query(RecurringPayment).filter(RecurringPayment.user_id == user_id).all()
    existing_by_norm: Dict[str, RecurringPayment] = {r.normalized_name: r for r in existing_records}

    new_count = 0
    updated_count = 0

    for item in detected_items:
        norm_key = item["normalized_name"]

        if norm_key in existing_by_norm:
            # Update existing record while strictly preserving user's status & custom notes
            rec = existing_by_norm[norm_key]
            rec.last_payment_date = item["last_payment_date"]
            rec.next_estimated_date = item["next_estimated_date"]
            rec.average_amount = item["average_amount"]
            rec.last_amount = item["last_amount"]
            rec.estimated_monthly_cost = item["estimated_monthly_cost"]
            rec.estimated_annual_cost = item["estimated_annual_cost"]
            rec.transaction_count = item["transaction_count"]
            rec.confidence = max(rec.confidence, item["confidence"])
            if not rec.notes:
                rec.notes = item["notes"]
            rec.updated_at = datetime.datetime.utcnow()
            updated_count += 1
        else:
            # Create new detected record
            rec = RecurringPayment(
                user_id=user_id,
                merchant_name=item["merchant_name"],
                normalized_name=item["normalized_name"],
                category=item["category"],
                frequency=item["frequency"],
                average_amount=item["average_amount"],
                last_amount=item["last_amount"],
                estimated_monthly_cost=item["estimated_monthly_cost"],
                estimated_annual_cost=item["estimated_annual_cost"],
                confidence=item["confidence"],
                status=item["status"], # "detected" or "confirmed"
                last_payment_date=item["last_payment_date"],
                next_estimated_date=item["next_estimated_date"],
                transaction_count=item["transaction_count"],
                notes=item["notes"],
            )
            db.add(rec)
            existing_by_norm[norm_key] = rec
            new_count += 1

    db.commit()

    all_user_records = db.query(RecurringPayment).filter(
        RecurringPayment.user_id == user_id
    ).order_by(RecurringPayment.estimated_monthly_cost.desc()).all()

    active_count = len([r for r in all_user_records if r.status != "dismissed"])

    return {
        "scanned_transactions_count": len(transactions),
        "new_detected_count": new_count,
        "updated_count": updated_count,
        "total_active_count": active_count,
        "items": all_user_records,
        "message": f"Scan completed: {new_count} new pattern(s) detected, {updated_count} existing record(s) updated across {len(transactions)} transactions.",
    }


def get_recurring_summary(db: Session, user_id: str) -> Dict[str, Any]:
    """
    Computes summary metrics for recurring payments:
    - Total monthly commitment (excluding dismissed items)
    - Total annual commitment (excluding dismissed items)
    - Active count, confirmed count, detected count, dismissed count
    - Upcoming payments in the next 30 days
    """
    records = db.query(RecurringPayment).filter(RecurringPayment.user_id == user_id).all()

    active_records = [r for r in records if r.status != "dismissed"]

    total_monthly = round(sum(r.estimated_monthly_cost for r in active_records), 2)
    total_annual = round(sum(r.estimated_annual_cost for r in active_records), 2)

    confirmed_count = len([r for r in records if r.status == "confirmed"])
    detected_count = len([r for r in records if r.status == "detected"])
    dismissed_count = len([r for r in records if r.status == "dismissed"])

    today = datetime.date.today()
    in_30_days = today + datetime.timedelta(days=30)

    upcoming = [
        r for r in active_records
        if r.next_estimated_date and today <= r.next_estimated_date <= in_30_days
    ]
    upcoming.sort(key=lambda r: r.next_estimated_date)

    return {
        "total_monthly_commitment": total_monthly,
        "total_annual_commitment": total_annual,
        "active_subscriptions_count": len(active_records),
        "confirmed_count": confirmed_count,
        "detected_count": detected_count,
        "dismissed_count": dismissed_count,
        "upcoming_payments_next_30_days": upcoming,
    }
