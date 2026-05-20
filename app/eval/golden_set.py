"""Golden evaluation set — questions with their expected intent, tables, and a
hand-verified correct ClickHouse SQL. This is the accuracy benchmark from the
SOW; grow it with real pilot questions over time.
"""

GOLDEN = [
    {
        "question": "How many partners signed up last month?",
        "intent": "Partners",
        "tables": ["partner"],
        "sql": "SELECT count(*) AS n FROM turtlemint.partner "
               "WHERE toStartOfMonth(created_at) = toStartOfMonth(addMonths(now(), -1))",
    },
    {
        "question": "What is the total premium by product type?",
        "intent": "Policies",
        "tables": ["policy"],
        "sql": "SELECT product_type, round(sum(premium), 2) AS total "
               "FROM turtlemint.policy GROUP BY product_type",
    },
    {
        "question": "Top 5 partners by number of policies sold",
        "intent": "Partners",
        "tables": ["partner", "policy"],
        "sql": "SELECT p.name, count() AS n FROM turtlemint.policy AS pol "
               "JOIN turtlemint.partner AS p ON p.partner_id = pol.partner_id "
               "GROUP BY p.name ORDER BY n DESC LIMIT 5",
    },
    {
        "question": "How many claims are still pending settlement?",
        "intent": "Claims",
        "tables": ["claim"],
        "sql": "SELECT count(*) AS n FROM turtlemint.claim "
               "WHERE status IN ('filed', 'under_review', 'approved')",
    },
    {
        "question": "How many active policies are there?",
        "intent": "Policies",
        "tables": ["policy"],
        "sql": "SELECT count(*) AS n FROM turtlemint.policy WHERE status = 'active'",
    },
    {
        "question": "Total commission paid to partners",
        "intent": "Commissions",
        "tables": ["commission"],
        "sql": "SELECT round(sum(amount), 2) AS total FROM turtlemint.commission "
               "WHERE status = 'paid'",
    },
    {
        "question": "Number of customers by state",
        "intent": "Customers",
        "tables": ["customer"],
        "sql": "SELECT state, count(*) AS n FROM turtlemint.customer GROUP BY state",
    },
    {
        "question": "Which insurer has the most policies?",
        "intent": "Policies",
        "tables": ["policy"],
        "sql": "SELECT insurer, count() AS n FROM turtlemint.policy "
               "GROUP BY insurer ORDER BY n DESC LIMIT 1",
    },
]
