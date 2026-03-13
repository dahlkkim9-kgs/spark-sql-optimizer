# -*- coding: utf-8 -*-
"""数据操作处理器 - 支持 MERGE/INSERT OVERWRITE"""
import re
import sys
import os
from typing import Literal, List, Tuple
from .base_processor import BaseProcessor


def _get_formatter():
    """动态导入 formatter_v4_fixed，兼容不同运行环境"""
    try:
        # 尝试从 backend.core 导入（API 环境）
        from backend.core.formatter_v4_fixed import format_sql_v4_fixed
        return format_sql_v4_fixed
    except ImportError:
        # 尝试从 core 导入（测试环境）
        try:
            # 确保 core 路径在 sys.path 中
            core_path = os.path.join(os.path.dirname(__file__), '..')
            if core_path not in sys.path:
                sys.path.insert(0, core_path)
            from core.formatter_v4_fixed import format_sql_v4_fixed
            return format_sql_v4_fixed
        except ImportError:
            # 最后尝试直接导入
            from formatter_v4_fixed import format_sql_v4_fixed
            return format_sql_v4_fixed


# 缓存导入的函数
_formatter_func = None


def _call_formatter(sql: str, keyword_case: str = 'upper') -> str:
    """调用 formatter_v4_fixed.format_sql_v4_fixed"""
    global _formatter_func
    if _formatter_func is None:
        _formatter_func = _get_formatter()
    return _formatter_func(sql, keyword_case=keyword_case)


class DataOperationsProcessor(BaseProcessor):
    """数据操作处理器 - 支持 MERGE/INSERT OVERWRITE"""

    def __init__(self):
        super().__init__()
        # MERGE 模式
        self.merge_pattern = re.compile(r'^\s*MERGE\s+INTO\b', re.IGNORECASE)
        # INSERT OVERWRITE 模式
        self.insert_overwrite_pattern = re.compile(
            r'INSERT\s+OVERWRITE\s+(?:TABLE\s+)?\S+',
            re.IGNORECASE
        )

    def can_process(self, sql: str) -> bool:
        """检查 SQL 是否是数据操作语句"""
        sql_upper = sql.upper().strip()
        # 检查 MERGE INTO
        if self.merge_pattern.search(sql):
            return True
        # 检查 INSERT OVERWRITE
        if self.insert_overwrite_pattern.search(sql):
            return True
        return False

    def process(
        self,
        sql: str,
        keyword_case: Literal['upper', 'lower', 'capitalize'] = 'upper'
    ) -> str:
        """处理数据操作 SQL"""
        # 去除首尾空白
        sql = sql.strip()

        # 检查是否是 MERGE 语句
        if self.merge_pattern.search(sql):
            return self._format_merge(sql, keyword_case)

        # 检查是否是 INSERT OVERWRITE 语句
        if self.insert_overwrite_pattern.search(sql):
            return self._format_insert_overwrite(sql, keyword_case)

        # 如果都不是，返回原样（理论上不会到这里）
        return sql

    def _format_merge(
        self,
        sql: str,
        keyword_case: Literal['upper', 'lower', 'capitalize'] = 'upper'
    ) -> str:
        """格式化 MERGE 语句

        MERGE 语法结构:
        MERGE INTO target
        USING source
        ON condition
        [ WHEN MATCHED [ AND condition ] THEN
            { UPDATE SET ... | DELETE } ]
        [ WHEN NOT MATCHED [ AND condition ] THEN
            INSERT ... ]
        """
        # 临时移除注释以避免干扰解析
        sql_without_comments, comments = self._remove_and_preserve_comments(sql)

        # 使用更健壮的方法解析 MERGE 语句
        # 按关键字分割
        parts = self._split_merge_statement(sql_without_comments)

        if not parts or 'target' not in parts:
            # 解析失败，返回原样
            return sql

        # 标准化关键字大小写
        target_part = self._normalize_merge_keywords(
            parts['target'], keyword_case
        )
        source_part = self._normalize_merge_keywords(
            parts['source'], keyword_case
        )
        on_part = self._normalize_merge_keywords(
            parts['on'], keyword_case
        )

        # 组装格式化后的 MERGE 语句
        lines = []
        lines.append(target_part.strip())
        lines.append(source_part.strip())
        lines.append(on_part.strip())

        # 添加 WHEN 分支
        for when_clause in parts.get('when_clauses', []):
            header = self._normalize_merge_keywords(
                when_clause['header'], keyword_case
            )
            lines.append(header.strip())
            # THEN 后的语句缩进 4 个空格
            for action_line in when_clause['actions']:
                lines.append('    ' + action_line.strip())

        result = '\n'.join(lines)

        # 恢复注释
        result = self._restore_comments(result, comments, sql)

        return result

    def _split_merge_statement(self, sql: str) -> dict:
        """分割 MERGE 语句为各个部分

        返回:
            {
                'target': 'MERGE INTO target',
                'source': 'USING source',
                'on': 'ON target.id = source.id',
                'when_clauses': [
                    {
                        'header': 'WHEN MATCHED THEN',
                        'actions': ['UPDATE SET ...']
                    },
                    ...
                ]
            }
        """
        result = {
            'target': '',
            'source': '',
            'on': '',
            'when_clauses': []
        }

        remaining = sql.strip()

        # 1. 提取 MERGE INTO
        merge_into_match = re.match(
            r'(MERGE\s+INTO)\s+(\S+)',
            remaining,
            re.IGNORECASE
        )
        if merge_into_match:
            result['target'] = merge_into_match.group(0)
            remaining = remaining[merge_into_match.end():].strip()
        else:
            return {}

        # 2. 提取 USING（可能包含子查询）
        using_match = re.match(
            r'(USING)\s+',
            remaining,
            re.IGNORECASE
        )
        if not using_match:
            return result

        # 提取 USING 后面的内容（可能是表名或子查询）
        remaining = remaining[using_match.end():].strip()
        source_content = self._extract_source_content(remaining)

        if not source_content:
            return result

        result['source'] = 'USING ' + source_content['content']
        remaining = source_content['remaining'].strip()

        # 3. 提取 ON 条件
        on_match = re.match(
            r'(ON)\s+',
            remaining,
            re.IGNORECASE
        )
        if not on_match:
            return result

        remaining = remaining[on_match.end():].strip()

        # 提取 ON 条件到 WHEN 关键字
        on_condition_end = self._find_when_position(remaining)
        if on_condition_end == -1:
            # 没有 WHEN 分支
            result['on'] = 'ON ' + remaining
            return result

        result['on'] = 'ON ' + remaining[:on_condition_end].strip()
        remaining = remaining[on_condition_end:].strip()

        # 4. 提取 WHEN 分支
        result['when_clauses'] = self._parse_when_clauses(remaining, 'upper')

        return result

    def _extract_source_content(self, sql: str) -> dict:
        """提取 USING 后面的内容（表名或子查询）

        返回:
            {
                'content': 'table_name 或 (子查询)',
                'remaining': '剩余的 SQL'
            }
        """
        if not sql:
            return {}

        sql = sql.strip()

        # 检查是否是子查询（以括号开头）
        if sql.startswith('('):
            # 找到匹配的右括号
            paren_end = self._find_matching_paren(sql, 0)
            if paren_end == -1:
                # 括号不匹配，返回整个内容
                return {'content': sql, 'remaining': ''}

            # 提取子查询
            subquery = sql[:paren_end + 1]
            remaining = sql[paren_end + 1:].strip()

            # 检查是否有别名（如 src）
            alias_match = re.match(r'^(\w+)\s*', remaining)
            if alias_match:
                alias = alias_match.group(1)
                remaining = remaining[alias_match.end():].strip()
                return {'content': f'{subquery} {alias}', 'remaining': remaining}
            else:
                return {'content': subquery, 'remaining': remaining}
        else:
            # 普通表名
            # 提取第一个词（表名）
            table_match = re.match(r'(\S+)\s*', sql)
            if table_match:
                table_name = table_match.group(1)
                remaining = sql[table_match.end():].strip()
                return {'content': table_name, 'remaining': remaining}
            else:
                return {'content': sql, 'remaining': ''}

    def _find_matching_paren(self, sql: str, start: int) -> int:
        """找到匹配的右括号位置

        Args:
            sql: SQL 语句
            start: 左括号位置

        Returns:
            右括号位置，如果未找到返回 -1
        """
        depth = 0
        i = start
        while i < len(sql):
            if sql[i] == '(':
                depth += 1
            elif sql[i] == ')':
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return -1

    def _find_when_position(self, sql: str) -> int:
        """找到 WHEN 关键字的位置

        Args:
            sql: SQL 语句

        Returns:
            WHEN 关键字位置，如果未找到返回 -1
        """
        # 使用新方法查找 WHEN 关键字，跳过字符串和注释
        return self._find_keyword_outside_strings(sql, r'\bWHEN\s+')

    def _find_keyword_outside_strings(self, sql: str, pattern: str) -> int:
        """查找不在字符串字面量中的关键字位置

        此方法跳过单引号和双引号内的内容，正确处理转义字符。
        例如: "ON col = 'WHEN xyz'" 中的 WHEN 会被跳过。

        Args:
            sql: SQL 语句
            pattern: 正则表达式模式（用于匹配关键字）

        Returns:
            关键字位置，如果未找到返回 -1
        """
        i = 0
        in_single_quote = False
        in_double_quote = False
        n = len(sql)

        # 编译正则表达式以提高性能
        keyword_regex = re.compile(pattern, re.IGNORECASE)

        while i < n:
            char = sql[i]

            # 处理转义字符
            if char == '\\' and i + 1 < n:
                # 跳过转义字符和下一个字符
                i += 2
                continue

            # 处理字符串字面量
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
                i += 1
                continue
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
                i += 1
                continue

            # 如果在字符串内，跳过
            if in_single_quote or in_double_quote:
                i += 1
                continue

            # 在字符串外，检查是否匹配关键字
            remaining = sql[i:]
            match = keyword_regex.search(remaining)
            if match:
                # 确保匹配的起始位置就是当前位置
                if match.start() == 0:
                    return i
                # 匹配不在当前位置，逐个字符处理以正确识别字符串
                # 不要跳过中间的字符

            # 未找到匹配，继续下一个字符
            i += 1

        return -1

    def _remove_and_preserve_comments(self, sql: str) -> tuple:
        """移除 SQL 注释并保存它们的位置，以便后续恢复

        处理两种类型的注释:
        1. 单行注释: -- comment
        2. 多行注释: /* comment */

        Args:
            sql: SQL 语句

        Returns:
            (处理后的 SQL, 注释列表) 其中注释列表格式为:
            [(position, comment_text), ...]
        """
        comments = []
        result = []
        i = 0
        n = len(sql)

        while i < n:
            # 检查单行注释 (--)
            if i + 1 < n and sql[i:i+2] == '--':
                start = i
                # 找到行尾
                while i < n and sql[i] != '\n':
                    i += 1
                comment_text = sql[start:i]
                comments.append((start, comment_text))
                # 跳过换行符
                if i < n and sql[i] == '\n':
                    result.append('\n')
                    i += 1
                continue

            # 检查多行注释 (/*)
            if i + 1 < n and sql[i:i+2] == '/*':
                start = i
                i += 2
                # 找到结束的 */
                while i + 1 < n and sql[i:i+2] != '*/':
                    i += 1
                if i + 1 < n:
                    i += 2  # 跳过 */
                comment_text = sql[start:i]
                comments.append((start, comment_text))
                continue

            # 普通字符，添加到结果
            result.append(sql[i])
            i += 1

        return ''.join(result), comments

    def _restore_comments(self, formatted_sql: str, comments: List[Tuple[int, str]], original_sql: str) -> str:
        """将收集的注释恢复到格式化后的 SQL 中

        策略:
        1. 找到注释在原始 SQL 中的行号
        2. 计算该行在格式化后 SQL 中的对应位置
        3. 在对应位置插入注释

        Args:
            formatted_sql: 格式化后的 SQL
            comments: 注释列表 [(position, comment_text), ...]
            original_sql: 原始 SQL（用于确定注释的行位置）

        Returns:
            恢复注释后的 SQL
        """
        if not comments:
            return formatted_sql

        # 计算原始 SQL 中每行的起始位置
        original_lines = original_sql.split('\n')
        line_positions = []
        pos = 0
        line_positions.append(0)
        for line in original_lines:
            pos += len(line) + 1  # +1 for newline
            line_positions.append(pos)

        # 按注释位置找到所在行
        comments_by_line = {}
        for comment_pos, comment_text in comments:
            # 二分查找找到注释所在的行
            line_num = 0
            for i in range(len(line_positions) - 1):
                if line_positions[i] <= comment_pos < line_positions[i + 1]:
                    line_num = i
                    break

            if line_num not in comments_by_line:
                comments_by_line[line_num] = []
            comments_by_line[line_num].append(comment_text)

        # 简单策略：直接在格式化后的 SQL 末尾添加所有注释
        # 更复杂的策略需要分析 SQL 结构
        if comments_by_line:
            # 将注释按行号排序
            sorted_lines = sorted(comments_by_line.keys())

            # 构建注释块
            comment_blocks = []
            for line_num in sorted_lines:
                for comment_text in comments_by_line[line_num]:
                    comment_blocks.append(comment_text)

            # 在格式化后的 SQL 前添加注释
            if comment_blocks:
                return '\n'.join(comment_blocks) + '\n' + formatted_sql

        return formatted_sql

    def _normalize_merge_keywords(
        self,
        part: str,
        keyword_case: Literal['upper', 'lower', 'capitalize']
    ) -> str:
        """标准化 MERGE 语句部分中的关键字"""
        if keyword_case == 'upper':
            part = re.sub(r'\bMERGE\b', 'MERGE', part, flags=re.IGNORECASE)
            part = re.sub(r'\bINTO\b', 'INTO', part, flags=re.IGNORECASE)
            part = re.sub(r'\bUSING\b', 'USING', part, flags=re.IGNORECASE)
            part = re.sub(r'\bON\b', 'ON', part, flags=re.IGNORECASE)
            part = re.sub(r'\bWHEN\b', 'WHEN', part, flags=re.IGNORECASE)
            part = re.sub(r'\bMATCHED\b', 'MATCHED', part, flags=re.IGNORECASE)
            part = re.sub(r'\bNOT\b', 'NOT', part, flags=re.IGNORECASE)
            part = re.sub(r'\bAND\b', 'AND', part, flags=re.IGNORECASE)
            part = re.sub(r'\bTHEN\b', 'THEN', part, flags=re.IGNORECASE)
            part = self._normalize_action_keywords(part, 'upper')
        elif keyword_case == 'lower':
            part = re.sub(r'\bMERGE\b', 'merge', part, flags=re.IGNORECASE)
            part = re.sub(r'\bINTO\b', 'into', part, flags=re.IGNORECASE)
            part = re.sub(r'\bUSING\b', 'using', part, flags=re.IGNORECASE)
            part = re.sub(r'\bON\b', 'on', part, flags=re.IGNORECASE)
            part = re.sub(r'\bWHEN\b', 'when', part, flags=re.IGNORECASE)
            part = re.sub(r'\bMATCHED\b', 'matched', part, flags=re.IGNORECASE)
            part = re.sub(r'\bNOT\b', 'not', part, flags=re.IGNORECASE)
            part = re.sub(r'\bAND\b', 'and', part, flags=re.IGNORECASE)
            part = re.sub(r'\bTHEN\b', 'then', part, flags=re.IGNORECASE)
            part = self._normalize_action_keywords(part, 'lower')
        else:  # capitalize
            part = re.sub(r'\bMERGE\b', 'Merge', part, flags=re.IGNORECASE)
            part = re.sub(r'\bINTO\b', 'Into', part, flags=re.IGNORECASE)
            part = re.sub(r'\bUSING\b', 'Using', part, flags=re.IGNORECASE)
            part = re.sub(r'\bON\b', 'On', part, flags=re.IGNORECASE)
            part = re.sub(r'\bWHEN\b', 'When', part, flags=re.IGNORECASE)
            part = re.sub(r'\bMATCHED\b', 'Matched', part, flags=re.IGNORECASE)
            part = re.sub(r'\bNOT\b', 'Not', part, flags=re.IGNORECASE)
            part = re.sub(r'\bAND\b', 'And', part, flags=re.IGNORECASE)
            part = re.sub(r'\bTHEN\b', 'Then', part, flags=re.IGNORECASE)
            part = self._normalize_action_keywords(part, 'capitalize')
        return part

    def _parse_when_clauses(
        self,
        sql: str,
        keyword_case: Literal['upper', 'lower', 'capitalize']
    ) -> List[dict]:
        """解析 WHEN 分支

        返回:
            [
                {
                    'header': 'WHEN MATCHED THEN',
                    'actions': ['UPDATE SET ...', 'DELETE']
                },
                ...
            ]
        """
        when_clauses = []
        remaining = sql.strip()

        while remaining:
            # 匹配 WHEN 分支
            when_match = re.search(
                r'(WHEN\s+(?:NOT\s+)?MATCHED(?:\s+AND\s+.*?)?\s+THEN)\s*(.*?)(?=WHEN\s+|$)',
                remaining,
                re.IGNORECASE | re.DOTALL
            )

            if not when_match:
                break

            header = when_match.group(1).strip()
            actions = when_match.group(2).strip()

            # 标准化关键字大小写
            if keyword_case == 'upper':
                header = re.sub(r'\bWHEN\b', 'WHEN', header, flags=re.IGNORECASE)
                header = re.sub(r'\bMATCHED\b', 'MATCHED', header, flags=re.IGNORECASE)
                header = re.sub(r'\bNOT\b', 'NOT', header, flags=re.IGNORECASE)
                header = re.sub(r'\bAND\b', 'AND', header, flags=re.IGNORECASE)
                header = re.sub(r'\bTHEN\b', 'THEN', header, flags=re.IGNORECASE)
                actions = self._normalize_action_keywords(actions, 'upper')
            elif keyword_case == 'lower':
                header = re.sub(r'\bWHEN\b', 'when', header, flags=re.IGNORECASE)
                header = re.sub(r'\bMATCHED\b', 'matched', header, flags=re.IGNORECASE)
                header = re.sub(r'\bNOT\b', 'not', header, flags=re.IGNORECASE)
                header = re.sub(r'\bAND\b', 'and', header, flags=re.IGNORECASE)
                header = re.sub(r'\bTHEN\b', 'then', header, flags=re.IGNORECASE)
                actions = self._normalize_action_keywords(actions, 'lower')
            else:  # capitalize
                header = re.sub(r'\bWHEN\b', 'When', header, flags=re.IGNORECASE)
                header = re.sub(r'\bMATCHED\b', 'Matched', header, flags=re.IGNORECASE)
                header = re.sub(r'\bNOT\b', 'Not', header, flags=re.IGNORECASE)
                header = re.sub(r'\bAND\b', 'And', header, flags=re.IGNORECASE)
                header = re.sub(r'\bTHEN\b', 'Then', header, flags=re.IGNORECASE)
                actions = self._normalize_action_keywords(actions, 'capitalize')

            # 分割动作（可能包含 UPDATE 和 DELETE）
            action_lines = self._split_actions(actions)

            when_clauses.append({
                'header': header,
                'actions': action_lines
            })

            # 移动到下一个 WHEN 分支
            remaining = remaining[when_match.end():].strip()

        return when_clauses

    def _split_actions(self, actions: str) -> List[str]:
        """分割动作语句（UPDATE/DELETE/INSERT）

        处理复杂的情况，例如：
        - UPDATE SET x = 1, y = 2
        - DELETE
        - INSERT (col1, col2) VALUES (val1, val2)
        """
        actions = actions.strip()

        # 简单情况：单行动作
        if not re.search(r'\n', actions):
            # 检查是否是多行 VALUES 语句
            if re.search(r'VALUES\s*\(', actions, re.IGNORECASE):
                # 分割 INSERT 和 VALUES
                insert_match = re.match(
                    r'(INSERT\s*\(.*?\))\s*(VALUES\s*\(.*?\))',
                    actions,
                    re.IGNORECASE | re.DOTALL
                )
                if insert_match:
                    return [
                        insert_match.group(1).strip(),
                        insert_match.group(2).strip()
                    ]
            return [actions]

        # 多行情况：按行分割并清理
        lines = actions.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)
        return cleaned_lines

    def _normalize_action_keywords(
        self,
        action: str,
        keyword_case: Literal['upper', 'lower', 'capitalize']
    ) -> str:
        """标准化动作语句中的关键字"""
        if keyword_case == 'upper':
            action = re.sub(r'\bUPDATE\b', 'UPDATE', action, flags=re.IGNORECASE)
            action = re.sub(r'\bSET\b', 'SET', action, flags=re.IGNORECASE)
            action = re.sub(r'\bDELETE\b', 'DELETE', action, flags=re.IGNORECASE)
            action = re.sub(r'\bINSERT\b', 'INSERT', action, flags=re.IGNORECASE)
            action = re.sub(r'\bVALUES\b', 'VALUES', action, flags=re.IGNORECASE)
        elif keyword_case == 'lower':
            action = re.sub(r'\bUPDATE\b', 'update', action, flags=re.IGNORECASE)
            action = re.sub(r'\bSET\b', 'set', action, flags=re.IGNORECASE)
            action = re.sub(r'\bDELETE\b', 'delete', action, flags=re.IGNORECASE)
            action = re.sub(r'\bINSERT\b', 'insert', action, flags=re.IGNORECASE)
            action = re.sub(r'\bVALUES\b', 'values', action, flags=re.IGNORECASE)
        else:  # capitalize
            action = re.sub(r'\bUPDATE\b', 'Update', action, flags=re.IGNORECASE)
            action = re.sub(r'\bSET\b', 'Set', action, flags=re.IGNORECASE)
            action = re.sub(r'\bDELETE\b', 'Delete', action, flags=re.IGNORECASE)
            action = re.sub(r'\bINSERT\b', 'Insert', action, flags=re.IGNORECASE)
            action = re.sub(r'\bVALUES\b', 'Values', action, flags=re.IGNORECASE)
        return action

    def _extract_original_case(self, original_sql: str, upper_pattern: str) -> str:
        """从原始 SQL 中提取保留大小写的部分

        Args:
            original_sql: 原始 SQL 语句
            upper_pattern: 大写模式（用于定位）

        Returns:
            保留原始大小写的 SQL 部分
        """
        # 简单实现：通过位置提取
        # 找到大写模式在原始 SQL 中的位置
        upper_sql = original_sql.upper()
        start_pos = upper_sql.find(upper_pattern.upper())
        if start_pos == -1:
            return upper_pattern

        end_pos = start_pos + len(upper_pattern)
        return original_sql[start_pos:end_pos]

    def _format_insert_overwrite(
        self,
        sql: str,
        keyword_case: Literal['upper', 'lower', 'capitalize'] = 'upper'
    ) -> str:
        """格式化 INSERT OVERWRITE 语句

        INSERT OVERWRITE 语法结构:
        INSERT OVERWRITE [TABLE] table_name
        [PARTITION (part_col1, part_col2, ...)]
        SELECT ...

        或者:
        INSERT OVERWRITE [TABLE] table_name
        SELECT ...
        """
        # 临时移除注释以避免干扰解析
        sql_without_comments, comments = self._remove_and_preserve_comments(sql)

        # 匹配 INSERT OVERWRITE 到 SELECT
        match = re.search(
            r'(INSERT\s+OVERWRITE\s+(?:TABLE\s+)?\S+.*?)\s*(SELECT\s+.*)',
            sql_without_comments,
            re.IGNORECASE | re.DOTALL
        )

        if not match:
            # 如果没有 SELECT，可能只有 INSERT OVERWRITE 部分
            # 直接返回标准化后的语句
            result = self._normalize_insert_overwrite_keywords(sql, keyword_case)
            # 恢复注释
            result = self._restore_comments(result, comments, sql)
            return result

        insert_part = match.group(1).strip()
        select_part = match.group(2).strip()

        # 标准化 INSERT OVERWRITE 部分的关键字
        insert_part = self._normalize_insert_overwrite_keywords(
            insert_part, keyword_case
        )

        # 格式化 SELECT 部分
        formatted_select = _call_formatter(select_part, keyword_case=keyword_case)

        # 清理格式化后的 SELECT（移除末尾分号）
        formatted_select = self._clean_formatted_select(formatted_select)

        # 组合
        result = f'{insert_part}\n{formatted_select}'

        # 恢复注释
        result = self._restore_comments(result, comments, sql)

        return result

    def _normalize_insert_overwrite_keywords(
        self,
        sql: str,
        keyword_case: Literal['upper', 'lower', 'capitalize']
    ) -> str:
        """标准化 INSERT OVERWRITE 语句中的关键字"""
        if keyword_case == 'upper':
            sql = re.sub(r'\bINSERT\b', 'INSERT', sql, flags=re.IGNORECASE)
            sql = re.sub(r'\bOVERWRITE\b', 'OVERWRITE', sql, flags=re.IGNORECASE)
            sql = re.sub(r'\bTABLE\b', 'TABLE', sql, flags=re.IGNORECASE)
            sql = re.sub(r'\bPARTITION\b', 'PARTITION', sql, flags=re.IGNORECASE)
        elif keyword_case == 'lower':
            sql = re.sub(r'\bINSERT\b', 'insert', sql, flags=re.IGNORECASE)
            sql = re.sub(r'\bOVERWRITE\b', 'overwrite', sql, flags=re.IGNORECASE)
            sql = re.sub(r'\bTABLE\b', 'table', sql, flags=re.IGNORECASE)
            sql = re.sub(r'\bPARTITION\b', 'partition', sql, flags=re.IGNORECASE)
        else:  # capitalize
            sql = re.sub(r'\bINSERT\b', 'Insert', sql, flags=re.IGNORECASE)
            sql = re.sub(r'\bOVERWRITE\b', 'Overwrite', sql, flags=re.IGNORECASE)
            sql = re.sub(r'\bTABLE\b', 'Table', sql, flags=re.IGNORECASE)
            sql = re.sub(r'\bPARTITION\b', 'Partition', sql, flags=re.IGNORECASE)
        return sql

    def _clean_formatted_select(self, formatted: str) -> str:
        """清理 _call_formatter 的输出，移除分号和多余空行"""
        lines = formatted.split('\n')
        # 移除最后的空行和分号行
        while lines and (not lines[-1].strip() or lines[-1].strip() == ';'):
            lines.pop()

        # 移除开头的空行
        while lines and not lines[0].strip():
            lines.pop(0)

        return '\n'.join(lines)
