# -*- coding: utf-8 -*-
"""V4 vs V5 格式化差异对比测试"""
import sys
sys.path.insert(0, 'c:\\Users\\61586\\Desktop\\自用工作文件\\deepseek\\测试文件\\spark-sql-optimizer\\backend\\core')

from formatter_v4_fixed import format_sql_v4_fixed
from formatter_v5_sqlglot import format_sql_v5

def compare_v4_v5(sql: str, test_name: str):
    """对比V4和V5的输出"""
    print(f"\n{'='*70}")
    print(f"测试: {test_name}")
    print(f"{'='*70}")
    print(f"\n原始SQL:")
    print(sql)
    print(f"\n{'-'*70}")

    v4_result = format_sql_v4_fixed(sql, indent=4)
    print(f"\n【V4 输出】")
    print(v4_result)

    v5_result = format_sql_v5(sql, indent=4)
    print(f"\n【V5 输出】")
    print(v5_result)

    if v4_result == v5_result:
        print(f"\n[WARNING] 结果相同")
    else:
        print(f"\n[SUCCESS] 结果不同!")

    return v4_result != v5_result

# 测试用例
test_cases = [
    (
        "select distinct a, b, c from table1 where x > 0 order by a",
        "简单 SELECT DISTINCT"
    ),
    (
        "select t1.a, t2.b, t3.c from t1 join t2 on t1.id = t2.id join t3 on t2.id = t3.id",
        "多表 JOIN"
    ),
    (
        "select case when x > 0 then 'positive' when x < 0 then 'negative' else 'zero' end as result from t1",
        "CASE WHEN"
    ),
    (
        "select a, (select max(b) from t2 where t2.id = t1.id) as max_b from t1",
        "标量子查询"
    ),
    (
        "with cte as (select a, b from t1) select a, b from cte",
        "CTE (WITH 语句)"
    ),
    (
        "select a, b from t1 where a in (select x from t2)",
        "IN 子查询"
    ),
]

# 运行测试
different_count = 0
for sql, name in test_cases:
    if compare_v4_v5(sql, name):
        different_count += 1

print(f"\n\n{'='*70}")
print(f"总结: {len(test_cases)} 个测试中，{different_count} 个结果不同")
print(f"{'='*70}")
