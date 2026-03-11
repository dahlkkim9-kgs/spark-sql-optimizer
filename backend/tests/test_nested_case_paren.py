# -*- coding: utf-8 -*-
"""
测试嵌套 CASE WHEN 括号保留功能
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from formatter_v4 import format_sql_v4


def test_nested_case_without_parens():
    """测试嵌套 CASE 无括号 - 应该保持无括号"""
    sql = """SELECT CASE WHEN a = 1 THEN CASE WHEN b = 1 THEN 'X' ELSE 'Y' END ELSE 'Z' END AS result"""

    result = format_sql_v4(sql)
    print("=== 测试: 嵌套 CASE 无括号 ===")
    print("输入:", sql)
    print("\n输出:")
    print(result)
    print()

    # 验证没有多余的括号
    assert "THEN (" not in result, "不应该添加括号"
    # 格式化后 THEN 和 CASE 在不同行，检查没有 "THEN (" 即可
    print("[PASS] 无括号的嵌套 CASE 正确处理")


def test_nested_case_with_parens():
    """测试嵌套 CASE 有括号 - 应该保留括号"""
    sql = """SELECT CASE WHEN a = 1 THEN (CASE WHEN b = 1 THEN 'X' ELSE 'Y' END) ELSE 'Z' END AS result"""

    result = format_sql_v4(sql)
    print("=== 测试: 嵌套 CASE 有括号 ===")
    print("输入:", sql)
    print("\n输出:")
    print(result)
    print()

    # 验证括号被保留
    assert "THEN (" in result, "应该保留括号"
    print("[PASS] 有括号的嵌套 CASE 正确处理")


def test_complex_nested_case():
    """测试复杂的嵌套 CASE (用户提供示例的简化版)"""
    sql = """
    SELECT
        CASE
            WHEN t1.itm_no LIKE '1025%' OR t1.itm_no LIKE '3145%'
            THEN (CASE WHEN t1.dr_cr_flag = '借' THEN '1' WHEN t1.dr_cr_flag = '贷' THEN '2' ELSE '' END)
            WHEN t1.itm_no LIKE '1%' OR t1.itm_no LIKE '6%'
            THEN (CASE WHEN t1.dr_cr_flag = '借' THEN '2' WHEN t1.dr_cr_flag = '贷' THEN '1' ELSE '' END)
            ELSE ''
        END AS cdflag11
    FROM table1 t1
    """

    result = format_sql_v4(sql)
    print("=== 测试: 复杂嵌套 CASE ===")
    print("输入:", sql[:100], "...")
    print("\n输出:")
    print(result)
    print()

    # 验证括号被保留（因为原始有括号）
    assert "THEN (" in result, "应该保留原始括号"
    print("[PASS] 复杂嵌套 CASE 正确处理")


def test_real_user_sql():
    """测试用户提供的真实 SQL"""
    sql = """SELECT  SUBSTR(t8.cdpt_accno,1,16) AS accountno  --主帐号
       ,t8.cdpt_accno AS accountno1 --主帐号1
       ,CASE WHEN SUBSTR(t8.cdpt_accno,1,3) = 'FTE'  THEN '01' WHEN SUBSTR(t8.cdpt_accno,1,3) = 'FTN'  THEN '02' ELSE '' END AS acctype
       ,CASE WHEN t1.itm_no LIKE '1025%' OR t1.itm_no LIKE '3145%' THEN (CASE WHEN t1.dr_cr_flag = '借' THEN '1' WHEN t1.dr_cr_flag = '贷' THEN '2' ELSE '' END ) WHEN t1.itm_no LIKE '1%' OR t1.itm_no LIKE '6%' THEN (CASE WHEN t1.dr_cr_flag = '借'  THEN '2' WHEN t1.dr_cr_flag = '贷'  THEN '1'  ELSE '' END) ELSE '' END AS cdflag11
FROM rbdb.unitrsdb_jg_ftu_dtl t1
LEFT JOIN ra03.ftzmis_itmno_with_tablename1 t2 ON t1.itm_no = t2.itm_no_kmhandbm
WHERE t1.etl_load_date = '{DATA_DT}' AND t1.inst_no LIKE '%F'
DISTRIBUTE BY ceil(rand()*1)"""

    result = format_sql_v4(sql)
    print("=== 测试: 用户真实 SQL ===")
    print("\n输出:")
    print(result)
    print()

    # 检查别名和注释是否保留
    assert "AS accountno" in result, "别名应该保留"
    assert "--主帐号" in result, "注释应该保留"
    # 检查嵌套 CASE 的括号（原始有括号，应该保留）
    assert "THEN (" in result, "原始有括号，应该保留"
    print("[PASS] 用户 SQL 正确处理")


if __name__ == '__main__':
    print("=" * 60)
    print("嵌套 CASE WHEN 括号保留测试")
    print("=" * 60)
    print()

    test_nested_case_without_parens()
    print()

    test_nested_case_with_parens()
    print()

    test_complex_nested_case()
    print()

    test_real_user_sql()
    print()

    print("=" * 60)
    print("所有测试通过!")
    print("=" * 60)
