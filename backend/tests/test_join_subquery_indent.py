# -*- coding: utf-8 -*-
"""Test JOIN subquery indentation - expecting SELECT to indent 6 spaces (same as FROM)"""
import pytest
from core.formatter_v4_fixed import format_sql_v4_fixed


def test_join_subquery_indent_6_spaces():
    """JOIN 后的子查询 SELECT 应该缩进 6 个空格（与 FROM 一致）"""
    sql = """
    SELECT *
    FROM table1 t1
    LEFT JOIN (
        SELECT corp_inn_accno, curr_code, cdpt_accno
        FROM rbdb.cdc_cpcddb_tb_cdmst_deppdcon_acc
        WHERE start_dt <= '{DATA_DT}'
    ) t8
    ON t1.acc = CAST(t8.corp_inn_accno AS STRING)
    """

    result = format_sql_v4_fixed(sql)
    lines = result.split('\n')

    # 找到 SELECT 行，检查缩进
    for line in lines:
        if line.strip().startswith('SELECT') and 'corp_inn_accno' in line:
            indent = len(line) - len(line.lstrip())
            print(f"SELECT indent: {indent} spaces")
            print(f"Line: '{line}'")
            assert indent == 6, f"Expected 6 spaces, got {indent}"
            break
    else:
        pytest.fail("SELECT line not found in JOIN subquery")


def test_from_subquery_indent_6_spaces():
    """FROM 后的子查询 SELECT 应该缩进 6 个空格"""
    sql = """
    SELECT *
    FROM (
        SELECT id, name
        FROM table1
    ) t
    """

    result = format_sql_v4_fixed(sql)
    lines = result.split('\n')

    # 找到 SELECT 行，检查缩进
    for line in lines:
        if line.strip().startswith('SELECT') and 'id, name' in line:
            indent = len(line) - len(line.lstrip())
            print(f"FROM subquery SELECT indent: {indent} spaces")
            assert indent == 6, f"Expected 6 spaces, got {indent}"
            break


def test_complex_join_with_nested_where():
    """测试复杂 JOIN 子查询（包含 WHERE 中嵌套子查询）"""
    sql = """
    SELECT *
    FROM table1 t1
    LEFT JOIN (
        SELECT corp_inn_accno, curr_code, cdpt_accno
        FROM rbdb.cdc_cpcddb_tb_cdmst_deppdcon_acc
        WHERE start_dt <= '{DATA_DT}'
            AND end_dt > '{DATA_DT}'
            AND (
                cdpt_accno LIKE 'FTE%'
                OR cdpt_accno LIKE 'FTN%'
            )
    ) t8
    ON t1.acc = CAST(t8.corp_inn_accno AS STRING)
    """

    result = format_sql_v4_fixed(sql)
    print(result)

    # 验证主子查询 SELECT 缩进为 6
    lines = result.split('\n')
    for i, line in enumerate(lines):
        if line.strip().startswith('SELECT') and 'corp_inn_accno' in line:
            indent = len(line) - len(line.lstrip())
            assert indent == 6, f"Expected 6 spaces for main subquery SELECT, got {indent}"
            break


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
