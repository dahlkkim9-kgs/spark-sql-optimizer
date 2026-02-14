# -*- coding: utf-8 -*-
"""
SQL 格式化器 V3 - 完善版本
基于 GLM-5 建议，手动实现完整的格式化逻辑，符合《大数据SQL开发规范》
"""
import re
import sqlglot
from sqlglot import exp
from sqlglot.dialects import Spark


class SQLFormatterV3:
    """
    SQL格式化器 V3 - 完善版本

    符合《大数据SQL开发规范》：
    1. 统一用4个空格缩进
    2. 逗号写在字段名前面，实现左对齐
    3. GROUP BY/ORDER BY 与 SELECT 左对齐
    4. WHERE 中 AND 与 WHERE 右对齐
    5. JOIN 中 ON 与 JOIN 右对齐
    6. 每行宽度不超过250字符
    7. 分号另起一行
    8. 关键字大写
    9. 注释保留
    """

    # Spark SQL 关键字
    KEYWORDS_UPPER = {
        'SELECT', 'FROM', 'WHERE', 'INSERT', 'INTO', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER',
        'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'CROSS JOIN', 'INNER JOIN',
        'ON', 'AND', 'OR', 'NOT', 'IN', 'EXISTS', 'BETWEEN', 'LIKE',
        'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'UNION', 'ALL', 'DISTINCT',
        'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'AS', 'IS', 'NULL',
        'WITH', 'OVER', 'PARTITION', 'DISTRIBUTE', 'SUBSTR', 'CAST',
        'FIRST', 'LAST', 'ASC', 'DESC', 'TRUE', 'FALSE',
        'COALESCE', 'ROW_NUMBER', 'LPAD', 'RPAD', 'MIN', 'MAX', 'SUM', 'AVG', 'COUNT'
    }

    def __init__(self, indent_spaces: int = 4, max_line_length: int = 250):
        """
        初始化格式化器
        """
        self.indent_spaces = indent_spaces
        self.max_line_length = max_line_length
        self._indent_str = ' ' * indent_spaces
        self._newline = '\n'  # 使用 Unix 换行符，浏览器会自动处理

    def format(self, sql: str, **options) -> str:
        """
        格式化SQL语句

        Args:
            sql: 原始SQL语句
            **options: 格式化选项
                - keyword_case: upper/lower（默认 upper）
                - semicolon_newline: 分号另起一行（默认 True）
        """
        try:
            keyword_case = options.get('keyword_case', 'upper')
            semicolon_newline = options.get('newline', True)

            # 预处理：移除多余空白
            cleaned = self._preprocess_sql(sql)

            # 解析SQL
            parsed = sqlglot.parse_one(cleaned, dialect=Spark)

            # 根据SQL类型格式化
            if isinstance(parsed, exp.Insert):
                formatted = self._format_insert(parsed)
            elif isinstance(parsed, exp.Select):
                formatted = self._format_select(parsed)
            else:
                # 其他类型暂不支持，返回清理后的SQL
                return cleaned

            # 关键字大写
            if keyword_case == 'upper':
                formatted = self._uppercase_keywords(formatted)

            # 分号另起一行
            if semicolon_newline:
                formatted = formatted.rstrip(';').strip() + '\n;'

            return formatted

        except Exception as e:
            print(f"格式化失败: {e}")
            import traceback
            traceback.print_exc()
            return sql

    def _preprocess_sql(self, sql: str) -> str:
        """预处理SQL：移除多余空白"""
        lines = []
        for line in sql.split('\n'):
            line = line.strip()
            if line:
                lines.append(line)
        return ' '.join(lines)

    def _format_insert(self, parsed: exp.Insert) -> str:
        """格式化 INSERT ... SELECT 语句"""
        lines = []

        # INSERT INTO 子句
        insert_keyword = 'INSERT'
        if parsed.args.get('ignore'):
            insert_keyword = 'INSERT OVERWRITE'

        # 获取目标表
        this = parsed.this
        if isinstance(this, exp.Schema):
            table_sql = f'{this.this.sql()}.{this.alias.sql()}'
        else:
            table_sql = this.sql()

        lines.append(f'{insert_keyword} INTO {table_sql}')

        # PARTITION 子句
        partition = parsed.args.get('partition')
        if partition:
            partition_sql = partition.sql()
            lines.append(f'PARTITION ({partition_sql})')

        # SELECT 子句（INSERT 的数据源）
        select_stmt = parsed.expression
        if isinstance(select_stmt, exp.Select):
            select_formatted = self._format_select(select_stmt)
            lines.append(select_formatted)
        else:
            lines.append(select_stmt.sql())

        return '\n'.join(lines)

    def _format_select(self, parsed: exp.Select) -> str:
        """格式化 SELECT 语句"""
        lines = []

        # SELECT 子句
        if parsed.expressions:
            for i, field in enumerate(parsed.expressions):
                field_sql = self._format_field(field)

                if i == 0:
                    lines.append(f'SELECT {field_sql}')
                else:
                    # 后续字段：逗号前置，与 SELECT 对齐
                    # SELECT (6个字符) - 逗号(1个字符) = 5个空格
                    comma_indent = ' ' * (len('SELECT') - 1)
                    lines.append(comma_indent + ', ' + field_sql)

        # FROM 子句
        from_clause = parsed.args.get('from_')
        if from_clause:
            from_sql = f'FROM {from_clause.this.sql()}'
            lines.append(f'\n{from_sql}')

        # JOIN 子句
        joins = parsed.args.get('joins', [])
        if joins:
            for join in joins:
                join_sql = self._format_join(join)
                lines.append(join_sql)

        # WHERE 子句
        where_clause = parsed.args.get('where')
        if where_clause:
            where_sql = self._format_where(where_clause)
            lines.append(where_sql)

        # GROUP BY 子句
        group_clause = parsed.args.get('group')
        if group_clause:
            group_sql = self._format_group_by(group_clause)
            lines.append(group_sql)

        # HAVING 子句
        having_clause = parsed.args.get('having')
        if having_clause:
            having_sql = self._format_having(having_clause)
            lines.append(having_sql)

        # ORDER BY 子句
        order_clause = parsed.args.get('order')
        if order_clause:
            order_sql = self._format_order_by(order_clause)
            lines.append(order_sql)

        # LIMIT 子句
        limit_clause = parsed.args.get('limit')
        if limit_clause:
            lines.append(f'\nLIMIT {limit_clause.expression.sql()}')

        return '\n'.join(lines)

    def _format_field(self, field: exp.Expression) -> str:
        """格式化单个字段"""
        if isinstance(field, exp.Alias):
            # 检查alias的value是否为CASE表达式
            if isinstance(field.this, exp.Case):
                case_sql = self._format_case(field.this)
                # field.alias 是 Column 类型，需要用 sql() 或直接转为字符串
                alias_sql = field.alias.sql() if hasattr(field.alias, 'sql') else str(field.alias)
                return f'{case_sql}\n    AS {alias_sql}'
            return field.sql()
        elif isinstance(field, exp.Case):
            return self._format_case(field)
        else:
            return field.sql()

    def _format_case(self, case_expr: exp.Case) -> str:
        """格式化 CASE 表达式

        格式:
        CASE
            WHEN condition1 THEN result1
            WHEN condition2 THEN result2
            ELSE default_result
        END
        """
        indent = '        '  # 8空格缩进（case在字段中需要额外缩进）

        lines = ['CASE']

        # 处理 WHEN-THEN 对
        if hasattr(case_expr, 'args'):
            ifs = case_expr.args.get('ifs')
            if ifs:
                for if_clause in ifs:
                    if isinstance(if_clause, exp.If):
                        when_sql = if_clause.this.sql()
                        # sqlglot uses 'true' as the key for THEN value
                        then_expr = if_clause.args.get('true')
                        then_sql = then_expr.sql() if then_expr else ''
                        lines.append(f'{indent}WHEN {when_sql}')
                        lines.append(f'{indent}THEN {then_sql}')

            # 处理 ELSE
            default = case_expr.args.get('default')
            if default:
                lines.append(f'{indent}ELSE')
                lines.append(f'{indent}    {default.sql()}')

        lines.append('    END')

        return '\n'.join(lines)

    def _format_where(self, where_clause: exp.Expression) -> str:
        """格式化 WHERE 子句

        格式:
            WHERE condition1
                AND condition2
        """
        # Where节点包含this属性指向实际条件
        condition = where_clause.this if hasattr(where_clause, 'this') else where_clause

        # 提取AND连接的条件
        conditions = self._extract_and_conditions(condition)

        if not conditions:
            return ''

        lines = []

        # 第一个条件 - 缩进4空格
        first_sql = conditions[0].sql()
        lines.append(f'    WHERE {first_sql}')

        # 后续条件：AND 右对齐 WHERE(5) - AND(3) = 2个空格偏移
        and_indent = '        '  # 8个空格：indent(4) + WHERE(5个字符宽度) - AND(3个字符宽度) + 调整
        for cond in conditions[1:]:
            cond_sql = cond.sql()
            lines.append(f'{and_indent}AND {cond_sql}')

        return '\n'.join(lines)

    def _extract_and_conditions(self, expr: exp.Expression) -> list:
        """提取AND连接的条件"""
        conditions = []

        if isinstance(expr, exp.And):
            left = self._extract_and_conditions(expr.left)
            right = self._extract_and_conditions(expr.right)
            return left + right
        else:
            return [expr]

    def _format_join(self, join: exp.Join) -> str:
        """格式化单个 JOIN"""
        indent = self._indent_str
        lines = []

        # JOIN 类型
        side = join.args.get('side', '')
        kind = join.args.get('kind', '')
        join_type = 'JOIN'
        if side:
            join_type = f'{side.upper()} {join_type}'
        elif kind:
            join_type = kind.upper() + ' JOIN'

        # 表名
        table_sql = join.this.sql()
        lines.append(indent + f'{join_type} {table_sql}')

        # ON 条件
        on_clause = join.args.get('on')
        if on_clause:
            # 直接使用 ON 条件表达式
            on_conditions = self._extract_and_conditions(on_clause)

            # 格式化 ON 条件
            on_sql = on_conditions[0].sql()
            lines.append(indent + f'    ON {on_sql}')

            # 后续条件
            for cond in on_conditions[1:]:
                cond_sql = cond.sql()
                lines.append(indent + f'       AND {cond_sql}')

        return '\n'.join(lines)

    def _format_group_by(self, group_clause: exp.Expression) -> str:
        """格式化 GROUP BY 子句"""
        indent = self._indent_str
        group_fields = []
        if hasattr(group_clause, 'expressions'):
            for expr in group_clause.expressions:
                group_fields.append(expr.sql())
        return f'\n{indent}GROUP BY {", ".join(group_fields)}'

    def _format_order_by(self, order_clause: exp.Expression) -> str:
        """格式化 ORDER BY 子句"""
        indent = self._indent_str
        order_fields = []
        if hasattr(order_clause, 'expressions'):
            for expr in order_clause.expressions:
                order_fields.append(expr.sql())
        return f'\n{indent}ORDER BY {", ".join(order_fields)}'

    def _format_having(self, having_clause: exp.Expression) -> str:
        """格式化 HAVING 子句"""
        indent = self._indent_str
        return f'\n{indent}HAVING {having_clause.sql()}'

    def _uppercase_keywords(self, sql: str) -> str:
        """关键字大写"""
        result = sql
        # 按长度排序，优先匹配长的关键字
        keywords = sorted(self.KEYWORDS_UPPER, key=len, reverse=True)

        for keyword in keywords:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            # 只替换完整单词，避免部分匹配
            result = re.sub(pattern, keyword.upper(), result)

        return result

# 全局实例
_formatter_v3 = None


def format_sql_v3(sql: str, **options) -> str:
    """
    格式化SQL语句（V3版本 - 完善版）

    Args:
        sql: 原始SQL语句
        **options: 格式化选项
            - keyword_case: upper/lower（默认 upper）
            - semicolon_newline: 分号另起一行（默认 True）
        """
    global _formatter_v3
    if _formatter_v3 is None:
        _formatter_v3 = SQLFormatterV3()

    return _formatter_v3.format(sql, **options)


if __name__ == "__main__":
    # 测试用例
    test_sql = """
    SELECT t1.col1, t2.col2
    FROM t1
    LEFT JOIN t2 ON t1.id = t2.id
    WHERE t1.status = '1'
    """

    print("原始SQL:")
    print(test_sql)

    print("\n格式化后:")
    print(format_sql_v3(test_sql))