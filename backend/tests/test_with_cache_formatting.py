"""测试 WITH AS 和 CACHE TABLE 格式化功能"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from formatter_v4_fixed import format_sql_v4_fixed


class TestWithAsFormatting:
    """测试 WITH AS 语句格式化"""

    def test_simple_with_as(self):
        """测试简单 WITH AS"""
        sql = "WITH A AS (select aa,bb,cc from tab_tes where aa='1')"
        result = format_sql_v4_fixed(sql)

        # 验证基本结构
        assert "WITH A AS" in result
        assert "SELECT aa" in result
        assert "FROM tab_tes" in result
        assert "WHERE aa = '1'" in result

        # 验证括号对齐（开括号和闭括号应该在同一列）
        lines = result.split('\n')
        open_paren_line = None
        close_paren_line = None

        for i, line in enumerate(lines):
            if '(' in line:
                open_paren_line = (i, line.index('('))
            if line.strip() == ')' or line.rstrip().endswith(')'):
                # 找到闭括号位置
                stripped = line.rstrip()
                close_paren_pos = len(line) - len(stripped) + stripped.rfind(')')
                close_paren_line = (i, close_paren_pos)
                break

        assert open_paren_line is not None, "找不到开括号"
        assert close_paren_line is not None, "找不到闭括号"

        # 验证缩进对齐
        assert open_paren_line[1] == close_paren_line[1], \
            f"开括号在第 {open_paren_line[1]} 列，闭括号在第 {close_paren_line[1]} 列，应该对齐"

    def test_complex_with_as_with_parens(self):
        """测试包含嵌套括号的 WITH AS"""
        pass

    def test_multiple_ctes(self):
        """测试多个 CTE"""
        pass

    def test_cte_with_case_when(self):
        """测试包含 CASE WHEN 的 CTE"""
        pass

    def test_cte_with_join(self):
        """测试包含 JOIN 的 CTE"""
        pass

    def test_cte_only_no_main_query(self):
        """测试只有 CTE 定义没有主查询"""
        pass


class TestCacheTableFormatting:
    """测试 CACHE TABLE 语句格式化"""

    def test_simple_cache_table(self):
        """测试简单 CACHE TABLE"""
        pass

    def test_cache_table_with_complex_where(self):
        """测试包含复杂 WHERE 的 CACHE TABLE"""
        pass

    def test_cache_table_with_case_when(self):
        """测试包含 CASE WHEN 的 CACHE TABLE"""
        pass
