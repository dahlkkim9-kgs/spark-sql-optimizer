"""
SQL格式化器V2测试文件
测试符合《大数据SQL开发规范》的格式化功能
"""
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from formatter_v2 import format_sql_v2


def test_basic_select():
    """测试基本SELECT语句格式化"""
    sql = "select id, name, age from users where age > 18"
    result = format_sql_v2(sql)
    print("=" * 60)
    print("测试1: 基本SELECT语句")
    print("-" * 60)
    print("原始SQL:")
    print(sql)
    print("\n格式化后:")
    print(result)
    print()


def test_comma_first():
    """测试逗号前置"""
    sql = "SELECT id, name, age, email, phone FROM users"
    result = format_sql_v2(sql)
    print("=" * 60)
    print("测试2: 逗号前置")
    print("-" * 60)
    print("原始SQL:")
    print(sql)
    print("\n格式化后:")
    print(result)
    print()


def test_join_with_on():
    """测试JOIN和ON子句"""
    sql = "SELECT a.id, b.name FROM table1 a LEFT JOIN table2 b ON a.id = b.id AND a.dt = b.dt WHERE a.dt = '2024-01-01'"
    result = format_sql_v2(sql)
    print("=" * 60)
    print("测试3: JOIN与ON子句对齐")
    print("-" * 60)
    print("原始SQL:")
    print(sql)
    print("\n格式化后:")
    print(result)
    print()


def test_where_and_alignment():
    """测试WHERE条件AND对齐"""
    sql = "SELECT * FROM users WHERE age > 18 AND status = 'active' AND city = 'Beijing'"
    result = format_sql_v2(sql)
    print("=" * 60)
    print("测试4: WHERE条件AND右对齐")
    print("-" * 60)
    print("原始SQL:")
    print(sql)
    print("\n格式化后:")
    print(result)
    print()


def test_case_when():
    """测试CASE WHEN格式化"""
    sql = "SELECT id, CASE WHEN type = 1 THEN 'A' WHEN type = 2 THEN 'B' ELSE 'Other' END AS type_name FROM users"
    result = format_sql_v2(sql)
    print("=" * 60)
    print("测试5: CASE WHEN格式化")
    print("-" * 60)
    print("原始SQL:")
    print(sql)
    print("\n格式化后:")
    print(result)
    print()


def test_insert_overwrite():
    """测试INSERT OVERWRITE语句"""
    sql = "insert overwrite table target_table select id, name from source_table where dt = '2024-01-01'"
    result = format_sql_v2(sql)
    print("=" * 60)
    print("测试6: INSERT OVERWRITE语句")
    print("-" * 60)
    print("原始SQL:")
    print(sql)
    print("\n格式化后:")
    print(result)
    print()


def test_complex_query():
    """测试复杂查询"""
    sql = """
    select a.id, a.name, b.amount, c.status
    from table_a a
    left join table_b b on a.id = b.id and a.dt = b.dt
    left join table_c c on b.id = c.id and b.type = c.type
    where a.dt = '2024-01-01' and a.status = '1'
    group by a.id, a.name, b.amount, c.status
    having count(*) > 0
    order by a.id
    limit 100
    """
    result = format_sql_v2(sql)
    print("=" * 60)
    print("测试7: 复杂查询")
    print("-" * 60)
    print("原始SQL:")
    print(sql.strip())
    print("\n格式化后:")
    print(result)
    print()


def test_subquery():
    """测试子查询"""
    sql = "SELECT * FROM (SELECT id, name FROM users WHERE age > 18) t WHERE t.name LIKE 'John%'"
    result = format_sql_v2(sql)
    print("=" * 60)
    print("测试8: 子查询")
    print("-" * 60)
    print("原始SQL:")
    print(sql)
    print("\n格式化后:")
    print(result)
    print()


def test_keyword_case():
    """测试关键字大小写"""
    sql = "select id, name, count(*) as cnt from users where age > 18 group by id, name"
    result = format_sql_v2(sql)
    print("=" * 60)
    print("测试9: 关键字/函数名大写")
    print("-" * 60)
    print("原始SQL:")
    print(sql)
    print("\n格式化后:")
    print(result)
    print()


def test_real_world_example():
    """测试真实场景SQL（符合开发规范示例）"""
    sql = """INSERT OVERWRITE TABLE ra14.t_9_1
SELECT a.cust_id
     , a.cust_name
     , NVL(b.prod_name, '未知') AS prod_name
     , SUM(b.amount) AS total_amount
FROM rbdb.psbcprod_z_cust AS a
LEFT JOIN rbdb.psbcprod_z_trade AS b
    ON a.cust_id = b.cust_id
   AND a.dt = b.dt
WHERE a.dt = '${bizdate}'
  AND a.status = '1'
GROUP BY a.cust_id
       , a.cust_name
       , b.prod_name
;"""

    result = format_sql_v2(sql)
    print("=" * 60)
    print("测试10: 真实场景SQL")
    print("-" * 60)
    print("原始SQL:")
    print(sql)
    print("\n格式化后:")
    print(result)
    print()


def main():
    """运行所有测试"""
    print("\n")
    print("#" * 60)
    print("# SQL格式化器V2 - 符合《大数据SQL开发规范》测试")
    print("#" * 60)
    print("\n")

    test_basic_select()
    test_comma_first()
    test_join_with_on()
    test_where_and_alignment()
    test_case_when()
    test_insert_overwrite()
    test_complex_query()
    test_subquery()
    test_keyword_case()
    test_real_world_example()

    print("=" * 60)
    print("所有测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
