# -*- coding: utf-8 -*-
"""v4 vs v5 格式化对比测试"""
import pytest
from formatter_v5_sqlglot import format_sql_v5

try:
    from formatter_v4_fixed import format_sql_v4_fixed
    HAS_V4 = True
except ImportError:
    HAS_V4 = False


@pytest.mark.skipif(not HAS_V4, reason="v4 not available")
def test_comparison_simple():
    """对比测试：简单 SELECT"""
    sql = "select a,b from t1"

    v4_result = format_sql_v4_fixed(sql)
    v5_result = format_sql_v5(sql)

    print("\n=== v4 结果 ===")
    print(v4_result)
    print("\n=== v5 结果 ===")
    print(v5_result)

    # 两者都应该能正确格式化
    assert "SELECT" in v4_result.upper()
    assert "SELECT" in v5_result.upper()


@pytest.mark.skipif(not HAS_V4, reason="v4 not available")
def test_comparison_complex():
    """对比测试：复杂子查询"""
    sql = "select a,(select max(x) from t2 where t2.id=t1.id) as max_x from t1"

    v4_result = format_sql_v4_fixed(sql)
    v5_result = format_sql_v5(sql)

    print("\n=== v4 复杂子查询 ===")
    print(v4_result)
    print("\n=== v5 复杂子查询 ===")
    print(v5_result)

    # v5 应该正确解析（v4 在这个案例中可能有问题）
    assert "SELECT" in v5_result.upper()
    assert "MAX" in v5_result.upper()
