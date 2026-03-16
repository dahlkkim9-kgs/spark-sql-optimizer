"""
测试缩进重构结果

验证「开括号 + 1」缩进规则是否正确应用
"""

import sys
import os

# 添加路径以导入 formatter
sys.path.insert(0, os.path.dirname(__file__))

from formatter_v4_fixed import format_sql_v4_fixed as format_sql


def test_where_paren_and():
    """测试 WHERE 括号内 AND"""
    sql = "SELECT * FROM table WHERE (a=1 AND b=2 AND c=3)"
    result = format_sql(sql)
    print("=== 测试 1: WHERE 括号内 AND ===")
    print("输入:", sql)
    print("输出:")
    print(result)
    print()

    # 验证缩进
    lines = result.split('\n')
    for line in lines:
        if line.strip() == 'a=1':
            # 找到开括号位置
            for prev in lines:
                if '(' in prev:
                    open_paren_pos = prev.index('(')
                    expected_indent = open_paren_pos + 1
                    actual_indent = len(line) - len(line.lstrip())
                    print(f"  验证: 开括号位置={open_paren_pos}, 期望缩进={expected_indent}, 实际缩进={actual_indent}")
                    if actual_indent == expected_indent:
                        print("  [PASS]")
                    else:
                        print(f"  [FAIL]: 缩进不匹配")
                    break
    print()


def test_where_paren_or():
    """测试 WHERE 括号内 OR"""
    sql = "SELECT * FROM table WHERE (a=1 OR b=2 OR c=3)"
    result = format_sql(sql)
    print("=== 测试 2: WHERE 括号内 OR ===")
    print("输入:", sql)
    print("输出:")
    print(result)
    print()


def test_mixed_nested():
    """测试混合嵌套"""
    sql = "SELECT * FROM table WHERE a=1 AND b=2 AND (c=3 OR d=4 OR e=5)"
    result = format_sql(sql)
    print("=== 测试 3: 混合嵌套 ===")
    print("输入:", sql)
    print("输出:")
    print(result)
    print()


def test_case_when_paren():
    """测试 CASE WHEN 括号内"""
    sql = "CASE WHEN (a=1 AND b=2 AND c=3) THEN 'result' ELSE 'other' END"
    result = format_sql(sql)
    print("=== 测试 4: CASE WHEN 括号内 ===")
    print("输入:", sql)
    print("输出:")
    print(result)
    print()


def test_from_subquery():
    """测试子查询 FROM"""
    sql = "SELECT * FROM (SELECT id, name FROM users WHERE age > 18) t"
    result = format_sql(sql)
    print("=== 测试 5: 子查询 FROM ===")
    print("输入:", sql)
    print("输出:")
    print(result)
    print()

    # 验证缩进
    lines = result.split('\n')
    for line in lines:
        if 'SELECT id' in line:
            # 找到 FROM 行
            for prev in lines:
                if 'FROM' in prev and '(' in prev:
                    open_paren_pos = prev.index('(')
                    expected_indent = open_paren_pos + 1
                    actual_indent = len(line) - len(line.lstrip())
                    print(f"  验证: 开括号位置={open_paren_pos}, 期望缩进={expected_indent}, 实际缩进={actual_indent}")
                    if actual_indent == expected_indent:
                        print("  [PASS]")
                    else:
                        print(f"  [FAIL]: 缩进不匹配")
                    break
    print()


def test_where_in_subquery():
    """测试子查询 WHERE IN"""
    sql = "SELECT * FROM table WHERE id IN (SELECT user_id FROM orders WHERE amount > 100)"
    result = format_sql(sql)
    print("=== 测试 6: 子查询 WHERE IN ===")
    print("输入:", sql)
    print("输出:")
    print(result)
    print()


def test_deep_nested():
    """测试深层嵌套"""
    sql = "SELECT * FROM table WHERE (a=1 AND (b=2 OR c=3))"
    result = format_sql(sql)
    print("=== 测试 7: 深层嵌套 ===")
    print("输入:", sql)
    print("输出:")
    print(result)
    print()


def main():
    print("=" * 60)
    print("SQL 格式化缩进重构测试")
    print("规则: 开括号位置 + 1")
    print("=" * 60)
    print()

    test_where_paren_and()
    test_where_paren_or()
    test_mixed_nested()
    test_case_when_paren()
    test_from_subquery()
    test_where_in_subquery()
    test_deep_nested()

    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == '__main__':
    main()
