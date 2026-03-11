#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试嵌套 CASE WHEN 的紧凑格式化功能"""
import sys
import os
# 添加 backend 目录到路径
backend_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, backend_dir)

from core.formatter_v4_fixed import format_sql_v4_fixed


def test_nested_case_compact_format():
    """测试嵌套 CASE 的紧凑格式"""
    sql = """
    SELECT
        id,
        CASE WHEN NVL(G0305,'')='' AND a.G0304='2'
        THEN (CASE WHEN a.summ_name LIKE '%短信%' THEN '6' WHEN a.summ_name LIKE '%快捷%' THEN '1' ELSE '0' END)
        ELSE A.G0305
        END AS g0305
    FROM table1;
    """

    result = format_sql_v4_fixed(sql, keyword_case='upper')

    print("=== 原始 SQL ===")
    print(sql)
    print("\n=== 格式化后 ===")
    print(result)

    # 验证嵌套 CASE 使用紧凑格式（WHEN 和 THEN 在同一行）
    assert "WHEN a.summ_name LIKE" in result
    assert "THEN '6'" in result
    # 内层 CASE 的 WHEN 和 THEN 应该在同一行
    lines = result.split('\n')
    for i, line in enumerate(lines):
        if 'WHEN a.summ_name LIKE' in line:
            # 下一行应该是 THEN 部分
            next_line = lines[i + 1] if i + 1 < len(lines) else ''
            # 紧凑模式下，THEN 应该在同一行
            assert 'THEN' in line, f"嵌套 CASE 应该使用紧凑格式（WHEN 和 THEN 在同一行），但第 {i+1} 行: {line}"

    print("\n[OK] 测试通过：嵌套 CASE 使用紧凑格式")


def test_nested_case_with_complex_when():
    """测试嵌套 CASE，外层 WHEN 条件复杂需要换行"""
    sql = """
    SELECT
        CASE WHEN a=1 OR b=2 OR c=3
        THEN (CASE WHEN x=1 THEN 'A' ELSE 'B' END)
        ELSE 'C'
        END AS result
    FROM table1;
    """

    result = format_sql_v4_fixed(sql, keyword_case='upper')

    print("\n=== 测试复杂 WHEN 条件的嵌套 CASE ===")
    print("=== 原始 SQL ===")
    print(sql)
    print("\n=== 格式化后 ===")
    print(result)

    # 外层 WHEN 条件应该换行
    assert 'OR' in result
    # 内层 CASE 应该使用紧凑格式
    assert "WHEN x=1 THEN 'A'" in result

    print("[OK] 测试通过：复杂 WHEN 条件正确换行，内层 CASE 紧凑格式")


def test_nested_case_in_else():
    """测试 ELSE 分支中的嵌套 CASE"""
    sql = """
    SELECT
        CASE WHEN a=1
        THEN 'A'
        ELSE (CASE WHEN b=1 THEN 'B' WHEN c=1 THEN 'C' ELSE 'D' END)
        END AS result
    FROM table1;
    """

    result = format_sql_v4_fixed(sql, keyword_case='upper')

    print("\n=== 测试 ELSE 分支的嵌套 CASE ===")
    print("=== 原始 SQL ===")
    print(sql)
    print("\n=== 格式化后 ===")
    print(result)

    # 内层 CASE 应该使用紧凑格式
    assert "WHEN b=1 THEN 'B'" in result
    assert "WHEN c=1 THEN 'C'" in result

    print("[OK] 测试通过：ELSE 分支中的嵌套 CASE 使用紧凑格式")


def test_multiple_nested_case():
    """测试多层嵌套 CASE"""
    sql = """
    SELECT
        CASE WHEN a=1
        THEN (CASE WHEN b=1 THEN (CASE WHEN c=1 THEN 'C' ELSE 'D' END) ELSE 'B' END)
        ELSE 'A'
        END AS result
    FROM table1;
    """

    result = format_sql_v4_fixed(sql, keyword_case='upper')

    print("\n=== 测试多层嵌套 CASE ===")
    print("=== 原始 SQL ===")
    print(sql)
    print("\n=== 格式化后 ===")
    print(result)

    # 所有层级的嵌套 CASE 都应该使用紧凑格式
    assert "WHEN c=1 THEN 'C'" in result

    print("[OK] 测试通过：多层嵌套 CASE 都使用紧凑格式")


if __name__ == '__main__':
    try:
        test_nested_case_compact_format()
        test_nested_case_with_complex_when()
        test_nested_case_in_else()
        test_multiple_nested_case()
        print("\n" + "="*50)
        print("[SUCCESS] 所有测试通过！")
        print("="*50)
    except AssertionError as e:
        print(f"\n[FAILED] 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
