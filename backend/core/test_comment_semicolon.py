# -*- coding: utf-8 -*-
"""测试：分号独立行输出

规则：所有 ; 分号换行输出到左边独立行，避免注释干扰语句完整性。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from formatter_v5_sqlglot import format_sql_v5


def test_semicolon_own_line_basic():
    """基本 SELECT 语句：分号在独立行"""
    sql = "SELECT a, b FROM t1"
    result = format_sql_v5(sql)

    assert result.rstrip().endswith(';'), f"应以分号结尾，实际:\n{result}"
    # 分号应该在独立行
    lines = result.rstrip().split('\n')
    assert lines[-1] == ';', f"最后行应只有分号，实际: '{lines[-1]}'"
    print("PASS: test_semicolon_own_line_basic")


def test_semicolon_own_line_with_comment():
    """语句末尾有注释时，分号仍在独立行"""
    sql = "SELECT a FROM t1 --查询数据"
    result = format_sql_v5(sql)

    lines = result.rstrip().split('\n')
    assert lines[-1] == ';', f"最后行应只有分号，实际: '{lines[-1]}'"
    # 倒数第二行应有注释
    assert '--' in lines[-2], f"注释应保留在分号前一行，实际: '{lines[-2]}'"
    print("PASS: test_semicolon_own_line_with_comment")


def test_semicolon_own_line_comment_in_original_semicolon():
    """原始 SQL 中 --comment; 格式：注释内分号不破坏语句分割"""
    sql = "ALTER TABLE t1 DROP IF EXISTS PARTITION(dt='x') --删除分区;\nINSERT INTO t1 SELECT a FROM t2"
    result = format_sql_v5(sql)

    lines = result.rstrip().split('\n')
    # 应该有多个 ; （每个语句一个，都在独立行）
    semicolon_lines = [i for i, l in enumerate(lines) if l.strip() == ';']
    assert len(semicolon_lines) >= 2, \
        f"期望至少2个分号独立行，实际{len(semicolon_lines)}，输出:\n{result}"
    print("PASS: test_semicolon_own_line_comment_in_original_semicolon")


def test_semicolon_own_line_two_statements():
    """两条语句：各有一个分号独立行"""
    sql = "SELECT a FROM t1; SELECT b FROM t2"
    result = format_sql_v5(sql)

    lines = result.rstrip().split('\n')
    semicolon_lines = [i for i, l in enumerate(lines) if l.strip() == ';']
    assert len(semicolon_lines) == 2, \
        f"期望2个分号独立行，实际{len(semicolon_lines)}，输出:\n{result}"
    print("PASS: test_semicolon_own_line_two_statements")


def test_semicolon_own_line_insert_partition():
    """INSERT INTO PARTITION：分号独立行"""
    sql = "INSERT INTO ra03.t PARTITION(DATA_DT='x') SELECT a, b FROM t1"
    result = format_sql_v5(sql)

    lines = result.rstrip().split('\n')
    assert lines[-1] == ';', f"最后行应只有分号，实际: '{lines[-1]}'"
    print("PASS: test_semicolon_own_line_insert_partition")


def test_semicolon_own_line_real_scenario():
    """真实场景：ALTER TABLE + INSERT INTO PARTITION"""
    sql = """--去掉交易类型为汉字和国家地区代码是ZZZ的数据插入结果表
ALTER TABLE RA03.T_GJDG_JRZF_G03 DROP IF EXISTS PARTITION(DATA_DT='{DATA_DT}');
INSERT INTO RA03.T_GJDG_JRZF_G03 PARTITION (DATA_DT='{DATA_DT}')
SELECT 'A', ''
FROM t1"""
    result = format_sql_v5(sql)

    lines = result.rstrip().split('\n')
    semicolon_lines = [i for i, l in enumerate(lines) if l.strip() == ';']
    assert len(semicolon_lines) >= 2, \
        f"期望至少2个分号独立行，实际{len(semicolon_lines)}，输出:\n{result}"
    # INSERT INTO 应存在
    assert 'INSERT INTO' in result.upper(), f"INSERT INTO 丢失，输出:\n{result}"
    # PARTITION 应存在
    assert 'PARTITION' in result.upper(), f"PARTITION 丢失，输出:\n{result}"
    print("PASS: test_semicolon_own_line_real_scenario")


def test_split_statements_semicolon_inside_comment():
    """分割：分号在 -- 注释内部时，仍正确分割"""
    from formatter_v5_sqlglot import SQLFormatterV5
    formatter = SQLFormatterV5()

    sql = "ALTER TABLE t1 DROP PARTITION(dt) --comment;\nSELECT a FROM t2"
    stmts = formatter._split_sql_statements(sql)
    assert len(stmts) >= 2, f"期望至少2条语句，实际{len(stmts)}: {stmts}"
    print("PASS: test_split_statements_semicolon_inside_comment")


if __name__ == "__main__":
    tests = [
        test_semicolon_own_line_basic,
        test_semicolon_own_line_with_comment,
        test_semicolon_own_line_comment_in_original_semicolon,
        test_semicolon_own_line_two_statements,
        test_semicolon_own_line_insert_partition,
        test_semicolon_own_line_real_scenario,
        test_split_statements_semicolon_inside_comment,
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
    print(f"分号独立行测试: {passed}/{passed+failed} 通过")
    if failed:
        print(f"失败: {failed}")
        sys.exit(1)
    else:
        print("全部通过!")
