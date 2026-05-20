"""Seed the dummy Turtlemint database into the embedded ClickHouse (chdb) store.

Run once before starting the backend:

    python -m app.data.seed

Re-running drops and recreates everything. Stop the backend first (it holds the
chdb session open).
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import List

from chdb import session as chs

from app.backend import config
from app.backend.schema_catalog import CATALOG

random.seed(42)  # deterministic categorical/text data
NOW = datetime.now()  # dates are seeded relative to "now" so temporal queries work

# Volumes
N_PARTNERS = 300
N_CUSTOMERS = 2000
N_POLICIES = 5000
CLAIM_RATE = 0.24  # fraction of policies with a claim

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Reyansh", "Mohammed", "Sai",
    "Krishna", "Ishaan", "Asha", "Priya", "Ananya", "Diya", "Aanya", "Saanvi",
    "Aadhya", "Kavya", "Fatima", "Neha", "Rohan", "Karan", "Vikram", "Rahul",
    "Sneha", "Pooja", "Meera", "Divya", "Suresh", "Ramesh",
]
LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Reddy", "Nair", "Iyer", "Rao", "Shah", "Gupta",
    "Mehta", "Joshi", "Kumar", "Singh", "Das", "Bose", "Chopra", "Kapoor",
    "Menon", "Pillai", "Desai",
]
CITY_STATE = [
    ("Mumbai", "Maharashtra"), ("Pune", "Maharashtra"), ("Bengaluru", "Karnataka"),
    ("Mysuru", "Karnataka"), ("Chennai", "Tamil Nadu"), ("Coimbatore", "Tamil Nadu"),
    ("Hyderabad", "Telangana"), ("Delhi", "Delhi"), ("Gurugram", "Haryana"),
    ("Ahmedabad", "Gujarat"), ("Surat", "Gujarat"), ("Jaipur", "Rajasthan"),
    ("Kolkata", "West Bengal"), ("Lucknow", "Uttar Pradesh"), ("Kochi", "Kerala"),
    ("Indore", "Madhya Pradesh"),
]
INSURERS = [
    "HDFC Ergo", "ICICI Lombard", "Bajaj Allianz", "Tata AIG", "Star Health",
    "Max Bupa", "SBI General", "Reliance General",
]
PRODUCT_TYPES = ["motor", "health", "life", "travel"]
PARTNER_STATUS = ["active", "active", "active", "inactive", "lapsed"]  # weighted
TIERS = ["bronze", "bronze", "silver", "silver", "gold", "platinum"]
POLICY_STATUS = ["active", "active", "active", "lapsed", "expired", "cancelled"]
CLAIM_STATUS = ["filed", "under_review", "approved", "rejected", "settled", "settled"]


def full_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def dt_within_days(max_days_ago: int, min_days_ago: int = 0) -> datetime:
    days = random.randint(min_days_ago, max_days_ago)
    secs = random.randint(0, 86399)
    return NOW - timedelta(days=days, seconds=secs)


def q(val: str) -> str:
    """Quote/escape a string for a ClickHouse string literal."""
    return "'" + val.replace("\\", "\\\\").replace("'", "''") + "'"


def dts(d: datetime) -> str:
    return q(d.strftime("%Y-%m-%d %H:%M:%S"))


def ds(d: datetime) -> str:
    return q(d.strftime("%Y-%m-%d"))


def create_schema(sess: chs.Session) -> None:
    db = CATALOG["database"]
    sess.query(f"DROP DATABASE IF EXISTS {db}")
    sess.query(f"CREATE DATABASE {db}")
    for t in CATALOG["tables"]:
        cols = ", ".join(f"{c['name']} {c['type']}" for c in t["columns"])
        sess.query(
            f"CREATE TABLE {db}.{t['name']} ({cols}) "
            f"ENGINE = MergeTree ORDER BY ({t['order_by']})"
        )


def insert_rows(sess: chs.Session, table: str, rows: List[str], batch: int = 1000) -> None:
    db = CATALOG["database"]
    for i in range(0, len(rows), batch):
        chunk = ",".join(rows[i:i + batch])
        sess.query(f"INSERT INTO {db}.{table} VALUES {chunk}")


def seed() -> None:
    config.ensure_dirs()
    sess = chs.Session(config.CHDB_PATH)
    try:
        create_schema(sess)

        # --- partners ---
        partner_rows = []
        for pid in range(1, N_PARTNERS + 1):
            city, state = random.choice(CITY_STATE)
            created = dt_within_days(540, 1)
            last_active = created + timedelta(days=random.randint(0, (NOW - created).days or 1))
            partner_rows.append(
                f"({pid},{q(full_name())},{q(city)},{q(state)},"
                f"{q(random.choice(PARTNER_STATUS))},{q(random.choice(TIERS))},"
                f"{dts(created)},{dts(min(last_active, NOW))})"
            )
        insert_rows(sess, "partner", partner_rows)

        # --- customers ---
        customer_rows = []
        for cid in range(1, N_CUSTOMERS + 1):
            city, state = random.choice(CITY_STATE)
            customer_rows.append(
                f"({cid},{q(full_name())},{q(city)},{q(state)},"
                f"{random.randint(18, 75)},{q(random.choice(['M', 'F']))},"
                f"{dts(dt_within_days(540, 1))})"
            )
        insert_rows(sess, "customer", customer_rows)

        # --- policies + commissions ---
        policy_rows, commission_rows = [], []
        for pol_id in range(1, N_POLICIES + 1):
            partner_id = random.randint(1, N_PARTNERS)
            customer_id = random.randint(1, N_CUSTOMERS)
            product = random.choice(PRODUCT_TYPES)
            premium = round(random.uniform(2000, 60000), 2)
            sum_assured = round(premium * random.uniform(8, 40), 2)
            issued = dt_within_days(540, 1)
            expiry = issued + timedelta(days=365)
            policy_rows.append(
                f"({pol_id},{partner_id},{customer_id},{q(product)},"
                f"{q(random.choice(INSURERS))},{premium},{sum_assured},"
                f"{q(random.choice(POLICY_STATUS))},{dts(issued)},{ds(expiry)})"
            )
            # commission ~ 12% of premium
            comm = round(premium * random.uniform(0.08, 0.18), 2)
            paid = random.random() < 0.7
            paid_at = dts(issued + timedelta(days=random.randint(15, 60))) if paid else "NULL"
            commission_rows.append(
                f"({pol_id},{partner_id},{pol_id},{comm},"
                f"{q('paid') if paid else q('pending')},{paid_at})"
            )
        insert_rows(sess, "policy", policy_rows)
        insert_rows(sess, "commission", commission_rows)

        # --- claims (subset of policies) ---
        claim_rows = []
        claim_id = 0
        for pol_id in range(1, N_POLICIES + 1):
            if random.random() > CLAIM_RATE:
                continue
            claim_id += 1
            status = random.choice(CLAIM_STATUS)
            amount = round(random.uniform(5000, 400000), 2)
            filed = dt_within_days(400, 1)
            if status == "settled":
                approved = round(amount * random.uniform(0.5, 1.0), 2)
                settled_at = dts(filed + timedelta(days=random.randint(5, 90)))
            elif status == "approved":
                approved = round(amount * random.uniform(0.5, 1.0), 2)
                settled_at = "NULL"
            else:
                approved = 0.0
                settled_at = "NULL"
            claim_rows.append(
                f"({claim_id},{pol_id},{amount},{approved},{q(status)},"
                f"{dts(filed)},{settled_at})"
            )
        insert_rows(sess, "claim", claim_rows)

        # --- report ---
        db = CATALOG["database"]
        print("Seeded dummy data into embedded ClickHouse (chdb):")
        for t in CATALOG["tables"]:
            res = sess.query(f"SELECT count(*) FROM {db}.{t['name']}", "CSV")
            print(f"  {t['name']:<12} {str(res).strip()} rows")
        print(f"\nStore path: {config.CHDB_PATH}")
    finally:
        sess.close()


if __name__ == "__main__":
    seed()
