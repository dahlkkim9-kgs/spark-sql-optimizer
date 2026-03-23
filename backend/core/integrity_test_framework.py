# -*- coding: utf-8 -*-
"""
SQL 格式化器完整性测试框架
基于 SQL 语法和语义的多维度验证
"""
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# 设置UTF-8编码输出
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 尝试导入 sqlglot
try:
    import sqlglot
    from sqlglot import parse_one, parse
    from sqlglot.optimizer import optimize
    HAS_SQLGLOT = True
except ImportError:
    HAS_SQLGLOT = False


class TestResult(Enum):
    """测试结果"""
    PASS = "✅ PASS"
    FAIL = "❌ FAIL"
    WARN = "⚠️  WARN"
    SKIP = "⏭️  SKIP"


@dataclass
class IntegrityCheck:
    """单个完整性检查结果"""
    name: str
    result: TestResult
    details: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)

    def __str__(self):
        status = self.result.value
        if self.details:
            return f"{status} | {self.name}: {self.details}"
        return f"{status} | {self.name}"


@dataclass
class TestReport:
    """测试报告"""
    test_name: str
    original_sql: str
    formatted_sql: str
    checks: List[IntegrityCheck] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """所有关键检查是否通过"""
        critical = [c for c in self.checks if c.result != TestResult.SKIP]
        return all(c.result == TestResult.PASS for c in critical)

    def print_report(self):
        """打印报告"""
        print(f"\n{'='*70}")
        print(f"测试: {self.test_name}")
        print(f"{'='*70}")

        for check in self.checks:
            print(check)

        if self.passed:
            print(f"\n{'='*70}")
            print(f"✅ 所有检查通过")
            print(f"{'='*70}")
        else:
            print(f"\n{'='*70}")
            print(f"❌ 存在失败检查")
            print(f"{'='*70}")


class SQLIntegrityValidator:
    """SQL 完整性验证器"""

    def __init__(self, formatter_func):
        """
        Args:
            formatter_func: 格式化函数，签名为 (sql: str) -> str
        """
        self.formatter = formatter_func

    def validate(self, sql: str, test_name: str = "Unnamed") -> TestReport:
        """
        执行完整的完整性验证

        Args:
            sql: 原始 SQL
            test_name: 测试名称

        Returns:
            TestReport: 测试报告
        """
        formatted = self.formatter(sql)
        report = TestReport(
            test_name=test_name,
            original_sql=sql,
            formatted_sql=formatted
        )

        # 执行所有检查
        report.checks = [
            self._check_parseable(sql, formatted),
            self._check_ast_equivalent(sql, formatted),
            self._check_element_counts(sql, formatted),
            self._check_keywords_preserved(sql, formatted),
            self._check_literals_preserved(sql, formatted),
            self._check_comments_preserved(sql, formatted),
        ]

        return report

    def _check_parseable(self, original: str, formatted: str) -> IntegrityCheck:
        """检查: 两个 SQL 都能被正确解析"""
        if not HAS_SQLGLOT:
            return IntegrityCheck(
                "可解析性",
                TestResult.SKIP,
                "sqlglot 未安装"
            )

        try:
            parse_one(original, dialect='spark')
            orig_parseable = True
        except Exception as e:
            return IntegrityCheck(
                "可解析性",
                TestResult.WARN,
                f"原始 SQL 解析失败: {e}"
            )

        try:
            parse_one(formatted, dialect='spark')
            form_parseable = True
        except Exception as e:
            return IntegrityCheck(
                "可解析性",
                TestResult.FAIL,
                f"格式化 SQL 解析失败: {e}"
            )

        return IntegrityCheck(
            "可解析性",
            TestResult.PASS,
            "原始和格式化 SQL 都能正确解析"
        )

    def _check_ast_equivalent(self, original: str, formatted: str) -> IntegrityCheck:
        """检查: AST 语义等价（核心检查）"""
        if not HAS_SQLGLOT:
            return IntegrityCheck(
                "AST 语义等价",
                TestResult.SKIP,
                "sqlglot 未安装"
            )

        try:
            orig_ast = parse_one(original, dialect='spark')
            form_ast = parse_one(formatted, dialect='spark')

            # 转换为标准化 SQL 进行对比
            orig_norm = orig_ast.sql(dialect='spark', normalize=True, pad=0)
            form_norm = form_ast.sql(dialect='spark', normalize=True, pad=0)

            if orig_norm == form_norm:
                return IntegrityCheck(
                    "AST 语义等价",
                    TestResult.PASS,
                    "格式化后 SQL 语义与原始 SQL 完全等价"
                )
            else:
                # 尝试更宽松的对比 - 检查关键结构
                orig_stmts = list(parse(original, dialect='spark'))
                form_stmts = list(parse(formatted, dialect='spark'))

                if len(orig_stmts) != len(form_stmts):
                    return IntegrityCheck(
                        "AST 语义等价",
                        TestResult.FAIL,
                        f"语句数量不同: 原始 {len(orig_stmts)} vs 格式化 {len(form_stmts)}"
                    )

                return IntegrityCheck(
                    "AST 语义等价",
                    TestResult.WARN,
                    "标准化 SQL 存在差异，但结构相同（可能是格式风格差异）"
                )

        except Exception as e:
            return IntegrityCheck(
                "AST 语义等价",
                TestResult.WARN,
                f"AST 对比失败: {e}"
            )

    def _check_element_counts(self, original: str, formatted: str) -> IntegrityCheck:
        """检查: SQL 元素数量（表、列、JOIN、子查询等）"""
        import re

        def count_elements(sql: str) -> Dict[str, int]:
            """统计 SQL 元素数量"""
            return {
                'SELECT': len(re.findall(r'\bSELECT\b', sql, re.IGNORECASE)),
                'FROM': len(re.findall(r'\bFROM\b', sql, re.IGNORECASE)),
                'JOIN': len(re.findall(r'\b(?:INNER|LEFT|RIGHT|FULL|CROSS)?\s*JOIN\b', sql, re.IGNORECASE)),
                'UNION': len(re.findall(r'\bUNION\b', sql, re.IGNORECASE)),
                '子查询': len(re.findall(r'\(\s*SELECT\b', sql, re.IGNORECASE)),
            }

        orig_counts = count_elements(original)
        form_counts = count_elements(formatted)

        mismatches = []
        for key in orig_counts:
            if orig_counts[key] != form_counts[key]:
                mismatches.append(f"{key}: {orig_counts[key]} -> {form_counts[key]}")

        if mismatches:
            return IntegrityCheck(
                "元素数量",
                TestResult.FAIL,
                f"元素数量变化: {', '.join(mismatches)}",
                metrics={'original': orig_counts, 'formatted': form_counts}
            )

        return IntegrityCheck(
            "元素数量",
            TestResult.PASS,
            f"所有元素数量一致 (SELECT:{orig_counts['SELECT']}, JOIN:{orig_counts['JOIN']}, 子查询:{orig_counts['子查询']})"
        )

    def _check_keywords_preserved(self, original: str, formatted: str) -> IntegrityCheck:
        """检查: SQL 关键字完整性"""
        import re

        # 从原始 SQL 提取所有 SQL 关键字（转换为小写计数）
        orig_keywords = re.findall(
            r'\b(SELECT|FROM|WHERE|JOIN|ON|AND|OR|GROUP|BY|HAVING|ORDER|UNION|INTERSECT|EXCEPT|CASE|WHEN|THEN|ELSE|END|OVER|PARTITION|WITH|AS|IN|EXISTS|BETWEEN|LIKE|IS|NULL)\b',
            original,
            re.IGNORECASE
        )

        # 从格式化后的 SQL 提取关键字
        form_keywords = re.findall(
            r'\b(SELECT|FROM|WHERE|JOIN|ON|AND|OR|GROUP|BY|HAVING|ORDER|UNION|INTERSECT|EXCEPT|CASE|WHEN|THEN|ELSE|END|OVER|PARTITION|WITH|AS|IN|EXISTS|BETWEEN|LIKE|IS|NULL)\b',
            formatted,
            re.IGNORECASE
        )

        # 统计关键字（不区分大小写）
        orig_counts = {}
        for kw in orig_keywords:
            orig_counts[kw.lower()] = orig_counts.get(kw.lower(), 0) + 1

        form_counts = {}
        for kw in form_keywords:
            form_counts[kw.lower()] = form_counts.get(kw.lower(), 0) + 1

        # 对比数量
        missing = []
        for kw, count in orig_counts.items():
            if form_counts.get(kw, 0) < count:
                missing.append(f"{kw}({count}->{form_counts.get(kw, 0)})")

        if missing:
            return IntegrityCheck(
                "关键字保留",
                TestResult.FAIL,
                f"关键字数量减少: {', '.join(missing)}"
            )

        return IntegrityCheck(
            "关键字保留",
            TestResult.PASS,
            f"所有 {len(orig_keywords)} 个关键字完整保留"
        )

    def _check_literals_preserved(self, original: str, formatted: str) -> IntegrityCheck:
        """检查: 字面量（字符串、数字）保留"""
        import re

        # 提取字符串字面量
        orig_strings = set(re.findall(r"'[^']*'", original))
        form_strings = set(re.findall(r"'[^']*'", formatted))

        missing_strings = orig_strings - form_strings
        extra_strings = form_strings - orig_strings

        # 提取数字字面量
        orig_numbers = set(re.findall(r'\b\d+\.?\d*\b', original))
        form_numbers = set(re.findall(r'\b\d+\.?\d*\b', formatted))

        missing_numbers = orig_numbers - form_numbers

        issues = []
        if missing_strings:
            issues.append(f"缺失字符串: {missing_strings}")
        if extra_strings:
            issues.append(f"多余字符串: {extra_strings}")
        if missing_numbers:
            issues.append(f"缺失数字: {missing_numbers}")

        if issues:
            return IntegrityCheck(
                "字面量保留",
                TestResult.FAIL,
                "; ".join(issues)
            )

        return IntegrityCheck(
            "字面量保留",
            TestResult.PASS,
            f"字符串 {len(orig_strings)} 个, 数字 {len(orig_numbers)} 个"
        )

    def _check_comments_preserved(self, original: str, formatted: str) -> IntegrityCheck:
        """检查: 注释保留"""
        import re

        # 提取行注释
        orig_line_comments = re.findall(r'--[^\n]*', original)
        form_line_comments = re.findall(r'--[^\n]*', formatted)

        # 简单检查：注释数量不应减少
        if len(orig_line_comments) > len(form_line_comments):
            missing = len(orig_line_comments) - len(form_line_comments)
            return IntegrityCheck(
                "注释保留",
                TestResult.WARN,
                f"缺失 {missing} 个行注释"
            )

        # 检查关键注释内容
        if orig_line_comments:
            # 提取注释中的关键词（忽略空白）
            orig_comment_words = set()
            for c in orig_line_comments:
                words = re.findall(r'\b\w+\b', c)
                orig_comment_words.update(w.lower() for w in words)

            form_comment_words = set()
            for c in form_line_comments:
                words = re.findall(r'\b\w+\b', c)
                form_comment_words.update(w.lower() for w in words)

            missing_words = orig_comment_words - form_comment_words
            if missing_words:
                return IntegrityCheck(
                    "注释保留",
                    TestResult.WARN,
                    f"注释内容可能变化: 缺失词 {missing_words}"
                )

        return IntegrityCheck(
            "注释保留",
            TestResult.PASS,
            f"行注释 {len(orig_line_comments)} 个"
        )


# 预定义的测试用例
CRITICAL_TEST_CASES = {
    "函数嵌套子查询": """
        SELECT p.category, AVG(COALESCE((SELECT SUM(o.quantity * o.unit_price) FROM order_items o WHERE o.product_id = p.id), 0)) as category_avg
        FROM products p
        GROUP BY p.category
    """,

    "UNION 集合操作": """
        SELECT a, b FROM t1 WHERE a > 0
        UNION ALL
        SELECT c, d FROM t2 WHERE c < 10
        UNION
        SELECT e, f FROM t3 WHERE e IS NOT NULL
    """,

    "窗口函数": """
        SELECT
            department,
            employee_name,
            ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS rank,
            SUM(salary) OVER (PARTITION BY department ORDER BY hire_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative
        FROM employees
    """,

    "CTE 嵌套": """
        WITH cte1 AS (
            SELECT a, b FROM t1
        ),
        cte2 AS (
            SELECT c, d FROM t2
        )
        SELECT * FROM cte1 JOIN cte2 ON cte1.a = cte2.c
    """,

    "CASE WHEN 嵌套": """
        SELECT CASE WHEN a > 0 THEN (CASE WHEN b > 0 THEN 1 ELSE 2 END) ELSE 0 END FROM t1
    """,

    "深层子查询": """
        SELECT * FROM (
            SELECT * FROM (
                SELECT * FROM (
                    SELECT a FROM t1
                ) t1
            ) t2
        ) t3
    """,

    "注释中的关键字": """
        --4. UNION + 嵌套 + CASE
        SELECT product_id FROM products
        UNION ALL
        SELECT order_id FROM orders
    """,

    "复杂 JOIN": """
        SELECT *
        FROM t1
        INNER JOIN t2 ON t1.id = t2.id AND t1.status = 'active'
        LEFT JOIN t3 ON t2.ref = t3.id
        WHERE t1.date > '2024-01-01'
    """,
}


def run_critical_tests(formatter_func, formatter_name: str) -> bool:
    """运行所有关键测试用例"""
    print(f"\n{'#'*70}")
    print(f"# {formatter_name} 完整性验证测试")
    print(f"{'#'*70}")

    validator = SQLIntegrityValidator(formatter_func)
    all_passed = True

    for test_name, sql in CRITICAL_TEST_CASES.items():
        report = validator.validate(sql.strip(), test_name)
        report.print_report()

        if not report.passed:
            all_passed = False

    # 总结
    print(f"\n{'#'*70}")
    if all_passed:
        print(f"# ✅ 所有关键测试通过")
    else:
        print(f"# ❌ 存在失败的测试")
    print(f"{'#'*70}\n")

    return all_passed


if __name__ == "__main__":
    # 测试 V5 格式化器
    from formatter_v5 import format_sql_v5

    success = run_critical_tests(format_sql_v5, "V5 Formatter")
    sys.exit(0 if success else 1)
