# -*- coding: utf-8 -*-
"""v5 多语句支持测试"""
from formatter_v5_sqlglot import format_sql_v5


def test_multi_statement():
    """测试多语句格式化"""
    sql = "select a, b from t1; select x, y from t2;"
    result = format_sql_v5(sql)
    print("\n=== 多语句测试 ===")
    print(result)
    # 应该有两个 SELECT
    assert result.count("SELECT") == 2
    # 应该有分号分隔的空行
    assert "\n\n" in result


def test_multi_statement_with_create():
    """测试多语句包含 CREATE TABLE"""
    sql = "create table t1 (a int); select * from t1;"
    result = format_sql_v5(sql)
    print("\n=== 多语句（含 CREATE） ===")
    print(result)
    assert "CREATE TABLE" in result.upper()
    assert "SELECT" in result.upper()


if __name__ == "__main__":
    test_multi_statement()
    test_multi_statement_with_create()
    print("\n所有测试通过!")
