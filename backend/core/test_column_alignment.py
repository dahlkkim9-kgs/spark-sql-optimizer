# -*- coding: utf-8 -*-
"""测试：CREATE TABLE 列对齐 — 字段名、类型、COMMENT 上下对齐"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from formatter_v5_sqlglot import format_sql_v5


def _extract_col_lines_with_indent(result):
    """从格式化结果中提取列定义行（保留前导缩进）"""
    lines = result.split('\n')
    col_lines = []
    in_cols = False
    for line in lines:
        s = line.strip()
        if 'CREATE TABLE' in s.upper() and '(' in s:
            in_cols = True
            continue
        if in_cols:
            if s.startswith(')') or s == ')':
                break
            if s and not s.startswith('CREATE'):
                col_lines.append(line)  # 保留原始缩进
    return col_lines


def _get_comment_positions(col_lines):
    """获取每行中 COMMENT 关键字的列位置"""
    positions = []
    for line in col_lines:
        pos = line.upper().find(' COMMENT ')
        if pos >= 0:
            positions.append(pos)
    return positions


def test_align_column_names():
    """列名应左对齐到最长列名宽度"""
    sql = """CREATE TABLE t1 (
    a INT COMMENT 'short'
    , abcdef STRING COMMENT 'long name'
    , xy DECIMAL(22,2) COMMENT 'medium'
)"""
    result = format_sql_v5(sql)
    col_lines = _extract_col_lines_with_indent(result)
    for cl in col_lines:
        print(f'  {cl}')

    # COMMENT 关键字在原始行中的列位置应对齐（保留前导缩进）
    comment_positions = _get_comment_positions(col_lines)
    if len(comment_positions) >= 2:
        max_diff = max(comment_positions) - min(comment_positions)
        assert max_diff <= 1, \
            f"列名未对齐! COMMENT位置: {comment_positions}\n{chr(10).join(col_lines)}"
    print("PASS: test_align_column_names")


def test_align_types():
    """类型应左对齐到最长类型宽度"""
    sql = """CREATE TABLE t1 (
    a INT COMMENT 'short'
    , b STRING COMMENT 'longer type name'
    , c VARCHAR(10) COMMENT 'has params'
    , d DECIMAL(22,2) COMMENT 'big number'
)"""
    result = format_sql_v5(sql)
    col_lines = _extract_col_lines_with_indent(result)
    for cl in col_lines:
        print(f'  {cl}')

    # COMMENT 关键字在各行应对齐
    comment_positions = _get_comment_positions(col_lines)
    if len(comment_positions) >= 2:
        max_diff = max(comment_positions) - min(comment_positions)
        assert max_diff <= 1, \
            f"COMMENT未对齐! 位置: {comment_positions}\n{chr(10).join(col_lines)}"
    print("PASS: test_align_types")


def test_align_with_partitioned_by():
    """PARTITIONED BY 表也应列对齐"""
    sql = """CREATE TABLE t1 (
    a INT COMMENT 'col a'
    , bbb STRING COMMENT 'col bbb'
) COMMENT 'test table'
PARTITIONED BY (dt STRING)"""
    result = format_sql_v5(sql)
    assert 'bbb' in result, f"列 bbb 丢失!\n{result}"
    assert 'PARTITIONED BY' in result.upper(), f"PARTITIONED BY 丢失!\n{result}"
    print("PASS: test_align_with_partitioned_by")


def test_align_short_columns():
    """简单短列也能对齐"""
    sql = """CREATE TABLE t1 (
    id INT
    , name STRING
)"""
    result = format_sql_v5(sql)
    assert 'id' in result and 'name' in result, f"列丢失!\n{result}"
    print("PASS: test_align_short_columns")


if __name__ == "__main__":
    tests = [
        test_align_column_names,
        test_align_types,
        test_align_with_partitioned_by,
        test_align_short_columns,
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
    print(f"CREATE TABLE 列对齐测试: {passed}/{passed+failed} 通过")
    if failed:
        print(f"失败: {failed}")
        sys.exit(1)
    else:
        print("全部通过!")
