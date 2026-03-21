# -*- coding: utf-8 -*-
"""v4 vs v5 详细对比测试"""
import sys
sys.path.insert(0, '.')

from formatter_v5_sqlglot import format_sql_v5
try:
    from formatter_v4_fixed import format_sql_v4_fixed
    HAS_V4 = True
except ImportError:
    HAS_V4 = False


def compare(name, sql):
    """对比 v4 和 v5 的输出"""
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"{'='*60}")
    print(f"原始 SQL:\n{sql}")
    print()

    if HAS_V4:
        v4_result = format_sql_v4_fixed(sql)
        print("--- v4 输出 ---")
        print(v4_result)
        print()

    v5_result = format_sql_v5(sql)
    print("--- v5 (sqlglot) 输出 ---")
    print(v5_result)
    print()


# 测试用例
compare("简单 SELECT", "select a, b, c from t1")

compare("带 WHERE 子句", "select a, b from t1 where x > 0 and y < 10")

compare("带 JOIN", "select t1.a, t2.b from t1 inner join t2 on t1.id = t2.id")

compare("子查询", "select a, (select max(x) from t2 where t2.id = t1.id) as max_x from t1")

compare("深层嵌套子查询", "select a, (select b from (select c from t1)) as nested from t2")

compare("CASE WHEN", "select case when x > 0 then 'positive' when x < 0 then 'negative' else 'zero' end as sign from t1")

compare("CTE WITH", "with cte1 as (select a, b from t1) select * from cte1")

compare("OVER 窗口函数", "select a, row_number() over (partition by b order by c desc) as rn from t1")

compare("CREATE TABLE", "create table t1 (a int comment 'column a', b string, c double)")

compare("多语句", "select a, b from t1; select x, y from t2;")

print("\n" + "="*60)
print("对比测试完成!")
print("="*60)
