# -*- coding: utf-8 -*-
"""Test line comment alignment in code blocks"""
import pytest
from core.formatter_v4_fixed import format_sql_v4_fixed


def test_case_when_comment_alignment():
    """CASE WHEN 中的行尾注释应该对齐"""
    sql = """SELECT CASE
WHEN a.summ_name LIKE '%test1%' THEN '6' --comment1
WHEN a.summ_name LIKE '%test2%' THEN '9' --comment2
WHEN a.summ_name LIKE '%test3%' THEN '6' --comment3
END AS type_code
FROM table1"""

    result = format_sql_v4_fixed(sql)
    print("=== Formatted result ===")
    print(result)
    print("=== End of result ===")

    lines = result.split('\n')

    # 找到所有带行尾注释的 WHEN/THEN 行
    comment_positions = []
    for line in lines:
        if '--' in line and not line.strip().startswith('--'):
            comment_pos = line.index('--')
            comment_positions.append(comment_pos)
            print(f"Comment at pos {comment_pos}: '{line.rstrip()}'")

    # 验证注释对齐（所有注释应该在相同列位置）
    if len(comment_positions) >= 2:
        # 检查是否所有注释位置相同
        unique_positions = set(comment_positions)
        print(f"Comment positions: {comment_positions}")
        print(f"Unique positions: {unique_positions}")
        # 如果有多个不同的位置，说明注释未对齐
        assert len(unique_positions) == 1, f"Comments not aligned, found positions: {unique_positions}"


def test_independent_comment_lines_indent():
    """独立的注释行应该继承代码块的缩进"""
    sql = """SELECT summ_name,
CASE
WHEN a.summ_name LIKE '%test1%' THEN '6' --comment1
-- when a.summ_name like '%test2%' then '9'
WHEN a.summ_name LIKE '%test3%' THEN '6'
END AS type_code
FROM table1"""

    result = format_sql_v4_fixed(sql)
    print("=== Formatted result ===")
    print(result)
    print("=== End of result ===")

    lines = result.split('\n')

    # 找到 CASE 块内的 WHEN 行和独立注释行
    case_indent = 0
    comment_indents = []

    for i, line in enumerate(lines):
        if 'WHEN' in line and 'summ_name' in line:
            # 获取 CASE 块内 WHEN 的缩进
            case_indent = len(line) - len(line.lstrip())
            print(f"WHEN line indent: {case_indent} -> '{line[:40]}...'")
        elif line.strip().startswith('--') and 'when' in line.lower():
            # 获取独立注释行的缩进
            comment_indent = len(line) - len(line.lstrip())
            comment_indents.append(comment_indent)
            print(f"Comment line indent: {comment_indent} -> '{line[:40]}...'")

    # 验证独立注释行的缩进与 CASE 块的缩进一致或接近
    if comment_indents:
        # 独立注释行应该有合理的缩进（不应该在行首）
        # 至少应该有 CASE 块的基本缩进
        print(f"CASE indent: {case_indent}")
        print(f"Comment indents: {comment_indents}")
        # 所有注释行的缩进应该大于 0
        for indent in comment_indents:
            assert indent > 0, f"Independent comment has no indent: {indent}"


def test_select_list_comment_alignment():
    """SELECT 字段列表中的行尾注释应该对齐"""
    sql = """
    SELECT id --ID
    , name --名称
    , age --年龄
    FROM table1
    """

    result = format_sql_v4_fixed(sql)
    lines = result.split('\n')

    # 找到所有带行尾注释的字段行
    comment_positions = []
    for line in lines:
        if '--' in line and not line.strip().startswith('--'):
            comment_pos = line.index('--')
            comment_positions.append(comment_pos)

    # 验证注释对齐
    if len(comment_positions) > 1:
        first_pos = comment_positions[0]
        for pos in comment_positions[1:]:
            assert abs(pos - first_pos) <= 1, f"Comments not aligned: {comment_positions}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
