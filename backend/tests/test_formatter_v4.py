import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from formatter_v4 import format_sql_v4

def test_format_preserves_field_comments():
    """Test that formatter v4 preserves field-level comments"""
    sql = "SELECT id -- primary key\nFROM table1"

    result = format_sql_v4(sql)

    assert "-- primary key" in result
    assert "SELECT id" in result


def test_format_preserves_table_comments():
    """Test that formatter v4 preserves table-level comments"""
    sql = "SELECT id\nFROM table1 -- main table"

    result = format_sql_v4(sql)

    assert "-- main table" in result


def test_format_preserves_case_comments():
    """Test that formatter v4 preserves comments in CASE expressions"""
    sql = """SELECT CASE
    WHEN a = 1 THEN 'A' -- condition A
    ELSE 'B'
END"""

    result = format_sql_v4(sql)

    assert "-- condition A" in result
