# -*- coding: utf-8 -*-
"""
V4 vs V5 格式化对比测试
比较两个版本的格式化结果，验证功能等价性
"""
import sys
import os
from pathlib import Path
from difflib import unified_diff

# 设置UTF-8编码输出
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from formatter_v4_fixed import format_sql_v4_fixed
from formatter_v5 import format_sql_v5


def compare_formatting(test_name: str, sql: str, show_diff: bool = False) -> dict:
    """比较 V4 和 V5 的格式化结果"""
    v4_result = format_sql_v4_fixed(sql)
    v5_result = format_sql_v5(sql)

    is_identical = v4_result == v5_result

    result = {
        'name': test_name,
        'identical': is_identical,
        'v4_length': len(v4_result),
        'v5_length': len(v5_result),
        'v4_lines': v4_result.count('\n') + 1,
        'v5_lines': v5_result.count('\n') + 1,
    }

    if not is_identical and show_diff:
        print(f"\n  差异详情 ({test_name}):")
        v4_lines = v4_result.splitlines(keepends=True)
        v5_lines = v5_result.splitlines(keepends=True)
        diff = unified_diff(v4_lines, v5_lines, lineterm='', fromfile='V4', tofile='V5')
        for line in diff:
            print(f"    {line.rstrip()}")

    return result


def test_comparison():
    """V4 vs V5 对比测试"""
    print("=" * 60)
    print("V4 vs V5 格式化对比测试")
    print("=" * 60)
    print()

    test_cases = [
        # 基础 SELECT - 应该完全相同（V5 回退到 V4）
        ("简单 SELECT", "SELECT a, b FROM t1"),
        ("WHERE 条件", "SELECT a FROM t1 WHERE b = 1"),
        ("JOIN", "SELECT * FROM t1 JOIN t2 ON t1.id = t2.id"),

        # 集合操作 - V5 使用专用处理器
        ("UNION ALL", "SELECT a FROM t1 UNION ALL SELECT b FROM t2"),
        ("UNION", "SELECT a FROM t1 UNION SELECT b FROM t2"),
        ("INTERSECT", "SELECT a FROM t1 INTERSECT SELECT b FROM t2"),

        # 窗口函数 - V5 使用专用处理器
        ("OVER 简单", "SELECT ROW_NUMBER() OVER (ORDER BY a) FROM t1"),
        ("OVER PARTITION", "SELECT ROW_NUMBER() OVER (PARTITION BY b ORDER BY c) FROM t1"),
        ("OVER 窗口帧", "SELECT SUM(a) OVER (ORDER BY b ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING) FROM t1"),

        # CTE
        ("WITH 单个", "WITH cte AS (SELECT a FROM t1) SELECT * FROM cte"),
        ("WITH 多个", "WITH c1 AS (SELECT a FROM t1), c2 AS (SELECT b FROM t2) SELECT * FROM c1 JOIN c2 ON c1.a = c2.b"),

        # CASE WHEN
        ("CASE WHEN", "SELECT CASE WHEN a > 0 THEN 1 ELSE 0 END FROM t1"),
        ("CASE WHEN 多分支", "SELECT CASE WHEN a > 0 THEN 1 WHEN a < 0 THEN -1 ELSE 0 END FROM t1"),

        # 聚合
        ("GROUP BY", "SELECT a, COUNT(*) FROM t1 GROUP BY a"),
        ("HAVING", "SELECT a, COUNT(*) FROM t1 GROUP BY a HAVING COUNT(*) > 1"),

        # 函数内子查询（V4 之前有 bug）
        ("函数嵌套", "SELECT AVG(COALESCE((SELECT SUM(a) FROM t2), 0)) FROM t1"),

        # 深层嵌套
        ("子查询嵌套", "SELECT * FROM (SELECT a FROM (SELECT b FROM t1))"),

        # 复杂场景
        ("复杂 JOIN + WHERE", """
            SELECT t1.a, t2.b, t3.c
            FROM t1
            JOIN t2 ON t1.id = t2.id
            LEFT JOIN t3 ON t2.ref = t3.id
            WHERE t1.status = 'active' AND t2.amount > 100
        """),

        ("INSERT OVERWRITE", "INSERT OVERWRITE TABLE target SELECT * FROM source"),
    ]

    results = []
    identical_count = 0
    different_count = 0

    for test_name, sql in test_cases:
        sql_clean = sql.strip()
        result = compare_formatting(test_name, sql_clean)

        results.append(result)

        if result['identical']:
            identical_count += 1
            print(f"  ✅ {test_name}: 完全相同 ({result['v4_lines']} 行)")
        else:
            different_count += 1
            print(f"  ⚠️  {test_name}: 存在差异")
            print(f"      V4: {result['v4_length']} 字符, {result['v4_lines']} 行")
            print(f"      V5: {result['v5_length']} 字符, {result['v5_lines']} 行")

    print()
    print("=" * 60)
    print(f"对比结果: {identical_count} 个完全相同, {different_count} 个存在差异")
    print("=" * 60)

    # 显示差异详情
    if different_count > 0:
        print()
        print("📊 差异分析:")
        for result in results:
            if not result['identical']:
                # 重新获取详细差异
                compare_formatting(result['name'], next(
                    sql for name, sql in test_cases if name == result['name']
                ), show_diff=True)

    return results


def test_real_file_comparison():
    """真实文件对比测试"""
    print()
    print("=" * 60)
    print("真实文件 V4 vs V5 对比")
    print("=" * 60)
    print()

    test_case_dir = Path(__file__).parent.parent.parent.parent / "测试用例表"
    test_files = [
        "JRJC_MON_B01_T18_GRKHXX.sql",
    ]

    for filename in test_files:
        file_path = test_case_dir / filename
        if not file_path.exists():
            continue

        print(f"\n📄 {filename}")

        with open(file_path, 'r', encoding='utf-8') as f:
            original_sql = f.read()

        v4_result = format_sql_v4_fixed(original_sql)
        v5_result = format_sql_v5(original_sql)

        is_identical = v4_result == v5_result

        if is_identical:
            print(f"  ✅ 完全相同")
        else:
            print(f"  ⚠️  存在差异")
            print(f"      V4: {len(v4_result)} 字符, {v4_result.count(chr(10)) + 1} 行")
            print(f"      V5: {len(v5_result)} 字符, {v5_result.count(chr(10)) + 1} 行")

            # 显示前几处差异
            v4_lines = v4_result.splitlines()
            v5_lines = v5_result.splitlines()
            diff_count = 0
            for i, (l1, l2) in enumerate(zip(v4_lines[:50], v5_lines[:50])):
                if l1 != l2:
                    diff_count += 1
                    if diff_count <= 3:
                        print(f"\n      第 {i+1} 行差异:")
                        print(f"        V4: {l1[:80]}")
                        print(f"        V5: {l2[:80]}")

            if diff_count > 3:
                print(f"      ... 还有 {diff_count - 3} 处差异")


if __name__ == "__main__":
    test_comparison()
    test_real_file_comparison()
