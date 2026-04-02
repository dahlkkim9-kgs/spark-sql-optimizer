# -*- coding: utf-8 -*-
"""测试三层嵌套 CASE WHEN 格式化"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.formatter_v5_sqlglot import SQLFormatterV5

formatter = SQLFormatterV5()

# 三层嵌套 CASE: THEN (CASE WHEN ... THEN (CASE ... END) ... END)
test_sql_1 = """
SELECT
    CASE
        WHEN a.type = 'A'
        THEN (CASE WHEN a.sub_type = 'X' THEN (CASE WHEN a.flag = '1' THEN 'AAA' WHEN a.flag = '2' THEN 'BBB' ELSE 'CCC' END) ELSE 'DFT' END)
        WHEN a.type = 'B'
        THEN 'BB'
        ELSE 'ZZ'
    END AS result_col
FROM table1 a
"""

# 三层嵌套: 真实SQL场景 - 证件类型 -> 子类型 -> 标志位
test_sql_2 = """
SELECT AAA
     , CASE
           WHEN t1.itm_no LIKE '1025%'
           THEN (
                 CASE
                     WHEN t1.dr_cr_flag = 'jie'
                     THEN (CASE WHEN t1.extra_flag = '1' THEN 'X1' WHEN t1.extra_flag = '2' THEN 'X2' ELSE 'X0' END)
                     WHEN t1.dr_cr_flag = 'dai'
                     THEN '2'
                     ELSE ''
                 END
                )
           WHEN t1.itm_no LIKE '2043%'
           THEN '3'
           ELSE ''
       END AS cdflag11
FROM table1 t1
"""

# 三层嵌套: 每个 THEN 都有不同的CASE
test_sql_3 = """
SELECT
    CASE
        WHEN a.level1 = '1'
        THEN (CASE WHEN a.level2 = 'A' THEN (CASE WHEN a.level3 = 'X' THEN 'R1' ELSE 'R2' END) WHEN a.level2 = 'B' THEN 'R3' ELSE 'R4' END)
        WHEN a.level1 = '2'
        THEN (CASE WHEN a.level2 = 'C' THEN (CASE WHEN a.level3 = 'Y' THEN 'R5' ELSE 'R6' END) ELSE 'R7' END)
        ELSE 'DEFAULT'
    END AS deep_nested
FROM table1 a
"""

def run_test(name, sql):
    print(f"\n{'='*70}")
    print(f"Test: {name}")
    print('='*70)
    print("Input SQL:")
    print(sql.strip())
    print("\nFormatted:")
    result = formatter.format(sql.strip())
    print(result)

    # 检查关键字完整性
    for kw in ['CASE', 'WHEN', 'THEN', 'ELSE', 'END']:
        input_count = sum(1 for _ in re.finditer(r'\b' + kw + r'\b', sql, re.IGNORECASE))
        output_count = sum(1 for _ in re.finditer(r'\b' + kw + r'\b', result, re.IGNORECASE))
        status = "OK" if input_count == output_count else "FAIL"
        print(f"  {kw}: {input_count} -> {output_count} {status}")

import re

if __name__ == '__main__':
    run_test("3-level nested CASE - basic", test_sql_1)
    run_test("3-level nested CASE - real world", test_sql_2)
    run_test("3-level nested CASE - multiple branches", test_sql_3)
