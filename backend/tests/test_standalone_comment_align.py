# -*- coding: utf-8 -*-
"""Test standalone comment alignment"""
import pytest
from core.formatter_v4_fixed import format_sql_v4_fixed


def test_case_when_comment_indent():
    """CASE WHEN 中的独立注释应该与 WHEN 对齐"""
    sql = """SELECT CASE
WHEN a.summ_name LIKE '%test1%' THEN '6'
-- comment for test2
WHEN a.summ_name LIKE '%test2%' THEN '9'
END AS type_code
FROM table1"""

    result = format_sql_v4_fixed(sql)
    print("=== Formatted result ===")
    print(result)
    print("=== End of result ===")

    lines = result.split('\n')

    # 找到注释行和其上一行
    for i, line in enumerate(lines):
        if line.strip().startswith('--') and 'comment for test2' in line:
            comment_indent = len(line) - len(line.lstrip())
            # 查找上一行 WHEN 的缩进
            for j in range(i - 1, -1, -1):
                if j >= 0 and 'WHEN' in lines[j]:
                    when_indent = len(lines[j]) - len(lines[j].lstrip())
                    print(f"WHEN indent: {when_indent}, Comment indent: {comment_indent}")
                    # 注释应该与 WHEN 缩进一致
                    assert comment_indent == when_indent, f"Comment indent {comment_indent} != WHEN indent {when_indent}"
                    break
            break


def test_where_comment_indent():
    """WHERE 中的独立注释应该与 WHERE/AND 对齐"""
    sql = """SELECT *
FROM table1
WHERE id = 1
-- AND status = 'active'
AND age > 18"""

    result = format_sql_v4_fixed(sql)
    print("=== Formatted result ===")
    print(result)
    print("=== End of result ===")

    lines = result.split('\n')

    # 找到注释行
    for i, line in enumerate(lines):
        if line.strip().startswith('--') and 'AND status' in line:
            comment_indent = len(line) - len(line.lstrip())
            # 查找上一行 WHERE/AND 的缩进
            for j in range(i - 1, -1, -1):
                if j >= 0 and lines[j].strip() and not lines[j].strip().startswith('--'):
                    prev_indent = len(lines[j]) - len(lines[j].lstrip())
                    print(f"Previous line indent: {prev_indent}, Comment indent: {comment_indent}")
                    # 注释应该与上一行缩进一致
                    assert comment_indent == prev_indent, f"Comment indent {comment_indent} != previous indent {prev_indent}"
                    break
            break


def test_join_comment_indent():
    """JOIN 中的独立注释应该与 JOIN 对齐"""
    sql = """SELECT *
FROM table1 t1
LEFT JOIN table2 t2
-- ON t1.id = t2.id
ON t1.id = t2.id"""

    result = format_sql_v4_fixed(sql)
    print("=== Formatted result ===")
    print(result)
    print("=== End of result ===")

    lines = result.split('\n')

    # 找到注释行
    for i, line in enumerate(lines):
        if line.strip().startswith('--') and 'ON t1.id' in line:
            comment_indent = len(line) - len(line.lstrip())
            # 查找上一行 JOIN 的缩进
            for j in range(i - 1, -1, -1):
                if j >= 0 and ('JOIN' in lines[j] or 'LEFT JOIN' in lines[j]):
                    join_indent = len(lines[j]) - len(lines[j].lstrip())
                    print(f"JOIN indent: {join_indent}, Comment indent: {comment_indent}")
                    # 注释应该与 JOIN 缩进一致
                    assert comment_indent == join_indent, f"Comment indent {comment_indent} != JOIN indent {join_indent}"
                    break
            break


def test_multiple_standalone_comments():
    """多个连续的独立注释都应该对齐"""
    sql = """SELECT CASE
WHEN a.summ_name LIKE '%test1%' THEN '6'
-- comment 1
-- comment 2
WHEN a.summ_name LIKE '%test2%' THEN '9'
END AS type_code
FROM table1"""

    result = format_sql_v4_fixed(sql)
    print("=== Formatted result ===")
    print(result)
    print("=== End of result ===")

    lines = result.split('\n')

    # 找到所有注释行
    comment_indents = []
    for i, line in enumerate(lines):
        if line.strip().startswith('--') and ('comment 1' in line or 'comment 2' in line):
            indent = len(line) - len(line.lstrip())
            comment_indents.append((indent, line.strip()))
            print(f"Comment indent: {indent}, line: {line.strip()}")

    # 所有注释应该有相同的缩进（与 WHEN 一致）
    if len(comment_indents) > 1:
        first_indent = comment_indents[0][0]
        for indent, _ in comment_indents[1:]:
            assert indent == first_indent, f"Comment indents not aligned: {[c[0] for c in comment_indents]}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
