"""
Spark SQL 静态分析器
纯静态分析，无需执行SQL
"""
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Issue:
    """优化问题"""
    rule: str
    severity: str  # HIGH, MEDIUM, LOW
    message: str
    line: int
    suggestion: str
    code_snippet: Optional[str] = None


class StaticAnalyzer:
    """Spark SQL静态分析器"""

    def __init__(self):
        self.rules = self._init_rules()

    def _init_rules(self) -> List[Dict]:
        """初始化优化规则"""
        return [
            {
                "name": "SELECT_STAR",
                "severity": "HIGH",
                "pattern": r"SELECT\s+\*",
                "message": "避免使用 SELECT *，只查询需要的字段以减少网络传输和内存开销",
                "suggestion": "列出具体需要的字段名",
                "rewrite": self._rewrite_select_star
            },
            {
                "name": "LIKE_LEADING_WILDCARD",
                "severity": "HIGH",
                "pattern": r"LIKE\s+['\"]%",
                "message": "LIKE 以通配符开头无法使用索引，性能较差",
                "suggestion": "考虑使用全文索引或修改查询逻辑",
                "rewrite": None
            },
            {
                "name": "CROSS_JOIN",
                "severity": "HIGH",
                "pattern": r"CROSS\s+JOIN",
                "message": "检测到笛卡尔积（CROSS JOIN），确保这是预期行为",
                "suggestion": "检查是否缺少JOIN条件",
                "rewrite": None
            },
            {
                "name": "IMPLICIT_CAST",
                "severity": "MEDIUM",
                "pattern": r"CAST\s*\(",
                "message": "建议显式类型转换以提高性能",
                "suggestion": "使用 CAST(字段 AS 类型) 进行显式转换",
                "rewrite": None
            },
            {
                "name": "OR_IN_WHERE",
                "severity": "MEDIUM",
                "pattern": r"WHERE.*OR.*OR",
                "message": "WHERE子句中多个OR条件可能导致性能问题",
                "suggestion": "考虑使用 IN 或 UNION ALL 重写",
                "rewrite": self._rewrite_or_to_in
            },
            {
                "name": "HAVING_WHERE",
                "severity": "MEDIUM",
                "pattern": r"HAVING\s",
                "message": "HAVING子句中的条件可以考虑下推到WHERE",
                "suggestion": "将可以在分组前过滤的条件移到WHERE子句",
                "rewrite": None
            },
            {
                "name": "DISTINCT_ORDER_BY",
                "severity": "LOW",
                "pattern": r"DISTINCT.*ORDER\s+BY",
                "message": "DISTINCT + ORDER BY 性能开销较大",
                "suggestion": "考虑是否真的需要排序，或者使用聚合函数替代",
                "rewrite": None
            },
            {
                "name": "HARDCODED_DATE",
                "severity": "LOW",
                "pattern": r"DATE\s*[=<>]\s*['\"]\d{4}-\d{2}-\d{2}",
                "message": "检测到硬编码日期，建议使用参数变量",
                "suggestion": "使用 ${date_var} 替代硬编码日期",
                "rewrite": None
            },
            {
                "name": "LIMIT_MISSING",
                "severity": "LOW",
                "pattern": r"ORDER\s+BY.*(?!LIMIT)",
                "message": "ORDER BY 没有 LIMIT 可能导致内存溢出",
                "suggestion": "添加 LIMIT 限制返回行数",
                "rewrite": None
            },
            {
                "name": "JOIN_NO_CONDITION",
                "severity": "HIGH",
                "pattern": r"JOIN\s+\w+\s+(?!ON|USING)",
                "message": "JOIN缺少ON条件，可能产生笛卡尔积",
                "suggestion": "添加JOIN条件: JOIN table ON a.id = b.id",
                "rewrite": None
            },
            {
                "name": "COUNT_DISTINCT_LARGE",
                "severity": "MEDIUM",
                "pattern": r"COUNT\s*\(\s*DISTINCT",
                "message": "COUNT(DISTINCT) 可能导致数据倾斜",
                "suggestion": "考虑使用近似计数函数（approx_count_distinct）",
                "rewrite": None
            },
            {
                "name": "SUBQUERY_DEEP",
                "severity": "MEDIUM",
                "pattern": r"\(\s*SELECT",
                "message": "检测到嵌套子查询，建议使用CTE（WITH子句）提高可读性",
                "suggestion": "使用 WITH 子句定义公共表达式",
                "rewrite": self._rewrite_subquery_to_cte
            }
        ]

    def analyze(self, sql: str, filename: str = None) -> Dict[str, Any]:
        """
        分析SQL并返回优化建议

        Args:
            sql: SQL语句
            filename: 文件名（可选）

        Returns:
            分析结果字典
        """
        issues = []
        lines = sql.split('\n')

        # 对每一行应用所有规则
        for line_num, line in enumerate(lines, start=1):
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith('--'):
                continue

            for rule in self.rules:
                pattern = rule["pattern"]
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(Issue(
                        rule=rule["name"],
                        severity=rule["severity"],
                        message=rule["message"],
                        line=line_num,
                        suggestion=rule["suggestion"]
                    ))
                    # 每行每个规则只报告一次
                    break

        # 尝试自动重写
        optimized_sql = self._rewrite_sql(sql, issues)

        return {
            "file": filename,
            "original_sql": sql,
            "optimized_sql": optimized_sql,
            "issues": [
                {
                    "rule": issue.rule,
                    "severity": issue.severity,
                    "message": issue.message,
                    "line": issue.line,
                    "suggestion": issue.suggestion
                }
                for issue in issues
            ],
            "issue_count": len(issues),
            "high_priority": sum(1 for i in issues if i.severity == "HIGH"),
            "medium_priority": sum(1 for i in issues if i.severity == "MEDIUM"),
            "low_priority": sum(1 for i in issues if i.severity == "LOW")
        }

    def _rewrite_sql(self, sql: str, issues: List[Issue]) -> str:
        """自动重写SQL"""
        optimized = sql

        for issue in issues:
            rule_name = issue.rule
            # 查找对应的重写函数
            rule = next((r for r in self.rules if r["name"] == rule_name), None)
            if rule and rule.get("rewrite"):
                try:
                    optimized = rule["rewrite"](optimized)
                except Exception as e:
                    print(f"重写规则 {rule_name} 失败: {e}")

        return optimized

    def _rewrite_select_star(self, sql: str) -> str:
        """重写 SELECT *（需要元数据支持，这里简化处理）"""
        # 简化版本：提示用户添加字段
        if "SELECT *" in sql.upper():
            return sql.replace("SELECT *", "SELECT column1, column2, column3 /* 添加具体字段 */")
        return sql

    def _rewrite_or_to_in(self, sql: str) -> str:
        """重写 OR 为 IN"""
        # 简化处理：将 status = 'A' OR status = 'B' 改为 status IN ('A', 'B')
        pattern = r"(\w+)\s*=\s*['\"](\w+)['\"]\s+OR\s+\1\s*=\s*['\"](\w+)['\"]"
        matches = list(re.finditer(pattern, sql, re.IGNORECASE))

        if matches and len(matches) >= 2:
            field = matches[0].group(1)
            values = [m.group(2) for m in matches]
            in_clause = f"{field} IN ({', '.join(repr(v) for v in values)})"
            # 简单替换第一个OR
            sql = re.sub(pattern, in_clause, sql, count=1, flags=re.IGNORECASE)

        return sql

    def _rewrite_subquery_to_cte(self, sql: str) -> str:
        """重写子查询为CTE"""
        # 检测是否有多个子查询
        subquery_count = sql.count("(SELECT")
        if subquery_count >= 2:
            # 提示使用CTE
            return sql + "\n/* 建议：使用 WITH 子句定义公共表达式以提高可读性和性能 */"
        return sql

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """分析单个SQL文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                sql = f.read()
            return self.analyze(sql, filename=file_path)
        except Exception as e:
            return {
                "error": f"无法读取文件 {file_path}: {str(e)}",
                "file": file_path
            }

    def analyze_batch(self, folder: str) -> List[Dict[str, Any]]:
        """批量分析文件夹中的SQL文件"""
        import os
        results = []

        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.endswith('.sql'):
                    file_path = os.path.join(root, file)
                    result = self.analyze_file(file_path)
                    results.append(result)

        return results
