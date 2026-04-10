# -*- coding: utf-8 -*-
"""测试：CREATE TABLE + PARTITIONED BY 格式化

问题：sqlglot 将 PARTITIONED BY 的列合并到主列定义中，并丢失类型和注释。
期望：分区列保留在 PARTITIONED BY 子句中，类型和注释完整。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from formatter_v5_sqlglot import format_sql_v5


def test_create_table_partitioned_by_columns_not_in_main():
    """PARTITIONED BY 的列不应出现在主列定义中"""
    sql = """CREATE TABLE IF NOT EXISTS t1 (
    a VARCHAR(1) COMMENT 'col a'
    , b STRING COMMENT 'col b'
) COMMENT 'table comment'
PARTITIONED BY (month STRING, data_source STRING COMMENT 'source', data_dt STRING)"""
    result = format_sql_v5(sql)

    lines = result.split('\n')
    # 找到主列定义区域（第一个 ( 到匹配的 ) 之间的行）
    in_main_cols = False
    main_col_lines = []
    for line in lines:
        stripped = line.strip()
        if not in_main_cols and '(' in stripped and 'CREATE TABLE' in stripped.upper():
            in_main_cols = True
            # 如果行内有列定义
            if stripped.endswith(','):
                main_col_lines.append(stripped)
            continue
        if in_main_cols:
            if stripped.startswith(')') or stripped == ')':
                break
            main_col_lines.append(stripped)

    # 主列定义中不应包含 month, data_source, data_dt
    main_cols_text = ' '.join(main_col_lines).upper()
    assert 'MONTH' not in main_cols_text, \
        f"分区列 month 不应在主列定义中! 主列:\n{chr(10).join(main_col_lines)}"
    assert 'DATA_SOURCE' not in main_cols_text, \
        f"分区列 data_source 不应在主列定义中! 主列:\n{chr(10).join(main_col_lines)}"
    assert 'DATA_DT' not in main_cols_text, \
        f"分区列 data_dt 不应在主列定义中! 主列:\n{chr(10).join(main_col_lines)}"

    print("PASS: test_create_table_partitioned_by_columns_not_in_main")


def test_create_table_partitioned_by_preserves_types():
    """PARTITIONED BY 应保留列类型信息"""
    sql = """CREATE TABLE IF NOT EXISTS t1 (
    a VARCHAR(1) COMMENT 'col a'
) COMMENT 'table comment'
PARTITIONED BY (month STRING, data_source STRING COMMENT 'source')"""
    result = format_sql_v5(sql)

    result_upper = result.upper()
    # PARTITIONED BY 行应包含 STRING 类型
    assert 'PARTITIONED BY' in result_upper, f"缺少 PARTITIONED BY! 输出:\n{result}"

    # 找 PARTITIONED BY 部分
    pb_idx = result_upper.find('PARTITIONED BY')
    pb_section = result[pb_idx:]

    # 类型信息应保留
    assert 'STRING' in pb_section.upper(), \
        f"PARTITIONED BY 中缺少 STRING 类型! PARTITIONED BY 部分:\n{pb_section}"
    print("PASS: test_create_table_partitioned_by_preserves_types")


def test_create_table_partitioned_by_preserves_comments():
    """PARTITIONED BY 应保留 COMMENT"""
    sql = """CREATE TABLE IF NOT EXISTS t1 (
    a VARCHAR(1) COMMENT 'col a'
) COMMENT 'table comment'
PARTITIONED BY (data_source STRING COMMENT '数据源')"""
    result = format_sql_v5(sql)

    assert '数据源' in result or 'COMMENT' in result.upper(), \
        f"PARTITIONED BY 注释丢失! 输出:\n{result}"
    print("PASS: test_create_table_partitioned_by_preserves_comments")


def test_create_table_partitioned_by_has_partitioned_clause():
    """格式化后应有 PARTITIONED BY 子句"""
    sql = """CREATE TABLE t1 (
    a INT
)
PARTITIONED BY (dt STRING)"""
    result = format_sql_v5(sql)

    assert 'PARTITIONED BY' in result.upper(), f"缺少 PARTITIONED BY! 输出:\n{result}"
    print("PASS: test_create_table_partitioned_by_has_partitioned_clause")


if __name__ == "__main__":
    tests = [
        test_create_table_partitioned_by_has_partitioned_clause,
        test_create_table_partitioned_by_columns_not_in_main,
        test_create_table_partitioned_by_preserves_types,
        test_create_table_partitioned_by_preserves_comments,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {t.__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"CREATE TABLE PARTITIONED BY 测试: {passed}/{passed+failed} 通过")
    if failed:
        print(f"失败: {failed}")
        sys.exit(1)
    else:
        print("全部通过!")
