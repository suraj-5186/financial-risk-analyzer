import re
from typing import Dict, Any, Optional

ALL_VALID_CATEGORIES = [
    "Food",
    "Groceries",
    "Shopping",
    "Transport",
    "Bills & Utilities",
    "Healthcare",
    "Salary",
    "Rent",
    "Education",
    "Entertainment",
    "Transfers",
    "Investment",
    "Freelance",
    "Other",
    "Needs Review",
]

# Aliases to normalize legacy or alternative category names
CATEGORY_ALIASES = {
    "travel": "Transport",
    "bills": "Bills & Utilities",
    "utilities": "Bills & Utilities",
    "bill": "Bills & Utilities",
}

# Merchant and keyword rules for Expense transactions
EXPENSE_RULES = [
    # 1. Food
    {
        "category": "Food",
        "high_confidence_patterns": [
            r"\b(swiggy|zomato|mcdonald|mcdonalds|starbucks|dominos|domino's|kfc|burger king|subway|pizza hut|dunkin|chipotle|taco bell|doordash|ubereats|uber eats|grubhub|blinkit|zepto|instamart|bigbasket|grofers|haldiram|barbeque nation|wendy|wendys)\b"
        ],
        "medium_confidence_patterns": [
            r"\b(restaurant|cafe|coffee|bakery|deli|grocery|groceries|supermarket|food|dining|bistro|kitchen|sweets|eatery|pizza|burger|chai|tea|bar & grill|pub|cafeteria|canteen)\b"
        ],
    },
    # 2. Shopping
    {
        "category": "Shopping",
        "high_confidence_patterns": [
            r"\b(amazon|flipkart|myntra|walmart|target|ebay|ikea|zara|h&m|uniqlo|nike|adidas|apple store|costco|best buy|aliexpress|shein|asos|nykaa|croma|reliance digital|decathlon)\b"
        ],
        "medium_confidence_patterns": [
            r"\b(shopping|retail|mall|clothing|apparel|footwear|shoes|electronics|boutique|fashion|department store|hardware store|jewellers|jewelers)\b"
        ],
    },
    # 3. Transport (Travel / Fuel)
    {
        "category": "Transport",
        "high_confidence_patterns": [
            r"\b(uber|ola|rapido|lyft|grab|irctc|indigo|air india|delta|united airlines|emirates|shell|chevron|fastag|bpcl|hpcl|ioc|iocnl|petrol|diesel|fuel station|toll plaza)\b"
        ],
        "medium_confidence_patterns": [
            r"\b(transport|travel|taxi|cab|metro|subway|railway|train|flight|airline|airport|fuel|gas station|parking|toll|bus|commute)\b"
        ],
    },
    # 4. Bills & Utilities
    {
        "category": "Bills & Utilities",
        "high_confidence_patterns": [
            r"\b(airtel|jio|vodafone|vi recharge|at&t|verizon|t-mobile|tata power|bescom|billdesk|tata play|dish tv|adani electricity|mahavitaran|recharge|dth)\b"
        ],
        "medium_confidence_patterns": [
            r"\b(electricity|power|water utility|water bill|gas utility|broadband|wifi|internet|utility|utilities|phone bill|sewer|electric bill)\b"
        ],
    },
    # 5. Healthcare
    {
        "category": "Healthcare",
        "high_confidence_patterns": [
            r"\b(apollo|medplus|1mg|pharmeasy|cvs|walgreens|practo|max healthcare|fortis|dr lal pathlabs|metropolis)\b"
        ],
        "medium_confidence_patterns": [
            r"\b(pharmacy|chemist|hospital|clinic|doctor|medical|dentist|dental|healthcare|diagnostic|pathology|lab test|optometry|medicine|physician|therapy)\b"
        ],
    },
    # 6. Rent
    {
        "category": "Rent",
        "high_confidence_patterns": [
            r"\b(house rent|apartment rent|flat rent|landlord|lease payment|society maintenance|flat maintenance|residential rent)\b"
        ],
        "medium_confidence_patterns": [
            r"\b(rent|maintenance fee|tenancy)\b"
        ],
    },
    # 7. Education
    {
        "category": "Education",
        "high_confidence_patterns": [
            r"\b(udemy|coursera|edx|duolingo|khan academy|byju|byjus|unacademy|skillshare)\b"
        ],
        "medium_confidence_patterns": [
            r"\b(tuition|school fee|college fee|university|course fee|education|textbook|training institute|exam fee|academy|school|college|books)\b"
        ],
    },
    # 8. Entertainment
    {
        "category": "Entertainment",
        "high_confidence_patterns": [
            r"\b(netflix|spotify|disney|disney\+|hulu|steam|playstation|xbox|bookmyshow|pvr|inox|amc|ticketmaster|prime video|apple music|youtube premium|nintendo|game pass)\b"
        ],
        "medium_confidence_patterns": [
            r"\b(entertainment|cinema|movie|theater|theatre|concert|arcade|gaming|amusement|event tickets|club)\b"
        ],
    },
    # 9. Transfers
    {
        "category": "Transfers",
        "high_confidence_patterns": [
            r"\b(upi/p2p|neft|imps|rtgs|venmo|zelle|cash app|wire transfer|atm withdrawal|cash withdrawal|self transfer)\b"
        ],
        "medium_confidence_patterns": [
            r"\b(transfer to|sent to|p2p payment|peer payment|fund transfer)\b"
        ],
    },
    # 10. Investment
    {
        "category": "Investment",
        "high_confidence_patterns": [
            r"\b(zerodha|groww|vanguard|fidelity|mutual fund|sip|etf|brokerage|robinhood|coinbase|binance|kraken|charles schwab)\b"
        ],
        "medium_confidence_patterns": [
            r"\b(investment|stocks|shares|securities|crypto)\b"
        ],
    },
]

# Income Rules
INCOME_RULES = [
    {
        "category": "Salary",
        "high_confidence_patterns": [
            r"\b(salary|payroll|direct dep|dir dep|monthly stipend|wages|employer pay|monthly pay|compensation)\b"
        ],
        "medium_confidence_patterns": [
            r"\b(stipend|bonus|paycheck)\b"
        ],
    },
    {
        "category": "Freelance",
        "high_confidence_patterns": [
            r"\b(upwork|fiverr|freelance|consulting fee|client payout|invoice payment|contract payment)\b"
        ],
        "medium_confidence_patterns": [
            r"\b(consulting|gig|freelancer)\b"
        ],
    },
    {
        "category": "Investment",
        "high_confidence_patterns": [
            r"\b(dividend|interest credit|mutual fund redemption|zerodha payout|groww payout|etf distribution|capital gain)\b"
        ],
        "medium_confidence_patterns": [
            r"\b(interest|yield|stock dividend|payout)\b"
        ],
    },
    {
        "category": "Transfers",
        "high_confidence_patterns": [
            r"\b(received from|upi/p2p|neft credit|imps credit|wire credit|reimbursement)\b"
        ],
        "medium_confidence_patterns": [
            r"\b(transfer from|deposit from|refund)\b"
        ],
    },
]


def normalize_category_name(category: Optional[str]) -> str:
    """Normalize category names to standard format."""
    if not category or not category.strip():
        return "Needs Review"
    cat_clean = category.strip().lower()
    if cat_clean in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[cat_clean]
    for valid in ALL_VALID_CATEGORIES:
        if valid.lower() == cat_clean:
            return valid
    return category.strip()


class AutoCategorizationEngine:
    """
    Deterministic rule-based categorization engine with confidence scoring and directional validation.
    """

    def categorize(
        self,
        description: str,
        tx_type: str = "Expense",
        amount: float = 0.0,
        current_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Suggests a category for a given transaction.
        Preserves user-selected categories if already assigned and valid.
        """
        # If user has already explicitly assigned a category that is not generic "Other" or empty
        if current_category and current_category.strip() not in ("", "Other", "Needs Review", "Uncategorized"):
            normalized = normalize_category_name(current_category)
            return {
                "suggested_category": normalized,
                "confidence": 1.0,
                "explanation": "Preserved existing category.",
                "is_reviewed": True,
            }

        desc = (description or "").strip()
        if not desc:
            return {
                "suggested_category": "Needs Review",
                "confidence": 0.20,
                "explanation": "Empty description; requires manual review.",
                "is_reviewed": False,
            }

        desc_lower = f" {desc.lower()} "
        is_income = tx_type.strip().capitalize() == "Income"

        # Directional Rule Evaluation
        rules = INCOME_RULES if is_income else EXPENSE_RULES

        # 1. High confidence match
        for rule in rules:
            for pattern in rule["high_confidence_patterns"]:
                match = re.search(pattern, desc_lower, re.IGNORECASE)
                if match:
                    matched_term = match.group(0).strip()
                    return {
                        "suggested_category": rule["category"],
                        "confidence": 0.95,
                        "explanation": f"Matched merchant/keyword '{matched_term}' ({rule['category']}).",
                        "is_reviewed": True,
                        "rule_matched": rule["category"],
                    }

        # 2. Medium confidence match
        for rule in rules:
            for pattern in rule.get("medium_confidence_patterns", []):
                match = re.search(pattern, desc_lower, re.IGNORECASE)
                if match:
                    matched_term = match.group(0).strip()
                    return {
                        "suggested_category": rule["category"],
                        "confidence": 0.80,
                        "explanation": f"Matched descriptive keyword '{matched_term}' ({rule['category']}).",
                        "is_reviewed": True,
                        "rule_matched": rule["category"],
                    }

        # 3. Income Directional Fallback
        if is_income:
            # Check for refund or cashback keywords
            if re.search(r"\b(refund|cashback|reward|reversal)\b", desc_lower):
                return {
                    "suggested_category": "Other",
                    "confidence": 0.85,
                    "explanation": "Identified refund/cashback credit transaction.",
                    "is_reviewed": True,
                    "rule_matched": "RefundReversal",
                }
            return {
                "suggested_category": "Needs Review",
                "confidence": 0.40,
                "explanation": "Unrecognized income source. Please review category.",
                "is_reviewed": False,
                "rule_matched": None,
            }

        # 4. Expense Ambiguous / Unknown Fallback
        return {
            "suggested_category": "Needs Review",
            "confidence": 0.35,
            "explanation": "Ambiguous or unrecognized merchant description. Requires manual review.",
            "is_reviewed": False,
            "rule_matched": None,
        }


# Global singleton instance
categorization_engine = AutoCategorizationEngine()


def categorize_transaction(
    description: str,
    transaction_type: str = "Expense",
    amount: float = 0.0,
    existing_category: Optional[str] = None,
) -> Dict[str, Any]:
    """Convenience functional wrapper for categorizing a transaction."""
    return categorization_engine.categorize(
        description=description,
        tx_type=transaction_type,
        amount=amount,
        current_category=existing_category,
    )


def categorize_statement_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses a raw bank statement row dictionary (case-insensitive keys)
    and returns normalized transaction fields with auto-categorization.
    """
    normalized_row = {str(k).strip().lower(): v for k, v in row.items()}
    
    # 1. Description / Narration
    desc = ""
    for k in ["narration", "description", "particulars", "remarks", "details", "desc", "memo"]:
        if k in normalized_row and normalized_row[k] is not None:
            desc = str(normalized_row[k]).strip()
            break

    # 2. Date
    date_val = ""
    for k in ["transaction date", "date", "tx date", "value date", "post date"]:
        if k in normalized_row and normalized_row[k] is not None:
            date_val = str(normalized_row[k]).strip()
            break

    # 3. Debit / Credit & Amount
    tx_type = "Expense"
    amount_val = 0.0

    debit_str = ""
    for k in ["withdrawal", "debit", "withdrawal amt", "dr"]:
        if k in normalized_row and normalized_row[k] is not None:
            debit_str = str(normalized_row[k]).strip().replace(",", "").replace("$", "").replace("₹", "")
            break

    credit_str = ""
    for k in ["deposit", "credit", "deposit amt", "cr"]:
        if k in normalized_row and normalized_row[k] is not None:
            credit_str = str(normalized_row[k]).strip().replace(",", "").replace("$", "").replace("₹", "")
            break

    try:
        debit_num = float(debit_str) if debit_str and debit_str != "-" else 0.0
    except (ValueError, TypeError):
        debit_num = 0.0

    try:
        credit_num = float(credit_str) if credit_str and credit_str != "-" else 0.0
    except (ValueError, TypeError):
        credit_num = 0.0

    if debit_num > 0:
        tx_type = "Expense"
        amount_val = debit_num
    elif credit_num > 0:
        tx_type = "Income"
        amount_val = credit_num
    else:
        # Check general amount column
        raw_amt_str = ""
        for k in ["amount", "txn amount", "net amount"]:
            if k in normalized_row and normalized_row[k] is not None:
                raw_amt_str = str(normalized_row[k]).strip().replace(",", "").replace("$", "").replace("₹", "")
                break
        try:
            parsed_amt = float(raw_amt_str) if raw_amt_str and raw_amt_str != "-" else 0.0
        except (ValueError, TypeError):
            parsed_amt = 0.0

        raw_type = ""
        for k in ["type", "dr/cr", "cr/dr", "txn type"]:
            if k in normalized_row and normalized_row[k] is not None:
                raw_type = str(normalized_row[k]).strip().upper()
                break

        if raw_type in ["INCOME", "CR", "CREDIT"] or parsed_amt < 0:
            tx_type = "Income" if raw_type in ["INCOME", "CR", "CREDIT"] else "Expense"
            amount_val = abs(parsed_amt)
        else:
            tx_type = "Expense"
            amount_val = abs(parsed_amt)

    # 4. Existing Category if provided
    raw_cat = ""
    for k in ["category", "cat"]:
        if k in normalized_row and normalized_row[k] is not None:
            raw_cat = str(normalized_row[k]).strip()
            break

    cat_result = categorization_engine.categorize(
        description=desc,
        tx_type=tx_type,
        amount=amount_val,
        current_category=raw_cat,
    )

    return {
        "transaction_date": date_val,
        "description": desc,
        "type": tx_type,
        "amount": amount_val,
        "suggested_category": cat_result["suggested_category"],
        "confidence": cat_result["confidence"],
        "explanation": cat_result["explanation"],
        "is_reviewed": cat_result["is_reviewed"],
        "rule_matched": cat_result.get("rule_matched"),
    }
