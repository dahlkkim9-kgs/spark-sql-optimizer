# -*- coding: utf-8 -*-
"""DISTINCT 处理测试"""
from formatter_v5_sqlglot import format_sql_v5


def test_distinct_simple():
    """测试 DISTINCT 基础用法"""
    sql = "select distinct a, b from t1"
    result = format_sql_v5(sql)
    print("\n=== DISTINCT 基础 ===")
    print(result)
    assert "DISTINCT" in result


def test_distinct_with_subquery():
    """测试 DISTINCT 带子查询"""
    sql = "select distinct a, (select x from t2) as sub from t1"
    result = format_sql_v5(sql)
    print("\n=== DISTINCT + 子查询 ===")
    print(result)
    assert "DISTINCT" in result


def test_distinct_with_join():
    """测试 DISTINCT 带 JOIN"""
    sql = "select distinct t1.a, t2.b from t1 inner join t2 on t1.id = t2.id"
    result = format_sql_v5(sql)
    print("\n=== DISTINCT + JOIN ===")
    print(result)
    assert "DISTINCT" in result


if __name__ == "__main__":
    test_distinct_simple()
    test_distinct_with_subquery()
    test_distinct_with_join()
    print("\n所有 DISTINCT 测试通过!")
