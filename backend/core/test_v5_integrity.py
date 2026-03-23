# -*- coding: utf-8 -*-
"""
V5 SQL 完整性验证测试
确保所有 SQL 内容在格式化后不丢失
"""
import sys
import os
from pathlib import Path

# 设置UTF-8编码输出
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from formatter_v5 import format_sql_v5


def verify_integrity(test_name: str, original_sql: str, expected_keywords: list) -> bool:
    """验证 SQL 格式化后关键内容是否完整"""
    try:
        formatted = format_sql_v5(original_sql)

        # 检查所有期望的关键字是否存在
        missing = []
        for keyword in expected_keywords:
            if keyword not in formatted:
                missing.append(keyword)

        if missing:
            print(f"  ❌ {test_name}: 缺失关键字 {missing}")
            print(f"     原始: {original_sql[:100]}...")
            print(f"     结果: {formatted[:100]}...")
            return False
        else:
            print(f"  ✅ {test_name}")
            return True

    except Exception as e:
        print(f"  ⚠️ {test_name}: 异常 - {e}")
        return False


def test_critical_scenarios():
    """测试关键场景"""
    print("=" * 60)
    print("V5 关键场景完整性测试")
    print("=" * 60)
    print()

    results = []

    # 1. 函数内嵌套子查询 - V4 之前的关键 bug
    print("【函数嵌套子查询】")
    results.append(verify_integrity(
        "AVG + COALESCE + SELECT + SUM",
        "SELECT p.category, AVG(COALESCE((SELECT SUM(o.quantity * o.unit_price) FROM order_items o), 0)) as category_avg FROM products p",
        ["SELECT", "AVG", "COALESCE", "SUM", "FROM"]
    ))

    results.append(verify_integrity(
        "COUNT + CASE WHEN",
        "SELECT COUNT(CASE WHEN status = 'active' THEN 1 END) FROM users",
        ["SELECT", "COUNT", "CASE", "WHEN", "FROM"]
    ))

    results.append(verify_integrity(
        "MAX + COALESCE + 子查询",
        "SELECT MAX(COALESCE((SELECT amount FROM payments WHERE user_id = u.id), 0)) FROM users u",
        ["SELECT", "MAX", "COALESCE", "FROM"]
    ))

    print()

    # 2. 集合操作
    print("【集合操作】")
    results.append(verify_integrity(
        "UNION ALL",
        "SELECT a, b FROM t1 UNION ALL SELECT c, d FROM t2",
        ["SELECT", "FROM", "UNION", "ALL"]
    ))

    results.append(verify_integrity(
        "INTERSECT",
        "SELECT a FROM t1 INTERSECT SELECT b FROM t2",
        ["SELECT", "FROM", "INTERSECT"]
    ))

    print()

    # 3. 窗口函数
    print("【窗口函数】")
    results.append(verify_integrity(
        "ROW_NUMBER OVER",
        "SELECT a, ROW_NUMBER() OVER (PARTITION BY b ORDER BY c) AS rn FROM t1",
        ["SELECT", "ROW_NUMBER", "OVER", "PARTITION", "ORDER", "FROM"]
    ))

    results.append(verify_integrity(
        "RANK OVER + 窗口帧",
        "SELECT a, RANK() OVER (ORDER BY b DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) FROM t1",
        ["SELECT", "RANK", "OVER", "ORDER", "ROWS", "BETWEEN"]
    ))

    print()

    # 4. CTE
    print("【CTE/WITH 语句】")
    results.append(verify_integrity(
        "WITH 子句",
        "WITH cte AS (SELECT a FROM t1) SELECT * FROM cte",
        ["WITH", "SELECT", "FROM"]
    ))

    results.append(verify_integrity(
        "多 CTE",
        "WITH c1 AS (SELECT a FROM t1), c2 AS (SELECT b FROM t2) SELECT * FROM c1 JOIN c2 ON c1.id = c2.id",
        ["WITH", "SELECT", "FROM", "JOIN"]
    ))

    print()

    # 5. CASE WHEN
    print("【CASE WHEN】")
    results.append(verify_integrity(
        "简单 CASE WHEN",
        "SELECT CASE WHEN x > 0 THEN 1 WHEN x < 0 THEN -1 ELSE 0 END FROM t1",
        ["SELECT", "CASE", "WHEN", "THEN", "ELSE", "END", "FROM"]
    ))

    results.append(verify_integrity(
        "嵌套 CASE WHEN",
        "SELECT CASE WHEN x > 0 THEN CASE WHEN y > 0 THEN 1 ELSE 2 END ELSE 0 END FROM t1",
        ["SELECT", "CASE", "WHEN", "THEN", "ELSE", "END", "FROM"]
    ))

    print()

    # 6. 复杂 JOIN + ON 条件
    print("【复杂 JOIN】")
    results.append(verify_integrity(
        "多表 JOIN",
        "SELECT * FROM t1 JOIN t2 ON t1.id = t2.id LEFT JOIN t3 ON t2.ref = t3.id",
        ["SELECT", "FROM", "JOIN", "ON", "LEFT"]
    ))

    results.append(verify_integrity(
        "JOIN + 子查询",
        "SELECT * FROM t1 JOIN (SELECT a, b FROM t2) t2 ON t1.id = t2.a",
        ["SELECT", "FROM", "JOIN", "ON"]
    ))

    print()

    # 7. 深层嵌套
    print("【深层嵌套】")
    results.append(verify_integrity(
        "4 层嵌套",
        "SELECT * FROM (SELECT * FROM (SELECT * FROM (SELECT a FROM t1)))",
        ["SELECT", "FROM"]
    ))

    results.append(verify_integrity(
        "EXISTS 深层嵌套",
        "SELECT * FROM t1 WHERE EXISTS (SELECT 1 FROM t2 WHERE EXISTS (SELECT 1 FROM t3))",
        ["SELECT", "FROM", "WHERE", "EXISTS"]
    ))

    print()

    # 8. 聚合 + GROUP BY + HAVING
    print("【聚合函数】")
    results.append(verify_integrity(
        "GROUP BY + HAVING",
        "SELECT a, COUNT(*) FROM t1 GROUP BY a HAVING COUNT(*) > 10",
        ["SELECT", "COUNT", "FROM", "GROUP", "BY", "HAVING"]
    ))

    results.append(verify_integrity(
        "多聚合函数",
        "SELECT SUM(a), AVG(b), MAX(c), MIN(d), COUNT(*) FROM t1",
        ["SELECT", "SUM", "AVG", "MAX", "MIN", "COUNT", "FROM"]
    ))

    print()

    # 汇总
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"测试结果: {passed}/{total} 通过")
    if passed == total:
        print("✅ 所有测试通过！V5 SQL 完整性验证成功")
    else:
        print(f"⚠️ 有 {total - passed} 个测试失败，需要修复")
    print("=" * 60)

    return passed == total


def test_real_files():
    """测试真实 SQL 文件"""
    print()
    print("=" * 60)
    print("真实 SQL 文件完整性测试")
    print("=" * 60)
    print()

    test_case_dir = Path(__file__).parent.parent.parent.parent / "测试用例表"

    test_files = [
        "JRJC_MON_B01_T18_GRKHXX.sql",
        "GJDG_JRZF_D01_PARALLEL_CWKJB - 副本.sql",
        "GJDG_JRZF_G03 - 副本.sql"
    ]

    all_passed = True
    for filename in test_files:
        file_path = test_case_dir / filename
        if not file_path.exists():
            print(f"  ⚠️ 文件不存在: {filename}")
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            original_sql = f.read()

        try:
            formatted = format_sql_v5(original_sql)

            # 关键关键字检查
            keywords = ["SELECT", "FROM"]
            missing = [kw for kw in keywords if kw not in formatted]

            if missing:
                print(f"  ❌ {filename}: 缺失关键字 {missing}")
                all_passed = False
            else:
                # 简单长度检查（格式化后应该变长，不应该变短太多）
                original_len = len(original_sql)
                formatted_len = len(formatted)

                if formatted_len < original_len * 0.8:
                    print(f"  ⚠️ {filename}: 结果长度异常 ({original_len} -> {formatted_len})")
                    all_passed = False
                else:
                    print(f"  ✅ {filename}: {original_len} -> {formatted_len} 字符")

        except Exception as e:
            print(f"  ❌ {filename}: 异常 - {e}")
            all_passed = False

    print()
    if all_passed:
        print("✅ 所有真实文件测试通过")
    else:
        print("⚠️ 部分文件测试失败")

    return all_passed


if __name__ == "__main__":
    # 运行关键场景测试
    scenario_passed = test_critical_scenarios()

    # 运行真实文件测试
    file_passed = test_real_files()

    # 总体结果
    print()
    print("=" * 60)
    if scenario_passed and file_passed:
        print("🎉 V5 SQL 完整性验证全部通过！")
        sys.exit(0)
    else:
        print("⚠️ V5 SQL 完整性验证发现问题，需要修复")
        sys.exit(1)
