# -*- coding: utf-8 -*-
"""
SQL Formatter V4 - 修复版
基于 V4，只添加多语句支持，不改变任何格式化规则
"""
import re
from typing import List, Dict, Tuple


# ==================== 预编译正则表达式（性能优化） ====================
# 注释相关
LINE_COMMENT_PATTERN = re.compile(r'--[^\n]*')
BLOCK_COMMENT_PATTERN = re.compile(r'/\*.*?\*/', re.DOTALL)
COMMENT_STRING_PATTERN = re.compile(r"COMMENT\s*'([^']*')", re.IGNORECASE)
COMMENT_PLACEHOLDER_PATTERN = re.compile(r'(__COMMENT_STR_\d+__)')
COMMENT_PREFIX_PATTERN = re.compile(r'^(\s*(__COMMENT_\d+__\s*\n?\s*)+)')
COMMENT_ADJACENT_PATTERN = re.compile(r'(__COMMENT_\d+__)\s+(__COMMENT_\d+__)')

# SQL 关键字和结构
CASE_PATTERN = re.compile(r'\bCASE\b', re.IGNORECASE)
SELECT_PATTERN = re.compile(r'\bSELECT\b', re.IGNORECASE)
ON_PATTERN = re.compile(r'\bON\b\s+', re.IGNORECASE)
AS_SELECT_PATTERN = re.compile(r'\bAS\s+SELECT\b', re.IGNORECASE)
FROM_PATTERN = re.compile(r'\bFROM\b', re.IGNORECASE)

# CREATE TABLE 相关
CREATE_TABLE_PATTERN = re.compile(r'(CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?\S+)\s*', re.IGNORECASE)
CREATE_TABLE_AS_PATTERN = re.compile(r'(CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?\S+(?:\s+AS\s+)?)\s*(SELECT\s+.*)', re.IGNORECASE | re.DOTALL)

# PARTITIONED BY 相关
PARTITIONED_BY_PATTERN = re.compile(r'(PARTITIONED\s+BY)\s*', re.IGNORECASE)
PARTITIONED_BY_FULL_PATTERN = re.compile(r'(PARTITIONED\s+BY)\s*\((.*)\)', re.IGNORECASE)
ROW_FORMAT_PATTERN = re.compile(r"(ROW\s+FORMAT\s+[\s\S]+?)(?:\s*$|\s*(?=\s*__COMMENT_STR_\d+__|\s*COMMENT\s|\s*PARTITIONED\s))", re.IGNORECASE)

# INSERT 相关
INSERT_TABLE_PATTERN = re.compile(r'(INSERT\s+INTO\s+(?:TABLE\s+)?\S+)\s*(SELECT\s+.*)', re.IGNORECASE | re.DOTALL)
INSERT_PARTITION_PATTERN = re.compile(r'(INSERT\s+INTO\s+(?:TABLE\s+)?\S+\s+PARTITION\s*\([^\)]*\)\s*)(SELECT.*)', re.IGNORECASE | re.DOTALL)

# VIEW 相关
VIEW_PATTERN = re.compile(r'(CREATE\s+(?:TEMPORARY\s+)?VIEW\s+\S+)\s+AS\s+(SELECT\s+.*)', re.IGNORECASE | re.DOTALL)

# CACHE TABLE 相关
CACHE_TABLE_PATTERN = re.compile(r'(CACHE\s+TABLE\s+\S+)\s+AS\s+(.*)', re.IGNORECASE | re.DOTALL)

# EXPLAIN 相关
EXPLAIN_PATTERN = re.compile(r'(EXPLAIN(?:\s+\w+)?)\s+(SELECT\s+.*)', re.IGNORECASE | re.DOTALL)

# CTE 相关
CTE_PATTERN = re.compile(r'(\w+)\s+AS\s+\((.*)\)', re.IGNORECASE | re.DOTALL)

# 子查询相关
SUBQUERY_PATTERN = re.compile(r'\(\s*(__COMMENT_\d+__\s*)?SELECT\b', re.IGNORECASE)
TRAILING_COMMENT_PATTERN = re.compile(r'(__COMMENT_\d+__)\s*$')

# 列解析相关
COLUMN_COMMENT_PLACEHOLDER_PATTERN = re.compile(r'(__COMMENT_STR_\d+__)')
COLUMN_COMMENT_PATTERN = re.compile(r"COMMENT\s+'([^']*)'", re.IGNORECASE)
COLUMN_TYPE_PATTERN = re.compile(r'^([A-Z]+\s*(\([^)]+\))?)', re.IGNORECASE)
TABLE_COMMENT_PATTERN = re.compile(r"(__COMMENT_STR_\d+__|COMMENT\s+'[^']*')\s*", re.IGNORECASE)

# CASE WHEN 相关
CASE_AS_PATTERN = re.compile(r'\s+AS\s+(\w+)(?:\s*(__COMMENT_\d+__)\s*)?$', re.IGNORECASE)
CASE_END_COMMENT_PATTERN = re.compile(r'\bEND\s*(__COMMENT_\d+__)\s*$', re.IGNORECASE)
CASE_SIMPLE_PATTERN = re.compile(r'CASE\s+(.+?)\s+END$', re.IGNORECASE | re.DOTALL)

# 空行处理
EMPTY_LINES_PATTERN = re.compile(r'\n{3,}')


# ==================== 函数多行结构保护 ====================
def _protect_multiline_functions(sql: str) -> Tuple[str, Dict[str, str]]:
    """保护函数调用中的多行结构，避免被 normalize 压缩

    例如：CONCAT('a',
                'b')
    会被替换为占位符 __FUNC_0__，normalize 后再恢复

    注意：需要排除 SQL 关键字，避免将 FROM (SELECT) 等误认为函数调用
    """
    function_map = {}
    placeholder_count = 0

    # SQL 关键字列表，不应该被当作函数名
    SQL_KEYWORDS = {
        'SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP',
        'ALTER', 'TRUNCATE', 'ANALYZE', 'GRANT', 'REVOKE', 'MERGE', 'UNION',
        'INTERSECT', 'EXCEPT', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'LEFT',
        'RIGHT', 'INNER', 'OUTER', 'FULL', 'JOIN', 'ON', 'AND', 'OR', 'NOT',
        'IN', 'EXISTS', 'BETWEEN', 'LIKE', 'IS', 'NULL', 'ORDER', 'BY', 'GROUP',
        'HAVING', 'LIMIT', 'OFFSET', 'WITH', 'RECURSIVE', 'PARTITION', 'OVERWRITE',
        'TABLE', 'VIEW', 'INDEX', 'DATABASE', 'SCHEMA', 'FUNCTION', 'PROCEDURE',
        'INTO', 'VALUES', 'SET', 'DESC', 'ASC', 'DISTINCT', 'ALL', 'ANY', 'SOME'
    }

    def find_matching_paren(s, start):
        """找到匹配的右括号"""
        depth = 0
        for i in range(start, len(s)):
            if s[i] == '(':
                depth += 1
            elif s[i] == ')':
                depth -= 1
                if depth == 0:
                    return i
        return -1

    protected_sql = []
    i = 0

    while i < len(sql):
        # 检查是否在标识符中间（跳过）
        if i > 0 and (sql[i-1].isalnum() or sql[i-1] == '_'):
            protected_sql.append(sql[i])
            i += 1
            continue

        # 检测函数调用：IDENTIFIER( （标识符后直接跟左括号）
        if sql[i].isalpha():
            # 获取完整的标识符（函数名）
            func_name_start = i
            while i < len(sql) and (sql[i].isalnum() or sql[i] == '_'):
                i += 1

            # 提取标识符
            identifier = sql[func_name_start:i].upper()

            # 检查后面是否直接跟着括号（跳过空白）
            while i < len(sql) and sql[i] in ' \t':
                i += 1

            # 如果是括号，且标识符不是 SQL 关键字，说明这是函数调用
            if i < len(sql) and sql[i] == '(' and identifier not in SQL_KEYWORDS:
                paren_start = i
                paren_end = find_matching_paren(sql, paren_start)

                if paren_end > 0:
                    # 提取完整的函数调用（包括函数名和括号内容）
                    func_call = sql[func_name_start:paren_end + 1]

                    # 检查函数调用内部是否有换行
                    if '\n' in func_call:
                        # 有换行，需要保护
                        placeholder = f"__FUNC_{placeholder_count}__"
                        function_map[placeholder] = func_call
                        placeholder_count += 1
                        protected_sql.append(placeholder)
                        i = paren_end + 1
                        continue
                    else:
                        # 没有换行，不需要保护，但需要添加函数名和括号内容
                        protected_sql.append(sql[func_name_start:paren_end + 1])
                        i = paren_end + 1
                        continue
                else:
                    # 没有找到匹配的右括号，按普通字符处理
                    protected_sql.append(sql[func_name_start:i])
            else:
                # 不是函数调用，是普通标识符
                protected_sql.append(sql[func_name_start:i])
        else:
            # 不是字母开头，直接添加
            protected_sql.append(sql[i])
            i += 1

    return ''.join(protected_sql), function_map


def _restore_multiline_functions(sql: str, function_map: Dict[str, str]) -> str:
    """恢复被保护的函数多行结构"""
    result = sql
    for placeholder, original in function_map.items():
        result = result.replace(placeholder, original)
    return result


def _protect_multiline_in_lists(sql: str) -> Tuple[str, Dict[str, str]]:
    """保护 IN 列表中的多行结构，避免被 normalize 压缩

    例如：IN ('1070' --注释
            ,'1080')
    会被替换为占位符 __INLIST_0__，normalize 后再恢复

    同时保护 NOT IN 的情况
    """
    in_list_map = {}
    placeholder_count = 0

    def find_matching_paren(s, start):
        """找到匹配的右括号，考虑字符串和注释"""
        depth = 0
        in_string = False
        string_char = None
        in_line_comment = False
        i = start

        while i < len(s):
            char = s[i]

            # 处理行注释
            if not in_string and char == '-' and i + 1 < len(s) and s[i + 1] == '-':
                in_line_comment = True
                i += 2
                continue

            if in_line_comment:
                if char == '\n':
                    in_line_comment = False
                i += 1
                continue

            # 处理字符串
            if not in_string and char in ('"', "'"):
                in_string = True
                string_char = char
                i += 1
                continue
            elif in_string and char == string_char:
                # 检查是否转义
                if i > 0 and s[i - 1] != '\\':
                    in_string = False
                    string_char = None
                i += 1
                continue

            if in_string:
                i += 1
                continue

            # 处理括号
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0:
                    return i

            i += 1

        return -1

    protected_sql = []
    i = 0

    while i < len(sql):
        # 检测 IN 或 NOT IN 模式
        # 需要确保 IN/NOT IN 是独立的关键字，不是其他标识符的一部分
        in_pattern = re.search(r'\b(IN|NOT IN)\s*\(', sql[i:], re.IGNORECASE)

        if in_pattern:
            in_keyword = in_pattern.group(1)
            in_start = i + in_pattern.start()
            paren_start = i + in_pattern.end() - 1  # 左括号的位置

            # 找到匹配的右括号
            paren_end = find_matching_paren(sql, paren_start)

            if paren_end > 0:
                # 提取完整的 IN 列表：IN (...)
                in_list_full = sql[in_start:paren_end + 1]

                # 检查是否包含 SELECT（子查询），如果是则跳过保护
                # 子查询应该由子查询保护逻辑处理，而不是 IN 列表保护逻辑
                if re.search(r'\bSELECT\b', in_list_full, re.IGNORECASE):
                    # 这是一个子查询，不作为 IN 列表保护
                    protected_sql.append(sql[i:paren_end + 1])
                    i = paren_end + 1
                    continue

                # 检查 IN 列表内部是否有换行
                if '\n' in in_list_full:
                    # 有换行，需要保护
                    placeholder = f"__INLIST_{placeholder_count}__"
                    in_list_map[placeholder] = in_list_full
                    placeholder_count += 1

                    # 添加 IN 之前的内容（如果有）
                    protected_sql.append(sql[i:in_start])
                    # 添加占位符
                    protected_sql.append(placeholder)

                    i = paren_end + 1
                    continue
                else:
                    # 没有换行，不需要保护
                    protected_sql.append(sql[i:paren_end + 1])
                    i = paren_end + 1
                    continue
            else:
                # 没有找到匹配的右括号，按普通字符处理
                protected_sql.append(sql[i])
                i += 1
        else:
            # 没有找到 IN 模式，添加当前字符
            protected_sql.append(sql[i])
            i += 1

    return ''.join(protected_sql), in_list_map


def _restore_multiline_in_lists(sql: str, in_list_map: Dict[str, str]) -> str:
    """恢复被保护的 IN 列表多行结构"""
    result = sql
    for placeholder, original in in_list_map.items():
        result = result.replace(placeholder, original)
    return result


def extract_balanced_paren_content(sql: str, start_pos: int) -> tuple[str, int]:
    """
    从 start_pos 开始，提取匹配的括号内容

    正确处理：
    - 嵌套括号 (如 (SELECT * FROM (SELECT ...)))
    - 字符串（单引号、双引号）
    - 转义字符（如 \\'）

    Args:
        sql: 完整 SQL 语句
        start_pos: 左括号 ( 的位置

    Returns:
        (括号内内容, 结束位置)
        结束位置是右括号 ) 之后的位置

    Raises:
        ValueError: 如果括号不匹配
    """
    if sql[start_pos] != '(':
        raise ValueError(f"start_pos {start_pos} 不是左括号位置")

    depth = 1
    i = start_pos + 1
    in_string = False
    string_char = None

    while i < len(sql) and depth > 0:
        ch = sql[i]

        # 处理字符串
        if ch in ("'", '"') and (i == 0 or sql[i-1] != '\\'):
            if not in_string:
                in_string = True
                string_char = ch
            elif ch == string_char:
                in_string = False

        # 只在非字符串中计数括号
        if not in_string:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1

        i += 1

    if depth != 0:
        raise ValueError(f"括号不匹配：从位置 {start_pos} 开始")

    # 返回括号内内容（不包含外层括号）和结束位置
    return sql[start_pos + 1:i - 1], i


def _normalize_select_fields(sql: str) -> str:
    """预处理 SELECT 字段，修复不规范的格式

    处理：
    1. 隐式别名（没有 AS 的别名）-> 添加 AS
    2. 紧贴的注释 -> 添加空格分隔
    3. 跳过 CACHE TABLE ... AS 和 WITH ... AS 后面的子查询

    Args:
        sql: 注释保护后的 SQL

    Returns:
        修复后的 SQL
    """
    import re

    # 跳过 WITH AS 和 CACHE TABLE 语句，避免破坏结构
    sql_upper = sql.strip().upper()
    if sql_upper.startswith('WITH') or sql_upper.startswith('CACHE TABLE'):
        return sql

    # ============ 新增：跳过 CACHE TABLE/WITH 子查询的 normalize ============
    # 检测并保护 CACHE TABLE ... AS (SELECT ...) 和 WITH ... AS (SELECT ...) 中的子查询
    # 避免破坏这些子查询的结构，导致后续正则无法匹配

    def protect_special_subqueries(sql_text):
        """保护 CACHE TABLE 和 WITH 语句中的子查询，避免被 normalize 破坏"""
        protected = sql_text
        subquery_map = {}
        counter = [0]

        def protect_subquery(match):
            """保护一个子查询"""
            placeholder = f"__PROTECTED_SUBQUERY_{counter[0]}__"
            counter[0] += 1
            subquery_map[placeholder] = match.group(0)
            return placeholder

        # 保护 CACHE TABLE ... AS (SELECT ...)
        # 只有在 SQL 中包含 CACHE TABLE 时才执行
        # 注释掉：正则表达式在 Python 3.14 中有语法错误
        # 现在使用括号计数解析器在各个格式化函数中处理
        # if re.search(r'\bCACHE\s+TABLE\b', protected, re.IGNORECASE):
        #     protected = re.sub(
        #         r'(CACHE\s+TABLE\s+\S+\s+AS\s*\()([^)]+(?:\([^)]*\))*\))',
        #         lambda m: m.group(1) + protect_subquery(m) if m.group(1) else m.group(0),
        #         protected,
        #         flags=re.IGNORECASE | re.DOTALL
        #     )

        # 保护 WITH ... AS (SELECT ...)
        # 只有在 SQL 中包含 WITH 时才执行
        # 注释掉：正则表达式在 Python 3.14 中有语法错误
        # 现在使用括号计数解析器在各个格式化函数中处理
        # if re.search(r'\bWITH\b', protected, re.IGNORECASE):
        #     # 定义 protect_with_ctes 辅助函数（内部函数，可以访问 subquery_map）
        #     def protect_with_ctes_repl(match):
        #         """WITH 子句的替换函数 - 返回处理后的字符串"""
        #         with_clause = match.group(0)
        #         # 对 WITH 子句中的每个 CTE 进行保护
        #         cte_counter = [0]
        #
        #         def protect_cte_subquery(cte_match):
        #             """保护单个 CTE 中的子查询"""
        #             placeholder = f"__PROTECTED_SUBQUERY_{counter[0]}__"
        #             counter[0] += 1
        #             subquery_map[placeholder] = cte_match.group(2)
        #             return cte_match.group(1) + placeholder + cte_match.group(3)
        #
        #         # 匹配 cte_name AS (subquery) 模式
        #         result = re.sub(
        #             r'(\w+\s+AS\s*\()([^)]+(?:\([^)]*\))*\))',
        #             protect_cte_subquery,
        #             with_clause,
        #             flags=re.IGNORECASE | re.DOTALL
        #         )
        #         return result
        #
        #     protected = re.sub(
        #         r'(WITH\s+(?:\w+\s+AS\s*\([^)]+(?:\([^)]*\))*\)\s*,?\s*)+',
        #         protect_with_ctes_repl,
        #         protected,
        #         flags=re.IGNORECASE | re.DOTALL
        #     )

        return protected, subquery_map

    # 保护特殊子查询
    sql_protected, protected_map = protect_special_subqueries(sql)

    # ============ 原有的 normalize 逻辑 ============

    def normalize_fields_in_select(match):
        """修复单个 SELECT 语句中的字段格式"""
        select_content = match.group(1)
        from_keyword = match.group(2) if match.lastindex >= 2 else ''  # 捕获 FROM 关键字
        rest_of_sql = match.group(3) if match.lastindex >= 3 else ''  # FROM 后面的内容

        if not select_content:
            return match.group(0)

        # 分割字段（按逗号，考虑括号和注释占位符）
        fields = []
        current = ''
        paren_depth = 0
        in_string = False
        string_char = None
        in_line_comment = False

        i = 0
        while i < len(select_content):
            char = select_content[i]

            # 检查行注释开始
            if char == '-' and i + 1 < len(select_content) and select_content[i + 1] == '-' and not in_string:
                in_line_comment = True

            # 如果在行注释中，继续添加字符直到换行
            if in_line_comment:
                current += char
                if char == '\n':
                    in_line_comment = False
                i += 1
                continue

            # 处理字符串
            if char in ("'", '"') and (i == 0 or select_content[i-1] != '\\'):
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                current += char
                i += 1
                continue

            if in_string:
                current += char
                i += 1
                continue

            # 处理括号
            if char == '(':
                paren_depth += 1
                current += char
            elif char == ')':
                paren_depth -= 1
                current += char
            elif char == ',' and paren_depth == 0:
                # 分割字段，包括逗号后面的注释（只到行尾）
                # 先找到逗号后面的内容（可能包含注释）
                rest = select_content[i + 1:]
                # 检查是否有行注释（只匹配到行尾，不匹配换行符后的内容）
                comment_match = re.match(r'\s*([^\n]*--.*)', rest)
                # 检查是否有注释占位符（__COMMENT_X__）
                # 使用 re.match 确保注释占位符紧跟在逗号后面（只允许空白字符）
                comment_placeholder_match = re.match(r'\s*(__COMMENT_\d+__)\s*$', rest)
                if comment_match:
                    # 把逗号后面的注释也添加到当前字段
                    current += char + comment_match.group(0)
                    i += len(comment_match.group(0)) + 1
                elif comment_placeholder_match:
                    # 注释占位符紧跟在逗号后面，添加到当前字段
                    current += char + comment_placeholder_match.group(0)
                    i += len(comment_placeholder_match.group(0)) + 1
                else:
                    current += char
                    i += 1
                # 分割字段
                field = current.strip()
                if field:
                    fields.append(field)
                current = ''
                continue  # 跳过后面的 i += 1
            else:
                current += char
            i += 1

        # 添加最后一个字段
        if current.strip():
            fields.append(current.strip())

        # 修复每个字段
        normalized_fields = []
        for field in fields:
            normalized = _normalize_single_field(field)
            # 跳过空字段（如单独的逗号处理后的结果）
            if normalized.strip():
                normalized_fields.append(normalized)

        # 重新组合（保留每个字段的原始格式，包括换行）
        result = 'SELECT '
        for i, field in enumerate(normalized_fields):
            if i == 0:
                result += field
            else:
                # 检查字段是否以逗号开头
                if field.strip().startswith(','):
                    result += field
                else:
                    result += ',\n' + field

        # 添加 FROM 部分（如果有）
        if from_keyword:
            # 在 FROM 前面添加换行符，避免 FROM 被当作字段的一部分
            result += f'\n{from_keyword} {rest_of_sql}'

        return result

    # 使用保护的 SQL 进行 normalize
    normalized = re.sub(
        r'\bSELECT\b([\s\S]+?)(\bFROM\b)([\s\S]+?)(?=;|\Z)',
        normalize_fields_in_select,
        sql_protected,
        flags=re.IGNORECASE
    )

    # 恢复保护的子查询
    for placeholder, original in protected_map.items():
        normalized = normalized.replace(placeholder, original)

    return normalized


def _normalize_single_field(field: str) -> str:
    """修复单个字段的格式

    处理：
    1. 隐式别名 -> 添加 AS
    2. 紧贴的注释 -> 添加空格
    注意：保留字段内部的换行符（如 CONCAT 函数）
    """
    import re

    # 移除前导逗号（如果有）
    original_field = field
    field = field.lstrip(',').strip()

    # 移除字段内部的换行符（如 'B' ACTIONDESC\n, 中的 \n）
    # 但保留多行函数（如 CONCAT）的换行符
    if '\n' in field:
        # 检查是否是多行函数（包含关键字如 CONCAT, LPAD 等）
        multi_line_keywords = {'CONCAT', 'LPAD', 'RPAD', 'SUBSTRING', 'CASE', 'CAST'}
        is_multi_line_function = any(keyword in field for keyword in multi_line_keywords)
        if not is_multi_line_function:
            # 不是多行函数，移除换行符
            lines = field.split('\n')
            field = ' '.join(line.strip() for line in lines if line.strip())

    # 检查是否已经有多行结构（包含换行符）
    has_newlines = '\n' in field

    # 提取注释和逗号（注释可能在末尾，也可能紧贴别名）
    comment_placeholder = None
    line_comment = None
    has_trailing_comma = False

    # 先检查注释占位符
    comment_placeholder_match = re.search(r'(__COMMENT_\d+__)\s*$', field)
    if comment_placeholder_match:
        comment_placeholder = comment_placeholder_match.group(1)
        before_comment = field[:comment_placeholder_match.start()].rstrip()
        # 检查注释占位符前面是否有逗号
        if before_comment.endswith(','):
            has_trailing_comma = True
            before_comment = before_comment[:-1].rstrip()
        field = before_comment
    else:
        # 检查行尾注释（可能在末尾，也可能紧贴别名）
        # 匹配 -- 后面的任何内容，不要求前面有空格
        line_comment_match = re.search(r'(?:\s*,?\s*)(--.*)$', field)
        if line_comment_match:
            line_comment = line_comment_match.group(1).strip()
            # 检查注释前面是否有逗号
            before_comment = field[:line_comment_match.start()]
            if before_comment.rstrip().endswith(','):
                has_trailing_comma = True
                before_comment = before_comment.rstrip()[:-1].rstrip()
            field = before_comment

    # 如果没有通过注释匹配找到逗号，检查字段是否以逗号结尾
    if not has_trailing_comma and field.rstrip().endswith(','):
        has_trailing_comma = True
        field = field.rstrip()[:-1].rstrip()

    if has_newlines:
        # 多行字段（如 CONCAT 函数），只处理末尾的注释添加
        # 不破坏内部结构，也不添加 AS（因为多行字段通常已经有 AS 或不需要 AS）
        if comment_placeholder:
            field += f'  {comment_placeholder}'
        elif line_comment:
            field += f'  {line_comment}'
        return field

    # 单行字段：添加 AS 关键字（如果需要）
    # SQL 关键字列表
    keywords = {'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'IS', 'NULL',
               'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'AS', 'JOIN', 'ON', 'LEFT', 'RIGHT',
               'INNER', 'OUTER', 'FULL', 'CROSS', 'NATURAL', 'VARCHAR', 'INT', 'DECIMAL',
               'STRING', 'DATE', 'TIMESTAMP', 'BOOLEAN', 'FLOAT', 'DOUBLE', 'BIGINT',
               'SMALLINT', 'TINYINT', 'CHAR', 'TEXT', 'COMMENT', 'LPAD', 'SUBSTRING',
               'ROW_NUMBER', 'OVER', 'PARTITION', 'ORDER', 'NVL', 'CONCAT', 'CAST',
               'DISTINCT', 'ALL', 'ANY', 'EXISTS'}

    # 分割单词
    parts = field.split()
    if not parts:
        # 空字段，只返回注释
        if comment_placeholder:
            return comment_placeholder
        elif line_comment:
            return line_comment
        return field

    # 分析最后一个单词是否是隐式别名
    if len(parts) >= 2:
        last_word = parts[-1]
        # 检查第一个单词是否是 DISTINCT
        is_distinct_field = (len(parts) >= 2 and parts[0].upper() == 'DISTINCT')

        # 检查最后一个单词是否可能是别名（字母和下划线组成，且不是关键字）
        # 排除注释占位符（__COMMENT_X__ 或 __COMMENT_STR_X__）
        is_comment_placeholder = re.match(r'^__COMMENT_(?:STR_)?\d+__$', last_word)

        # 修改：支持小写开头的别名
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', last_word) and last_word.upper() not in keywords and not is_comment_placeholder:
            # 检查倒数第二个单词是否不是运算符
            if len(parts) >= 2 and parts[-2] not in {',', '+', '-', '*', '/', '(', ')'}:
                # 检查倒数第二个单词是否已经是 AS 关键字
                if len(parts) >= 2 and parts[-2].upper() == 'AS':
                    # 已经有 AS，不需要添加
                    field_value = field
                # 如果是 DISTINCT 字段，不要添加 AS
                elif is_distinct_field:
                    # DISTINCT 后面的是字段名，不是别名
                    field_value = field
                else:
                    # 最后一个单词是隐式别名，需要添加 AS
                    value_parts = parts[:-1]
                    alias = last_word
                    # 重新组合字段值和别名
                    field_value = ' '.join(value_parts)
                    if alias:
                        field_value += f' AS {alias}'
            else:
                field_value = field
        else:
            field_value = field
    else:
        field_value = field

    # 添加注释
    if comment_placeholder:
        field_value += f'  {comment_placeholder}'
    elif line_comment:
        field_value += f'  {line_comment}'

    return field_value


def format_sql_v4_fixed(sql: str, **options) -> str:
    """
    Format SQL with:
    1. Inline comment preservation
    2. Proper nested CASE WHEN formatting
    3. Comma-first style (逗号前置)
    4. Multi-statement support (新增：多语句支持)
    5. Preprocessing: Normalize field aliases and comments (新增)
    """
    keyword_case = options.get('keyword_case', 'upper')

    # Step 1: Protect comments before parsing
    sql_protected, comment_map = _protect_comments(sql)

    # Step 1.5: Preprocess - Normalize field aliases and comments (新增)
    # 启用预处理，在 FROM 前添加换行，避免注释后直接跟 FROM 导致合并
    sql_normalized = _normalize_select_fields(sql_protected)

    # Step 2: Split by semicolon (respecting parentheses and strings)
    statements = _split_by_semicolon(sql_normalized)

    # Step 3: Format each statement with original V4 logic
    formatted_statements = []
    for stmt in statements:
        stmt = stmt.strip()
        if not stmt:
            continue

        # 使用原有的格式化逻辑
        formatted = _format_sql_structure(stmt, keyword_case)
        formatted_statements.append(formatted)

    # Step 4: Join with semicolons（分号独占一行）
    statements_with_semicolon = [f'{stmt}\n;' for stmt in formatted_statements]
    result = '\n\n'.join(statements_with_semicolon)

    # Step 5: Uppercase keywords if requested（在注释恢复之前执行，避免大写注释中的关键字）
    if keyword_case == 'upper':
        result = _uppercase_keywords(result)

    # Step 6: Restore comments from placeholders
    result = _restore_protected_comments(result, comment_map)

    # Step 6.5: 对齐独立注释行（与上一行代码对齐）
    result = _align_standalone_comments(result)

    # Step 7: Clean up empty lines within SQL statements (keep only one empty line between statements)
    result = _cleanup_empty_lines(result)

    return result


def _cleanup_empty_lines(sql: str) -> str:
    """清理SQL中的多余空行，增加美观性

    规则：
    1. 完全删除SQL语句内部的所有空行
    2. 只在语句之间（分号后）保留一个空行作为分隔
    3. 清除语句开头和结尾的空行
    """
    lines = sql.split('\n')

    # 首先删除所有空行
    non_empty_lines = [line for line in lines if line.strip() != '']

    # 然后在分号后添加空行作为语句分隔符
    result_lines = []
    for i, line in enumerate(non_empty_lines):
        result_lines.append(line)
        # 如果当前行以分号结尾，且不是最后一行，添加一个空行
        if line.rstrip().endswith(';') and i < len(non_empty_lines) - 1:
            result_lines.append('')

    return '\n'.join(result_lines)


def _align_standalone_comments(sql: str) -> str:
    """
    对齐独立注释行：将注释缩进与上一行代码对齐

    规则：
    1. 识别独立注释行（以 -- 开头，前面是换行符或行首）
    2. 查找上一行非空代码行的缩进
    3. 将注释行缩进调整为相同值

    适用场景：
    - CASE WHEN 中的独立注释
    - WHERE 子句中的独立注释
    - JOIN 子句中的独立注释
    - SELECT 字段列表中的独立注释
    """
    lines = sql.split('\n')
    result = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 检查是否是独立注释行（以 -- 开头）
        if stripped.startswith('--'):
            # 查找上一行非空代码行的缩进
            indent = 0
            for j in range(i - 1, -1, -1):
                if j >= 0:
                    prev_line = lines[j]
                    # 跳过空行和其他注释行
                    if prev_line.strip() and not prev_line.strip().startswith('--'):
                        indent = len(prev_line) - len(prev_line.lstrip())
                        break

            # 应用缩进
            result.append(' ' * indent + stripped)
        else:
            result.append(line)

    return '\n'.join(result)


def _split_by_semicolon(sql: str) -> List[str]:
    """按分号分割SQL，尊重括号和字符串"""
    statements = []
    current = ''
    depth = 0
    in_string = False
    string_char = None
    i = 0

    while i < len(sql):
        char = sql[i]

        # 处理字符串
        if char in ("'", '"') and (i == 0 or sql[i-1] != '\\'):
            if not in_string:
                in_string = True
                string_char = char
            elif char == string_char:
                in_string = False
            current += char
            i += 1
            continue

        if in_string:
            current += char
            i += 1
            continue

        # 处理括号
        if char == '(':
            depth += 1
            current += char
        elif char == ')':
            depth -= 1
            current += char
        elif char == ';' and depth == 0:
            if current.strip():
                statements.append(current.strip())
            current = ''
        else:
            current += char

        i += 1

    if current.strip():
        statements.append(current.strip())

    return statements


def _protect_comments(sql: str) -> tuple:
    """Replace comments with placeholders to protect them during parsing"""
    comment_map = {}
    protected = sql
    counter = [0]

    def replace_comment(match):
        placeholder = f"__COMMENT_{counter[0]}__"
        comment_map[placeholder] = match.group(0)
        counter[0] += 1
        return placeholder

    # Protect line comments
    protected = re.sub(r'--[^\n]*', replace_comment, protected)

    # Protect block comments
    protected = re.sub(r'/\*.*?\*/', replace_comment, protected, flags=re.DOTALL)

    return protected, comment_map


def _restore_protected_comments(sql: str, comment_map: dict) -> str:
    """Restore comments from placeholders, ensuring proper line breaks"""
    result = sql

    # 按照占位符在SQL中出现的顺序处理
    placeholder_positions = []
    for placeholder in comment_map.keys():
        pos = result.find(placeholder)
        if pos != -1:
            placeholder_positions.append((pos, placeholder))
    placeholder_positions.sort(key=lambda x: x[0])

    for _, placeholder in placeholder_positions:
        comment = comment_map[placeholder]
        # 不使用 strip()，保留注释内容中的空格（包括末尾空格）
        # 注释保护时 regex 是 --[^\n]*，不会包含 -- 前面的空格

        # 检查是否是行注释（以 -- 开头）
        if comment.startswith('--'):
            # 查找占位符的上下文
            pattern = re.escape(placeholder)
            match = re.search(pattern, result)
            if match:
                # 获取占位符前后的内容
                before = result[:match.start()]
                after_raw = result[match.end():]
                after = after_raw.lstrip()

                # 判断是否是独立行的注释
                # 检查占位符紧前面的字符是否是换行符或开头
                is_standalone_before = (match.start() == 0 or result[match.start() - 1] == '\n')
                # 检查后面是否紧跟着另一个注释占位符（可能有前导空格）
                follows_another_comment = bool(re.match(r'\s*__COMMENT_\d+__', after_raw))

                if is_standalone_before:
                    # 独立行注释
                    if follows_another_comment:
                        # 相邻注释：后面不添加换行（下一个注释会添加前导换行）
                        if match.start() == 0:
                            # 在字符串开头，不需要前导换行
                            result = result.replace(placeholder, comment, 1)
                        else:
                            # 在换行符后，需要前导换行
                            result = result.replace(placeholder, '\n' + comment, 1)
                    else:
                        # 最后一个注释：后面添加换行
                        if match.start() == 0:
                            # 在字符串开头，不需要前导换行
                            result = result.replace(placeholder, comment + '\n', 1)
                        else:
                            # 在换行符后，需要前导换行
                            result = result.replace(placeholder, '\n' + comment + '\n', 1)
                else:
                    # 行内注释（字段后的注释）：保持同一行
                    result = result.replace(placeholder, ' ' + comment, 1)
            else:
                result = result.replace(placeholder, ' ' + comment, 1)
        else:
            # 块注释 /* ... */
            pattern = re.escape(placeholder)
            match = re.search(pattern, result)
            if match:
                after = result[match.end():].lstrip()
                # 块注释后面如果有内容，需要换行
                if after and not after.startswith('\n'):
                    result = result.replace(placeholder, comment + '\n', 1)
                else:
                    result = result.replace(placeholder, comment, 1)
            else:
                result = result.replace(placeholder, comment, 1)

    # 清理多余的空行（超过2个连续换行变成2个）
    result = EMPTY_LINES_PATTERN.sub('\n\n', result)

    # 清理每行的尾随空格，但保留注释行中的空格
    lines = result.split('\n')
    cleaned_lines = []
    for line in lines:
        # 检查行中是否包含注释（-- 或 /* */
        has_line_comment = '--' in line
        has_block_comment = '/*' in line and '*/' in line
        if has_line_comment or has_block_comment:
            # 保留包含注释的行的原始格式（包括尾随空格）
            cleaned_lines.append(line)
        else:
            # 其他行去除尾随空格
            cleaned_lines.append(line.rstrip())
    result = '\n'.join(cleaned_lines)

    # 确保 FROM 前有换行（修复注释后 FROM 合并到同一行的问题）
    # 匹配：任意内容 + 注释或字段 + FROM
    # 替换为：确保 FROM 前有换行符
    # 这个正则会匹配没有换行分隔的情况，如 "d0117 --comment FROM"
    result = re.sub(
        r'([^\s\n][^\n]*?--.*?)\s+(FROM\b)',
        r'\1\n\2',
        result,
        flags=re.IGNORECASE
    )

    return result


def _protect_select_field_comments(sql: str) -> tuple:
    """在normalize之前预先提取SELECT字段列表

    问题：normalize操作会删除换行符，导致字段边界被破坏

    解决：在normalize之前预先提取字段列表并返回，normalize后使用
    返回：(处理后的SQL, 字段列表) 或 (原SQL, None)
    """
    # 找到 SELECT ... FROM 之间的内容
    select_match = re.search(r'\bSELECT\b(.+?)\bFROM\b', sql, re.IGNORECASE | re.DOTALL)
    if not select_match:
        return sql, None

    fields_section = select_match.group(1)

    # 检查是否包含注释占位符（只有包含注释才需要特殊处理）
    if '__COMMENT_' not in fields_section:
        return sql, None

    # 使用 _parse_select_fields 来提取字段（这个函数已经正确处理了字段分割）
    fields = _parse_select_fields(fields_section)

    return sql, fields


def _protect_from_newline(sql: str) -> str:
    """保护 FROM 前的换行，避免 normalize 后注释直接跟 FROM

    在 normalize 之前，将 FROM 前的换行替换为占位符
    normalize 后恢复为换行
    """
    # 匹配：任何内容 + 换行 + FROM
    # 替换为：任何内容 + 占位符 + FROM
    # 使用非贪婪匹配，避免匹配多个换行
    result = re.sub(r'(\S)\s*\n\s*\b(FROM)\b', r'\1 __FROM_NEWLINE__ \2', sql, flags=re.IGNORECASE)
    return result


def _restore_from_newline(sql: str) -> str:
    """恢复 FROM 前的换行"""
    # 将 __FROM_NEWLINE__ 替换为换行符
    return sql.replace('__FROM_NEWLINE__ ', '\n')


# ============================================================
# 以下是 V4 原有的格式化逻辑，扩展支持更多SQL语句类型
# ============================================================

def _format_sql_structure(sql: str, keyword_case: str = 'upper', indent_level: int = 0) -> str:
    """
    格式化 SQL 结构

    Args:
        sql: 原始 SQL
        keyword_case: 关键字大小写
        indent_level: 缩进层级（每级4个空格），用于子查询
    """
    """Format SQL structure without comments - V4 原有逻辑 + 支持更多语句类型"""

    # 如果是SELECT语句且有注释，预先提取字段信息
    # 这需要在任何其他处理之前进行
    extracted_fields = None
    if re.search(r'^\s*\bSELECT\b', sql, re.IGNORECASE) and '__COMMENT_' in sql:
        sql, extracted_fields = _protect_select_field_comments(sql)

    # 检测是否已经对齐（在保护 COMMENT 之前进行）
    # 对于已对齐的 SQL，避免破坏其格式
    is_aligned = False
    if 'CREATE TABLE' in sql.upper():
        # 提取列定义部分进行检测
        match = re.search(r'\((.*)\)', sql, re.DOTALL)
        if match:
            columns_content = match.group(1)
            # 简单检测：是否有多个连续空格（表示对齐）
            if '  ' in columns_content:
                is_aligned = True

    # 保护函数调用的多行结构（在 normalize 之前）
    sql, function_map = _protect_multiline_functions(sql)

    # 保护 IN 列表的多行结构（在 normalize 之前）
    sql, in_list_map = _protect_multiline_in_lists(sql)

    # 保护 COMMENT '...' 字符串中的空格（在 normalize 之前）
    comment_string_map = {}
    def protect_comment_strings(match):
        placeholder = f"__COMMENT_STR_{len(comment_string_map)}__"
        comment_string_map[placeholder] = match.group(0)
        return placeholder

    # 保护 COMMENT '...' 格式中的字符串
    sql = COMMENT_STRING_PATTERN.sub(protect_comment_strings, sql)

    # Normalize whitespace
    # 对于已对齐的 SQL，只做必要的清理（去除多余空行）
    # 对于未对齐的 SQL，执行完整的 normalize
    if is_aligned:
        # 已对齐：只清理每行首尾空格，保持内部空格
        lines = sql.split('\n')
        cleaned_lines = []
        for line in lines:
            # 保留行内的空格结构
            cleaned_lines.append(line.rstrip())
        sql = '\n'.join(cleaned_lines)
    else:
        # 未对齐：执行完整 normalize
        # 在 normalize 之前，保护 FROM 前的换行（避免注释后直接跟 FROM）
        if re.search(r'\bSELECT\b', sql, re.IGNORECASE):
            sql, extracted_fields = _protect_select_field_comments(sql)
            # 保护 FROM 前的换行
            sql = _protect_from_newline(sql)
        sql = ' '.join(sql.split())

    # 确保相邻的注释占位符之间有换行（normalize 可能会把换行变成空格）
    sql = COMMENT_ADJACENT_PATTERN.sub(r'\1\n\2', sql)

    # 恢复 FROM 前的换行（normalize 之前保护的）
    sql = _restore_from_newline(sql)

    # 检查语句类型（跳过注释占位符）
    sql_upper = sql.strip().upper()
    # 移除开头的注释占位符来检测类型
    sql_for_type = COMMENT_PREFIX_PATTERN.sub('', sql_upper).strip()

    # 先提取开头的注释占位符
    comment_prefix_match = COMMENT_PREFIX_PATTERN.match(sql)
    comment_prefix = comment_prefix_match.group(0) if comment_prefix_match else ''

    # 移除注释前缀后的SQL
    sql_without_comments = sql[len(comment_prefix):].strip() if comment_prefix else sql

    # 辅助函数：恢复 COMMENT 字符串、函数多行结构和 IN 列表多行结构
    def restore_comment_strings(text):
        result = text
        for placeholder, original in comment_string_map.items():
            result = result.replace(placeholder, original)
        # 恢复函数多行结构
        result = _restore_multiline_functions(result, function_map)
        # 恢复 IN 列表多行结构
        result = _restore_multiline_in_lists(result, in_list_map)
        return result

    # ============ DDL 语句 ============
    if sql_for_type.startswith('DROP DATABASE'):
        result = comment_prefix.strip() + '\n' + sql_without_comments if comment_prefix.strip() else sql_without_comments
        return restore_comment_strings(result)

    if sql_for_type.startswith('DROP'):
        formatted = _format_drop_statement(sql_without_comments)
        result = comment_prefix.strip() + '\n' + formatted if comment_prefix.strip() else formatted
        return restore_comment_strings(result)

    if sql_for_type.startswith('CREATE DATABASE'):
        result = comment_prefix.strip() + '\n' + sql_without_comments if comment_prefix.strip() else sql_without_comments
        return restore_comment_strings(result)

    if sql_for_type.startswith('CREATE TABLE'):
        if AS_SELECT_PATTERN.search(sql_for_type):
            formatted = _format_create_table_as(sql_without_comments)
            result = comment_prefix.strip() + '\n' + formatted if comment_prefix.strip() else formatted
            return restore_comment_strings(result)
        formatted = _format_create_table(sql_without_comments)
        result = comment_prefix.strip() + '\n' + formatted if comment_prefix.strip() else formatted
        return restore_comment_strings(result)

    if sql_for_type.startswith('CREATE VIEW') or sql_for_type.startswith('CREATE TEMPORARY VIEW'):
        formatted = _format_create_view(sql_without_comments)
        result = comment_prefix.strip() + '\n' + formatted if comment_prefix.strip() else formatted
        return restore_comment_strings(result)

    if sql_for_type.startswith('CREATE FUNCTION'):
        result = comment_prefix.strip() + '\n' + sql_without_comments if comment_prefix.strip() else sql_without_comments
        return restore_comment_strings(result)

    if sql_for_type.startswith('ALTER TABLE'):
        result = comment_prefix.strip() + '\n' + sql_without_comments if comment_prefix.strip() else sql_without_comments
        return restore_comment_strings(result)

    if sql_for_type.startswith('TRUNCATE TABLE') or sql_for_type.startswith('TRUNCATE'):
        result = comment_prefix.strip() + '\n' + sql_without_comments if comment_prefix.strip() else sql_without_comments
        return restore_comment_strings(result)

    if sql_for_type.startswith('ANALYZE TABLE'):
        result = comment_prefix.strip() + '\n' + sql_without_comments if comment_prefix.strip() else sql_without_comments
        return restore_comment_strings(result)

    # ============ DML 语句 ============
    if sql_for_type.startswith('INSERT') and 'PARTITION' in sql_for_type:
        # INSERT INTO ... PARTITION ... SELECT ...
        # 需要提取 INSERT 头部和 SELECT ... 部分
        match = INSERT_PARTITION_PATTERN.match(sql_without_comments)
        if match:
            insert_header = match.group(1)
            # 查找 SELECT 的开始位置
            select_start = sql_without_comments.upper().find('SELECT')
            if select_start >= 0:
                # 提取 SELECT ... 部分（从 SELECT 到语句结尾）
                select_part = sql_without_comments[select_start:]
                # 格式化 SELECT ... 部分
                select_formatted = _format_sql_structure(select_part, keyword_case)
                result = insert_header + '\n' + select_formatted
                # 添加注释前缀（如果有的话）
                result = comment_prefix.strip() + '\n' + result if comment_prefix.strip() else result
                return restore_comment_strings(result)

    elif sql_for_type.startswith('INSERT OVERWRITE') or sql_for_type.startswith('INSERT INTO'):
        if 'SELECT' in sql_for_type:
            formatted = _format_insert_select(sql_without_comments)
            result = comment_prefix.strip() + '\n' + formatted if comment_prefix.strip() else formatted
            return restore_comment_strings(result)
        formatted = _format_insert_statement(sql_without_comments)
        result = comment_prefix.strip() + '\n' + formatted if comment_prefix.strip() else formatted
        return restore_comment_strings(result)

    if sql_for_type.startswith('UPDATE'):
        formatted = _format_update_statement(sql_without_comments)
        result = comment_prefix.strip() + '\n' + formatted if comment_prefix.strip() else formatted
        return restore_comment_strings(result)

    if sql_for_type.startswith('DELETE'):
        formatted = _format_delete_statement(sql_without_comments)
        result = comment_prefix.strip() + '\n' + formatted if comment_prefix.strip() else formatted
        return restore_comment_strings(result)

    if sql_for_type.startswith('MERGE INTO'):
        formatted = _format_merge_statement(sql_without_comments)
        result = comment_prefix.strip() + '\n' + formatted if comment_prefix.strip() else formatted
        return restore_comment_strings(result)

    # ============ CTE (WITH ... AS) ============
    if sql_for_type.startswith('WITH'):
        formatted = _format_with_statement(sql_without_comments)
        result = comment_prefix.strip() + '\n' + formatted if comment_prefix.strip() else formatted
        return restore_comment_strings(result)

    # ============ 缓存相关 ============
    if sql_for_type.startswith('CACHE TABLE'):
        formatted = _format_cache_table(sql_without_comments)
        result = comment_prefix.strip() + '\n' + formatted if comment_prefix.strip() else formatted
        return restore_comment_strings(result)

    if sql_for_type.startswith('UNCACHE TABLE'):
        result = comment_prefix.strip() + '\n' + sql_without_comments if comment_prefix.strip() else sql_without_comments
        return restore_comment_strings(result)

    if sql_for_type.startswith('REFRESH'):
        result = comment_prefix.strip() + '\n' + sql_without_comments if comment_prefix.strip() else sql_without_comments
        return restore_comment_strings(result)

    # ============ 其他语句 ============
    if sql_for_type.startswith('EXPLAIN'):
        # EXPLAIN 后面通常跟SELECT等，需要格式化
        if 'SELECT' in sql_for_type:
            formatted = _format_explain(sql_without_comments)
            result = comment_prefix.strip() + '\n' + formatted if comment_prefix.strip() else formatted
            return restore_comment_strings(result)
        result = comment_prefix.strip() + '\n' + sql_without_comments if comment_prefix.strip() else sql_without_comments
        return restore_comment_strings(result)

    if sql_for_type.startswith('SHOW') or sql_for_type.startswith('DESCRIBE') or sql_for_type.startswith('DESC '):
        result = comment_prefix.strip() + '\n' + sql_without_comments if comment_prefix.strip() else sql_without_comments
        return restore_comment_strings(result)

    if sql_for_type.startswith('USE') or sql_for_type.startswith('SET'):
        result = comment_prefix.strip() + '\n' + sql_without_comments if comment_prefix.strip() else sql_without_comments
        return restore_comment_strings(result)

    # ============ SELECT 语句（默认）============
    # 先提取开头的注释占位符（与其他语句类型保持一致）
    comment_prefix_match = re.match(r'^(\s*(__COMMENT_\d+__\s*\n?\s*)+)', sql)
    comment_prefix = comment_prefix_match.group(0) if comment_prefix_match else ''

    # 移除注释前缀后的SQL（用于解析）
    sql_without_comments = sql[len(comment_prefix):].strip() if comment_prefix else sql

    # 检测是否包含 UNION
    if re.search(r'\bUNION\b', sql_without_comments, re.IGNORECASE):
        # 使用 UNION 格式化
        formatted = _format_union_statement(sql_without_comments, keyword_case)
        final_result = comment_prefix.strip() + '\n' + formatted if comment_prefix.strip() else formatted
        return restore_comment_strings(final_result)

    # Parse SQL clauses（使用没有注释前缀的SQL）
    parts = _parse_sql_parts(sql_without_comments, keyword_case, indent_level, extracted_fields)

    # Format each part
    lines = []

    # 计算基础缩进（用于子查询）
    base_indent = '    ' * indent_level

    # SELECT clause
    if parts['select']:
        select_lines = _format_select_clause(parts['select'])
        # 为子查询中的 SELECT 添加缩进
        if indent_level > 0:
            lines.append(base_indent + select_lines[0])
            for line in select_lines[1:]:
                lines.append(base_indent + line)
        else:
            lines.extend(select_lines)

    # FROM clause
    if parts['from']:
        if indent_level > 0:
            # 子查询：FROM 需要缩进
            from_line = f'{base_indent}FROM {parts["from"]}'
        else:
            # 主查询：FROM 不需要缩进（但内容可能包含换行的子查询）
            from_line = f'FROM {parts["from"]}'
        # 确保前面有换行（除了第一行 SELECT）
        if lines:
            from_line = '\n' + from_line
        lines.append(from_line)

    # JOIN clauses
    for join in parts['joins']:
        join_lines = _format_join_clause(join)
        # 为子查询中的 JOIN 添加缩进
        if indent_level > 0:
            for line in join_lines:
                lines.append(base_indent + line.lstrip())
        else:
            lines.extend(join_lines)

    # WHERE clause
    if parts['where']:
        where_lines = _format_where_clause(parts['where'])
        # 为子查询中的 WHERE 添加缩进
        if indent_level > 0:
            for line in where_lines:
                new_line = base_indent + line if not line.startswith(' ') else line
                lines.append(new_line)
        else:
            lines.extend(where_lines)

    # GROUP BY clause
    if parts['group_by']:
        group_by_line = f'    GROUP BY {parts["group_by"]}'
        if indent_level > 0:
            group_by_line = f'{base_indent}    GROUP BY {parts["group_by"]}'
        lines.append('\n' + group_by_line)

    # ORDER BY clause
    if parts['order_by']:
        order_by_line = f'    ORDER BY {parts["order_by"]}'
        if indent_level > 0:
            order_by_line = f'{base_indent}    ORDER BY {parts["order_by"]}'
        lines.append('\n' + order_by_line)

    # DISTRIBUTE BY clause
    if parts['distribute_by']:
        distribute_by_line = f'DISTRIBUTE BY {parts["distribute_by"]}'
        if indent_level > 0:
            distribute_by_line = f'{base_indent}DISTRIBUTE BY {parts["distribute_by"]}'
        lines.append('\n' + distribute_by_line)

    result = '\n'.join(lines)

    # 添加注释前缀（与其他语句类型保持一致）
    final_result = comment_prefix.strip() + '\n' + result if comment_prefix.strip() else result
    return restore_comment_strings(final_result)


# ============ 新增语句格式化函数 ============

def _format_create_view(sql: str) -> str:
    """格式化 CREATE VIEW 语句"""
    # CREATE VIEW xxx AS SELECT ...
    match = VIEW_PATTERN.match(sql)
    if not match:
        return sql

    view_header = match.group(1)
    select_part = match.group(2)

    select_formatted = _format_sql_structure(select_part)
    return f"{view_header} AS\n{select_formatted}"


def _format_update_statement(sql: str) -> str:
    """格式化 UPDATE 语句"""
    # UPDATE table SET col=val WHERE ...
    return sql


def _format_delete_statement(sql: str) -> str:
    """格式化 DELETE 语句"""
    # DELETE FROM table WHERE ...
    return sql


def _format_merge_statement(sql: str) -> str:
    """格式化 MERGE INTO 语句"""
    # MERGE INTO ... USING ... ON ... WHEN MATCHED THEN ...
    return sql


def _parse_cte_definitions(cte_part: str) -> list[tuple[str, str]]:
    """
    解析 CTE 定义部分

    Args:
        cte_part: "WITH" 之后，主查询之前的内容（如 "A AS (...), B AS (...)"）

    Returns:
        [(cte_name, subquery_sql), ...]
    """
    ctes = []
    rest = cte_part.strip()

    # 去掉开头的 "WITH"
    if rest.upper().startswith('WITH'):
        rest = rest[4:].strip()

    depth = 0
    current = ''
    i = 0

    while i < len(rest):
        char = rest[i]

        if char == '(':
            if depth == 0:
                # 找到 CTE 名称和 AS 之前的部分，保留 "cte_name AS " 格式
                current = current.strip()
                # 不需要修改 current，直接添加 (
                current += char
                depth += 1
            else:
                current += char
                depth += 1
        elif char == ')':
            current += char
            depth -= 1
            if depth == 0:
                # CTE 定义结束
                # 格式: "cte_name AS (subquery)"
                match = re.match(r'(\w+)\s+AS\s*\((.*)\)', current, re.IGNORECASE | re.DOTALL)
                if match:
                    cte_name = match.group(1)
                    subquery = match.group(2).strip()
                    ctes.append((cte_name, subquery))
                current = ''
        elif depth == 0 and char == ',':
            # 逗号分隔多个 CTE
            current = ''
        else:
            current += char

        i += 1

    # 处理最后一个
    if current.strip():
        match = re.match(r'(\w+)\s+AS\s*\((.*)\)', current, re.IGNORECASE | re.DOTALL)
        if match:
            cte_name = match.group(1)
            subquery = match.group(2).strip()
            ctes.append((cte_name, subquery))

    return ctes


def _format_with_statement(sql: str) -> str:
    """格式化 WITH ... AS ... SELECT 语句 (CTE)"""

    upper_sql = sql.upper()
    if not upper_sql.startswith('WITH'):
        return _format_sql_structure(sql)

    # 查找主 SELECT 的位置（不在括号内的）
    paren_count = 0
    main_select_pos = -1
    in_string = False
    string_char = None

    i = 0
    while i < len(sql):
        char = sql[i]

        # 处理字符串
        if char in ("'", '"') and (i == 0 or sql[i-1] != '\\'):
            if not in_string:
                in_string = True
                string_char = char
            elif char == string_char:
                in_string = False

        if not in_string:
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1

            # 查找 SELECT 关键字
            if sql[i:i+6].upper() == 'SELECT' and (i + 6 >= len(sql) or not sql[i+6].isalnum()):
                if paren_count == 0:
                    main_select_pos = i
                    break
        i += 1

    if main_select_pos == -1:
        # 没有找到主 SELECT，只有 CTE 定义
        return _format_cte_only(sql)

    # 分离 CTE 部分和主查询
    cte_part = sql[:main_select_pos].strip()
    main_query = sql[main_select_pos:].strip()

    # 解析 CTE 定义
    ctes = _parse_cte_definitions(cte_part)

    # 格式化每个 CTE
    formatted_ctes = []
    for idx, (cte_name, subquery) in enumerate(ctes):
        # 格式化子查询
        formatted_subquery = _format_sql_structure(subquery, keyword_case='upper', indent_level=0)

        # 计算缩进
        # 第一个 CTE: "WITH cte_name AS ("
        # 后续 CTE: ",\ncte_name AS ("
        if idx == 0:
            header = f"WITH {cte_name} AS ("
            paren_pos = len(header)
        else:
            # 需要考虑换行符
            header = f",\n{cte_name} AS ("
            # 缩进到 CTE 名称位置（2 个空格 + 名称长度 + " AS ("）
            paren_pos = 2 + len(cte_name) + 5

        # paren_pos 是 header 的长度，开括号在 paren_pos - 1 位置
        # SELECT 应该在开括号位置（paren_pos - 1）开始，不对齐到开括号后面
        # 闭括号应该对齐到开括号位置
        subquery_indent = ' ' * (paren_pos - 1)
        close_paren_indent = ' ' * (paren_pos - 1)

        # 为每一行添加缩进
        lines = []
        for line in formatted_subquery.split('\n'):
            if line.strip():
                lines.append(subquery_indent + line)
            else:
                lines.append('')

        formatted_cte = header + '\n' + '\n'.join(lines) + f'\n{close_paren_indent})'
        formatted_ctes.append(formatted_cte)

    # 格式化主查询
    main_formatted = _format_sql_structure(main_query)

    return '\n'.join(formatted_ctes) + '\n' + main_formatted


def _format_cte_only(sql: str) -> str:
    """格式化只有 CTE 定义的 WITH 语句（没有主查询）"""
    # WITH cte_name AS (subquery)

    # 去掉 WITH 和末尾的分号
    rest = sql[4:].strip()  # 去掉 'WITH'
    had_semicolon = False
    if rest.endswith(';'):
        rest = rest[:-1].strip()
        had_semicolon = True

    # 使用新的解析函数
    ctes = _parse_cte_definitions("WITH " + rest)

    # 格式化每个 CTE
    formatted_ctes = []
    for idx, (cte_name, subquery) in enumerate(ctes):
        # 格式化子查询
        formatted_subquery = _format_sql_structure(subquery, keyword_case='upper', indent_level=0)

        # 计算缩进
        if idx == 0:
            header = f"WITH {cte_name} AS ("
            paren_pos = len(header)
        else:
            header = f",\n{cte_name} AS ("
            paren_pos = 2 + len(cte_name) + 5

        # paren_pos 是 header 的长度，开括号在 paren_pos - 1 位置
        # SELECT 应该在开括号位置（paren_pos - 1）开始，不对齐到开括号后面
        # 闭括号应该对齐到开括号位置
        subquery_indent = ' ' * (paren_pos - 1)
        close_paren_indent = ' ' * (paren_pos - 1)

        # 为每一行添加缩进
        lines = []
        for line in formatted_subquery.split('\n'):
            if line.strip():
                lines.append(subquery_indent + line)
            else:
                lines.append('')

        formatted_cte = header + '\n' + '\n'.join(lines) + f'\n{close_paren_indent})'
        formatted_ctes.append(formatted_cte)

    result = '\n'.join(formatted_ctes)
    if had_semicolon:
        result += ';'

    return result


def _format_cache_table(sql: str) -> str:
    """格式化 CACHE TABLE 语句"""
    # CACHE TABLE table_name AS (subquery) 或 CACHE TABLE table_name AS subquery

    # 检查是否有括号
    paren_pos = sql.find(' AS ')
    if paren_pos == -1:
        return sql

    # 查找 AS 之后的开括号
    after_as = sql[paren_pos + 4:].strip()
    if not after_as.startswith('('):
        # 无括号格式：CACHE TABLE table_name AS SELECT ...
        # 尝试直接格式化
        if 'SELECT' in after_as.upper():
            select_match = re.match(r'(SELECT\s+.*)', after_as, re.IGNORECASE | re.DOTALL)
            if select_match:
                header = sql[:paren_pos + 4]  # "CACHE TABLE table_name AS "
                subquery = select_match.group(1)
                formatted_subquery = _format_sql_structure(subquery, keyword_case='upper', indent_level=0)
                return f"{header}\n{formatted_subquery}"
        return sql

    # 有括号格式：使用括号计数解析器
    try:
        subquery, end_pos = extract_balanced_paren_content(sql, paren_pos + 5)  # +4 for " AS ", +1 for "("
    except ValueError:
        return sql

    header = sql[:paren_pos + 5]  # "CACHE TABLE table_name AS ("
    table_name = sql[12:paren_pos].strip()  # 提取表名（在 "CACHE TABLE " 和 " AS " 之间）

    # 计算开括号位置（用于缩进）
    # 格式: "CACHE TABLE table_name AS ("
    paren_pos_in_header = len(header) - 1

    # 格式化子查询内容
    formatted_subquery = _format_sql_structure(subquery, keyword_case='upper', indent_level=0)

    # 为每一行添加缩进（缩进到开括号位置 + 1）
    subquery_indent = ' ' * (paren_pos_in_header + 1)
    lines = []
    for line in formatted_subquery.split('\n'):
        if line.strip():
            lines.append(subquery_indent + line)
        else:
            lines.append('')

    # 闭括号对齐到开括号位置
    close_paren_indent = ' ' * paren_pos_in_header

    return f"{header}\n" + '\n'.join(lines) + f"\n{close_paren_indent})"


def _format_explain(sql: str) -> str:
    """格式化 EXPLAIN 语句"""
    # EXPLAIN SELECT ...
    match = EXPLAIN_PATTERN.match(sql)
    if not match:
        return sql

    explain_header = match.group(1)
    select_part = match.group(2)

    select_formatted = _format_sql_structure(select_part)
    return f"{explain_header}\n{select_formatted}"


def _format_drop_statement(sql: str) -> str:
    """格式化 DROP 语句"""
    # DROP TABLE IF EXISTS table_name
    # 保持简单格式
    return sql


def _is_column_def_aligned(column_lines: List[str]) -> bool:
    """检测列定义是否已经对齐

    检查逻辑：
    1. 检查字段名后面是否有多个空格（表示对齐）
    2. 检查类型后面是否有多个空格（表示对齐）
    """
    if len(column_lines) < 2:
        return False

    # 统计有多少行有"对齐式"的空格
    aligned_count = 0
    total_count = 0

    for line in column_lines:
        original = line
        # 去掉开头逗号来分析
        if line.strip().startswith(','):
            line = line[1:].lstrip()
        else:
            line = line.lstrip()

        if not line:
            continue

        total_count += 1

        # 查找字段名后的空格数量
        i = 0
        while i < len(line) and not line[i].isspace():
            i += 1

        # 统计连续空格
        space_count = 0
        while i < len(line) and line[i].isspace():
            space_count += 1
            i += 1

        # 如果有多个空格（>=3），认为这行是对齐的
        if space_count >= 3:
            aligned_count += 1

    # 如果大部分行都有对齐式的空格，认为已对齐
    return total_count >= 2 and aligned_count >= total_count * 0.7


def _parse_column_parts(col_def: str) -> dict:
    """解析列定义的各个部分

    返回: {
        'name': 'JRJGDM',
        'type': 'STRING',
        'comment': '金融机构代码',
        'comment_placeholder': '__COMMENT_STR_0__',  # 如果是占位符
        'constraints': 'NOT NULL'  # 可选
    }
    """
    col_def = col_def.strip()
    if col_def.startswith(','):
        col_def = col_def[1:].strip()

    # 检查是否有 COMMENT 占位符
    comment_placeholder = None
    placeholder_match = COLUMN_COMMENT_PLACEHOLDER_PATTERN.search(col_def)
    if placeholder_match:
        comment_placeholder = placeholder_match.group(1)
        # 将占位符当作 COMMENT 处理
        comment = comment_placeholder
        # 移除占位符部分来分析字段名和类型
        col_def = col_def[:placeholder_match.start()].strip()
    else:
        # 提取真实的 COMMENT
        comment = None
        comment_match = COLUMN_COMMENT_PATTERN.search(col_def)
        if comment_match:
            comment = comment_match.group(1)
            # 移除 COMMENT 部分
            col_def = col_def[:comment_match.start()].strip()

    # 分割字段名和类型
    parts = col_def.split()
    if len(parts) < 2:
        return {
            'name': col_def if col_def else parts[0] if parts else '',
            'type': '',
            'comment': comment or '',
            'comment_placeholder': comment_placeholder
        }

    name = parts[0]
    # 类型可能包含空格（如 DECIMAL(10, 2)）
    type_part = ' '.join(parts[1:])
    # 移除可能的约束（NOT NULL, DEFAULT 等）
    type_match = re.match(r'^([A-Z]+\s*(\([^)]+\))?)', type_part, re.IGNORECASE)
    if type_match:
        col_type = type_match.group(1)
    else:
        col_type = parts[1]

    return {
        'name': name,
        'type': col_type,
        'comment': comment or '',
        'comment_placeholder': comment_placeholder
    }


def _align_columns_smartly(column_lines: List[str]) -> List[str]:
    """智能对齐列定义

    根据最长字段名和类型计算对齐位置，生成美观的格式
    对齐规则类似用户原始格式：
    - 字段名右对齐在位置 20
    - 类型右对齐在位置 40
    - COMMENT 左对齐在位置 60
    """
    if not column_lines:
        return column_lines

    # 解析所有列
    parsed_columns = []
    for line in column_lines:
        line = line.strip()
        if not line:
            continue
        parsed = _parse_column_parts(line)
        parsed_columns.append(parsed)

    if not parsed_columns:
        return column_lines

    # 计算最大宽度
    max_name_len = max(len(c['name']) for c in parsed_columns)
    max_type_len = max(len(c['type']) for c in parsed_columns)

    # 使用更精确的对齐位置（类似用户原始格式）
    # 字段名列：最小20字符，确保最长字段名右对齐
    name_width = max(max_name_len, 20)
    # 类型列：确保类型右对齐在40字符位置
    type_align_pos = 40  # COMMENT 的起始位置
    type_width = type_align_pos - name_width - 1  # 减1是因为前面的空格

    # 生成对齐的行
    result = []
    for i, col in enumerate(parsed_columns):
        # 逗号前置（除第一行外）
        if i > 0:
            prefix = ','
        else:
            prefix = ' '

        # 对齐字段名（左对齐，但在固定宽度内）
        name_part = col['name'].ljust(name_width)

        # 计算类型部分的起始位置
        line_start = f"{prefix}{name_part}"
        current_pos = len(line_start)

        # 类型需要右对齐到 type_align_pos 位置
        type_part = col['type'].rjust(type_align_pos - current_pos)

        line = line_start + type_part

        # 添加 COMMENT（如果有）
        if col.get('comment_placeholder'):
            # 使用占位符
            line += f"     {col['comment_placeholder']}"
        elif col.get('comment'):
            # 添加 COMMENT 和 5 个空格（类似用户原始格式）
            line += f"     COMMENT '{col['comment']}'"

        result.append(line)

    return result


def _format_create_table(sql: str) -> str:
    """格式化 CREATE TABLE 语句，智能对齐列定义和 PARTITIONED BY"""
    # 手动解析 SQL，正确处理嵌套括号
    # 匹配 CREATE TABLE ... 直到最后的分号或结束
    header_match = CREATE_TABLE_PATTERN.match(sql)
    if not header_match:
        return sql

    create_header = header_match.group(0)
    remaining_sql = sql[header_match.end():].strip()

    # 检查是否有 PARTITIONED BY 但没有列定义的情况
    # 如: CREATE TABLE test PARTITIONED BY (...)
    if remaining_sql.upper().startswith('PARTITIONED'):
        # 直接格式化 PARTITIONED BY 部分
        partition_formatted = _format_partitioned_by(remaining_sql)
        return create_header + '\n' + '\n'.join(partition_formatted)

    # 查找第一个括号（列定义的开始）
    if not remaining_sql.startswith('('):
        return sql

    # 手动提取列定义部分（考虑嵌套括号）
    depth = 0
    columns_end = -1

    for i, char in enumerate(remaining_sql):
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
            if depth == 0:
                columns_end = i
                break

    if columns_end == -1:
        return sql

    columns_str = remaining_sql[1:columns_end]  # 去掉外层括号
    table_options = remaining_sql[columns_end + 1:].strip()

    # 分割列定义，保留原始行
    column_lines = _split_column_definitions_preserve(columns_str)

    # 总是应用智能对齐，确保所有列（无论是否有 COMMENT）都对齐
    formatted_columns = _align_columns_smartly(column_lines)

    # 构建结果
    lines = [create_header]
    lines.append('(')

    for col in formatted_columns:
        lines.append(col)

    lines.append(')')

    # 处理 table_options (COMMENT, PARTITIONED BY, ROW FORMAT 等)
    if table_options:
        # 解析各个选项
        options = _parse_table_options(table_options)

        # COMMENT 单独一行
        if options.get('comment'):
            lines.append(options['comment'])

        # PARTITIONED BY 需要格式化
        if options.get('partitioned_by'):
            partition_formatted = _format_partitioned_by(options['partitioned_by'])
            lines.extend(partition_formatted)

        # 其他选项（ROW FORMAT, STORED AS 等）单独一行
        for opt in ['row_format', 'stored_as', 'location', 'serde_properties']:
            if options.get(opt):
                lines.append(options[opt])

    return '\n'.join(lines)


def _parse_table_options(options_str: str) -> dict:
    """解析表选项部分

    返回: {
        'comment': "COMMENT '...'" 或占位符 "__COMMENT_STR_X__",
        'partitioned_by': "PARTITIONED BY (...)",
        'row_format': "ROW FORMAT DELIMITED NULL DEFINED AS ''",
        ...
    }
    """
    options = {}
    remaining = options_str.strip()

    # 提取 COMMENT（支持原始格式和占位符格式）
    # 占位符格式: __COMMENT_STR_0__
    comment_match = TABLE_COMMENT_PATTERN.match(remaining)
    if comment_match:
        options['comment'] = comment_match.group(1)
        remaining = remaining[comment_match.end():].strip()

    # 提取 PARTITIONED BY（支持嵌套括号）
    # 需要手动解析以支持嵌套括号（如 DECIMAL(2000000000000,5)）
    partition_match = PARTITIONED_BY_PATTERN.match(remaining)
    if partition_match:
        partition_start = partition_match.end()
        # 查找括号开始
        if remaining[partition_start:].startswith('('):
            # 手动解析嵌套括号
            depth = 0
            partition_end = -1
            for i, char in enumerate(remaining[partition_start:]):
                if char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1
                    if depth == 0:
                        partition_end = partition_start + i
                        break
            if partition_end > 0:
                options['partitioned_by'] = remaining[:partition_end + 1]
                remaining = remaining[partition_end + 1:].strip()

    # 提取 ROW FORMAT (支持各种格式)
    # ROW FORMAT DELIMITED, ROW FORMAT SERDE, etc.
    row_format_match = ROW_FORMAT_PATTERN.match(remaining)
    if row_format_match:
        options['row_format'] = row_format_match.group(1).strip()
        remaining = remaining[row_format_match.end():].strip()

    # 其他选项
    if remaining:
        options['other'] = remaining

    return options


def _format_partitioned_by(partition_str: str) -> List[str]:
    """格式化 PARTITIONED BY 部分

    输入: "PARTITIONED BY (aaa STRING COMMENT 'a', bbb STRING COMMENT 'b')"
    输出: ["PARTITIONED BY", "(", " aaa         STRING                      COMMENT  'a'", ",bbb         STRING                      COMMENT  'b'", ")"]
    """
    # 提取 PARTITIONED BY 和括号内容
    match = PARTITIONED_BY_FULL_PATTERN.match(partition_str)
    if not match:
        return [partition_str]

    partition_header = match.group(1)
    columns_content = match.group(2)

    # 分割分区列
    partition_columns = []
    current = ''
    depth = 0

    for char in columns_content:
        if char == '(':
            depth += 1
            current += char
        elif char == ')':
            depth -= 1
            current += char
        elif char == ',' and depth == 0:
            partition_columns.append(current.strip())
            current = ''
        else:
            current += char

    if current.strip():
        partition_columns.append(current.strip())

    # 格式化分区列（逗号前置风格）
    result = [partition_header, '(']

    if partition_columns:
        # 总是应用智能对齐，确保所有列都对齐
        aligned = _align_columns_smartly(partition_columns)
        # 处理逗号前置风格
        for i, col in enumerate(aligned):
            if i == 0:
                # 第一个字段：去除前导空格，不添加逗号
                result.append(col.lstrip())
            else:
                # 后续字段：确保逗号在行首，格式为 ', field'
                if col.startswith(','):
                    # 已经有逗号，直接使用
                    result.append(col)
                else:
                    # 没有逗号，添加逗号
                    result.append(', ' + col)

    result.append(')')

    return result


def _split_column_definitions_preserve(columns_str: str) -> List[str]:
    """分割列定义，保留原始格式（包括空格）"""
    columns = []
    current = ''
    depth = 0

    for char in columns_str:
        if char == '(':
            depth += 1
            current += char
        elif char == ')':
            depth -= 1
            current += char
        elif char == ',' and depth == 0:
            columns.append(current.rstrip())  # 保留右侧空格前的内容
            current = ''
        else:
            current += char

    if current.strip():
        columns.append(current.rstrip())

    return columns


def _split_column_definitions(columns_str: str) -> List[str]:
    """分割列定义，尊重括号"""
    columns = []
    current = ''
    depth = 0

    for char in columns_str:
        if char == '(':
            depth += 1
            current += char
        elif char == ')':
            depth -= 1
            current += char
        elif char == ',' and depth == 0:
            columns.append(current.strip())
            current = ''
        else:
            current += char

    if current.strip():
        columns.append(current.strip())

    return columns


def _format_insert_statement(sql: str) -> str:
    """格式化普通 INSERT 语句"""
    # INSERT INTO TABLE xxx VALUES (...)
    return sql


def _format_create_table_as(sql: str) -> str:
    """格式化 CREATE TABLE AS SELECT 语句"""
    # 分离 CREATE TABLE 部分和 SELECT 部分
    match = CREATE_TABLE_AS_PATTERN.match(sql)
    if not match:
        return sql

    create_part = match.group(1).strip()  # 去除尾部空格/换行
    select_part = match.group(2)

    # 检查 create_part 是否已经包含 AS
    has_as = re.search(r'\s+AS\s*$', create_part, re.IGNORECASE)

    if has_as:
        # 已有 AS，去除 AS 后的空白
        create_part = re.sub(r'\s+AS\s*$', '', create_part, flags=re.IGNORECASE)

    # 格式化 SELECT 部分
    select_formatted = _format_sql_structure(select_part)

    # 返回结果（添加 AS）
    return f"{create_part} AS\n{select_formatted}"


def _format_insert_select(sql: str) -> str:
    """格式化 INSERT ... SELECT 语句"""
    # 分离 INSERT 部分和 SELECT 部分
    match = INSERT_TABLE_PATTERN.match(sql)
    if not match:
        return sql

    insert_part = match.group(1)
    select_part = match.group(2)

    # 格式化 SELECT 部分
    select_formatted = _format_sql_structure(select_part)

    return f"{insert_part}\n{select_formatted}"


def _parse_sql_parts(sql: str, keyword_case: str = 'upper', indent_level: int = 0, pre_extracted_fields: List[str] = None) -> Dict:
    """Parse SQL into its component parts - V4 原有逻辑"""
    parts = {
        'select': [],
        'from': '',
        'joins': [],
        'where': '',
        'group_by': '',
        'order_by': '',
        'distribute_by': ''
    }

    # First, identify and protect subqueries and window functions
    protected_sql = sql
    placeholders = {}

    # Protect OVER(...) window functions - handle nested parens
    i = 0
    while i < len(protected_sql):
        # Look for OVER keyword
        if protected_sql[i:i+4].upper() == 'OVER' and (i + 4 >= len(protected_sql) or not protected_sql[i+4].isalnum()):
            # Find the opening parenthesis
            j = i + 4
            while j < len(protected_sql) and protected_sql[j] in ' \t\n':
                j += 1
            if j < len(protected_sql) and protected_sql[j] == '(':
                # Find matching closing parenthesis
                paren_start = j
                paren_depth = 1
                k = j + 1
                while k < len(protected_sql) and paren_depth > 0:
                    if protected_sql[k] == '(':
                        paren_depth += 1
                    elif protected_sql[k] == ')':
                        paren_depth -= 1
                    k += 1
                # Extract OVER(...) and replace with placeholder
                over_content = protected_sql[i:k]
                placeholder = f"__OVER_{len(placeholders)}__"
                placeholders[placeholder] = over_content
                protected_sql = protected_sql[:i] + placeholder + protected_sql[k:]
                continue
        i += 1

    # Protect subqueries in parentheses that contain SELECT
    paren_depth = 0
    paren_start = -1
    i = 0
    while i < len(protected_sql):
        if protected_sql[i] == '(':
            if paren_depth == 0:
                paren_start = i
            paren_depth += 1
        elif protected_sql[i] == ')':
            paren_depth -= 1
            if paren_depth == 0 and paren_start >= 0:
                paren_content = protected_sql[paren_start:i+1]
                if re.search(r'\bSELECT\b', paren_content, re.IGNORECASE):
                    placeholder = f"__SUBQUERY_{len(placeholders)}__"
                    placeholders[placeholder] = paren_content
                    protected_sql = protected_sql[:paren_start] + placeholder + protected_sql[i+1:]
                    i = -1
                    paren_depth = 0
                    paren_start = -1
        i += 1

    # Now parse the protected SQL
    # Pattern to find clause boundaries at the TOP LEVEL only
    clause_pattern = r'\b(SELECT|FROM|LEFT\s+JOIN|RIGHT\s+JOIN|INNER\s+JOIN|CROSS\s+JOIN|JOIN|WHERE|GROUP\s+BY|ORDER\s+BY|DISTRIBUTE\s+BY|HAVING|LIMIT)\b'

    matches = list(re.finditer(clause_pattern, protected_sql, re.IGNORECASE))

    for i, match in enumerate(matches):
        clause_type = match.group(1).upper().replace(' ', '_')
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(protected_sql)
        # 获取原始内容
        raw_content = protected_sql[start:end]
        # 检查内容是否以换行开头（包含嵌套的缩进子查询）
        if raw_content.lstrip().startswith('\n'):
            # 包含嵌套的缩进子查询，保留完整内容
            clause_content = raw_content.rstrip(' ,')
        else:
            # 普通内容，strip 移除多余空格
            clause_content = raw_content.strip().rstrip(',')

        # Restore placeholders in content and format subqueries
        for placeholder, original in placeholders.items():
            if placeholder in clause_content:
                # 检查是否是子查询占位符
                if placeholder.startswith('__SUBQUERY_'):
                    # 递归格式化子查询（增加缩进层级）
                    # 去除外层括号
                    subquery_content = original[1:-1] if original.startswith('(') and original.endswith(')') else original
                    # 格式化子查询（不增加缩进层级，手动添加缩进）
                    formatted_subquery = _format_sql_structure(subquery_content, keyword_case, 0)
                    # 重新添加括号（如果需要）
                    if original.startswith('(') and original.endswith(')'):
                        # 检查子查询是否是简单的 SELECT...FROM...
                        # 如果是单行，保持括号在同一行；如果是多行，换行并添加缩进
                        if '\n' in formatted_subquery:
                            # 检测子查询前面的模式，确定缩进
                            placeholder_pos = clause_content.find(placeholder)
                            before_placeholder = clause_content[:placeholder_pos]

                            # 检测是否在 FROM 子句中
                            if clause_type == 'FROM' and placeholder_pos == 0:
                                # FROM 子句中的顶级子查询：缩进 6 个空格（与 FROM ( 中的 ( 对齐）
                                subquery_indent = '      '  # 6 个空格
                                close_paren_indent = '     '   # 5 个空格，与 FROM ( 中的 ( 对齐
                            else:
                                # 检测是否在 IN/NOT IN 中（嵌套子查询）
                                # before_placeholder 后面就是子查询占位符，相当于 ( 子查询
                                # 所以我们只需要检测 before_placeholder 是否以 IN/NOT IN/EXISTS 加空格结尾
                                in_pattern = re.search(r'\b(IN|NOT IN|EXISTS)\s*$', before_placeholder, re.IGNORECASE)
                                if in_pattern:
                                    # 嵌套子查询：SELECT 缩进到开括号位置 + 1
                                    # 计算开括号位置
                                    if clause_type == 'WHERE':
                                        # WHERE 子句的基础缩进是 6 个空格
                                        base_clause_indent = 6
                                        # "WHERE " 的长度是 6
                                        # before_placeholder 包含条件内容（如 "khzjdm NOT IN "）
                                        paren_pos = base_clause_indent + 6 + len(before_placeholder)
                                    elif clause_type in ('JOIN', 'LEFT_JOIN', 'RIGHT_JOIN', 'INNER_JOIN', 'FULL_JOIN', 'CROSS_JOIN'):
                                        # JOIN 子句的基础缩进是 0 个空格
                                        base_clause_indent = 0
                                        join_keyword = match.group(1).upper() if 'match' in dir() else 'JOIN'
                                        join_len = len(join_keyword) + 1  # +1 for space
                                        paren_pos = base_clause_indent + join_len + len(before_placeholder.strip())
                                    else:
                                        # 其他情况：使用标准缩进
                                        base_indent = '    ' * (indent_level + 1)
                                        subquery_indent = base_indent
                                        close_paren_indent = '    ' * indent_level
                                        # 跳过后续计算，直接使用标准缩进
                                        in_pattern = None

                                    if in_pattern:
                                        # SELECT 缩进到开括号位置 + 1
                                        subquery_indent = ' ' * (paren_pos + 1)
                                        # 闭括号缩进到开括号位置
                                        close_paren_indent = ' ' * paren_pos
                                        # 调试输出
                                        import sys
                                else:
                                    # 其他情况：使用标准缩进
                                    base_indent = '    ' * (indent_level + 1)
                                    subquery_indent = base_indent
                                    close_paren_indent = '    ' * indent_level

                            # 为子查询的每一行添加缩进
                            indented_lines = []
                            in_nested_subquery = False  # 标记是否在嵌套子查询中
                            for line in formatted_subquery.split('\n'):
                                if line.strip():  # 非空行添加缩进
                                    # 检查是否是嵌套子查询的开始（有多余的缩进）
                                    leading_spaces = len(line) - len(line.lstrip())
                                    # 如果缩进超过标准缩进（4个空格的倍数），说明是嵌套子查询
                                    if leading_spaces > 4 and leading_spaces % 4 != 0:
                                        # 嵌套子查询，保留原始缩进
                                        in_nested_subquery = True
                                        indented_lines.append(line)
                                    elif in_nested_subquery and leading_spaces > 0:
                                        # 仍在嵌套子查询中，保留原始缩进
                                        indented_lines.append(line)
                                        # 检查是否是嵌套子查询的结束（闭括号行）
                                        if ')' in line and '(' not in line:
                                            in_nested_subquery = False
                                    else:
                                        # 普通行，移除原始缩进，添加新计算的缩进
                                        indented_lines.append(subquery_indent + line.lstrip())
                                else:  # 空行保持空行
                                    indented_lines.append('')
                            indented_subquery = '\n'.join(indented_lines)

                            # 后处理：如果子查询内部有嵌套的子查询（在 IN/NOT IN 中），需要重新计算缩进
                            # 检测是否有 NOT IN ( ... ) 或 IN ( ... ) 模式，其中 ... 包含换行
                            has_nested = '\n(' in indented_subquery and re.search(r'\b(?:NOT IN|IN|EXISTS)\s*\(', indented_subquery, re.IGNORECASE)
                            if has_nested:
                                # 找到 NOT IN ( 的位置，并计算嵌套子查询应该缩进到的位置
                                lines = indented_subquery.split('\n')
                                result_lines = []
                                i = 0
                                while i < len(lines):
                                    line = lines[i]
                                    # 检测是否是 NOT IN ( 或 IN ( 或 EXISTS (
                                    match = re.search(r'(\s+(?:NOT IN|IN|EXISTS)\s+\()$', line.rstrip(), re.IGNORECASE)
                                    if match:
                                        # 找到了 IN ( 模式，下一行应该有嵌套的子查询
                                        # 计算括号位置（与 IN ( 中的 ( 对齐）
                                        paren_start_pos = len(line.rstrip()) - len(match.group(1)) + len(match.group(1))
                                        # 将子查询内容缩进到括号位置
                                        result_lines.append(line)
                                        i += 1
                                        # 处理子查询内容
                                        paren_depth = 1
                                        while i < len(lines) and paren_depth > 0:
                                            nested_line = lines[i]
                                            # 计算括号深度
                                            paren_depth += nested_line.count('(') - nested_line.count(')')
                                            # 如果不是闭括号行，添加缩进
                                            if i < len(lines) - 1 or paren_depth > 0:
                                                if nested_line.strip() == ')':
                                                    # 闭括号，对齐到开括号
                                                    result_lines.append(' ' * (paren_start_pos - 1) + nested_line.strip())
                                                elif nested_line.strip():
                                                    # 内容行，缩进到括号位置
                                                    result_lines.append(' ' * paren_start_pos + nested_line.strip())
                                                else:
                                                    result_lines.append('')
                                            i += 1
                                    else:
                                        result_lines.append(line)
                                        i += 1
                                else:
                                    result_lines.append(line)
                                    i += 1
                                indented_subquery = '\n'.join(result_lines)

                            clause_content = clause_content.replace(placeholder, '(\n' + indented_subquery + '\n' + close_paren_indent + ')')
                        else:
                            clause_content = clause_content.replace(placeholder, '(' + formatted_subquery + ')')
                    else:
                        clause_content = clause_content.replace(placeholder, formatted_subquery)
                else:
                    # OVER(...) 等其他占位符直接恢复
                    clause_content = clause_content.replace(placeholder, original)

        if clause_type == 'SELECT':
            parts['select'] = _parse_select_fields(clause_content, pre_extracted_fields)
        elif clause_type == 'FROM':
            parts['from'] = clause_content
        elif 'JOIN' in clause_type:
            parts['joins'].append({
                'type': match.group(1).upper(),
                'content': clause_content
            })
        elif clause_type == 'WHERE':
            parts['where'] = clause_content
        elif clause_type == 'GROUP_BY':
            parts['group_by'] = clause_content
        elif clause_type == 'ORDER_BY':
            parts['order_by'] = clause_content
        elif clause_type == 'DISTRIBUTE_BY':
            parts['distribute_by'] = clause_content

    return parts


def _parse_select_fields(fields_str: str, pre_extracted_fields: List[str] = None) -> List[str]:
    """Parse SELECT fields, handling nested parentheses and comments - V4 原有逻辑 + 注释保护"""
    # 如果有预先提取的字段列表，直接使用
    if pre_extracted_fields is not None:
        return pre_extracted_fields

    # 原有逻辑：没有预先提取时使用字符级别解析
    fields = []
    current_field = ''
    paren_depth = 0

    for char in fields_str:
        if char == '(':
            paren_depth += 1
            current_field += char
        elif char == ')':
            paren_depth -= 1
            current_field += char
        elif char == ',' and paren_depth == 0:
            # 分割字段
            fields.append(current_field.strip())
            current_field = ''
        else:
            current_field += char

    if current_field.strip():
        # 处理最后一个字段
        last_field = current_field.strip()
        
        # 检查是否包含 FROM 关键字（防止 FROM 被错误地包含在字段中）
        # 使用字符级别扫描，在括号深度为 0 时查找 FROM
        paren_depth_scan = 0
        in_string = False
        string_char = None
        i = 0
        from_pos = -1
        while i < len(last_field):
            ch = last_field[i]
            
            # 处理字符串（简化版，不检查转义）
            if ch in ("'", '"'):
                if not in_string:
                    in_string = True
                    string_char = ch
                elif ch == string_char:
                    in_string = False
                    string_char = None
            
            # 处理括号（只在非字符串状态下）
            if not in_string:
                if ch == '(':
                    paren_depth_scan += 1
                elif ch == ')':
                    paren_depth_scan -= 1
                elif paren_depth_scan == 0:
                    # 检查是否匹配 FROM 关键字
                    if i + 4 <= len(last_field) and last_field[i:i+4].upper() == 'FROM':
                        # 确保 FROM 前面是单词边界
                        if i == 0 or not last_field[i-1].isalnum():
                            # 确保 FROM 后面是空格或括号
                            if i + 4 >= len(last_field) or not last_field[i+4].isalnum():
                                from_pos = i
                                break
            i += 1
        
        if from_pos >= 0:
            # 截断 FROM 及之后的内容
            last_field = last_field[:from_pos].strip()
        
        fields.append(last_field)

    # 处理独立的注释占位符（如 , __COMMENT_X__），将其合并到前一个字段
    # 同时处理以注释占位符开头的字段（如 __COMMENT_X__\n field_content）
    result = []
    for i, field in enumerate(fields):
        field = field.strip()
        # 检查是否是独立的注释占位符
        if re.match(r'^__COMMENT_\d+__$', field):
            # 合并到前一个字段
            if result:
                result[-1] = result[-1] + '  ' + field
            else:
                # 如果是第一个字段，保留它
                result.append(field)
        # 检查是否以注释占位符开头，后面还有其他内容
        elif re.match(r'^__COMMENT_\d+__\s', field):
            # 提取注释占位符和剩余内容
            comment_match = re.match(r'^(__COMMENT_\d+__\s+)(.*)', field, re.DOTALL)
            if comment_match:
                comment_part = comment_match.group(1)
                remaining_part = comment_match.group(2)
                # 合并注释到前一个字段
                if result:
                    result[-1] = result[-1] + '  ' + comment_part.strip()
                else:
                    # 如果是第一个字段，保留它
                    result.append(comment_part.strip())
                # 将剩余内容作为新字段
                if remaining_part.strip():
                    result.append(remaining_part.strip())
        else:
            result.append(field)

    return result


def _format_select_clause(fields: List[str]) -> List[str]:
    """Format SELECT clause with comma-first style and smart alignment"""
    if not fields:
        return ['SELECT']

    # 首先格式化每个字段（处理 CASE 表达式等）
    formatted_fields = []
    for i, field in enumerate(fields):
        formatted_field = _format_field(field, is_first=(i == 0))
        formatted_fields.append(formatted_field)

    # 应用智能对齐
    aligned_fields = _align_select_fields_smartly(formatted_fields)

    # 生成最终输出
    lines = []
    for i, field in enumerate(aligned_fields):
        if i == 0:
            lines.append(f'SELECT {field}')
        else:
            # Comma-first style: align with SELECT
            lines.append(f'     , {field}')

    return lines


def _format_field(field: str, is_first: bool = False) -> str:
    """Format a single field, handling CASE expressions - V4 原有逻辑"""
    field = field.strip()

    # Check if field contains CASE expression
    if re.search(r'\bCASE\b', field, re.IGNORECASE):
        return _format_case_expression(field, base_indent=0 if not is_first else 4)

    return field


def _parse_select_field_parts(field: str) -> dict:
    """解析 SELECT 字段的各个部分

    返回: {
        'expression': 'field1 或 CONCAT(a,b) 或 CASE...END',
        'alias': 'alias1' 或 None,
        'comment': '__COMMENT_X__' 或 '-- comment' 或 None,
        'had_as': True/False,  # 原始字段是否已经有 AS 别名
        'original_expression': '原始字段（包含 AS）'  # 用于保留已有 AS 的字段
    }
    """
    field = field.strip()
    result = {'expression': field, 'alias': None, 'comment': None, 'had_as': False, 'original_expression': None}

    # 如果字段包含换行（如 CASE 表达式），不进行解析，保持原样
    if '\n' in field:
        result['expression'] = field
        return result

    # 首先检查是否有注释占位符或行尾注释
    # 注释占位符格式: __COMMENT_X__
    # 使用正向后顾确保不重复匹配
    comment_placeholder_match = re.search(r'(?<!\S)(__COMMENT_\d+__)\s*$', field)
    if comment_placeholder_match:
        result['comment'] = comment_placeholder_match.group(1)
        # 从注释占位符开始的位置截断，不包含前面的空格
        field = field[:comment_placeholder_match.start()].strip()
    else:
        # 检查是否有行尾注释 (-- comment)
        line_comment_match = re.search(r'(?<!\S)(--.*)\s*$', field)
        if line_comment_match:
            result['comment'] = line_comment_match.group(1).strip()
            field = field[:line_comment_match.start()].strip()

    # 检查是否有 AS 别名
    # AS 别名格式: AS alias 或直接 alias（在表达式后面）
    # 首先检测重复的AS（如: expr AS alias AS 或 expr AS alias AS alias2）
    # 模式: 表达式 AS 别名 AS [可能的其他内容]
    duplicate_as_pattern = re.compile(r'^(.+?)\s+AS\s+(\w+)\s+AS\s*$', re.IGNORECASE)
    duplicate_match = duplicate_as_pattern.search(field)
    if duplicate_match:
        # 发现重复AS，格式：expr AS alias AS
        # 这种情况下，alias 被重复了，只保留一个
        result['alias'] = duplicate_match.group(2)
        result['expression'] = duplicate_match.group(1)
        result['had_as'] = True
        # 保存包含 AS 的完整表达式（去除重复AS）
        result['original_expression'] = duplicate_match.group(1) + ' AS ' + duplicate_match.group(2)
    else:
        # 正常的AS检测
        as_pattern = re.compile(r'\s+AS\s+(\w+)(?:\s*)$', re.IGNORECASE)
        as_match = as_pattern.search(field)
        if as_match:
            result['alias'] = as_match.group(1)
            result['expression'] = field[:as_match.start()].strip()
            result['had_as'] = True  # 标记原始字段已有 AS
            # 保存包含 AS 的完整表达式
            result['original_expression'] = field  # 包含 AS 的完整表达式
        else:
            # 检查是否有无 AS 的别名（表达式后直接跟标识符）
            # 这种情况比较复杂，需要排除函数调用等情况
            # 首先检查第一个单词是否是 DISTINCT
            words = field.split()
            if len(words) > 1 and words[0].upper() == 'DISTINCT':
                # DISTINCT 后面的字段不是别名，直接返回
                result['expression'] = field
            elif len(words) > 1:
                last_word = words[-1]
                # 检查是否可能是别名（不包含特殊字符，不是关键字）
                if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', last_word):
                    # 确保不是函数或关键字
                    keywords = {'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'IS', 'NULL',
                               'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'AS', 'JOIN', 'ON', 'DISTINCT'}
                    if last_word.upper() not in keywords:
                        # 检查前面是否有逗号或运算符，如果有则不是别名
                        if len(words) >= 2 and words[-2] not in {',', '+', '-', '*', '/', '(', ')'}:
                            result['alias'] = last_word
                            result['expression'] = ' '.join(words[:-1])
            # 如果没有别名，确保 expression 是处理后的 field（已去除注释）
            if result['alias'] is None:
                result['expression'] = field

    return result


def _calculate_line_length_excluding_comments(expression: str) -> int:
    """计算表达式长度，排除注释部分

    支持 -- 行注释 和 /* 块注释 */

    Args:
        expression: 表达式字符串

    Returns:
        排除注释后的长度
    """
    # 移除行注释
    result = re.sub(r'--[^\n]*', '', expression)
    # 移除块注释
    result = re.sub(r'/\*.*?\*/', '', result, flags=re.DOTALL)
    # 移除多余空格
    result = ' '.join(result.split())
    return len(result)


def _format_function_call_intelligently(expression: str, max_line_length: int = 250, field_start_pos: int = 0) -> str:
    """智能格式化函数调用

    根据函数参数数量、长度和嵌套深度判断是否需要换行
    - 单参数或整行短：保持单行
    - 单个参数过长或整行过长：每个参数一行
    - 嵌套函数：递归格式化

    Args:
        expression: 函数调用表达式，如 "CONCAT('a', 'b', 'c')"
        max_line_length: 最大单行长度（默认250字符）
        field_start_pos: 函数在字段中的起始列位置，用于计算缩进

    Returns:
        格式化后的表达式
    """
    # 常见的 SQL 函数名
    COMMON_FUNCTIONS = {
        'CONCAT', 'LPAD', 'RPAD', 'SUBSTRING', 'SUBSTR', 'TRIM', 'UPPER', 'LOWER',
        'COALESCE', 'IFNULL', 'NULLIF', 'ISNULL', 'CAST', 'CONVERT',
        'DATE_FORMAT', 'DATE_ADD', 'DATE_SUB', 'DATEDIFF',
        'ROUND', 'CEIL', 'FLOOR', 'ABS', 'MOD', 'POWER', 'SQRT',
        'MAX', 'MIN', 'AVG', 'SUM', 'COUNT', 'STDDEV', 'VARIANCE',
        'ROW_NUMBER', 'RANK', 'DENSE_RANK', 'LEAD', 'LAG', 'FIRST_VALUE', 'LAST_VALUE',
        'REGEXP_REPLACE', 'REGEXP_EXTRACT', 'SPLIT', 'EXPLODE',
        'GET_JSON_OBJECT', 'FROM_JSON', 'TO_JSON',
        'HASH', 'MD5', 'SHA', 'SHA1', 'SHA2'
    }

    # 检测函数调用：IDENTIFIER(...)
    func_match = re.match(r'^([A-Z_][A-Z0-9_]*)\s*\((.*)\)\s*$', expression.strip(), re.IGNORECASE | re.DOTALL)

    if not func_match:
        # 不是函数调用，返回原表达式
        return expression

    func_name = func_match.group(1).upper()

    # 如果不是已知函数，可能不是函数调用（如列名），保持原样
    if func_name not in COMMON_FUNCTIONS:
        return expression

    params_str = func_match.group(2).strip()

    # 如果参数为空，返回原表达式
    if not params_str:
        return expression

    # 解析参数（考虑嵌套括号和字符串）
    params = _split_function_params(params_str)

    # 判断是否需要换行（新逻辑）
    # 1. 单个参数长度超过100字符
    # 2. 整行长度（排除注释）超过250字符
    needs_multiline = (
        any(len(p.strip()) > 100 for p in params) or  # 单个参数超过100字符
        _calculate_line_length_excluding_comments(expression) > max_line_length  # 整行超过限制
    )

    if not needs_multiline:
        # 保持单行，但递归处理嵌套函数
        formatted_params = []
        for param in params:
            formatted_param = _format_function_call_intelligently(param.strip(), max_line_length, field_start_pos)
            formatted_params.append(formatted_param)
        return f"{func_name}({', '.join(formatted_params)})"

    # 多行格式化：每个参数一行，统一缩进
    # 检查是否有嵌套函数（参数中包含换行）
    has_nested = any('\n' in _format_function_call_intelligently(p.strip(), max_line_length, field_start_pos) for p in params)

    # 计算缩进：参数缩进 = 字段起始位置 + 函数名长度 + 1（左括号） + 4（基础缩进）
    param_indent = field_start_pos + len(func_name) + 1 + 4

    result = [f"{func_name}("]
    for i, param in enumerate(params):
        param = param.strip()
        # 递归格式化参数（嵌套函数的起始位置累加）
        nested_start_pos = field_start_pos + len(func_name) + 1 + param_indent
        formatted_param = _format_function_call_intelligently(param, max_line_length, nested_start_pos)

        if '\n' in formatted_param:
            # 嵌套函数，保持其多行结构，统一缩进
            lines = formatted_param.split('\n')
            if i == 0:
                result.append(f"{' ' * param_indent}{lines[0]}")
            else:
                # 逗号前置，逗号缩进少一个空格，参数内容与第一个参数对齐
                result.append(f"{' ' * (param_indent - 1)}, {lines[0]}")
            for line in lines[1:]:
                result.append(f"{' ' * param_indent}{line}")
        else:
            # 单行参数
            if i == 0:
                result.append(f"{' ' * param_indent}{formatted_param}")
            else:
                # 逗号前置，逗号缩进少一个空格，参数内容与第一个参数对齐
                result.append(f"{' ' * (param_indent - 1)}, {formatted_param}")
    # 闭括号与函数名对齐
    result.append(f"{' ' * field_start_pos})")

    return '\n'.join(result)


def _split_function_params(params_str: str) -> List[str]:
    """分割函数参数，考虑嵌套括号和字符串

    Args:
        params_str: 参数字符串，如 "'a', 'b', CONCAT('c', 'd')"

    Returns:
        参数列表
    """
    params = []
    current_param = []
    depth = 0
    in_string = False
    string_char = None

    i = 0
    while i < len(params_str):
        char = params_str[i]

        # 处理字符串
        if not in_string and char in ('"', "'"):
            in_string = True
            string_char = char
            current_param.append(char)
        elif in_string and char == string_char:
            # 检查是否是转义
            if i > 0 and params_str[i-1] == '\\':
                current_param.append(char)
            else:
                in_string = False
                current_param.append(char)
        elif in_string:
            current_param.append(char)
        # 处理括号
        elif char == '(':
            depth += 1
            current_param.append(char)
        elif char == ')':
            depth -= 1
            current_param.append(char)
        # 处理逗号分隔符（仅在顶层）
        elif char == ',' and depth == 0 and not in_string:
            param = ''.join(current_param).strip()
            if param:
                params.append(param)
            current_param = []
        else:
            current_param.append(char)

        i += 1

    # 添加最后一个参数
    last_param = ''.join(current_param).strip()
    if last_param:
        params.append(last_param)

    return params


def _align_select_fields_smartly(fields: List[str]) -> List[str]:
    """智能对齐 SELECT 字段

    根据字段表达式的最大宽度，对齐 AS 别名和注释
    注意：多行字段（如 CASE 表达式）不参与对齐计算
    现在支持智能函数换行格式化
    """
    if not fields:
        return fields

    # 解析所有字段
    parsed_fields = []
    for field in fields:
        field = field.strip()
        if not field:
            continue
        parsed = _parse_select_field_parts(field)
        parsed_fields.append(parsed)

    if not parsed_fields:
        return fields

    # 分离单行字段和多行字段
    single_line_fields = []
    multi_line_fields = []

    for i, p in enumerate(parsed_fields):
        # 检查字段表达式是否包含换行
        if '\n' in p['expression']:
            multi_line_fields.append((i, p))
        else:
            single_line_fields.append((i, p))

    # 计算单行字段表达式的最大宽度
    max_expr_len = 0
    for _, p in single_line_fields:
        expr_len = len(p['expression'])
        if expr_len > max_expr_len:
            max_expr_len = expr_len

    # 对于多行字段（如 CASE WHEN），需要检查其"原始"表达式的长度
    # 在格式化之前，CASE WHEN 是单行的，所以我们需要从格式化后的多行中提取原始长度
    for i, p in multi_line_fields:
        # 检查是否是 CASE 表达式
        expr = p['expression']
        if expr.strip().startswith('CASE'):
            # CASE 表达式的最后一行是 "END AS alias"
            # 我们需要计算 CASE 到 END 的长度（不包括缩进）
            lines = expr.split('\n')
            if lines:
                first_line = lines[0].strip()  # "CASE"
                last_line = lines[-1].strip()  # "END AS alias" 或 "END"
                # CASE 表达式的"核心"长度 = CASE + WHEN...THEN...ELSE...END 的长度
                # 由于我们无法准确还原，这里使用一个近似值
                # 检查最后一行是否有 AS
                as_match = re.search(r'\bEND\s+AS\s+(\w+)', last_line, re.IGNORECASE)
                if as_match:
                    # 有 AS，CASE 表达式的长度是 CASE...END 的长度
                    # 粗略估计：第一行长度 + WHEN...THEN...ELSE...END 的长度
                    # 实际上，更准确的方法是使用原始 SQL 的长度
                    # 让我们使用整个多行表达式中最长的一行作为参考
                    # CASE WHEN 表达式不参与对齐计算，跳过
                    pass

    # 计算别名的最大宽度（用于对齐没有别名的字段）
    # 注意：需要同时考虑单行和多行字段的别名
    max_alias_len = 0
    for _, p in single_line_fields:
        if p['alias']:
            alias_len = len(p['alias'])
            if alias_len > max_alias_len:
                max_alias_len = alias_len
    for _, p in multi_line_fields:
        # 对于多行字段，需要从表达式中提取 AS 别名
        expr = p['expression']
        lines = expr.split('\n')
        if lines:
            last_line = lines[-1].strip()
            as_match = re.search(r'\bEND\s+AS\s+(\w+)(?:\s+(__COMMENT_\d+__)\s*)?$', last_line, re.IGNORECASE)
            if as_match:
                alias_len = len(as_match.group(1))
                if alias_len > max_alias_len:
                    max_alias_len = alias_len

    # 计算注释对齐的基准位置
    # 需要找出所有字段中"表达式 + AS + 别名"（或"表达式"）的最大长度
    # 注意：不包含 CASE WHEN 字段
    max_full_field_len = 0
    for _, p in single_line_fields:
        # 计算完整字段长度：表达式 + AS + 别名
        field_len = len(p['expression'])
        if p['alias']:
            field_len += 4 + len(p['alias'])  # " AS " + 别名
        if field_len > max_full_field_len:
            max_full_field_len = field_len
    # 跳过多行字段（CASE WHEN）在注释对齐中的计算
    # CASE WHEN 字段不参与注释对齐

    # 如果没有单行字段，直接返回原始字段
    if not single_line_fields:
        result = []
        for p in parsed_fields:
            if p.get('had_as', False) and p.get('original_expression'):
                # 原始字段已有 AS，使用完整表达式
                field_str = p['original_expression']
            else:
                field_str = p['expression']
            # 添加 AS（如果需要）
            if p['alias'] and not p.get('had_as', False):
                field_str += f" AS {p['alias']}"
            # 添加注释
            if p['comment']:
                field_str += f"  {p['comment']}"
            result.append(field_str)
        return result

    # 生成对齐的字段字符串
    result = [None] * len(parsed_fields)

    # 处理单行字段（应用对齐和智能函数格式化）
    for i, p in single_line_fields:
        # 如果原始字段已有 AS，使用包含 AS 的完整表达式
        if p.get('had_as', False) and p.get('original_expression'):
            field_str = p['original_expression']  # 包含 AS 的完整表达式
        else:
            field_str = p['expression']  # 只有表达式部分

        # 智能格式化函数调用（在提取 AS 别名之前）
        # 注意：field_str 可能包含 AS 别名，需要先分离
        expression_part = field_str
        alias_part = None

        # 检查是否有 AS 别名（在已有 AS 的情况下）
        if p.get('had_as', False):
            as_match = re.search(r'\s+AS\s+(\w+)$', field_str, re.IGNORECASE)
            if as_match:
                expression_part = field_str[:as_match.start()].strip()
                alias_part = as_match.group(1)

        # 应用智能函数格式化
        formatted_expr = _format_function_call_intelligently(expression_part)

        # 检查格式化后是否变成多行
        is_multiline = '\n' in formatted_expr

        if is_multiline:
            # 多行字段，不参与对齐
            field_str = formatted_expr
            # 添加 AS 别名（如果有）
            if alias_part:
                field_str += f" AS {alias_part}"
            elif p['alias'] and not p.get('had_as', False):
                field_str += f" AS {p['alias']}"
            # 添加注释（如果有）
            if p['comment']:
                field_str += f"  {p['comment']}"
            result[i] = field_str
            continue

        # 单行字段，应用对齐
        field_str = formatted_expr

        # 如果有 AS 别名，恢复它
        if alias_part:
            field_str += f" AS {alias_part}"

        # 添加 AS 别名（如果有）
        if p['alias'] and not p.get('had_as', False):
            # 新对齐逻辑：表达式对齐到 max_expr_len，然后 AS，然后别名
            field_str = field_str.ljust(max_expr_len)
            field_str += f" AS {p['alias']}"
        elif p.get('had_as', False):
            # 原始字段已有 AS，也应用新对齐逻辑
            # 需要重新分离表达式和别名
            as_match = re.search(r'\s+AS\s+(\w+)$', field_str, re.IGNORECASE)
            if as_match:
                expr_only = field_str[:as_match.start()].strip()
                alias_only = as_match.group(1)
                field_str = expr_only.ljust(max_expr_len)
                field_str += f" AS {alias_only}"
        else:
            # 没有 AS 别名：对齐到 max_expr_len + 4 + max_alias_len
            # 这样可以与有别名 + 最长别名的字段对齐
            align_pos = max_expr_len + 4 + max_alias_len
            field_str = field_str.ljust(align_pos)

        # 添加注释（对齐到 max_full_field_len + 2）
        if p['comment']:
            # 计算当前字段的完整长度
            current_len = len(field_str)
            # 注释对齐位置 = max_full_field_len + 2（两个空格）
            align_pos = max_full_field_len + 2
            if current_len < align_pos:
                field_str = field_str.ljust(align_pos)
            field_str += p['comment']  # 注释前不需要额外空格

        result[i] = field_str

    # 处理多行字段（CASE WHEN 不参与对齐，保持原样）
    for i, p in multi_line_fields:
        # 对于多行字段，检查是否是 CASE WHEN 表达式
        field_str = p['expression']

        # CASE WHEN 表达式保持原样，不参与对齐
        if field_str.strip().startswith('CASE'):
            # 已经被格式化好了，直接使用
            # 如果有独立的注释需要添加
            if p['comment'] and '__COMMENT_' not in field_str:
                lines = field_str.split('\n')
                # 将注释添加到最后一行
                lines[-1] += f"  {p['comment']}"
                field_str = '\n'.join(lines)
        else:
            # 其他多行字段，保持原样
            if p['comment']:
                lines = field_str.split('\n')
                lines[-1] += f"  {p['comment']}"
                field_str = '\n'.join(lines)

        result[i] = field_str

    return result


def _format_case_expression(case_sql: str, base_indent: int = 0) -> str:
    """Format CASE expression with proper indentation for nested CASEs - V4 原有逻辑"""

    # Extract alias if present (handle comment placeholders too)
    alias_match = re.search(r'\s+AS\s+(\w+)(?:\s*(__COMMENT_\d+__)\s*)?$', case_sql, re.IGNORECASE)
    alias = alias_match.group(1) if alias_match else None
    alias_comment = ''
    trailing_comment = ''

    if alias_match:
        alias_comment = alias_match.group(2) or ''
        case_sql = case_sql[:alias_match.start()].strip()
    else:
        # 检查 END 后面是否有注释（没有别名的情况）
        # 例如: END --个人年收入 或 END--个人年收入
        end_comment_match = re.search(r'\bEND\s*(__COMMENT_\d+__)\s*$', case_sql, re.IGNORECASE)
        if end_comment_match:
            trailing_comment = ' ' + end_comment_match.group(1)
            # 只移除注释占位符，保留END
            case_sql = case_sql[:end_comment_match.start()].strip() + ' END'
            # 标记已经处理过END，避免重复添加
            case_sql = case_sql + '__END_HANDLED__'

    # Remove outer parentheses if they wrap the entire CASE expression
    if case_sql.startswith('(') and case_sql.endswith(')'):
        inner = case_sql[1:-1].strip()
        if re.search(r'^CASE\b', inner, re.IGNORECASE):
            case_sql = inner

    # Format the CASE expression
    formatted = _format_case_recursive(case_sql.replace('__END_HANDLED__', ''), base_indent=base_indent)

    if alias:
        if base_indent == 0:
            formatted = formatted.rstrip() + f' AS {alias}'
            if alias_comment:
                formatted += f' {alias_comment}'
        else:
            formatted += f'\n    AS {alias}'
            if alias_comment:
                formatted += f' {alias_comment}'
    elif trailing_comment:
        # 没有别名，只有注释
        formatted = formatted.rstrip() + trailing_comment

    return formatted


def _unwrap_parentheses(s: str) -> tuple:
    """递归去除外层括号，直到遇到 CASE 关键字或没有括号

    Args:
        s: 输入字符串

    Returns:
        (unwrapped_string, paren_count) - 去除括号后的字符串和去除的括号层数
    """
    original = s
    paren_count = 0

    while True:
        s = s.strip()

        # 临时移除末尾的注释占位符，以便检查括号
        s_no_comments = re.sub(r'\s*__COMMENT_\d+__\s*$', '', s).strip()

        # 检查是否被括号包裹（需要正确匹配括号）
        if s.startswith('(') and (s.endswith(')') or s_no_comments.endswith(')')):
            # 检查括号是否正确匹配（最外层的左右括号）
            depth = 0
            matched = False
            # 使用原始字符串 s 进行括号匹配
            for i, char in enumerate(s):
                if char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1
                    # 检查是否到达最后一个有意义的字符（忽略注释占位符）
                    if depth == 0:
                        # 检查从 i 位置往后是否只有注释占位符和空格
                        remaining = s[i+1:].strip()
                        is_meaningful_end = remaining == '' or re.match(r'^__COMMENT_\d+__$', remaining)
                        if is_meaningful_end:
                            # 找到匹配的最外层括号
                            s = s[1:i].strip()
                            paren_count += 1
                            matched = True
                            break
                        else:
                            # 括号不匹配，停止
                            break

            if not matched:
                break

            # 检查是否包含 CASE（用于决定是否继续去除）
            contains_case = re.search(r'\bCASE\b', s, re.IGNORECASE)

            # 如果去除括号后以 CASE 开头，停止去除（已找到 CASE）
            if re.search(r'^CASE\b', s, re.IGNORECASE):
                break

            # 如果包含 CASE 但不以 CASE 开头（说明还有括号），继续去除
            if contains_case and s.startswith('('):
                continue

            # 如果去除括号后包含 CASE，停止
            if contains_case:
                break

            # 不包含 CASE，继续去除括号（处理普通表达式）
        else:
            # 没有外层括号
            break

    return s, paren_count


def _format_case_recursive(case_sql: str, base_indent: int = 0, compact_mode: bool = False, paren_indent: int = None) -> str:
    """Recursively format CASE expressions including nested ones

    Args:
        case_sql: CASE 表达式字符串
        base_indent: 基础缩进（空格数）
        compact_mode: 紧凑模式 - WHEN 和 THEN 在同一行（用于嵌套 CASE）
        paren_indent: 括号对齐位置（用于嵌套 CASE 的括号对齐）
    """
    indent = ' ' * base_indent

    if paren_indent is not None:
        # 括号包裹的嵌套 CASE：使用括号对齐
        # CASE/END 与括号后 1 个空格对齐（paren_indent + 1）
        # WHEN 再缩进 5 空格
        inner_indent = ' ' * (paren_indent + 1 + 5)
        end_indent = ' ' * (paren_indent + 1)  # END 与 CASE 对齐
    elif base_indent == 0:
        inner_indent = ' ' * 11
        end_indent = ' ' * 7
    else:
        inner_indent = ' ' * (base_indent + 4)
        end_indent = indent

    case_sql = case_sql.strip()

    if not case_sql.upper().startswith('CASE'):
        return case_sql

    # Find the matching END for this CASE
    depth = 0
    end_pos = -1
    content_start = 4

    for i in range(len(case_sql)):
        if case_sql[i:i+4].upper() == 'CASE' and (i == 0 or not case_sql[i-1].isalnum()):
            depth += 1
        elif case_sql[i:i+3].upper() == 'END' and (i+3 >= len(case_sql) or not case_sql[i+3].isalnum()):
            depth -= 1
            if depth == 0:
                end_pos = i
                break

    if end_pos == -1:
        case_match = re.match(r'CASE\s+(.+?)\s+END$', case_sql, re.IGNORECASE | re.DOTALL)
        if not case_match:
            return case_sql
        inner_content = case_match.group(1)
    else:
        inner_content = case_sql[content_start:end_pos].strip()

    parts = _parse_case_parts(inner_content)

    # CASE 的缩进：当有括号对齐时，CASE 比括号多 1 个空格
    if paren_indent is not None:
        case_indent = ' ' * (paren_indent + 1)
    else:
        case_indent = indent

    lines = [f'{case_indent}CASE']

    for when_cond, then_val in parts['whens']:
        when_stripped = when_cond.strip()
        then_stripped = then_val.strip()

        # 检查是否包含嵌套 CASE
        has_nested_case = re.search(r'\bCASE\b', then_stripped, re.IGNORECASE)
        has_paren_wrapper = False
        inner_then = then_stripped

        # 使用新的括号去除函数，递归去除所有外层括号
        inner_then, paren_count = _unwrap_parentheses(then_stripped)
        if paren_count > 0 and re.search(r'^CASE\b', inner_then, re.IGNORECASE):
            has_paren_wrapper = True
            has_nested_case = True

        if has_nested_case:
            # 嵌套 CASE - 使用紧凑模式递归格式化
            nested_content = inner_then if has_paren_wrapper else then_stripped

            # 计算括号位置（用于对齐）
            if has_paren_wrapper:
                # THEN ( 应该与 WHEN 对齐（使用相同的缩进）
                then_line_indent = len(inner_indent)
                # paren_indent 是 THEN ( 中 ( 的位置，用于内层 CASE 的缩进对齐
                # 紧凑模式: THEN ( 行的格式: [then_line_indent]WHEN [when] THEN (
                # ( 的位置 = then_line_indent + len("WHEN ") + len(when_stripped) + len(" THEN (")
                paren_indent_compact = then_line_indent + len("WHEN ") + len(when_stripped) + len(" THEN (")
                # 非紧凑模式: THEN ( 行的格式: [then_line_indent]THEN (
                # ( 的位置 = then_line_indent + len("THEN (")
                paren_indent_normal = then_line_indent + len("THEN (")
                # paren_pos 是 ( 在 THEN ( 行中的位置（不再使用，保留用于兼容）
                paren_pos = then_line_indent + len('THEN (') - 1
            else:
                # 没有括号包裹的嵌套 CASE
                # 仍然需要计算 paren_indent，让内层 CASE 正确缩进
                # 假设格式是: [inner_indent]THEN CASE
                # 内层 CASE 应该缩进到 THEN 后 6 个字符的位置（与 "THEN (" 的括号位置一致）
                then_line_indent = len(inner_indent)
                paren_indent_compact = then_line_indent + len("THEN (")
                paren_indent_normal = then_line_indent + len("THEN (")
                paren_pos = None

            # 检查 WHEN 条件是否需要格式化（包含 OR/AND）
            when_needs_format = _needs_when_condition_formatting(when_stripped)

            if compact_mode and not when_needs_format:
                # 紧凑模式：WHEN 条件简单时，THEN [content] 在同一行
                # 使用紧凑模式的括号位置
                nested_formatted = _format_case_recursive(nested_content, base_indent=0, compact_mode=True, paren_indent=paren_indent_compact)
                if has_paren_wrapper:
                    lines.append(f'{" " * then_line_indent}WHEN {when_stripped} THEN (')
                else:
                    # 原始 SQL 没有括号，保持原样：WHEN ... THEN CASE
                    lines.append(f'{inner_indent}WHEN {when_stripped} THEN')
                for nested_line in nested_formatted.split('\n'):
                    lines.append(nested_line)
                if has_paren_wrapper:
                    # ) 应该与 ( 在 THEN ( 中的位置对齐
                    # THEN ( 行的格式: [then_line_indent spaces]WHEN [when] THEN (
                    # ( 的位置 = then_line_indent + len("WHEN ") + len(when_stripped) + len(" THEN (")
                    close_paren_pos = then_line_indent + len("WHEN ") + len(when_stripped) + len(" THEN (")
                    lines.append(f'{" " * close_paren_pos})')
                # else: 没有括号，不需要闭合括号
            elif when_needs_format:
                # WHEN 条件需要格式化（多行）
                # 使用非紧凑模式的括号位置
                nested_formatted = _format_case_recursive(nested_content, base_indent=0, compact_mode=True, paren_indent=paren_indent_normal)
                when_formatted = _format_when_condition(when_stripped, inner_indent)
                lines.append(f'{inner_indent}WHEN {when_formatted}')
                if has_paren_wrapper:
                    lines.append(f'{" " * then_line_indent}THEN (')
                else:
                    # 原始 SQL 没有括号，保持原样：THEN CASE
                    lines.append(f'{" " * then_line_indent}THEN')
                for nested_line in nested_formatted.split('\n'):
                    lines.append(nested_line)
                if has_paren_wrapper:
                    # ) 应该与 ( 在 THEN ( 中的位置对齐
                    # THEN ( 行的格式: [then_line_indent spaces]THEN (
                    # ( 的位置 = then_line_indent + len("THEN (")
                    close_paren_pos = then_line_indent + len("THEN (")
                    lines.append(f'{" " * close_paren_pos})')
                # else: 没有括号，不需要闭合括号
            else:
                # 非紧凑模式：WHEN、THEN 分行
                # 使用非紧凑模式的括号位置
                nested_formatted = _format_case_recursive(nested_content, base_indent=0, compact_mode=True, paren_indent=paren_indent_normal)
                when_formatted = _format_when_condition(when_stripped, inner_indent)
                lines.append(f'{inner_indent}WHEN {when_formatted}')
                if has_paren_wrapper:
                    lines.append(f'{" " * then_line_indent}THEN (')
                else:
                    # 原始 SQL 没有括号，保持原样：THEN CASE
                    lines.append(f'{" " * then_line_indent}THEN')
                for nested_line in nested_formatted.split('\n'):
                    lines.append(nested_line)
                if has_paren_wrapper:
                    # ) 应该与 ( 在 THEN ( 中的位置对齐
                    # THEN ( 行的格式: [then_line_indent spaces]THEN (
                    # ( 的位置 = then_line_indent + len("THEN (")
                    close_paren_pos = then_line_indent + len("THEN (")
                    lines.append(f'{" " * close_paren_pos})')
                # else: 没有括号，不需要闭合括号
        else:
            # 非 CASE 值
            if compact_mode:
                # 紧凑模式：WHEN condition THEN value 在同一行
                lines.append(f'{inner_indent}WHEN {when_stripped} THEN {then_stripped}')
            else:
                # 标准模式
                when_formatted = _format_when_condition(when_stripped, inner_indent)
                lines.append(f'{inner_indent}WHEN {when_formatted}')
                lines.append(f'{inner_indent}THEN {then_stripped}')

    if parts['else']:
        else_val = parts['else'].strip()
        has_nested_case = re.search(r'\bCASE\b', else_val, re.IGNORECASE)
        has_paren_wrapper = False
        inner_else = else_val

        # 使用新的括号去除函数，递归去除所有外层括号
        inner_else, paren_count = _unwrap_parentheses(else_val)
        if paren_count > 0 and re.search(r'^CASE\b', inner_else, re.IGNORECASE):
            has_paren_wrapper = True
            has_nested_case = True

        if has_nested_case:
            # ELSE 分支的嵌套 CASE
            nested_content = inner_else if has_paren_wrapper else else_val

            # 计算括号位置（用于对齐）
            if has_paren_wrapper:
                # ELSE ( 应该与 WHEN 的 THEN ( 对齐
                # 所以使用与 THEN ( 相同的缩进
                else_line_indent = len(inner_indent)
                # paren_indent 是 ELSE ( 中 ( 的位置，用于内层 CASE 的缩进对齐
                # ELSE ( 行的格式: [else_line_indent spaces]ELSE (
                # ( 的位置 = else_line_indent + len("ELSE") + 1 (空格) = else_line_indent + 5
                paren_indent = else_line_indent + len("ELSE") + 1
                # paren_pos 是 ( 在 ELSE ( 行中的位置（不再使用，保留用于兼容）
                paren_pos = else_line_indent + len('ELSE (') - 1
            else:
                # 没有括号包裹的嵌套 CASE
                # 仍然需要计算 paren_indent，让内层 CASE 正确缩进
                # 假设格式是: [inner_indent]ELSE CASE
                # 内层 CASE 应该缩进到 ELSE 后 6 个字符的位置（与 "ELSE (" 的括号位置一致）
                else_line_indent = len(inner_indent)
                paren_indent = else_line_indent + len("ELSE") + 1
                paren_pos = None

            nested_formatted = _format_case_recursive(nested_content, base_indent=0, compact_mode=True, paren_indent=paren_indent)

            if has_paren_wrapper:
                lines.append(f'{" " * else_line_indent}ELSE (')
                for nested_line in nested_formatted.split('\n'):
                    lines.append(nested_line)
                # ) 应该与 ELSE ( 中的 ( 对齐
                # ELSE ( 行的格式: [else_line_indent spaces]ELSE (
                # ( 的位置 = else_line_indent + len("ELSE (") - 1
                lines.append(f'{" " * (else_line_indent + len("ELSE (") - 1)})')
            else:
                lines.append(f'{inner_indent}ELSE')
                for nested_line in nested_formatted.split('\n'):
                    lines.append(nested_line)
        else:
            # ELSE 分支的非 CASE 值
            lines.append(f'{inner_indent}ELSE {else_val}')

    lines.append(f'{end_indent}END')

    return '\n'.join(lines)


def _needs_when_condition_formatting(condition: str) -> bool:
    """检查 WHEN 条件是否需要格式化（包含多个 OR/AND 需要换行）"""
    # 移除注释占位符和字符串内容
    temp = re.sub(r'__COMMENT_\d+__', '', condition)
    temp = re.sub(r"'[^']*'", "''", temp)  # 替换字符串为空串

    # 检查是否包含需要换行的 OR/AND
    # 1. 检查括号内的 OR/AND
    paren_or_pattern = r'\([^)]*\bOR\b[^)]*\)'
    paren_and_pattern = r'\([^)]*\bAND\b[^)]*\)'
    if re.search(paren_or_pattern, temp, re.IGNORECASE):
        return True
    if re.search(paren_and_pattern, temp, re.IGNORECASE):
        # 需要至少 2 个 AND 才需要换行
        and_count = len(re.findall(r'\bAND\b', temp, re.IGNORECASE))
        if and_count >= 2:
            return True

    # 2. 检查顶层多个 OR/AND（不在括号内的）
    or_parts = _split_by_logical_op(condition, 'OR')
    if len(or_parts) > 1:
        return True
    and_parts = _split_by_logical_op(condition, 'AND')
    if len(and_parts) > 1:
        return True

    return False


def _format_when_condition(condition: str, base_indent: str) -> str:
    """Format WHEN condition, splitting OR/AND if there are multiple

    支持括号内的连续 OR/AND 条件换行：
    - (a=1 OR b=2 OR c=3) 会被格式化为多行
    - 即使括号嵌套也能处理
    """
    # 首先检查并处理括号内的连续 OR/AND
    # base_indent 是字符串，需要转换为整数（空格数）
    base_indent_int = len(base_indent)
    processed = _split_parenthesized_conditions(condition, base_indent_int)

    # 如果处理后没有变化，或处理结果不完整（不包含原始条件的开头），返回原条件使用正常处理
    if processed == condition or not processed.strip().startswith(condition.strip()[:20]):
        # 进行正常的 OR/AND 分割（不处理括号内）
        or_parts = _split_by_logical_op(condition, 'OR')  # 使用原始 condition

        if len(or_parts) <= 1:
            and_parts = _split_by_logical_op(condition, 'AND')  # 使用原始 condition
            if len(and_parts) <= 1:
                return condition

            lines = [and_parts[0].strip()]
            or_indent = ' ' * (len(base_indent) + 8)
            for part in and_parts[1:]:
                lines.append(f'{or_indent}AND {part.strip()}')
            return '\n'.join(lines)

        lines = [or_parts[0].strip()]
        or_indent = ' ' * (len(base_indent) + 8)
        for part in or_parts[1:]:
            and_parts = _split_by_logical_op(part.strip(), 'AND')
            if len(and_parts) > 1:
                and_lines = [and_parts[0].strip()]
                and_indent = ' ' * (len(base_indent) + 16)
                for ap in and_parts[1:]:
                    and_lines.append(f'{and_indent}AND {ap.strip()}')
                lines.append(f'{or_indent}OR {and_lines[0]}')
                for al in and_lines[1:]:
                    lines.append(al)
            else:
                lines.append(f'{or_indent}OR {part.strip()}')

        return '\n'.join(lines)
    else:
        # 已经处理了括号内的 OR/AND，需要添加缩进
        # 注意：processed 的第一行（开括号）会被添加到 'WHEN ' 后面，所以不需要额外缩进
        # 后续行需要相对于 WHEN 进行缩进
        lines = processed.split('\n')
        if len(lines) > 1:
            # 计算缩进：闭括号与 ( 对齐，内容缩进6个空格
            # base_indent 是字符串，需要用整数计算
            paren_count = len(base_indent) + 5  # 8 + 5 = 13，与 ( 对齐
            content_count = len(base_indent) + 6  # 8 + 6 = 14
            paren_indent = ' ' * paren_count
            content_indent = ' ' * content_count

            result = [lines[0]]  # 第一行（开括号），直接使用，会添加到 WHEN 后面
            for line in lines[1:]:
                stripped = line.strip()
                if stripped.startswith(')'):
                    # 检查是否包含连接符和第二个括号
                    if ') AND (' in stripped or ') OR (' in stripped:
                        # 拆分成三行：闭括号，连接符，开括号
                        parts = stripped.split(' ', 2)
                        if len(parts) == 3:
                            result.append(paren_indent + parts[0])  # )
                            result.append(paren_indent + parts[1])  # AND
                            result.append(paren_indent + parts[2])  # (
                        else:
                            result.append(paren_indent + stripped)
                    else:
                        result.append(paren_indent + stripped)
                else:
                    # 内容行，使用 content_indent
                    result.append(content_indent + stripped)
            return '\n'.join(result)
        else:
            return processed


def _split_parenthesized_conditions(condition: str, base_indent: int = 0) -> str:
    """分割括号内的连续 OR/AND 条件

    Args:
        condition: 要格式化的条件
        base_indent: 当前上下文的基础缩进（空格数）

    支持复杂情况，按照相对缩进：
    - (a=1 OR b=2 OR c=3) - 单组运算符
    - (a=1 OR b=2) AND (c=3 OR d=4) - 多组运算符
    - 闭合括号与开放括号对齐
    - 括号内内容相对缩进 4 空格
    """
    import re

    def find_matching_paren(s, start):
        """找到匹配的右括号"""
        depth = 0
        for i in range(start, len(s)):
            if s[i] == '(':
                depth += 1
            elif s[i] == ')':
                depth -= 1
                if depth == 0:
                    return i
        return -1

    def protect_strings(s: str) -> tuple:
        """保护字符串"""
        string_markers = []
        def protect(match):
            placeholder = f'__STRING_{len(string_markers)}__'
            string_markers.append(match.group(0))
            return placeholder
        protected = re.sub(r"('[^']*')", protect, s)
        return protected, string_markers

    def restore_strings(text: str, markers: list) -> str:
        """恢复字符串"""
        for idx, marker in enumerate(markers):
            text = text.replace(f'__STRING_{idx}__', marker)
        return text

    def split_by_op(content: str, op: str) -> list:
        """分割内容（不考虑字符串保护，字符串已保护）"""
        parts = []
        current = ''
        depth = 0
        i = 0
        op_len = len(op)

        while i < len(content):
            char = content[i]

            if char == '(':
                depth += 1
                current += char
                i += 1
            elif char == ')':
                depth -= 1
                current += char
                i += 1
            elif depth == 0 and i + op_len <= len(content) and content[i:i+op_len].upper() == op:
                before_ok = (i == 0 or not content[i-1].isalnum() and content[i-1] != '_')
                after_ok = (i + op_len >= len(content) or not content[i+op_len].isalnum() and content[i+op_len] != '_')
                if before_ok and after_ok:
                    parts.append(current.strip())
                    current = ''
                    i += op_len
                    continue
            else:
                current += char
                i += 1

        if current.strip():
            parts.append(current.strip())

        return parts if parts else [content]

    def format_paren_content(paren_content: str, content_prefix_len: int = 0) -> str:
        """格式化括号内的内容

        Args:
            paren_content: 括号内的内容
            content_prefix_len: 开括号前的内容长度（用于闭合括号对齐）
        """
        # 括号内内容缩进 = 开括号前长度 + 6 空格
        inner_indent = ' ' * (content_prefix_len + 6)

        # 保护字符串
        protected, string_markers = protect_strings(paren_content)

        # 首先尝试按OR分割
        or_parts = split_by_op(protected, 'OR')

        if len(or_parts) > 1:
            lines = ['(']  # 开放括号（无缩进，将随前面内容）
            for i, part in enumerate(or_parts):
                restored = restore_strings(part.strip(), string_markers)
                if i == 0:
                    lines.append(inner_indent + restored)
                else:
                    lines.append(inner_indent + 'OR ' + restored)
            # 闭合括号缩进 = 开括号前长度
            lines.append(' ' * content_prefix_len + ')')
            return '\n'.join(lines)

        # 没有OR，检查AND
        and_parts = split_by_op(protected, 'AND')
        if len(and_parts) > 1:
            lines = ['(']  # 开放括号
            for i, part in enumerate(and_parts):
                restored = restore_strings(part.strip(), string_markers)
                if i == 0:
                    lines.append(inner_indent + restored)
                else:
                    lines.append(inner_indent + 'AND ' + restored)
            # 闭合括号缩进 = 开括号前长度
            lines.append(' ' * content_prefix_len + ')')
            return '\n'.join(lines)

        # 如果没有需要分割的，返回原内容
        return paren_content

    def find_paren_groups(s: str) -> list:
        """找到所有顶级括号组及其连接运算符

        返回: [(paren_start, paren_content, paren_end, connector), ...]
        """
        groups = []
        i = 0

        while i < len(s):
            # 跳过空白和非括号内容，找下一个 '('
            while i < len(s) and s[i] != '(':
                i += 1

            if i >= len(s):
                break

            # 找到匹配的右括号
            paren_end = find_matching_paren(s, i)
            if paren_end < 0:
                break

            # 括号内容
            content = s[i+1:paren_end]

            # 找到括号后的连接运算符（AND/OR）
            j = paren_end + 1
            connector = ''
            while j < len(s) and s[j] == ' ':
                j += 1

            if j < len(s):
                # 检查是否是 AND 或 OR
                if j + 2 < len(s) and s[j:j+3].upper() == 'AND':
                    connector = s[j:j+3]
                elif j + 1 < len(s) and s[j:j+2].upper() == 'OR':
                    connector = s[j:j+2]

            groups.append((i, content, paren_end, connector))

            # 移动到下一个位置
            if connector:
                i = j + len(connector)
            else:
                i = paren_end + 1

        return groups

    # 主处理逻辑：分析条件结构
    paren_groups = find_paren_groups(condition)

    # 检查是否是完整的括号表达式（整个条件被一对括号包裹）
    # 如果不是，直接返回原条件（不处理部分括号）
    if len(paren_groups) == 0:
        return condition

    # 检查第一个括号是否在开头，最后一个括号是否在结尾
    first_paren_start = paren_groups[0][0]
    last_paren_end = paren_groups[-1][2]

    # 去掉前后空白后检查
    trimmed_condition = condition.strip()
    is_full_paren_expr = (
        trimmed_condition.startswith('(') and
        trimmed_condition.endswith(')') and
        first_paren_start == 0 and
        last_paren_end == len(trimmed_condition) - 1
    )

    # 如果不是完整的括号表达式，直接返回原条件
    if not is_full_paren_expr:
        return condition

    # 如果只有一个括号组或没有括号组，使用简单处理
    if len(paren_groups) <= 1:
        # 检查是否有需要格式化的内容
        if '(' in condition:
            paren_start = condition.index('(')
            paren_end = find_matching_paren(condition, paren_start)
            if paren_end > 0:
                paren_content = condition[paren_start+1:paren_end]
                temp = paren_content.replace("'", "''")
                if temp.upper().count(' OR ') >= 1 or temp.upper().count(' AND ') >= 1:
                    # 计算开括号前内容长度
                    prefix_len = paren_start
                    # format_paren_content 会返回带括号的格式化结果
                    formatted = format_paren_content(paren_content, prefix_len)
                    # 只添加括号前的内容
                    prefix = condition[:paren_start]
                    return prefix + formatted
        return condition

    # 多个括号组：需要处理它们之间的连接
    # 重新设计：构建完整的输出，然后统一处理缩进
    result_lines = []

    i = 0
    while i < len(paren_groups):
        start, content, end, connector = paren_groups[i]

        # 检查此括号组是否需要格式化
        temp = content.replace("'", "''")
        needs_format = temp.upper().count(' OR ') >= 1 or temp.upper().count(' AND ') >= 1

        if needs_format:
            # 格式化括号组
            # 计算开括号前内容长度（相对于 condition 字符串）
            prefix_len = start
            formatted = format_paren_content(content, prefix_len)

            # 检查是否有下一个括号组
            if connector and i + 1 < len(paren_groups):
                next_start, next_content, next_end, _ = paren_groups[i + 1]
                next_temp = next_content.replace("'", "''")
                next_needs_format = next_temp.upper().count(' OR ') >= 1 or next_temp.upper().count(' AND ') >= 1

                if next_needs_format:
                    # 下一个括号也需要格式化
                    # 使用与第一个括号相同的前缀长度（保持同级缩进）
                    next_prefix_len = prefix_len
                    next_formatted = format_paren_content(next_content, next_prefix_len)

                    # 合并两个格式化的括号组
                    # 格式：第一个括号的多行内容 + ) + connector + ( + 第二个括号的多行内容
                    current_lines = formatted.split('\n')
                    next_lines = next_formatted.split('\n')

                    # 添加第一个括号的所有行（除了最后一行闭括号）
                    result_lines.extend(current_lines[:-1])

                    # 闭括号 + 连接符 + 下一个开括号
                    last_line = current_lines[-1]
                    result_lines.append(last_line + ' ' + connector.strip() + ' ' + next_lines[0])

                    # 添加下一个括号的其余行
                    result_lines.extend(next_lines[1:])

                    i += 2
                else:
                    # 下一个括号不需要格式化
                    current_lines = formatted.split('\n')
                    result_lines.extend(current_lines[:-1])
                    last_line = current_lines[-1]
                    result_lines.append(last_line + ' ' + connector.strip() + ' (' + next_content + ')')
                    i += 2
            else:
                # 没有下一个括号组，直接添加
                result_lines.extend(formatted.split('\n'))
                i += 1
        else:
            # 当前括号不需要格式化
            if connector and i + 1 < len(paren_groups):
                next_start, next_content, next_end, _ = paren_groups[i + 1]
                next_temp = next_content.replace("'", "''")
                next_needs_format = next_temp.upper().count(' OR ') >= 1 or next_temp.upper().count(' AND ') >= 1

                if next_needs_format:
                    # 下一个括号需要格式化
                    next_prefix_len = next_start
                    next_formatted = format_paren_content(next_content, next_prefix_len)
                    next_lines = next_formatted.split('\n')

                    # 当前括号 + 连接符 + 下一个开括号
                    result_lines.append('(' + content + ') ' + connector.strip() + ' ' + next_lines[0])
                    result_lines.extend(next_lines[1:])
                    i += 2
                else:
                    # 两个都不需要格式化
                    result_lines.append('(' + content + ') ' + connector.strip() + ' (' + next_content + ')')
                    i += 2
            else:
                # 没有下一个括号组
                result_lines.append('(' + content + ')')
                i += 1

    return '\n'.join(result_lines)


def _split_inside_parens(content: str, op: str) -> List[str]:
    """在括号内分割条件，处理嵌套括号"""
    parts = []
    current = ''
    paren_depth = 0
    string_depth = 0

    for char in content:
        # 处理字符串
        if char in ("'", '"'):
            if string_depth == 0:
                string_depth = 1
            elif string_depth == 1 and (len(current) == 0 or current[-1] != '\\'):
                string_depth = 0

        if string_depth == 0:
            if char == '(':
                paren_depth += 1
                current += char
            elif char == ')':
                paren_depth -= 1
                current += char
            elif (char.upper() == op[0] and
                  len(current) > 0 and
                  paren_depth == 0 and
                  # 检查是否是完整的运算符单词
                  (len(content) > current.rfind(char) + len(op) and
                   content[current.rfind(char):current.rfind(char)+len(op)].upper() == op)):
                parts.append(current.strip())
                current = ''
            else:
                current += char
        else:
            current += char

    if current.strip():
        parts.append(current.strip())

    return parts if parts else [content]


def _parse_case_parts(content: str) -> Dict:
    """Parse CASE content into WHEN-THEN pairs and ELSE - V4 原有逻辑"""
    parts = {
        'whens': [],
        'else': ''
    }

    i = 0
    current_when = ''
    current_then = ''
    in_when = False
    in_then = False
    paren_depth = 0
    case_depth = 0

    tokens = re.split(r'(\bWHEN\b|\bTHEN\b|\bELSE\b|\bCASE\b|\bEND\b|\(|\))', content, flags=re.IGNORECASE)

    i = 0
    while i < len(tokens):
        token = tokens[i]
        token_upper = token.upper() if token else ''

        if token_upper == 'CASE':
            case_depth += 1
            if in_when:
                current_when += token
            elif in_then:
                current_then += token
        elif token_upper == 'END':
            case_depth -= 1
            if in_when:
                current_when += token
            elif in_then:
                current_then += token
        elif token_upper == 'WHEN' and case_depth == 0:
            if current_when and current_then:
                parts['whens'].append((current_when.strip(), current_then.strip()))
            current_when = ''
            current_then = ''
            in_when = True
            in_then = False
        elif token_upper == 'THEN' and case_depth == 0:
            in_when = False
            in_then = True
        elif token_upper == 'ELSE' and case_depth == 0:
            if current_when and current_then:
                parts['whens'].append((current_when.strip(), current_then.strip()))
            current_when = ''
            current_then = ''
            in_when = False
            in_then = False
            else_content = ''
            j = i + 1
            while j < len(tokens):
                else_token = tokens[j]
                else_token_upper = else_token.upper() if else_token else ''
                if else_token_upper == 'CASE':
                    case_depth += 1
                elif else_token_upper == 'END':
                    case_depth -= 1
                if case_depth < 0:
                    break
                else_content += else_token
                j += 1
            parts['else'] = else_content.strip()
            i = j - 1
        else:
            if in_when:
                current_when += token
            elif in_then:
                current_then += token

        i += 1

    if current_when.strip() and current_then.strip():
        parts['whens'].append((current_when.strip(), current_then.strip()))

    return parts


def _format_join_clause(join: Dict) -> List[str]:
    """Format JOIN clause

    JOIN 与 FROM 对齐（无缩进），ON 条件缩进 4 个空格
    """
    lines = []
    join_type = join['type']
    content = join['content']

    # Check for subquery
    subquery_start = content.find('(SELECT')
    if subquery_start == -1:
        subquery_start = content.find('( SELECT')
    if subquery_start == -1:
        subquery_start = content.find('(__COMMENT_')
    if subquery_start == -1:
        match = re.search(r'\(\s*(__COMMENT_\d+__\s*)?SELECT\b', content, re.IGNORECASE)
        if match:
            subquery_start = match.start()

    if subquery_start is not None and subquery_start >= 0:
        paren_depth = 0
        subquery_end = -1
        for i in range(subquery_start, len(content)):
            if content[i] == '(':
                paren_depth += 1
            elif content[i] == ')':
                paren_depth -= 1
                if paren_depth == 0:
                    subquery_end = i
                    break

        if subquery_end > 0:
            subquery_full = content[subquery_start+1:subquery_end].strip()
            after_subquery = content[subquery_end+1:].strip()
            subquery_formatted = _format_subquery(subquery_full)

            trailing_comment_match = re.search(r'(__COMMENT_\d+__)\s*$', after_subquery)
            trailing_comment = ''
            after_subquery_clean = after_subquery
            if trailing_comment_match:
                trailing_comment = ' ' + trailing_comment_match.group(1)
                after_subquery_clean = after_subquery[:trailing_comment_match.start()].strip()

            on_match = re.search(r'\bON\b\s+', after_subquery_clean, re.IGNORECASE)
            alias_part = after_subquery_clean
            on_condition = ''

            if on_match:
                alias_part = after_subquery_clean[:on_match.start()].strip()
                on_condition = after_subquery_clean[on_match.end():].strip()

            alias_part = alias_part + trailing_comment

            # JOIN 与 FROM 对齐（无缩进）
            lines.append(f'{join_type}')
            lines.append(f'    (')
            lines.append(f'{subquery_formatted}')
            lines.append(f'    ) {alias_part}')
            if on_condition:
                lines.append(f'    ON {on_condition}')
            return lines

    on_match = re.search(r'\bON\b\s+(.+)$', content, re.IGNORECASE | re.DOTALL)

    if on_match:
        table = content[:on_match.start()].strip()
        on_condition = on_match.group(1).strip()

        # JOIN 与 FROM 对齐（无缩进）
        lines.append(f'{join_type} {table}')
        # 格式化ON条件，按AND分割并换行
        on_lines = _format_on_condition(on_condition)
        lines.extend(on_lines)
    else:
        lines.append(f'{join_type} {content}')

    return lines


def _format_on_condition(on_condition: str) -> List[str]:
    """Format ON condition with AND on new lines

    ON 缩进 4 个空格，AND/OR 也缩进 4 个空格（与 ON 对齐）
    """
    lines = []

    conditions = _split_by_logical_op(on_condition, 'AND')

    if not conditions:
        return [f'    ON {on_condition}']

    # 第一个条件
    first_cond = conditions[0].strip()

    # 检查第一个条件是否包含OR
    or_parts = _split_by_logical_op(first_cond, 'OR')
    if len(or_parts) > 1:
        lines.append(f'    ON {or_parts[0].strip()}')
        for op in or_parts[1:]:
            lines.append(f'    OR {op.strip()}')
    else:
        lines.append(f'    ON {first_cond}')

    # 后续条件（按AND换行）
    for cond in conditions[1:]:
        cond = cond.strip()
        if not cond:
            continue

        # 检查是否包含OR
        or_parts = _split_by_logical_op(cond, 'OR')
        if len(or_parts) > 1:
            lines.append(f'    AND {or_parts[0].strip()}')
            for op in or_parts[1:]:
                lines.append(f'    OR {op.strip()}')
        else:
            lines.append(f'    AND {cond}')

    return lines


def _format_subquery(subquery: str, keyword_case: str = 'upper', indent_level: int = 0) -> str:
    """Format a subquery with proper indentation - V4 原有逻辑"""
    parts = _parse_sql_parts(subquery, keyword_case, indent_level)

    lines = []

    if parts['select']:
        select_lines = _format_select_clause(parts['select'])
        for sl in select_lines:
            lines.append('            ' + sl)

    if parts['from']:
        lines.append(f'            FROM {parts["from"]}')

    if parts['where']:
        where_conditions = _split_by_logical_op(parts['where'], 'AND')
        first_cond = where_conditions[0].strip()

        or_parts = _split_by_logical_op(first_cond, 'OR')
        if len(or_parts) > 1:
            lines.append(f'            WHERE {or_parts[0].strip()}')
            for op in or_parts[1:]:
                lines.append(f'                OR {op.strip()}')
        else:
            lines.append(f'            WHERE {first_cond}')

        for cond in where_conditions[1:]:
            cond = cond.strip()
            if cond.startswith('(') and cond.endswith(')'):
                inner = cond[1:-1].strip()
                or_parts = _split_by_logical_op(inner, 'OR')
                if len(or_parts) > 1:
                    lines.append(f'                AND (')
                    lines.append(f'                    {or_parts[0].strip()}')
                    for op in or_parts[1:]:
                        lines.append(f'                    OR {op.strip()}')
                    lines.append(f'                )')
                    continue
            or_parts = _split_by_logical_op(cond, 'OR')
            if len(or_parts) > 1:
                lines.append(f'                AND {or_parts[0].strip()}')
                for op in or_parts[1:]:
                    lines.append(f'                OR {op.strip()}')
            else:
                lines.append(f'                AND {cond}')

    return '\n'.join(lines)


def _format_where_clause(where: str) -> List[str]:
    """Format WHERE clause with AND on new lines

    WHERE 与 FROM 对齐（无缩进），AND 缩进 4 个空格
    保留子查询的多行格式
    """
    lines = []

    # 检测 WHERE 子句是否包含换行
    has_newlines = '\n' in where

    if has_newlines:
        # 包含换行，保留原有格式
        # 添加 WHERE 前缀
        lines.append(f'WHERE {where}')
    else:
        # 没有换行，使用原有逻辑
        conditions = _split_by_logical_op(where, 'AND')

        if conditions:
            first_formatted = _format_condition_with_ors(conditions[0].strip(), 4)
            # WHERE 与 FROM 对齐（无缩进）
            lines.append(f'WHERE {first_formatted}')

            for cond in conditions[1:]:
                cond_formatted = _format_condition_with_ors(cond.strip(), 4)
                # AND 缩进 4 个空格
                lines.append(f'    AND {cond_formatted}')

    return lines


def _split_by_union(sql: str) -> List[str]:
    """分割 UNION/UNION ALL 连接的多个 SELECT 语句

    处理嵌套括号和字符串，避免误分割

    返回格式: [SELECT语句1, 'UNION' 或 'UNION ALL', SELECT语句2, ...]
    """
    statements = []
    current = []
    paren_depth = 0
    in_string = False
    string_char = None
    i = 0

    while i < len(sql):
        char = sql[i]

        # 处理字符串
        if not in_string and char in ('"', "'"):
            in_string = True
            string_char = char
            current.append(char)
            i += 1
            continue
        elif in_string and char == string_char:
            # 检查是否转义
            if i > 0 and sql[i - 1] != '\\':
                in_string = False
                string_char = None
            current.append(char)
            i += 1
            continue

        if in_string:
            current.append(char)
            i += 1
            continue

        # 处理括号
        if char == '(':
            paren_depth += 1
            current.append(char)
            i += 1
            continue
        elif char == ')':
            paren_depth -= 1
            current.append(char)
            i += 1
            continue

        # 检查 UNION 关键字（只在括号外检测）
        if paren_depth == 0 and i + 5 <= len(sql):
            # 检查 UNION 或 UNION ALL
            if sql[i:i+5].upper() == 'UNION' and (i + 5 >= len(sql) or not sql[i + 5].isalnum()):
                # 保存当前语句
                stmt = ''.join(current).strip()
                if stmt:
                    statements.append(stmt)

                # 跳过 UNION 关键字
                i += 5
                # 跳过空白
                while i < len(sql) and sql[i] in ' \t\n':
                    i += 1

                # 检查是否有 ALL
                if i + 3 <= len(sql) and sql[i:i+3].upper() == 'ALL' and (i + 3 >= len(sql) or not sql[i + 3].isalnum()):
                    # 添加 UNION ALL 作为独立的语句部分
                    statements.append('UNION ALL')
                    i += 3
                else:
                    # 添加 UNION 作为独立的语句部分
                    statements.append('UNION')

                # 清空 current，准备收集下一个语句
                current = []
                # 跳过 UNION 后的空白
                while i < len(sql) and sql[i] in ' \t\n':
                    i += 1
                continue

        current.append(char)
        i += 1

    # 添加最后一个语句
    stmt = ''.join(current).strip()
    if stmt:
        statements.append(stmt)

    return statements


def _format_union_statement(sql: str, keyword_case: str = 'upper') -> str:
    """格式化包含 UNION 的 SELECT 语句

    每个 SELECT 分别格式化，然后用 UNION 连接
    """
    # 检测是否包含 UNION
    if not re.search(r'\bUNION\b', sql, re.IGNORECASE):
        # 没有 UNION，使用正常格式化
        return _format_sql_structure(sql, keyword_case)

    # 分割 UNION
    union_parts = _split_by_union(sql)

    if len(union_parts) <= 1:
        # 没有分割出多个部分，使用正常格式化
        return _format_sql_structure(sql, keyword_case)

    # 格式化每个 SELECT 部分
    formatted_parts = []
    for i, part in enumerate(union_parts):
        part = part.strip()
        if part.upper() in ('UNION', 'UNION ALL'):
            # 这是 UNION 关键字，保留（已经是大写）
            formatted_parts.append(part.upper())
        else:
            # 这是 SELECT 语句，格式化它
            formatted = _format_sql_structure(part, keyword_case)
            formatted_parts.append(formatted)

    # 用换行连接所有部分（UNION 已经在 formatted_parts 中）
    return '\n'.join(formatted_parts)


def _format_condition_with_ors(condition: str, base_indent: int) -> str:
    """Format a condition that may contain multiple ORs - V4 原有逻辑"""
    # 首先处理括号内的连续 OR/AND 条件
    condition = _split_parenthesized_conditions(condition, base_indent)

    trailing_comment = ''
    core_condition = condition

    if condition.startswith('('):
        paren_depth = 0
        close_paren_pos = -1
        for i, char in enumerate(condition):
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
                if paren_depth == 0:
                    close_paren_pos = i
                    break

        if close_paren_pos > 0:
            after_paren = condition[close_paren_pos + 1:].strip()
            if after_paren:
                comment_match = re.match(r'^(__COMMENT_\d+__)', after_paren)
                if comment_match:
                    trailing_comment = ' ' + comment_match.group(1)
                    core_condition = condition[:close_paren_pos + 1]
                elif after_paren.startswith('--'):
                    trailing_comment = ' ' + after_paren
                    core_condition = condition[:close_paren_pos + 1]

    if core_condition.startswith('(') and core_condition.endswith(')'):
        inner = core_condition[1:-1].strip()
        or_parts = _split_by_logical_op(inner, 'OR')
        if len(or_parts) > 1:
            lines = ['(']
            for i, part in enumerate(or_parts):
                part_formatted = _format_condition_with_ands(part.strip(), base_indent + 4)
                if i == 0:
                    lines.append(f'{" " * (base_indent + 4)}{part_formatted}')
                else:
                    lines.append(f'{" " * (base_indent + 4)}OR {part_formatted}')
            lines.append(f'{" " * base_indent}){trailing_comment}')
            return '\n'.join(lines)

    or_parts = _split_by_logical_op(condition, 'OR')
    if len(or_parts) > 1:  # 改为 > 1，2个或更多OR就换行
        lines = []
        for i, part in enumerate(or_parts):
            if i == 0:
                lines.append(part.strip())
            else:
                lines.append(f'{" " * base_indent}OR {part.strip()}')
        return '\n'.join(lines)

    return condition


def _format_condition_with_ands(condition: str, base_indent: int) -> str:
    """Format a condition that may contain multiple ANDs - V4 原有逻辑"""
    # 首先处理括号内的连续 OR/AND 条件
    condition = _split_parenthesized_conditions(condition, base_indent)

    and_parts = _split_by_logical_op(condition, 'AND')
    if len(and_parts) > 1:  # 改为 > 1，2个或更多AND就换行
        lines = []
        for i, part in enumerate(and_parts):
            if i == 0:
                lines.append(part.strip())
            else:
                lines.append(f'{" " * base_indent}AND {part.strip()}')
        return '\n'.join(lines)
    return condition


def _split_by_logical_op(sql: str, op: str) -> List[str]:
    """Split SQL by AND or OR, respecting parentheses and CASE blocks - V4 原有逻辑"""
    conditions = []
    current = ''
    paren_depth = 0
    case_depth = 0

    tokens = re.split(rf'(\b{op}\b|\(|\)|\bCASE\b|\bEND\b)', sql, flags=re.IGNORECASE)

    for token in tokens:
        token_upper = token.upper() if token else ''

        if token == '(':
            paren_depth += 1
            current += token
        elif token == ')':
            paren_depth -= 1
            current += token
        elif token_upper == 'CASE':
            case_depth += 1
            current += token
        elif token_upper == 'END':
            case_depth -= 1
            current += token
        elif token_upper == op and paren_depth == 0 and case_depth == 0:
            if current.strip():
                conditions.append(current.strip())
            current = ''
        else:
            current += token

    if current.strip():
        conditions.append(current.strip())

    return conditions


def _uppercase_keywords(sql: str) -> str:
    """Convert SQL keywords to uppercase - V4 原有逻辑 + 新增关键字"""
    keywords = [
        # DML
        'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'EXISTS',
        'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE',
        # DDL
        'CREATE', 'DROP', 'ALTER', 'TABLE', 'IF', 'NOT', 'EXISTS',
        # JOIN
        'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN', 'CROSS JOIN', 'JOIN', 'ON',
        # GROUP/ORDER
        'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'DISTRIBUTE BY',
        # CASE
        'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'AS', 'IS', 'NULL',
        # 其他
        'LIKE', 'BETWEEN', 'DISTINCT', 'OVER', 'PARTITION BY',
        'ASC', 'DESC', 'NVL', 'CAST', 'SUBSTR', 'SUBSTRING',
        'LPAD', 'RPAD', 'ROW_NUMBER', 'COALESCE', 'RAND', 'CEIL',
        'SUM', 'COUNT', 'MAX', 'MIN', 'AVG',
        # Spark SQL 特有
        'COMMENT', 'STRING', 'INT', 'BIGINT', 'DOUBLE', 'FLOAT',
        'FORMAT', 'DELIMITED', 'DEFINED', 'ROW'
    ]

    result = sql
    for keyword in sorted(keywords, key=len, reverse=True):
        pattern = r'\b' + re.escape(keyword) + r'\b'
        result = re.sub(pattern, keyword.upper(), result, flags=re.IGNORECASE)

    return result
