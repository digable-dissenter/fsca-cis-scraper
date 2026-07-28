"""Experience requirements lookup and validation module under Board Notice 194 of 2017."""

# FSP Categories
CATEGORY_I = "CATEGORY I"
CATEGORY_II = "CATEGORY II"
CATEGORY_III = "CATEGORY III"

# Service Types
ADVICE = "advice"
INTERMEDIARY = "intermediary"


def normalize_product_name(name: str) -> str:
    """Normalize product names for consistent lookup.

    E.g., handles plurals, hyphens, and slight wording differences.
    """
    if not name:
        return ""
    
    # Lowercase and clean spaces/hyphens
    val = name.lower().replace("-", " ").replace("/", " ").replace(",", " ")
    val = " ".join(val.split())
    
    # Replace "or" with "and"
    val = val.replace(" or ", " and ")
    
    # Common replacements to align different sources
    replacements = {
        "participatory interest in one and more collective investment scheme": "participatory interest in collective investment scheme",
        "participatory interest in a collective investment scheme": "participatory interest in collective investment scheme",
        "participatory interests in a collective investment scheme": "participatory interest in collective investment scheme",
        "participatory interests in one and more collective investment scheme": "participatory interest in collective investment scheme",
        "pension funds benefit": "pension fund benefit",
        "forex investment": "forex investment",
        "foreign exchange investment": "forex investment",
    }
    
    # Word-by-word standardisation (plural to singular for common nouns)
    words = val.split()
    standard_words = []
    for w in words:
        if w.endswith("ies"):
            w = w[:-3] + "y"
        elif w.endswith("s") and not w.endswith("ss") and w not in ["class", "business", "status", "forex"]:
            w = w[:-1]
        standard_words.append(w)
    
    normalized = " ".join(standard_words)
    
    for old, new in replacements.items():
        if old in normalized:
            normalized = normalized.replace(old, new)
            
    return normalized.strip()


# Table 1: Category I Experience Requirements (in months)
CATEGORY_I_REQUIREMENTS = {
    "long term insurance subcategory a": {ADVICE: 6, INTERMEDIARY: 2},
    "short term insurance personal line": {ADVICE: 12, INTERMEDIARY: 6},
    "long term insurance subcategory b1": {ADVICE: 12, INTERMEDIARY: 6},
    "long term insurance subcategory c": {ADVICE: 12, INTERMEDIARY: 6},
    "retail pension benefit": {ADVICE: 12, INTERMEDIARY: 6},
    "short term insurance commercial line": {ADVICE: 12, INTERMEDIARY: 6},
    "pension fund benefit": {ADVICE: 12, INTERMEDIARY: 6},
    "share": {ADVICE: 24, INTERMEDIARY: 12},
    "money market instrument": {ADVICE: 24, INTERMEDIARY: 12},
    "debenture and securitised debt": {ADVICE: 24, INTERMEDIARY: 12},
    "warrant certificate and other instrument": {ADVICE: 24, INTERMEDIARY: 12},
    "bond": {ADVICE: 24, INTERMEDIARY: 12},
    "derivative instrument": {ADVICE: 24, INTERMEDIARY: 12},
    "participatory interest in collective investment scheme": {ADVICE: 12, INTERMEDIARY: 12},
    "forex investment": {ADVICE: 24, INTERMEDIARY: 12},
    "health service benefit": {ADVICE: 24, INTERMEDIARY: 24},
    "long term deposit": {ADVICE: 6, INTERMEDIARY: 3},
    "short term deposit": {ADVICE: 6, INTERMEDIARY: 3},
    "friendly society benefit": {ADVICE: 6, INTERMEDIARY: 2},
    "long term insurance subcategory b2": {ADVICE: 12, INTERMEDIARY: 6},
    "long term insurance subcategory b2 a": {ADVICE: 12, INTERMEDIARY: 6},
    "long term insurance subcategory b1 a": {ADVICE: 12, INTERMEDIARY: 6},
    "short term insurance personal line a1": {ADVICE: 12, INTERMEDIARY: 6},
    "structured deposit": {ADVICE: 24, INTERMEDIARY: 12},
    "security and instrument": {ADVICE: 24, INTERMEDIARY: 12},
    "participatory interest in hedge fund": {ADVICE: 24, INTERMEDIARY: 12},
}

# Table 2: Category II Experience Requirements (in months)
# Note: Category II FSPs only have a single experience requirement for rendering
# services (referred to as Advice / Intermediary interchangeably in the notice).
CATEGORY_II_REQUIREMENTS = {
    "long term insurance subcategory b1": 24,
    "long term insurance subcategory c": 24,
    "retail pension benefit": 24,
    "pension fund benefit": 24,
    "share": 36,
    "money market instrument": 36,
    "debenture and securitised debt": 36,
    "warrant certificate and other instrument": 36,
    "bond": 36,
    "derivative instrument": 36,
    "participatory interest in collective investment scheme": 24,
    "forex investment": 36,
    "long term deposit": 12,
    "short term deposit": 12,
    "long term insurance subcategory b2": 24,
    "long term insurance subcategory b2 a": 24,
    "long term insurance subcategory b1 a": 24,
    "structured deposit": 36,
    "security and instrument": 36,
    "participatory interest in hedge fund": 36,
}


def get_experience_requirement(category: str, product_name: str, service_type: str = ADVICE) -> int | None:
    """Retrieve the experience requirement in months for a given product and category."""
    cat_upper = category.upper()
    prod_norm = normalize_product_name(product_name)
    service_lower = service_type.lower()
    
    if "CATEGORY III" in cat_upper:
        # Category III general experience requirement is 36 months
        return 36
        
    elif "CATEGORY IIA" in cat_upper or "CATEGORY 2A" in cat_upper:
        # Category IIA (Hedge Fund) experience requirement is 36 months (3 years)
        return 36

    elif "CATEGORY II" in cat_upper:
        return CATEGORY_II_REQUIREMENTS.get(prod_norm)
        
    elif "CATEGORY IV" in cat_upper or "CATEGORY 4" in cat_upper:
        # Category IV (Assistance Business) experience requirement is 12 months (1 year)
        return 12

    elif "CATEGORY I" in cat_upper:
        # Match sub-parts (e.g. CATEGORY I FSP)
        reqs = CATEGORY_I_REQUIREMENTS.get(prod_norm)
        if reqs:
            return reqs.get(service_lower, reqs.get(ADVICE))
        
    return None


def validate_experience(
    category: str, product_name: str, service_type: str, experience_months: int
) -> tuple[bool, int]:
    """Validate if the given experience (in months) meets the required threshold.

    Returns:
        A tuple of (meets_requirement, required_months).
    """
    req_months = get_experience_requirement(category, product_name, service_type)
    if req_months is None:
        # If no requirement exists for this specific combination, we assume validation passes (0 months)
        return True, 0
    return experience_months >= req_months, req_months


def get_product_codes(category: str, product_name: str) -> tuple[str, str, str]:
    """Map category and product name to category_code, sub_category_code, and combined_code."""
    import re
    cat_upper = category.upper()
    prod_norm = normalize_product_name(product_name)
    
    # 1. Determine category code
    if "CATEGORY III" in cat_upper:
        cat_code = "3"
    elif "CATEGORY IIA" in cat_upper or "CATEGORY 2A" in cat_upper:
        cat_code = "20"
    elif "CATEGORY II" in cat_upper:
        cat_code = "2"
    elif "CATEGORY IV" in cat_upper:
        cat_code = "4"
    elif "CATEGORY I" in cat_upper:
        cat_code = "1"
    else:
        cat_code = ""

    # 2. Map subcategory codes
    subcat_code = ""
    
    cat1_map = {
        "long term insurance subcategory a": "1",
        "short term insurance personal lines": "2",
        "long term insurance subcategory b1": "3",
        "long term insurance subcategory c": "4",
        "retail pension benefits": "5",
        "short term insurance commercial lines": "6",
        "pension fund benefits": "7",
        "pension funds benefits": "7",
        "shares": "8",
        "money market instruments": "9",
        "debentures and securitised debt": "10",
        "warrants certificates or other instruments": "11",
        "warrants, certificates or other instruments": "11",
        "bonds": "12",
        "derivative instruments": "13",
        "participatory interests in a collective investment scheme": "14",
        "forex investment": "15",
        "health service benefits": "16",
        "long term insurance subcategory b2": "17",
        "long term insurance subcategory b2 a": "18",
        "long term insurance subcategory b2-a": "18",
        "long term insurance subcategory b1 a": "19",
        "long term insurance subcategory b1-a": "19",
        "short term insurance personal lines a1": "20",
        "long term insurance subcategory b2 b": "21",
        "long term insurance subcategory b2-b": "21",
        "long term insurance subcategory b1 b": "22",
        "long term insurance subcategory b1-b": "22",
        "structured deposits": "24",
        "short term insurance commercial lines a1": "26",
        "crypto assets": "27"
    }

    cat2_map = {
        "long term insurance subcategory b1": "1",
        "long term insurance subcategory c": "2",
        "retail pension benefits": "3",
        "pension fund benefits": "4",
        "pension funds benefits": "4",
        "shares": "5",
        "money market instruments": "6",
        "debentures and securitised debt": "7",
        "warrants certificates or other instruments": "8",
        "warrants, certificates or other instruments": "8",
        "bonds": "9",
        "derivative instruments": "10",
        "participatory interests in a collective investment scheme": "11",
        "participatory interests in one or more collective investment schemes": "11",
        "forex investment": "12",
        "long term insurance subcategory b2": "13",
        "long term insurance subcategory b2 a": "14",
        "long term insurance subcategory b2-a": "14",
        "long term insurance subcategory b1 a": "15",
        "long term insurance subcategory b1-a": "15",
        "long term insurance subcategory b2 b": "16",
        "long term insurance subcategory b2-b": "16",
        "long term insurance subcategory b1 b": "17",
        "long term insurance subcategory b1-b": "17",
        "structured deposits": "18",
        "crypto assets": "21"
    }

    cat3_map = {
        "long term insurance subcategory b1": "1",
        "long term insurance subcategory c": "2",
        "retail pension benefits": "3",
        "pension fund benefits": "4",
        "pension funds benefits": "4",
        "shares": "5",
        "money market instruments": "6",
        "debentures and securitised debt": "7",
        "warrants certificates or other instruments": "8",
        "warrants, certificates or other instruments": "8",
        "bonds": "9",
        "derivative instruments": "10",
        "participatory interests in a collective investment scheme": "11",
        "participatory interests in one or more collective investment schemes": "11",
        "forex investment": "12",
        "long term insurance subcategory b2": "13",
        "long term insurance subcategory b2 a": "14",
        "long term insurance subcategory b2-a": "14",
        "long term insurance subcategory b1 a": "15",
        "long term insurance subcategory b1-a": "15",
        "long term insurance subcategory b2 b": "16",
        "long term insurance subcategory b2-b": "16",
        "long term insurance subcategory b1 b": "17",
        "long term insurance subcategory b1-b": "17",
        "structured deposits": "18",
        "crypto assets": "21"
    }

    if cat_code == "1":
        for k, v in cat1_map.items():
            if k in prod_norm or prod_norm in k:
                subcat_code = v
                break
    elif cat_code == "2":
        for k, v in cat2_map.items():
            if k in prod_norm or prod_norm in k:
                subcat_code = v
                break
    elif cat_code == "3":
        for k, v in cat3_map.items():
            if k in prod_norm or prod_norm in k:
                subcat_code = v
                break
    elif cat_code == "4":
        if "assistance" in prod_norm:
            subcat_code = "1"
    elif cat_code == "20":
        if "hedge fund" in prod_norm:
            subcat_code = "1"

    if not subcat_code:
        m = re.search(r'\b\d+(?:\.\d+)?\b', product_name)
        if m:
            subcat_code = m.group(0)
        else:
            subcat_code = "1"
            
    combined_code = f"{cat_code}.{subcat_code}" if cat_code and subcat_code else ""
    return cat_code, subcat_code, combined_code
