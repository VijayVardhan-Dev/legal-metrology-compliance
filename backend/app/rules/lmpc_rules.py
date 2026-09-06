from app.rules.base import RuleDefinition


LMPC_SOURCE = (
    "https://consumeraffairs.nic.in/sites/default/files/"
    "file-uploads/legal-metrology/packaged-commoditiesrules.pdf"
)


LMPC_RULES = [
    RuleDefinition(
        "LM-PC-001", "LMPC", "Rule 3", "Determine whether packaged-commodity requirements apply.",
        {"requires": ["package_quantity_or_unit", "industrial_institutional_context"]},
        ["Rule 3 exemptions must be evaluated from package/context facts."], None,
        "APPLICABILITY_GATEWAY", "HIGH", "2011", LMPC_SOURCE,
        "This gateway does not assume retail applicability when package/context facts are unavailable.",
        "Applicability & Exemption Limits", "applicability", "Rule 3 applicability gateway.",
    ),
    RuleDefinition(
        "LM-PC-002", "LMPC", "Rule 6(1)(a)", "Declare the identity and address of manufacturer, packer, or importer.",
        {"requires": ["applicable_identity"]}, [], "MANUFACTURER", "PRESENCE", "HIGH", "2011",
        LMPC_SOURCE, "A clearly incomplete identity is reviewable; absent identity is a definitive failure when applicable.",
        "Identity of Manufacturer / Packer / Importer", "identity", "Identity declaration.",
    ),
    RuleDefinition(
        "LM-PC-003", "LMPC", "Rule 6(1)(b)", "Declare the generic name of the commodity.",
        {"requires": ["confident_commodity_classification"]}, [], "PRODUCT_NAME", "GENERIC_NAME", "HIGH", "2011",
        LMPC_SOURCE, "A brand name alone is not treated as a generic commodity name.",
        "Generic Commodity Name", "product_name", "Generic commodity name.",
    ),
    RuleDefinition(
        "LM-PC-004", "LMPC", "Rule 6(1)(c)", "Declare net quantity using a numeric value and recognizable unit.",
        {"requires": ["applicable_identity"]}, [], "NET_QUANTITY", "NUMERIC_UNIT", "HIGH", "2011",
        LMPC_SOURCE, "Numeric quantity and unit are checked without applying legal tolerances.",
        "Net Quantity Presence", "net_quantity", "Net quantity declaration.",
    ),
    RuleDefinition(
        "LM-PC-005", "LMPC", "Rule 6(1)(e)", "Declare the retail sale price / maximum retail price.",
        {"requires": ["applicable_identity"]}, [], "MRP", "PRICE", "HIGH", "2011",
        LMPC_SOURCE, "No unsupported currency phrase or tax wording is required by this MVP check.",
        "Retail Sale Price / MRP", "mrp", "MRP declaration.",
    ),
    RuleDefinition(
        "LM-PC-008", "LMPC", "Rule 6(2)", "Declare consumer-care contact information.",
        {"requires": ["applicable_identity"]}, [], "CONSUMER_CARE", "CONTACT", "MEDIUM", "2011",
        LMPC_SOURCE, "Phone, email, or address evidence is accepted as contact evidence.",
        "Consumer Care Information", "consumer_care", "Consumer care information.",
    ),
    RuleDefinition(
        "LM-PC-010", "LMPC", "Rule 6(1)(aa)", "Declare country of origin for imported commodities.",
        {"requires": ["import_status"]}, [], "COUNTRY_OF_ORIGIN", "IMPORTED_ONLY", "HIGH", "2011",
        LMPC_SOURCE, "Domestic goods do not fail solely because origin is absent.",
        "Country of Origin", "origin", "Country of origin.",
    ),
]
