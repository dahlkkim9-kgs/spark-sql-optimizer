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
