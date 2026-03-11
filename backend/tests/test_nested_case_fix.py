# -*- coding: utf-8 -*-
"""
测试嵌套 CASE WHEN 括号保留修复
"""
import sys
sys.path.insert(0, '..')

from core.formatter_v4 import format_sql_v4

# 测试用例1: THEN 后嵌套 CASE 带括号
test_sql_1 = """
SELECT
CASE WHEN a.cert_type IN ('1070','1181') THEN (CASE WHEN a.cert_no LIKE 'H%' THEN 'HKG' WHEN a.cert_no LIKE 'M%' THEN 'MAC' ELSE 'ZZZ' END) ELSE 'ZZZ' END AS G0302
FROM table1
"""

# 测试用例2: ELSE 后嵌套 CASE 带括号
test_sql_2 = """
SELECT
CASE WHEN a.cert_type = '1051' THEN 'ZZZ' ELSE (CASE WHEN NVL(b.cd_value1,'') ='' THEN 'ZZZ' ELSE b.cd_value1 END) END AS G0302
FROM table1
"""

# 测试用例3: 复杂的多层嵌套
test_sql_3 = """
SELECT
CASE WHEN a.dw_flag_code='1' THEN (CASE WHEN a.summ_name LIKE '%工资%' THEN '11' WHEN a.tx_remark LIKE '%奖金%' THEN '11' ELSE '12' END) WHEN a.dw_flag_code='2' THEN '7' ELSE '8' END AS g0305
FROM table1
"""

# 测试用例4: 带注释的情况
test_sql_4 = """
SELECT
CASE WHEN a.cert_type IN ('1070','1181') THEN (CASE WHEN a.cert_no LIKE 'H%' THEN 'HKG' ELSE 'ZZZ' END) ELSE 'ZZZ' END AS G0302 -- 持卡人所属国家
FROM table1
"""

def run_test(name, sql):
    print(f"\n{'='*60}")
    print(f"Test: {name}")
    print('='*60)
    print("Original SQL:")
    print(sql.strip())
    print("\nFormatted:")
    result = format_sql_v4(sql)
    print(result)

    # Check if parentheses are preserved
    if '(' in sql and 'CASE' in sql:
        # Count parentheses in original and result
        orig_parens = sql.count('(')
        result_parens = result.count('(')
        print(f"\nParentheses check: Original({orig_parens}) -> Result({result_parens})")
        if orig_parens == result_parens:
            print("[PASS] Parentheses count matches")
        else:
            print("[FAIL] Parentheses count mismatch, possible issue")

if __name__ == '__main__':
    run_test("Nested CASE in THEN with parens", test_sql_1)
    run_test("Nested CASE in ELSE with parens", test_sql_2)
    run_test("Complex multi-level nested", test_sql_3)
    run_test("Nested CASE with comment", test_sql_4)
