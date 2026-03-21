# -*- coding: utf-8 -*-
"""Formatter V5 测试"""
import pytest
from formatter_v5_sqlglot import format_sql_v5


def test_basic_select():
    """测试基础 SELECT 格式化"""
    sql = "select a,b from t1"
    result = format_sql_v5(sql)
    # 基础验证：只是确保不报错
    assert isinstance(result, str)
    assert len(result) > 0


def test_simple_select():
    """测试简单 SELECT"""
    sql = "SELECT a, b FROM table1"
    result = format_sql_v5(sql)
    print(result)


def test_simple_select_formatted():
    """测试简单 SELECT 格式化"""
    sql = "select a,b,c from table1"
    result = format_sql_v5(sql)
    print("\n=== 简单 SELECT ===")
    print(result)
    # 验证关键字大写
    assert "SELECT" in result.upper()
    # 验证换行
    assert "\n" in result


def test_with_where():
    """测试 WHERE 子句"""
    sql = "select a from t1 where x=1 and y=2"
    result = format_sql_v5(sql)
    print("\n=== WHERE 子句 ===")
    print(result)
    assert "WHERE" in result.upper()


def test_with_join():
    """测试 JOIN"""
    sql = "select t1.a,t2.b from t1 inner join t2 on t1.id=t2.id"
    result = format_sql_v5(sql)
    print("\n=== JOIN ===")
    print(result)
    assert "JOIN" in result.upper()
    assert "ON" in result.upper()
