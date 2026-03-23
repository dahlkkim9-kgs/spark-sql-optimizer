import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from formatter_v4_fixed import format_sql_v4_fixed

def test_format_preserves_field_comments():
    """Test that formatter v4 preserves field-level comments"""
    sql = "SELECT id -- primary key\nFROM table1"

    result = format_sql_v4_fixed(sql)

    assert "-- primary key" in result
    assert "SELECT id" in result


def test_format_preserves_table_comments():
    """Test that formatter v4 preserves table-level comments"""
    sql = "SELECT id\nFROM table1 -- main table"

    result = format_sql_v4_fixed(sql)

    assert "-- main table" in result


def test_format_preserves_case_comments():
    """Test that formatter v4 preserves comments in CASE expressions"""
    sql = """SELECT CASE
    WHEN a = 1 THEN 'A' -- condition A
    ELSE 'B'
END"""

    result = format_sql_v4_fixed(sql)

    assert "-- condition A" in result


def test_format_complex_sql_with_comments():
    """Test formatting complex SQL with multiple comment types"""
    sql = """SELECT id -- primary key
     , name -- user name
     , CASE
         WHEN status = 1 THEN 'active' -- active status
         ELSE 'inactive'
     END AS status_text
FROM users -- user table
    LEFT JOIN orders -- order table
        ON users.id = orders.user_id
WHERE users.active = 1 -- only active users
;"""

    result = format_sql_v4_fixed(sql)

    # All comments should be preserved
    assert "-- primary key" in result
    assert "-- user name" in result
    assert "-- active status" in result
    assert "-- user table" in result
    assert "-- order table" in result
    assert "-- only active users" in result


def test_format_block_comments():
    """Test preserving block comments"""
    sql = "SELECT id /* primary key */, name FROM users"

    result = format_sql_v4_fixed(sql)

    assert "/* primary key */" in result


def test_format_standalone_comment_lines():
    """Test preserving standalone comment lines"""
    sql = """-- This is a header comment
SELECT id, name
-- Filter active users
FROM users
WHERE active = 1"""

    result = format_sql_v4_fixed(sql)

    assert "-- This is a header comment" in result
    assert "-- Filter active users" in result


def test_function_embedded_subquery_does_not_runaway_indent():
    """
    Regression: subquery inside nested function args should not get runaway indentation.

    Shape: AVG(COALESCE((SELECT ...), 0))
    """
    sql = """SELECT
  AVG(
    COALESCE(
      (
        SELECT SUM(o.quantity * o.unit_price)
        FROM order_items o
        INNER JOIN orders ord ON o.order_id = ord.order_id
        WHERE o.product_id = p.product_id
          AND ord.order_date BETWEEN '2024-01-01' AND '2024-12-31'
      ),
      0
    )
  ) AS category_avg
FROM products p
;"""

    formatted = format_sql_v4_fixed(sql)

    def leading_spaces(line: str) -> int:
        return len(line) - len(line.lstrip(" "))

    lines = formatted.splitlines()
    # pick the SELECT line that belongs to the inner subquery block (not the outer SELECT)
    select_line = next(l for l in lines if "SELECT SUM(" in l.upper())

    # The nested SELECT should not be indented excessively ("runaway indent").
    # Keep this threshold conservative to avoid regressions while preserving overall style.
    assert leading_spaces(select_line) <= 30
