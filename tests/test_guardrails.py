from app.backend import guardrails


def test_select_passes_and_gets_limit():
    r = guardrails.check("SELECT name FROM turtlemint.partner")
    assert r.ok
    assert r.limit_applied
    assert "LIMIT" in r.sql.upper()


def test_existing_limit_not_doubled():
    r = guardrails.check("SELECT name FROM turtlemint.partner LIMIT 5")
    assert r.ok
    assert not r.limit_applied
    assert r.sql.upper().count("LIMIT") == 1


def test_cte_select_passes():
    sql = ("WITH t AS (SELECT partner_id FROM turtlemint.policy) "
           "SELECT count(*) FROM t")
    r = guardrails.check(sql)
    assert r.ok


def test_insert_blocked():
    r = guardrails.check("INSERT INTO turtlemint.partner VALUES (1)")
    assert not r.ok


def test_update_blocked():
    r = guardrails.check("UPDATE turtlemint.partner SET name='x'")
    assert not r.ok


def test_delete_blocked():
    r = guardrails.check("DELETE FROM turtlemint.partner")
    assert not r.ok


def test_drop_blocked():
    r = guardrails.check("DROP TABLE turtlemint.partner")
    assert not r.ok


def test_multi_statement_blocked():
    r = guardrails.check("SELECT 1; DROP TABLE turtlemint.partner")
    assert not r.ok


def test_stacked_injection_blocked():
    r = guardrails.check(
        "SELECT * FROM turtlemint.partner WHERE name='a'; DELETE FROM turtlemint.policy"
    )
    assert not r.ok
