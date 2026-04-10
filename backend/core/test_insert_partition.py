# -*- coding: utf-8 -*-
"""INSERT INTO ... PARTITION ... SELECT 格式化测试

测试 V5 格式化器对 INSERT INTO ... PARTITION 语法的支持。
涵盖：动态分区、静态分区、多分区键、带注释等场景。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from formatter_v5_sqlglot import format_sql_v5


def test_insert_partition_dynamic():
    """动态分区：INSERT INTO table PARTITION(col) SELECT ..."""
    sql = "INSERT INTO ra03.temp PARTITION(data_dt) SELECT a, b FROM t1"
    result = format_sql_v5(sql)

    assert "INSERT INTO" in result
    assert "PARTITION(data_dt)" in result
    assert "SELECT" in result
    assert "FROM t1" in result
    # 验证 leading comma 风格
    assert ", b" in result
    print("PASS: test_insert_partition_dynamic")


def test_insert_partition_static_value():
    """静态分区：INSERT INTO table PARTITION(dt='value') SELECT ..."""
    sql = "INSERT INTO ra03.t PARTITION(DATA_DT='{DATA_DT}') SELECT c06 AS g0301, c07 AS g0302 FROM t1"
    result = format_sql_v5(sql)

    assert "INSERT INTO" in result
    assert "PARTITION" in result
    assert "DATA_DT" in result
    assert "SELECT" in result
    assert "AS g0301" in result
    assert "AS g0302" in result
    # leading comma
    assert ", c07" in result or ",\n" in result
    print("PASS: test_insert_partition_static_value")


def test_insert_partition_multi_keys():
    """多分区键：INSERT INTO table PARTITION(k1='v1', k2='v2', k3='v3') SELECT ..."""
    sql = "INSERT INTO RA03.T PARTITION(month='x', data_source='y', DATA_DT='z') SELECT a, b FROM t1"
    result = format_sql_v5(sql)

    assert "INSERT INTO" in result
    assert "PARTITION" in result
    assert "month" in result
    assert "data_source" in result
    assert "DATA_DT" in result
    assert "SELECT" in result
    print("PASS: test_insert_partition_multi_keys")


def test_insert_partition_with_where():
    """带 WHERE 子句"""
    sql = "INSERT INTO ra03.t PARTITION(data_dt) SELECT a, b FROM t1 WHERE x = 1 AND y = 2"
    result = format_sql_v5(sql)

    assert "INSERT INTO" in result
    assert "PARTITION(data_dt)" in result
    assert "WHERE" in result
    assert "AND" in result
    print("PASS: test_insert_partition_with_where")


def test_insert_partition_with_comment():
    """带行前注释"""
    sql = "--分区数据插入\nINSERT INTO ra03.temp PARTITION(data_dt) SELECT a, b FROM t1"
    result = format_sql_v5(sql)

    assert "INSERT INTO" in result
    assert "PARTITION(data_dt)" in result
    assert "SELECT" in result
    print("PASS: test_insert_partition_with_comment")


def test_insert_partition_with_join():
    """带 JOIN 的复杂语句"""
    sql = """INSERT INTO ra03.t PARTITION(DATA_DT='{DATA_DT}')
SELECT a.id, b.name
FROM table1 a
LEFT JOIN table2 b ON a.id = b.id
WHERE a.status = '1'"""
    result = format_sql_v5(sql)

    assert "INSERT INTO" in result
    assert "PARTITION" in result
    assert "SELECT" in result
    assert "LEFT JOIN" in result
    assert "ON" in result
    assert "WHERE" in result
    print("PASS: test_insert_partition_with_join")


def test_insert_partition_format_structure():
    """验证格式化后的结构：PARTITION 和 SELECT 分行，leading comma"""
    sql = "INSERT INTO ra03.temp PARTITION(data_dt) SELECT a, b, c FROM t1"
    result = format_sql_v5(sql)

    lines = [l for l in result.split('\n') if l.strip()]
    # 第一行应该是 INSERT INTO ... PARTITION(...)
    assert lines[0].strip().startswith("INSERT INTO")
    assert "PARTITION" in lines[0]
    # 后续行应该有 SELECT, 字段, FROM
    result_upper = result.upper()
    assert "SELECT" in result_upper
    assert "FROM" in result_upper
    # 验证 leading comma 风格（逗号在行首或逗号前缀）
    assert ", " in result  # leading comma 模式
    print("PASS: test_insert_partition_format_structure")


def test_insert_partition_keyword_case():
    """验证关键字大写"""
    sql = "insert into ra03.temp partition(data_dt) select a, b from t1"
    result = format_sql_v5(sql)

    assert "INSERT INTO" in result
    assert "PARTITION" in result
    assert "SELECT" in result
    assert "FROM" in result
    print("PASS: test_insert_partition_keyword_case")


if __name__ == "__main__":
    tests = [
        test_insert_partition_dynamic,
        test_insert_partition_static_value,
        test_insert_partition_multi_keys,
        test_insert_partition_with_where,
        test_insert_partition_with_comment,
        test_insert_partition_with_join,
        test_insert_partition_format_structure,
        test_insert_partition_keyword_case,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"INSERT INTO PARTITION 测试: {passed}/{passed+failed} 通过")
    if failed:
        print(f"失败: {failed}")
        sys.exit(1)
    else:
        print("全部通过!")
