"""测试基于 sqlglot 的格式化器"""
from core.formatter import format_sql

# 测试用例
test_cases = [
    # 简单 SQL
    "select aa,bb,cc,dd from tab123 where aa='1' and bb='3' and cc='4'",

    # 带 CASE WHEN 的 SQL
    """select id,
case when type = 'A' then 'Type A'
when type = 'B' then 'Type B'
else 'Other' end as type_desc
from users""",

    # 用户提供的复杂 SQL
    """SELECT SUBSTR(t8.cdpt_accno,1,16) AS accountno
,t8.cdpt_accno AS accountno1
,CASE WHEN SUBSTR(t8.cdpt_accno,1,3) = 'FTE' THEN '01'
WHEN SUBSTR(t8.cdpt_accno,1,3) = 'FTN' THEN '02'
ELSE '' END AS acctype
,t7.zmdm AS currency
FROM XXXTAB
WHERE t1.etl_load_date = '{DATA_DT}'""",
]

for i, sql in enumerate(test_cases):
    print(f"\n{'='*60}")
    print(f"测试案例 {i + 1}:")
    print(f"{'='*60}")
    print("\n原始 SQL:")
    print(sql)
    print("\n格式化后:")
    result = format_sql(sql, keyword_case='upper', indent=4, comma='front', semicolon=True)
    print(result)
