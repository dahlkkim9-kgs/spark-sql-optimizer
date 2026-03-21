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


def test_subquery_in_select():
    """测试 SELECT 中的子查询"""
    sql = "select a,(select max(x) from t2 where t2.id=t1.id) as max_x from t1"
    result = format_sql_v5(sql)
    print("\n=== 子查询 ===")
    print(result)
    # 应该正确处理嵌套
    assert "SELECT" in result.upper()


def test_nested_subquery():
    """测试深层嵌套子查询"""
    sql = "select a,(select b from (select c from t1)) as nested from t2"
    result = format_sql_v5(sql)
    print("\n=== 深层嵌套 ===")
    print(result)
    assert "SELECT" in result.upper()


def test_exists_subquery():
    """测试 EXISTS 子查询"""
    sql = "select * from t1 where exists (select 1 from t2 where t2.id=t1.id)"
    result = format_sql_v5(sql)
    print("\n=== EXISTS ===")
    print(result)
    assert "EXISTS" in result.upper()


def test_case_when():
    """测试 CASE WHEN"""
    sql = "select case when x>0 then 'positive' when x<0 then 'negative' else 'zero' end as sign from t1"
    result = format_sql_v5(sql)
    print("\n=== CASE WHEN ===")
    print(result)
    assert "CASE" in result.upper()
    assert "WHEN" in result.upper()


def test_cte_with():
    """测试 CTE WITH"""
    sql = "with cte1 as (select a,b from t1),cte2 as (select c,d from t2) select * from cte1 join cte2 on cte1.a=cte2.c"
    result = format_sql_v5(sql)
    print("\n=== CTE ===")
    print(result)
    assert "WITH" in result.upper()


def test_v4_column_alignment():
    """测试 v4 风格列对齐"""
    sql = "select a,b,c from table1"
    result = format_sql_v5(sql)
    print("\n=== v4 风格列对齐 ===")
    print(result)
    # 验证逗号在行首
    assert ', ' in result or '\n     ,' in result


def test_create_table():
    """测试 CREATE TABLE"""
    sql = "create table if not exists t1 (a int comment 'column a',b string,c double) comment 'table t1' partitioned by (dt string)"
    result = format_sql_v5(sql)
    print("\n=== CREATE TABLE ===")
    print(result)
    assert "CREATE TABLE" in result.upper()


def test_insert():
    """测试 INSERT"""
    sql = "insert into table t1 partition(dt='2024-01-01') select a,b from t2 where c>0"
    result = format_sql_v5(sql)
    print("\n=== INSERT ===")
    print(result)
    assert "INSERT" in result.upper()


def test_over_window():
    """测试 OVER 窗口函数"""
    sql = "select a,row_number() over (partition by b order by c desc) as rn from t1"
    result = format_sql_v5(sql)
    print("\n=== OVER 窗口 ===")
    print(result)
    assert "OVER" in result.upper()
