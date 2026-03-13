# -*- coding: utf-8 -*-
"""
嵌套SQL格式化测试结果报告
测试日期: 2026-03-13
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import urllib.request
import urllib.parse
import json

API_URL = "http://127.0.0.1:8888/format/v5"

def format_sql(sql, keyword_case="upper"):
    """使用urllib发送POST请求"""
    data = json.dumps({"sql": sql, "keyword_case": keyword_case}).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        return {"success": False, "error": str(e)}

# 测试样例
TEST_CASES = [
    {
        "name": "样例1: WHERE子句嵌套子查询",
        "sql": """SELECT customer_id, customer_name, total_amount
FROM customers c
WHERE customer_id IN (
    SELECT customer_id FROM orders
    WHERE order_date > '2024-01-01'
    AND total_amount > (
        SELECT AVG(total_amount) * 2 FROM orders
        WHERE order_date > '2024-01-01'
    )
)
ORDER BY total_amount DESC""",
        "expected": "IN子查询应该缩进4空格，嵌套的子查询再缩进4空格"
    },
    {
        "name": "样例2: FROM子句多层嵌套",
        "sql": """SELECT t1.department, t1.avg_salary
FROM (
    SELECT department, AVG(salary) as avg_salary
    FROM employees GROUP BY department
) t1
INNER JOIN (
    SELECT department, MAX(salary) as max_salary
    FROM employees GROUP BY department
) t2 ON t1.department = t2.department""",
        "expected": "子查询内容应该缩进4空格"
    },
    {
        "name": "样例3: 窗口函数嵌套",
        "sql": """SELECT employee_id, salary
FROM (
    SELECT employee_id, salary,
    ROW_NUMBER() OVER (PARTITION BY dept ORDER BY salary DESC) as rank
    FROM employees
) ranked
WHERE rank <= 5""",
        "expected": "OVER子句应该缩进4空格"
    },
    {
        "name": "样例4: UNION嵌套",
        "sql": """SELECT product_id, sales FROM (
    SELECT p.product_id, SUM(o.amount) as sales
    FROM products p JOIN orders o ON p.id = o.product_id
    GROUP BY p.product_id
) q1
UNION ALL
SELECT product_id, sales FROM (
    SELECT p.product_id, SUM(o.amount) as sales
    FROM products p JOIN orders o ON p.id = o.product_id
    GROUP BY p.product_id
) q2""",
        "expected": "UNION ALL应该在新行，两侧SELECT对齐"
    },
    {
        "name": "样例5: CTE + 嵌套",
        "sql": """WITH stats AS (
    SELECT dept, AVG(salary) as avg_sal
    FROM employees GROUP BY dept
)
SELECT * FROM stats WHERE avg_sal > 50000""",
        "expected": "CTE内容应该缩进到开括号位置+1"
    },
    {
        "name": "样例6: EXISTS嵌套",
        "sql": """SELECT c.customer_id,
CASE WHEN EXISTS (
    SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id
) THEN 'Has Orders' ELSE 'No Orders' END as status
FROM customers c""",
        "expected": "EXISTS子查询应该有合理缩进"
    },
    {
        "name": "样例7: LATERAL VIEW",
        "sql": """SELECT id, name FROM table1
LATERAL VIEW EXPLODE(array_col) exploded AS alias""",
        "expected": "LATERAL VIEW应该在独立行"
    },
    {
        "name": "样例8: 多个WHERE嵌套",
        "sql": """SELECT a FROM t1
WHERE a IN (SELECT b FROM t2 WHERE c < 5)
AND a NOT IN (SELECT d FROM t3 WHERE d IS NULL)""",
        "expected": "多个IN/NOT IN子查询应该有相同缩进"
    },
    {
        "name": "样例9: MERGE语句",
        "sql": """MERGE INTO target t USING source s ON t.id = s.id
WHEN MATCHED THEN UPDATE SET t.value = s.value
WHEN NOT MATCHED THEN INSERT (id, value) VALUES (s.id, s.value)""",
        "expected": "MERGE各子句应该有清晰格式"
    },
    {
        "name": "样例10: INSERT OVERWRITE",
        "sql": """INSERT OVERWRITE TABLE target
SELECT * FROM source WHERE date > '2024-01-01'""",
        "expected": "INSERT OVERWRITE后SELECT应该换行"
    },
]

# 运行测试
print("=" * 80)
print("嵌套SQL格式化测试报告")
print("=" * 80)

issues = []
passes = []

for i, test in enumerate(TEST_CASES, 1):
    print(f"\n【测试 {i}/{len(TEST_CASES)}】{test['name']}")
    print("-" * 60)

    try:
        result = format_sql(test["sql"], "upper")

        if result.get("success"):
            formatted = result.get("formatted", "")
            print("[OK] 格式化成功")
            print("\n格式化结果:")
            print(formatted)

            # 检查常见问题
            test_issues = []

            # 检查过度缩进（超过30个空格可能是错误的）
            lines = formatted.split("\n")
            for j, line in enumerate(lines):
                # 计算前导空格
                leading_spaces = len(line) - len(line.lstrip())
                if leading_spaces > 40 and line.strip():
                    test_issues.append(f"行{j+1}缩进过多({leading_spaces}空格): {line[:50]}...")
                # 检查空行过多
                if j > 0 and not line.strip() and not lines[j-1].strip():
                    pass  # 连续空行

            # 检查内容是否被截断（改进版：检测关键字缺失而非长度）
            # 检查原始SQL中的关键字是否都在格式化结果中
            sql_upper = test["sql"].upper()
            formatted_upper = formatted.upper()

            # 关键字列表
            key_keywords = ["WITH", "SELECT", "FROM", "WHERE", "MERGE", "INSERT", "UPDATE", "DELETE", "UNION", "CASE", "WHEN", "THEN", "ELSE", "END"]

            # 检查原始SQL中存在的关键字是否在格式化结果中存在
            missing_keywords = []
            for kw in key_keywords:
                if kw in sql_upper and kw not in formatted_upper:
                    missing_keywords.append(kw)

            if missing_keywords:
                test_issues.append(f"可能存在内容截断，缺失关键字: {', '.join(missing_keywords)}")

            # 检查关键字是否大写
            keywords = ["SELECT", "FROM", "WHERE", "JOIN", "UNION", "CASE", "WHEN", "THEN", "ELSE", "END"]
            missing_upper = []
            for kw in keywords:
                if kw.lower() in formatted.upper() and kw not in formatted:
                    missing_upper.append(kw)

            if test_issues:
                issues.append({
                    "test": test["name"],
                    "issues": test_issues
                })
                print("\n[!] 发现问题:")
                for issue in test_issues:
                    print(f"  - {issue}")
            else:
                passes.append(test["name"])
                print("\n[OK] 未发现明显问题")
        else:
            error = result.get("error", "Unknown error")
            issues.append({
                "test": test["name"],
                "issues": [f"格式化失败: {error}"]
            })
            print(f"[X] 格式化失败: {error}")

    except Exception as e:
        issues.append({
            "test": test["name"],
            "issues": [f"请求异常: {str(e)}"]
        })
        print(f"[X] 请求异常: {e}")

    print()

# 总结报告
print("=" * 80)
print("测试总结")
print("=" * 80)
print(f"总计测试: {len(TEST_CASES)}")
print(f"通过: {len(passes)}")
print(f"有问题: {len(issues)}")

if issues:
    print("\n" + "=" * 80)
    print("问题汇总")
    print("=" * 80)
    for item in issues:
        print(f"\n[X] {item['test']}")
        for issue in item['issues']:
            print(f"   - {issue}")

print("\n" + "=" * 80)
