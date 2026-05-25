"""Dummy schema catalog for the NL-SQL tool.

This is the stand-in for OpenMetadata during the dummy-data phase. It is the
SINGLE source of truth for:
  * the dummy database DDL (the seed script builds tables from this), and
  * the schema context handed to the LLM at SQL-generation time.

When real data arrives, this module gets replaced by a live OpenMetadata
fetch (per the SOW's hybrid schema strategy) — the rest of the pipeline is
unchanged because everyone reads the schema through these helpers.
"""
from __future__ import annotations

from typing import Dict, List

from app.backend.config import DB_NAME

CATALOG: Dict = {
    "database": DB_NAME,
    "tables": [
        {
            "name": "partner",
            "description": "Insurance advisors (POSP) who sign up on Turtlemint and sell policies.",
            "order_by": "partner_id",
            "columns": [
                {"name": "partner_id", "type": "UInt32", "description": "Unique partner ID."},
                {"name": "name", "type": "String", "description": "Partner's full name."},
                {"name": "city", "type": "String", "description": "City the partner operates in."},
                {"name": "state", "type": "String", "description": "Indian state of the partner."},
                {"name": "status", "type": "String", "description": "One of 'active', 'inactive', 'lapsed'."},
                {"name": "tier", "type": "String", "description": "Performance tier: 'bronze', 'silver', 'gold', 'platinum'."},
                {"name": "created_at", "type": "DateTime", "description": "When the partner signed up."},
                {"name": "last_active_at", "type": "DateTime", "description": "Last time the partner was active on the platform."},
            ],
        },
        {
            "name": "customer",
            "description": "End customers who purchase insurance policies.",
            "order_by": "customer_id",
            "columns": [
                {"name": "customer_id", "type": "UInt32", "description": "Unique customer ID."},
                {"name": "name", "type": "String", "description": "Customer's full name."},
                {"name": "city", "type": "String", "description": "Customer's city."},
                {"name": "state", "type": "String", "description": "Customer's Indian state."},
                {"name": "age", "type": "UInt8", "description": "Customer age in years."},
                {"name": "gender", "type": "String", "description": "'M' or 'F'."},
                {"name": "created_at", "type": "DateTime", "description": "When the customer record was created."},
            ],
        },
        {
            "name": "policy",
            "description": "Insurance policies sold through partners to customers.",
            "order_by": "policy_id",
            "columns": [
                {"name": "policy_id", "type": "UInt32", "description": "Unique policy ID."},
                {"name": "partner_id", "type": "UInt32", "description": "Partner who sold the policy (joins partner.partner_id)."},
                {"name": "customer_id", "type": "UInt32", "description": "Customer who bought it (joins customer.customer_id)."},
                {"name": "product_type", "type": "String", "description": "Line of business: 'motor', 'health', 'life', 'travel'."},
                {"name": "insurer", "type": "String", "description": "Underwriting insurer, e.g. 'HDFC Ergo', 'ICICI Lombard'."},
                {"name": "premium", "type": "Float64", "description": "Annual premium in INR."},
                {"name": "sum_assured", "type": "Float64", "description": "Sum assured / coverage amount in INR."},
                {"name": "status", "type": "String", "description": "One of 'active', 'lapsed', 'expired', 'cancelled'."},
                {"name": "issued_at", "type": "DateTime", "description": "When the policy was issued (new business date)."},
                {"name": "expiry_date", "type": "Date", "description": "Policy expiry date."},
            ],
        },
        {
            "name": "claim",
            "description": "Claims filed against policies.",
            "order_by": "claim_id",
            "columns": [
                {"name": "claim_id", "type": "UInt32", "description": "Unique claim ID."},
                {"name": "policy_id", "type": "UInt32", "description": "Policy the claim is against (joins policy.policy_id)."},
                {"name": "amount", "type": "Float64", "description": "Amount claimed in INR."},
                {"name": "approved_amount", "type": "Float64", "description": "Amount approved/settled in INR (0 if not yet settled)."},
                {"name": "status", "type": "String", "description": "One of 'filed', 'under_review', 'approved', 'rejected', 'settled'."},
                {"name": "filed_at", "type": "DateTime", "description": "When the claim was filed."},
                {"name": "settled_at", "type": "Nullable(DateTime)", "description": "When the claim was settled; NULL if not settled."},
            ],
        },
        {
            "name": "commission",
            "description": "Commission earned by partners on policies they sold.",
            "order_by": "commission_id",
            "columns": [
                {"name": "commission_id", "type": "UInt32", "description": "Unique commission record ID."},
                {"name": "partner_id", "type": "UInt32", "description": "Partner who earned it (joins partner.partner_id)."},
                {"name": "policy_id", "type": "UInt32", "description": "Policy it was earned on (joins policy.policy_id)."},
                {"name": "amount", "type": "Float64", "description": "Commission amount in INR."},
                {"name": "status", "type": "String", "description": "'pending' or 'paid'."},
                {"name": "paid_at", "type": "Nullable(DateTime)", "description": "When commission was paid; NULL if pending."},
            ],
        },
        # ── Real data from Turtlemint OpenMetadata (ch-spectrum.spectrum.spectrum.policydetail) ──
        {
            "name": "policydetail",
            "database": "spectrum",           # overrides default DB_NAME
            "description": "Real Turtlemint policy records from ClickHouse Spectrum — life, motor, health policies with full sales hierarchy, premium and payment details.",
            "order_by": "_id",
            "columns": [
                {"name": "_id",                                   "type": "String",           "description": "Unique MIS folder / policy record ID (e.g. MIS_PGLI40TZKTM)."},
                {"name": "policynumber",                          "type": "String",           "description": "Insurer-assigned policy number."},
                {"name": "status",                                "type": "String",           "description": "Policy status: ACTIVE, LAPSED, CANCELLED, etc."},
                {"name": "substatus",                             "type": "String",           "description": "Sub-status: IN_FORCE, LAPSED, PAID_UP, etc."},
                {"name": "recordstatus",                          "type": "String",           "description": "MIS record status: COMPLETE, PENDING, etc."},
                {"name": "qcstatus",                              "type": "String",           "description": "QC status: RESOLVED, PENDING, etc."},
                {"name": "vertical",                              "type": "String",           "description": "Business vertical: LIFE, MOTOR, HEALTH, TRAVEL."},
                {"name": "businessvertical",                      "type": "String",           "description": "Business vertical label: Retail, SME, etc."},
                {"name": "productcategory",                       "type": "String",           "description": "Product category: LIFE, MOTOR, HEALTH, etc."},
                {"name": "category",                              "type": "String",           "description": "Product sub-category: term, ulip, traditional, endowment, etc."},
                {"name": "plantype",                              "type": "String",           "description": "Plan type: ulip, traditional, term, etc."},
                {"name": "planname",                              "type": "String",           "description": "Full plan/product name, e.g. 'ICICI Pru Life Time Classic'."},
                {"name": "insurer",                               "type": "String",           "description": "Insurer code, e.g. ICICIPRULI, HDFCLI, SBILI, MAXLI."},
                {"name": "businesstype",                          "type": "String",           "description": "NEW or RENEWAL."},
                {"name": "channeltype",                           "type": "String",           "description": "Sales channel: partner, direct, bqp, etc."},
                {"name": "createdat",                             "type": "Nullable(DateTime)","description": "Record creation timestamp."},
                {"name": "issuancedate",                          "type": "Nullable(DateTime)","description": "Date the policy was issued by the insurer."},
                {"name": "startdate",                             "type": "Nullable(DateTime)","description": "Policy risk start date."},
                {"name": "enddate",                               "type": "Nullable(DateTime)","description": "Policy risk end date / maturity date."},
                {"name": "sales_date",                            "type": "Nullable(DateTime)","description": "Date the sale was closed."},
                {"name": "year",                                  "type": "Nullable(Int32)",  "description": "Year of the sales_date (partition key)."},
                {"name": "month",                                 "type": "Nullable(Int32)",  "description": "Month of the sales_date (1–12)."},
                {"name": "premiumdetails_grosspremium",           "type": "Nullable(Float64)","description": "Gross premium in INR (including taxes)."},
                {"name": "premiumdetails_netpremium",             "type": "Nullable(Float64)","description": "Net premium in INR (excluding taxes)."},
                {"name": "premiumdetails_annualisednetpremium",   "type": "Nullable(Float64)","description": "Annualised net premium — use for yearly premium comparisons."},
                {"name": "premiumdetails_servicetax",             "type": "Nullable(Float64)","description": "GST / service tax component of premium in INR."},
                {"name": "payment_paidamount",                    "type": "Nullable(Float64)","description": "Total amount paid by the customer so far in INR."},
                {"name": "payment_paymentstatus",                 "type": "String",           "description": "Payment status: Completed, Pending, Overdue."},
                {"name": "payment_paymentfrequency",              "type": "String",           "description": "Payment frequency: MONTHLY, QUARTERLY, ANNUAL, SINGLE."},
                {"name": "payment_totalinstallementpaid",         "type": "Nullable(Int32)",  "description": "Number of instalments paid so far."},
                {"name": "payment_installmentamount",             "type": "Nullable(Float64)","description": "Per-instalment amount in INR."},
                {"name": "eligiblepremiumdetail_eligiblepremium", "type": "Nullable(Float64)","description": "Eligible premium for payout calculation."},
                {"name": "policyrisk_suminsured",                 "type": "Nullable(Float64)","description": "Sum insured / sum assured in INR."},
                {"name": "policyrisk_policyterm",                 "type": "Nullable(Int32)",  "description": "Total policy term in years."},
                {"name": "salesdetail_region",                    "type": "String",           "description": "Sales region: East, West, North, South."},
                {"name": "salesdetail_branchlocation",            "type": "String",           "description": "Branch city/location where the sale originated."},
                {"name": "salesdetail_intermediaryname",          "type": "String",           "description": "Partner/intermediary name who sold the policy."},
                {"name": "salesdetail_intermediaryinternalid",    "type": "String",           "description": "Internal DP number of the selling partner, e.g. 'DP - 1915334'."},
                {"name": "salesdetail_intermediarylevel",         "type": "String",           "description": "Partner level: partner_level_1, partner_level_2, etc."},
                {"name": "salesdetail_am",                        "type": "String",           "description": "Area Manager name for this sale."},
                {"name": "salesdetail_rm",                        "type": "String",           "description": "Relationship Manager name for this sale."},
                {"name": "salesdetail_sm",                        "type": "String",           "description": "Sales Manager name for this sale."},
                {"name": "salesdetail_nationalhead",              "type": "String",           "description": "National Head name for this sale."},
                {"name": "pibranchlocation",                      "type": "String",           "description": "PI branch location city."},
                {"name": "leadid",                                "type": "String",           "description": "Lead ID that originated this policy (joins lead management system)."},
                {"name": "customerid",                            "type": "String",           "description": "Customer ID (joins customer records)."},
                {"name": "tenant",                                "type": "String",           "description": "Tenant identifier, always 'turtlemint'."},
            ],
        },

        # ── Sachet lending platform — MongoDB BSON dumps ──────────────────────
        {
            "name": "leadorderinfo",
            "database": "sachet",
            "description": (
                "Sachet lending platform loan leads (100k+ records). "
                "Tracks personal-loan and other lending product leads through the "
                "funnel from quote → credit-stage → proposal → payment. "
                "IMPORTANT: columns use flattened snake_case names, e.g. "
                "leadcustomerinfo_customername, leadcustomerinfo_pan."
            ),
            "order_by": "_id",
            "columns": [
                {"name": "_id",                               "type": "String",            "description": "MongoDB document ID."},
                {"name": "externalleadid",                    "type": "String",            "description": "External reference ID for this lead."},
                {"name": "leadid",                            "type": "String",            "description": "Internal Turtlemint lead ID."},
                {"name": "aggregatorid",                      "type": "String",            "description": "Aggregator reference ID."},
                {"name": "referenceid",                       "type": "String",            "description": "Reference ID (same as externalleadid in most cases)."},
                {"name": "productcode",                       "type": "String",            "description": "Product type: personal-loan, mobile, health, motor, etc."},
                {"name": "leadstage",                         "type": "String",            "description": "Current funnel stage: quote, credit-stage, proposal, payment, issuance, Preoffer drop-off, closed."},
                {"name": "leadstatus",                        "type": "String",            "description": "Lead status: active, closed, any."},
                {"name": "leadquality",                       "type": "String",            "description": "Lead quality score: GOOD, BAD, MEDIUM."},
                {"name": "leadsource",                        "type": "String",            "description": "Lead source: NEW, RENEWAL, etc."},
                {"name": "provider",                          "type": "String",            "description": "Lender/provider assigned to this lead, e.g. kissht, pfl, moneyview, smfg."},
                {"name": "partnerid",                         "type": "String",            "description": "Partner who originated the lead."},
                {"name": "partnername",                       "type": "String",            "description": "Partner display name."},
                {"name": "partnermobile",                     "type": "String",            "description": "Partner mobile number."},
                {"name": "broker",                            "type": "String",            "description": "Broker: always turtlemint."},
                {"name": "tenant",                            "type": "String",            "description": "Tenant: always turtlemint."},
                {"name": "createdat",                         "type": "Nullable(DateTime)","description": "When the lead was created."},
                {"name": "updatedat",                         "type": "Nullable(DateTime)","description": "When the lead was last updated."},
                {"name": "transactiondate",                   "type": "Nullable(DateTime)","description": "Transaction date (date portion of lead creation)."},
                {"name": "journey_journeytype",               "type": "String",            "description": "Journey type: assisted (partner-assisted) or direct (customer self-serve)."},
                {"name": "leadcustomerinfo_customername",     "type": "String",            "description": "Customer full name."},
                {"name": "leadcustomerinfo_firstname",        "type": "String",            "description": "Customer first name."},
                {"name": "leadcustomerinfo_lastname",         "type": "String",            "description": "Customer last name."},
                {"name": "leadcustomerinfo_mobilenumber",     "type": "String",            "description": "Customer mobile number."},
                {"name": "leadcustomerinfo_pan",              "type": "String",            "description": "Customer PAN number."},
                {"name": "leadcustomerinfo_dob",              "type": "String",            "description": "Customer date of birth (DD/MM/YYYY)."},
                {"name": "leadcustomerinfo_city",             "type": "String",            "description": "Customer city."},
                {"name": "leadcustomerinfo_gender",           "type": "String",            "description": "Customer gender: Male, Female."},
                {"name": "leadcustomerinfo_monthlyincome",    "type": "Nullable(Float64)", "description": "Customer monthly income in INR."},
                {"name": "leadcustomerinfo_loanamount",       "type": "Nullable(Float64)", "description": "Requested loan amount in INR."},
                {"name": "leadcustomerinfo_creditscore",      "type": "String",            "description": "Credit score (CRIF): numeric string or 'NA' / '0' if unavailable."},
                {"name": "leadcustomerinfo_creditscoreavailable", "type": "String",        "description": "Whether credit score was successfully fetched: True/False."},
                {"name": "leadcustomerinfo_otpsubmitted",     "type": "String",            "description": "Whether customer submitted OTP consent: True/False."},
                {"name": "leadcustomerinfo_panvalid",         "type": "String",            "description": "Whether PAN was validated: True/False."},
                {"name": "leadcustomerinfo_employmenttype",   "type": "String",            "description": "Customer employment type: Salaried, Self-employed, etc."},
                {"name": "leadextrainfo_leadsavestatus",      "type": "String",            "description": "Lead save status: SUCCESS, FAILED."},
                {"name": "leadextrainfo_isofferselected",     "type": "String",            "description": "Whether customer selected a loan offer: True/False."},
                {"name": "leadextrainfo_isleadformsubmitted", "type": "String",            "description": "Whether lead form was fully submitted: True/False."},
                {"name": "leadextrainfo_isapioffer",          "type": "String",            "description": "Whether an API-based offer was generated: True/False."},
                {"name": "leadextrainfo_apireject",           "type": "String",            "description": "Whether lead was rejected by lender API: True/False."},
            ],
        },
        {
            "name": "loanoffers",
            "database": "sachet",
            "description": (
                "Loan offer responses from lenders for personal-loan applications. "
                "One row per offer (exploded from offers[] array). "
                "IMPORTANT: columns use flattened snake_case names. "
                "offer_* columns are per-lender offer details."
            ),
            "order_by": "_id",
            "columns": [
                {"name": "_id",                               "type": "String",            "description": "MongoDB document ID (parent loan application)."},
                {"name": "referenceid",                       "type": "String",            "description": "Reference ID for this loan application."},
                {"name": "externalleadid",                    "type": "String",            "description": "External lead ID."},
                {"name": "aggregatorid",                      "type": "String",            "description": "Aggregator reference ID."},
                {"name": "productcode",                       "type": "String",            "description": "Product: personal-loan."},
                {"name": "flowtype",                          "type": "String",            "description": "Flow type: OFFERS."},
                {"name": "leadquality",                       "type": "String",            "description": "Lead quality: GOOD, BAD, MEDIUM."},
                {"name": "totaloffers",                       "type": "Nullable(Int32)",   "description": "Total number of lender offers received for this application."},
                {"name": "processedoffers",                   "type": "Nullable(Int32)",   "description": "Number of offers processed/returned."},
                {"name": "apiofferavailable",                 "type": "String",            "description": "Whether at least one API offer was available: True/False."},
                {"name": "transactiondate",                   "type": "Nullable(DateTime)","description": "Date of the loan offer request."},
                {"name": "createdat",                         "type": "Nullable(DateTime)","description": "When this record was created."},
                {"name": "leadcustomerinfo_customername",     "type": "String",            "description": "Applicant full name."},
                {"name": "leadcustomerinfo_pan",              "type": "String",            "description": "Applicant PAN."},
                {"name": "leadcustomerinfo_mobilenumber",     "type": "String",            "description": "Applicant mobile number."},
                {"name": "leadcustomerinfo_monthlyincome",    "type": "Nullable(Float64)", "description": "Applicant monthly income in INR."},
                {"name": "leadcustomerinfo_loanamount",       "type": "Nullable(Float64)", "description": "Requested loan amount in INR."},
                {"name": "leadcustomerinfo_creditscore",      "type": "String",            "description": "CRIF credit score (numeric or 'NA')."},
                {"name": "leadcustomerinfo_employmenttype",   "type": "String",            "description": "Employment type: Salaried, Self-employed."},
                {"name": "leadcustomerinfo_gender",           "type": "String",            "description": "Gender."},
                {"name": "offer_provider",                    "type": "String",            "description": "Lender name for this offer: smfg, kissht, moneyview, pfl, stashfin, herofincorp."},
                {"name": "offer_loanamount",                  "type": "Nullable(Float64)", "description": "Loan amount offered by this lender in INR."},
                {"name": "offer_roi",                         "type": "Nullable(Float64)", "description": "Rate of interest offered by this lender (% per annum)."},
                {"name": "offer_interestrate",                "type": "Nullable(Float64)", "description": "Interest rate (same as roi for most lenders)."},
                {"name": "offer_emi",                         "type": "Nullable(Float64)", "description": "Monthly EMI for this offer in INR."},
                {"name": "offer_processingfee",               "type": "Nullable(Float64)", "description": "Processing fee charged by this lender in INR."},
                {"name": "offer_status",                      "type": "String",            "description": "Offer status: success, reject."},
                {"name": "offer_isgridreject",                "type": "String",            "description": "Whether rejected by eligibility grid (True/False)."},
                {"name": "offer_isapiReject",                 "type": "String",            "description": "Whether rejected by lender API (True/False)."},
            ],
        },
    ],
    "business_definitions": [
        {"term": "active partner", "definition": "A partner whose status = 'active'."},
        {"term": "signed up", "definition": "Refers to partner.created_at (partner) or customer.created_at (customer)."},
        {"term": "new business", "definition": "Policies issued in a period, measured by policy.issued_at."},
        {"term": "lapsed policy", "definition": "A policy whose status = 'lapsed'."},
        {"term": "settled claim", "definition": "A claim whose status = 'settled'."},
        {"term": "GWP", "definition": "Gross Written Premium = sum(policy.premium) over issued policies in a period."},
        {"term": "premium", "definition": "policy.premium, the annual premium in INR."},
        {"term": "claim ratio", "definition": "sum(claim.approved_amount) / sum(policy.premium) for the relevant scope."},
    ],
    "example_queries": [
        {
            "question": "How many partners signed up last month?",
            "sql": "SELECT count(*) AS partners_signed_up FROM turtlemint.partner "
                   "WHERE toStartOfMonth(created_at) = toStartOfMonth(addMonths(now(), -1))",
        },
        {
            "question": "What is the total premium by product type?",
            "sql": "SELECT product_type, round(sum(premium), 2) AS total_premium "
                   "FROM turtlemint.policy GROUP BY product_type ORDER BY total_premium DESC",
        },
        {
            "question": "Top 5 partners by number of policies sold",
            "sql": "SELECT p.name AS partner, count() AS policies_sold "
                   "FROM turtlemint.policy AS pol "
                   "JOIN turtlemint.partner AS p ON p.partner_id = pol.partner_id "
                   "GROUP BY p.name ORDER BY policies_sold DESC LIMIT 5",
        },
        {
            "question": "How many claims are still pending settlement?",
            "sql": "SELECT count(*) AS open_claims FROM turtlemint.claim "
                   "WHERE status IN ('filed', 'under_review', 'approved')",
        },
    ],
}


def schema_prompt() -> str:
    """Render the catalog as a compact text block for the LLM prompt."""
    db = CATALOG["database"]
    lines: List[str] = [f"Database: {db} (ClickHouse dialect)", ""]
    for table in CATALOG["tables"]:
        lines.append(f"TABLE {db}.{table['name']} -- {table['description']}")
        for col in table["columns"]:
            lines.append(f"  {col['name']} {col['type']} -- {col['description']}")
        lines.append("")
    lines.append("Business definitions:")
    for d in CATALOG["business_definitions"]:
        lines.append(f"  - {d['term']}: {d['definition']}")
    return "\n".join(lines)


def example_block() -> str:
    """Few-shot example question -> SQL pairs (the golden-set seed)."""
    out: List[str] = []
    for ex in CATALOG["example_queries"]:
        out.append(f"Q: {ex['question']}\nSQL: {ex['sql']}")
    return "\n\n".join(out)


def table_names() -> List[str]:
    return [t["name"] for t in CATALOG["tables"]]


# Business domains for the Intent Agent.
DOMAINS: List[str] = ["Partners", "Customers", "Policies", "Claims", "Commissions"]


def get_table(name: str):
    for t in CATALOG["tables"]:
        if t["name"] == name:
            return t
    return None


def table_doc(table) -> str:
    """One embeddable text blob describing a table (for the vector index)."""
    cols = ", ".join(c["name"] for c in table["columns"])
    return f"{table['name']}: {table['description']} Columns: {cols}"


def schema_prompt_for(tables: List[str], pruned: dict = None) -> str:
    """Render schema for just the chosen tables — the 'live schema fetch' output.

    `pruned`, if given, is {table_name: [keep_columns]} from the Column Prune
    Agent; otherwise all columns are included.

    Each table uses its own `database` field if set, otherwise the catalog default.
    """
    default_db = CATALOG["database"]
    lines: List[str] = ["ClickHouse dialect — always qualify table as db.table", ""]
    for name in tables:
        t = get_table(name)
        if not t:
            continue
        db = t.get("database", default_db)   # real tables may be in spectrum db
        keep = set(pruned.get(name, [])) if pruned else None
        lines.append(f"TABLE {db}.{t['name']} -- {t['description']}")
        for col in t["columns"]:
            if keep is None or col["name"] in keep:
                lines.append(f"  {col['name']} {col['type']} -- {col['description']}")
        lines.append("")
    lines.append("Business definitions:")
    for d in CATALOG["business_definitions"]:
        lines.append(f"  - {d['term']}: {d['definition']}")
    return "\n".join(lines)
