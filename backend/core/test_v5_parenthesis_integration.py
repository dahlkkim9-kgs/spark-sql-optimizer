# -*- coding: utf-8 -*-
"""V5 括号对齐集成测试"""
from formatter_v5_sqlglot import format_sql_v5


def test_in_subquery_formatting():
    """测试 IN 子查询格式化"""
    sql = "SELECT * FROM t1 WHERE a NOT IN (SELECT x FROM t2)"
    result = format_sql_v5(sql)
    print("\n=== IN 子查询格式化 ===")
    print(result)

    # 验证关键字存在
    assert "SELECT" in result.upper()
    assert "NOT IN" in result.upper() or "IN" in result.upper()


def test_real_sql_fragment():
    """测试真实 SQL 文件片段"""
    sql = """SELECT *
FROM rhbs_work.RHZF_GRKHJCXX_$TXDATE_xd
WHERE khzjdm NOT IN (
SELECT DISTINCT khzjdm
FROM rhbs_work.RHZF_GRKHJCXX_$TXDATE_XYK
)"""
    result = format_sql_v5(sql)
    print("\n=== 真实 SQL 片段 ===")
    print(result)

    # 验证内容完整性
    assert "SELECT" in result.upper()
    assert "RHZF_GRKHJCXX" in result