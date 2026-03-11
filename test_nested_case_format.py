#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试嵌套 CASE WHEN 格式化"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from core.formatter_v4_fixed import format_sql_v4_fixed

# 测试 SQL - 简化的嵌套 CASE
test_sql = """SELECT
    id,
    CASE WHEN NVL(G0305,'')='' AND a.G0304='2' THEN (CASE WHEN a.summ_name like '%短信扣费%' THEN '6' WHEN a.summ_name like '%快捷支付%' THEN '1' ELSE '0' END)
    ELSE A.G0305
    END AS g0305
FROM table1;"""

print("=== 原始 SQL ===")
print(test_sql)
print("\n=== 格式化后 ===")
result = format_sql_v4_fixed(test_sql, keyword_case='upper')
print(result)
