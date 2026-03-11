# -*- coding: utf-8 -*-
"""
Test WHERE clause comment preservation
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from formatter_v4 import format_sql_v4


def test_where_simple_comments():
    """Test preserving simple WHERE condition comments"""
    sql = '''SELECT id, name
FROM users
WHERE status = 1 -- only active users
AND dept = 'IT' -- IT department
'''
    result = format_sql_v4(sql)
    assert '-- only active users' in result
    assert '-- IT department' in result
    print('[PASS] test_where_simple_comments')


def test_where_or_group_with_comments():
    """Test preserving comments in parenthesized OR groups"""
    sql = '''SELECT t1.acc_date
FROM rbdb.unitrsdb_jg_ftu_dtl t1
WHERE t1.etl_load_date = '{DATA_DT}' -- data date
AND (t2.tablename = 'FTZ210101' -- table match 1
OR t3.tablename = 'FTZ210101' -- table match 2
OR t4.tablename = 'FTZ210101') -- table match 3
'''
    result = format_sql_v4(sql)

    # All comments should be preserved
    assert "-- data date" in result
    assert "-- table match 1" in result
    assert "-- table match 2" in result
    assert "-- table match 3" in result

    # OR conditions should be on separate lines
    assert "OR t3.tablename" in result
    assert "OR t4.tablename" in result

    print('[PASS] test_where_or_group_with_comments')


def test_where_multiple_conditions_with_comments():
    """Test preserving comments across multiple WHERE conditions"""
    sql = '''SELECT *
FROM table1
WHERE condition1 = 'A' -- comment 1
AND condition2 = 'B' -- comment 2
AND condition3 = 'C' -- comment 3
'''
    result = format_sql_v4(sql)
    assert '-- comment 1' in result
    assert '-- comment 2' in result
    assert '-- comment 3' in result
    print('[PASS] test_where_multiple_conditions_with_comments')


def test_where_nested_parens_with_comments():
    """Test preserving comments with nested parentheses"""
    sql = '''SELECT *
FROM table1
WHERE (a = 1 -- first condition
OR b = 2) -- second condition
AND c = 3 -- third condition
'''
    result = format_sql_v4(sql)
    assert '-- first condition' in result
    assert '-- second condition' in result
    assert '-- third condition' in result
    print('[PASS] test_where_nested_parens_with_comments')


if __name__ == '__main__':
    print('=' * 60)
    print('WHERE Clause Comment Preservation Tests')
    print('=' * 60)
    print()

    test_where_simple_comments()
    test_where_or_group_with_comments()
    test_where_multiple_conditions_with_comments()
    test_where_nested_parens_with_comments()

    print()
    print('=' * 60)
    print('All tests passed!')
    print('=' * 60)
