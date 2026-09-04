from app.rules.base import RuleDefinition


FSSAI_SOURCE = "https://www.fssai.gov.in/cms/food-safety-and-standards-regulations.php"


FSSAI_RULES = [
    RuleDefinition(
        "FSSAI-001", "FSSAI", "FSS (Labelling and Display) Regulations 2020",
        "Declare the applicable date of manufacture or packaging for food.",
        {"requires": ["food_commodity"]}, [], "MANUFACTURING_DATE", "DATE", "HIGH", "2020",
        FSSAI_SOURCE, "Food applicability is based on the stored product category.",
        "Date of Manufacture / Packaging", "food_date", "Manufacture or packaging date.",
    ),
    RuleDefinition(
        "FSSAI-002", "FSSAI", "FSS (Labelling and Display) Regulations 2020",
        "Declare an expiry or use-by date for food.",
        {"requires": ["food_commodity"]}, [], "USE_BY", "EXPIRY_USE_BY", "HIGH", "2020",
        FSSAI_SOURCE, "BEST_BEFORE is not automatically treated as USE_BY.",
        "Expiry / Use-by Date", "food_date", "Expiry or use-by date.",
    ),
    RuleDefinition(
        "FSSAI-003", "FSSAI", "FSS (Labelling and Display) Regulations 2020",
        "Declare a batch, lot, or code identifier for food.",
        {"requires": ["food_commodity"]}, [], "BATCH_LOT_NUMBER", "BATCH", "HIGH", "2020",
        FSSAI_SOURCE, "A batch/lot/code identifier must be present and readable.",
        "Batch / Lot Number", "batch", "Batch or lot identifier.",
    ),
]
