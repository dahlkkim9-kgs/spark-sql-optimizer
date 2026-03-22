"""
Spark SQL 静态分析器
纯静态分析，无需执行SQL
"""
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import sqlglot
from sqlglot import exp
from sqlglot.dialects import Spark
from .formatter_v4_fixed import format_sql_v4_fixed as format_sql


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
            # ========== 新增规则 ==========
            # 1. IN子查询检测
            {
                "name": "IN_SUBQUERY",
                "severity": "HIGH",
                "pattern": r"\bIN\s*\(\s*SELECT\b",
                "message": "避免使用 IN (SELECT ...) 子查询，可能导致性能下降",
                "suggestion": "建议改用 LEFT SEMI JOIN 以利用谓词下推和优化器能力",
                "rewrite": self._rewrite_in_subquery
            },
            # 2. NOT IN子查询检测
            {
                "name": "NOT_IN_SUBQUERY",
                "severity": "HIGH",
                "pattern": r"\bNOT\s+IN\s*\(\s*SELECT\b",
                "message": "避免使用 NOT IN (SELECT ...) 子查询，不仅性能差且 NULL 值处理易出错",
                "suggestion": "建议改用 LEFT ANTI JOIN",
                "rewrite": self._rewrite_not_in_subquery
            },
            # 3. IN列表过长检测
            {
                "name": "IN_VALUES_LONG",
                "severity": "MEDIUM",
                "pattern": r"\bIN\s*\([^)]{100,}\)",
                "message": "IN 子句列表过长，可能导致 Catalyst 优化器生成过大的执行计划或栈溢出",
                "suggestion": "建议将常量列表放入临时表或使用 JOIN 代替",
                "rewrite": self._rewrite_in_values_long
            },
            # 4. WHERE子句函数使用检测
            {
                "name": "WHERE_FUNCTION",
                "severity": "MEDIUM",
                "pattern": r"\bWHERE\s+[^'\"]*?\b[a-z_][a-z0-9_]*\s*\([^)]+\)\s*(=|<>|>|<|>=|<=)",
                "message": "WHERE 子句中对列使用函数会导致无法利用索引或分区裁剪",
                "suggestion": "建议将函数逻辑转换为等价的范围查询或计算好值后再传入",
                "rewrite": self._rewrite_where_function
            },
            # 5. 分区裁剪失效检测
            {
                "name": "PARTITION_PRUNING",
                "severity": "HIGH",
                "pattern": r"\bWHERE\s+[^'\"]*?\b(YEAR|MONTH|DAY|TO_DATE|DATE_FORMAT)\s*\([^)]+\)\s*=",
                "message": "分区列上使用函数会导致分区裁剪失效，触发全表扫描",
                "suggestion": "建议直接使用分区列进行范围过滤，如 partition_col >= '2024-01-01' AND partition_col < '2025-01-01'",
                "rewrite": self._rewrite_partition_pruning
            },
            # 6. SELECT子句子查询检测（放在 SUBQUERY_DEEP 前面）
            {
                "name": "SUBQUERY_IN_SELECT",
                "severity": "MEDIUM",
                "pattern": r"\bSELECT\s+.*\(\s*SELECT\b",
                "message": "SELECT 子句中包含标量子查询，每一行都会执行一次子查询，性能极差",
                "suggestion": "建议使用 JOIN 或窗口函数重写",
                "rewrite": self._rewrite_subquery_in_select
            },
            # 原有的 SUBQUERY_DEEP 规则（调整为只检测 WHERE/子查询）
            {
                "name": "SUBQUERY_DEEP",
                "severity": "MEDIUM",
                "pattern": r"\bWHERE\s+.*\(\s*SELECT|\bIN\s*\(\s*SELECT|\bEXISTS\s*\(\s*SELECT",
                "message": "检测到嵌套子查询，建议使用CTE（WITH子句）提高可读性",
                "suggestion": "使用 WITH 子句定义公共表达式",
                "rewrite": self._rewrite_subquery_to_cte
            },
            # 7. COUNT DISTINCT检测（覆盖原有规则）
            {
                "name": "COUNT_DISTINCT",
                "severity": "MEDIUM",
                "pattern": r"\bCOUNT\s*\(\s*DISTINCT\b",
                "message": "COUNT(DISTINCT ...) 在数据量大时 shuffle 压力大，且不利于优化",
                "suggestion": "如果允许近似统计，建议使用 approx_count_distinct；或考虑 GROUP BY 改写",
                "rewrite": self._rewrite_count_distinct
            },
            # 8. WHERE中UDF检测
            {
                "name": "UDF_IN_WHERE",
                "severity": "HIGH",
                "pattern": r"\bWHERE\s+.*?\b[a-z_]+[a-z0-9_]*\s*\(",
                "message": "WHERE 子句中使用 UDF 会导致无法谓词下推，且序列化开销大",
                "suggestion": "建议使用 Spark 内置函数替代 UDF，或将 UDF 逻辑改写为 SQL",
                "rewrite": self._rewrite_udf_in_where
            },
            # 9. LEFT JOIN过滤条件位置检测
            {
                "name": "LEFT_JOIN_WHERE_FILTER",
                "severity": "HIGH",
                "pattern": r"\bLEFT\s+(?:OUTER\s+)?JOIN\b.*?\bON\b.*?\bAND\b",
                "message": "LEFT JOIN 的左表过滤条件写在 ON 子句中不会过滤结果行数，逻辑可能错误",
                "suggestion": "左表的过滤条件应移至 WHERE 子句，右表的过滤条件应在 ON 子句中",
                "rewrite": self._rewrite_left_join_where_filter
            },
            # ========== 代码规范规则 ==========
            # 10. 表名中包含日期检测
            {
                "name": "TABLE_NAME_WITH_DATE",
                "severity": "HIGH",
                "pattern": r"\b(?:FROM|JOIN|TABLE|INSERT\s+INTO|UPDATE|CREATE\s+TABLE)\s+(?:\w+\.)?\w*[12]\d{3}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\w*",
                "message": "检测到表名中包含日期（如 table_20250102），请检查是否为分区表命名或临时表",
                "suggestion": "建议使用分区表规范命名，如 table_name PARTITION(dt='20250102')，或使用变量替代硬编码日期",
                "rewrite": None
            },
            # 11. 注释中包含分号检测
            {
                "name": "COMMENT_WITH_SEMICOLON",
                "severity": "HIGH",
                "pattern": r"--[^;\n]*;",
                "message": "检测到注释行中包含分号（;），可能导致SQL解析错误",
                "suggestion": "请检查注释内容，如果分号是注释说明的一部分，请确保不会影响SQL解析；如果是误写的分号，请删除",
                "rewrite": None
            },
            # 12. 敏感信息检测（身份证号、敏感字段名）
            {
                "name": "SENSITIVE_INFO_DETECTED",
                "severity": "HIGH",
                "pattern": r"\b1[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b|(?:身份证|证件号|id_card|idcard|identity|sfz)",
                "message": "检测到可能的敏感信息（身份证号或相关字段名），请确保符合数据安全规范",
                "suggestion": "建议对敏感字段进行脱敏处理（如 md5/hash），或确保已获得相应授权；检查字段命名是否符合安全规范",
                "rewrite": None
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

        # 先对整个 SQL 进行规则检测（支持跨行匹配）
        for rule in self.rules:
            pattern = rule["pattern"]
            if re.search(pattern, sql, re.IGNORECASE | re.MULTILINE):
                # 查找匹配位置的行号
                match = re.search(pattern, sql, re.IGNORECASE | re.MULTILINE)
                if match:
                    # 计算匹配位置的行号
                    match_pos = match.start()
                    line_num = sql[:match_pos].count('\n') + 1
                    issues.append(Issue(
                        rule=rule["name"],
                        severity=rule["severity"],
                        message=rule["message"],
                        line=line_num,
                        suggestion=rule["suggestion"]
                    ))

        # 尝试自动重写
        rewritten_sql = self._rewrite_sql(sql, issues)

        # 使用新的格式化器格式化重写后的SQL
        optimized_sql = format_sql(rewritten_sql, keyword_case='upper', indent=4, comma_start=True, semicolon_newline=True)

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

    # ========== 新增 rewrite 函数 ==========

    def _rewrite_in_subquery(self, sql: str) -> str:
        """重写 IN (SELECT...) 为 LEFT SEMI JOIN"""
        # 简化实现：添加提示注释
        if re.search(r'\bIN\s*\(\s*SELECT\b', sql, re.IGNORECASE):
            return sql + "\n/* 建议：将 IN (SELECT...) 改写为 LEFT SEMI JOIN 以提高性能 */"
        return sql

    def _rewrite_not_in_subquery(self, sql: str) -> str:
        """重写 NOT IN (SELECT...) 为 LEFT ANTI JOIN"""
        # 简化实现：添加提示注释
        if re.search(r'\bNOT\s+IN\s*\(\s*SELECT\b', sql, re.IGNORECASE):
            return sql + "\n/* 建议：将 NOT IN (SELECT...) 改写为 LEFT ANTI JOIN 以提高性能 */"
        return sql

    def _rewrite_in_values_long(self, sql: str) -> str:
        """重写过长的 IN 列表"""
        # 检测过长的 IN 列表
        pattern = r'\bIN\s*\([^)]{100,}\)'
        if re.search(pattern, sql, re.IGNORECASE):
            return sql + "\n/* 建议：IN 列表过长，考虑使用临时表或 VALUES 子句 */"
        return sql

    def _rewrite_where_function(self, sql: str) -> str:
        """重写 WHERE 中的函数调用"""
        # 检测 WHERE 中的函数调用
        pattern = r'\bWHERE\s+.*?\b\w+\s*\([^)]*\)\s*(=|>|<|>=|<=|!=|<>|LIKE|IN)'
        if re.search(pattern, sql, re.IGNORECASE):
            return sql + "\n/* 建议：WHERE 子句中对列使用函数会阻止索引/分区裁剪，考虑在 SELECT 中计算或使用范围查询 */"
        return sql

    def _rewrite_partition_pruning(self, sql: str) -> str:
        """重写分区裁剪失效的写法"""
        # 检测 YEAR/MONTH/DAY 函数作用于分区列
        pattern = r'\bWHERE\s+.*?\b(YEAR|MONTH|DAY|TO_DATE|DATE_FORMAT)\s*\([^)]*\)\s*='
        if re.search(pattern, sql, re.IGNORECASE):
            return sql + "\n/* 建议：对分区列使用函数会阻止分区裁剪，应直接使用分区列进行范围比较 */"
        return sql

    def _rewrite_subquery_in_select(self, sql: str) -> str:
        """重写 SELECT 子句中的子查询"""
        # 检测 SELECT 中的子查询
        pattern = r'\bSELECT\s+[^,]*?\(\s*SELECT\b'
        if re.search(pattern, sql, re.IGNORECASE):
            return sql + "\n/* 建议：SELECT 中的标量子查询性能极差，考虑使用 JOIN 或窗口函数重写 */"
        return sql

    def _rewrite_count_distinct(self, sql: str) -> str:
        """重写 COUNT(DISTINCT...) 为近似计数"""
        # 检测 COUNT(DISTINCT...)
        pattern = r'\bCOUNT\s*\(\s*DISTINCT\s+([^)]+)\)'
        match = re.search(pattern, sql, re.IGNORECASE)
        if match:
            column = match.group(1)
            # 添加建议注释
            return sql + "\n/* 建议：如果允许近似统计，使用 approx_count_distinct({}) 替代 COUNT(DISTINCT {}) */".format(column, column)
        return sql

    def _rewrite_udf_in_where(self, sql: str) -> str:
        """重写 WHERE 中的 UDF"""
        # Spark 内置函数白名单（小写）- 扩展版本
        builtin_funcs = {
            'abs', 'acos', 'asin', 'atan', 'avg', 'cast', 'ceil', 'coalesce',
            'collect_list', 'collect_set', 'concat', 'concat_ws', 'cos',
            'count', 'current_date', 'current_timestamp', 'date_add',
            'date_format', 'date_sub', 'day', 'dayofmonth', 'dayofweek',
            'dayofyear', 'degrees', 'dense_rank', 'exp', 'first', 'floor',
            'from_unixtime', 'from_unix_timestamp', 'get_json_object', 'greatest', 'hash', 'hour',
            'if', 'in', 'isnan', 'isnotnull', 'isnull', 'last', 'least', 'length',
            'like', 'ln', 'locate', 'log', 'log10', 'lower', 'lpad', 'lcase',
            'ltrim', 'max', 'md5', 'min', 'minute', 'mod', 'month',
            'nvl', 'parse_url', 'pow', 'rank', 'regexp_extract',
            'regexp_replace', 'repeat', 'round', 'rpad', 'rtrim', 'second',
            'sha', 'sha1', 'sha2', 'sin', 'size', 'soundex', 'space', 'sqrt', 'substr',
            'substring', 'sum', 'tan', 'to_date', 'to_json', 'to_timestamp',
            'to_unix_timestamp', 'translate', 'trim', 'trunc', 'upper', 'ucase',
            'uuid', 'weekofyear', 'when', 'year', 'initcap', 'ascii',
            'base64', 'bin', 'bit_count', 'bit_length', 'btrim', 'ceil', 'ceiling',
            'char', 'chr', 'coalesce', 'collect_list', 'collect_set', 'concat',
            'conv', 'cos', 'cosh', 'cot', 'current_catalog', 'current_database',
            'current_date', 'current_schema', 'current_timestamp', 'current_user',
            'date_add', 'date_format', 'date_sub', 'datediff', 'day', 'dayofmonth',
            'degrees', 'dense_rank', 'e', 'exp', 'explode', 'first',
            'floor', 'from_unixtime', 'from_utc_timestamp', 'get_json_object',
            'greatest', 'hash', 'hex', 'hour', 'if', 'ifnull', 'in',
            'initcap', 'inline', 'input_file_block_length', 'input_file_block_start',
            'instr', 'isnotnull', 'isnull', 'last', 'last_day', 'lcase',
            'least', 'length', 'levenshtein', 'locate', 'log', 'log10',
            'log2', 'log', 'lower', 'lpad', 'ltrim', 'map',
            'map_keys', 'map_values', 'max', 'md5', 'min', 'minute',
            'mod', 'month', 'monotonically_increasing_id', 'named_struct',
            'nanvl', 'negative', 'next_day', 'not', 'now', 'ntile',
            'nvl', 'nvl2', 'octet_length', 'or', 'parse_url', 'percent_rank',
            'pi', 'pmod', 'posexplode', 'positive', 'pow', 'printf',
            'radians', 'rand', 'rank', 'reflect', 'regexp_count',
            'regexp_extract', 'regexp_replace', 'repeat', 'reverse', 'rpad',
            'rtrim', 'second', 'sequence', 'sha', 'sha1', 'sha2',
            'shiftleft', 'shiftright', 'sign', 'sin', 'sinh', 'size',
            'soundex', 'space', 'spark_partition_id', 'split', 'sqrt',
            'stack', 'stddev', 'stddev_pop', 'stddev_samp', 'str_to_map',
            'string', 'struct', 'subdate', 'substr', 'substring', 'sum',
            'tan', 'tanh', 'timestamp', 'to_date', 'to_json', 'to_timestamp',
            'to_utc_timestamp', 'translate', 'trim', 'trunc', 'ucase',
            'unbase64', 'unhex', 'upper', 'uuid', 'var_pop', 'var_samp',
            'variance', 'weekofyear', 'when', 'window', 'xxhash64', 'year'
        }

        # 检测 WHERE 中的函数调用（非内置函数）
        pattern = r'\bWHERE\s+.*?\b([a-z_][a-z0-9_]*)\s*\('
        matches = re.finditer(pattern, sql, re.IGNORECASE)
        for match in matches:
            func_name = match.group(1).lower()
            if func_name not in builtin_funcs:
                return sql + f"\n/* 建议：WHERE 中的 UDF '{func_name}' 会阻止谓词下推，考虑使用 Spark 内置函数 */"
        return sql

    def _rewrite_left_join_where_filter(self, sql: str) -> str:
        """重写 LEFT JOIN 中错误位置的过滤条件"""
        # 检测 LEFT JOIN ... ON ... AND 模式
        # 这种情况下需要检查是否有左表的条件被错误地放在 ON 中
        pattern = r'\bLEFT\s+(?:OUTER\s+)?JOIN\s+(\w+)\s+(?:AS\s+)?(\w+)\s+ON\s+\w+\.\w+\s*=\s*\w+\.\w+\s+AND\s+(\w+)\.\w+'
        match = re.search(pattern, sql, re.IGNORECASE)
        if match:
            right_table = match.group(1).lower()
            filter_table = match.group(3).lower()
            # 如果 ON 后的 AND 条件中引用的表是左表（不是右表），给出警告
            # 注意：这里简单判断，实际可能需要更复杂的分析
            if filter_table != right_table:
                return sql + "\n/* 警告：LEFT JOIN 的左表过滤条件应放在 WHERE 子句中，而不是 ON 子句中 */"
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

    def format_sql(self, sql: str, **options) -> str:
        """
        格式化SQL语句（符合《大数据SQL开发规范》）

        Args:
            sql: 原始SQL语句
            **options: 格式化选项
                - keyword_case: 关键字大小写 (默认 'upper')
                - indent: 缩进空格数 (默认 4)
                - comma_start: 逗号前置 (默认 True)
                - semicolon_newline: 分号另起一行 (默认 True)

        Returns:
            格式化后的SQL字符串
        """
        # 设置默认选项（符合开发规范）
        format_options = {
            'keyword_case': options.get('keyword_case', 'upper'),
            'indent': options.get('indent', 4),
            'comma_start': options.get('comma_start', True),
            'semicolon_newline': options.get('semicolon_newline', True),
        }

        try:
            return format_sql(sql, **format_options)
        except Exception as e:
            # 如果格式化失败，返回原始SQL
            print(f"格式化失败: {e}")
            import traceback
            traceback.print_exc()
            return sql
