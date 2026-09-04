import re

DECLARATION_TYPES = (
    "PRODUCT_NAME",
    "BRAND",
    "NET_QUANTITY",
    "MRP",
    "MANUFACTURER",
    "PACKER",
    "IMPORTER",
    "MANUFACTURING_DATE",
    "PACKING_DATE",
    "BEST_BEFORE",
    "USE_BY",
    "CONSUMER_CARE",
    "BATCH_LOT_NUMBER",
    "COUNTRY_OF_ORIGIN",
)

MRP_PATTERN = re.compile(
    r"(?i)\b(?:m[\s.]*r[\s.]*p|maximum\s+retail\s+price)\s*"
    r"[:.\-]*\s*(?:₹|rs\.?|inr)?\s*([0-9]+(?:[.,][0-9]{1,2})?)"
)
QUANTITY_PATTERN = re.compile(
    r"(?i)(?:net\s*(?:weight|wt|quantity|qty)|(?<![a-z])netwt)"
    r"\s*[:.\-]*\s*([0-9]+(?:[.,][0-9]+)?)\s*"
    r"(kg|kgs|g|gm|gram|grams|ml|millilitre|milliliter|l|lt|ltr|litre|liter)"
)
STANDALONE_QUANTITY_PATTERN = re.compile(
    r"(?i)(?<![a-z0-9])([0-9]+(?:[.,][0-9]+)?)\s*"
    r"(kg|kgs|g|gm|gram|grams|ml|millilitre|milliliter|l|lt|ltr|litre|liter)"
    r"\b"
)
DATE_PATTERN = re.compile(
    r"(?i)(\d{1,2}(?:[./-]\d{1,2})?[./-]\d{2,4}|\d{1,2}[/-]\d{4}|\d{4}[/-]\d{1,2})"
)
RELATIVE_DATE_PATTERN = re.compile(
    r"(?i)\b\d+\s+(?:months?|years?|days?)\s+from\s+the\s+date\s+of\s+packing\b"
)
BATCH_PATTERN = re.compile(
    r"(?i)\b(?:lot|batch)\s*\.?\s*(?:no|number)?\s*[:.\-]?\s*"
    r"([a-z0-9][a-z0-9./_-]*)|"
    r"\bb\s*\.?\s*(?:no|number)\s*[:.\-]?\s*([a-z0-9][a-z0-9./_-]*)"
)

LABEL_PATTERNS = {
    "BRAND": re.compile(r"(?i)\bbrand\s*[:.\-]?"),
    "MANUFACTURER": re.compile(
        r"(?i)\b(?:manufactured|manufacturing|mfg|mfd)\s*(?:by)?\s*[:.\-]?"
    ),
    "PACKER": re.compile(
        r"(?i)\b(?:packed|packing|pkd)\s*(?:by)?\s*[:.\-]?"
    ),
    "IMPORTER": re.compile(r"(?i)\b(?:imported|importer)\s*(?:by)?\s*[:.\-]?"),
    "BEST_BEFORE": re.compile(r"(?i)\b(?:best\s*before)\s*[:.\-]?"),
    "USE_BY": re.compile(r"(?i)\b(?:use\s*by|expiry|exp)\s*[:.\-]?"),
    "CONSUMER_CARE": re.compile(
        r"(?i)\b(?:consumer\s*care|customer\s*care|customer\s*service|"
        r"helpline|contact|phone|email|complaints?|suggestions?|queries?)\b"
    ),
    "COUNTRY_OF_ORIGIN": re.compile(
        r"(?i)\b(?:country\s+of\s+origin|made\s+in|origin)\s*[:.\-]?"
    ),
}
