# -*- coding: utf-8 -*-
"""测试窗口函数处理器 (OVER/PARTITION BY/window frames)"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from processors.window_functions import WindowFunctionsProcessor


class TestWindowFunctionsProcessor:
    """测试窗口函数处理器"""

    def test_can_process_over(self):
        """测试检测 OVER 子句"""
        processor = WindowFunctionsProcessor()
        assert processor.can_process("SELECT ROW_NUMBER() OVER (PARTITION BY dept) FROM employees") == True
        assert processor.can_process("SELECT SUM(amount) OVER (ORDER BY date) FROM sales") == True
        assert processor.can_process("SELECT RANK() OVER () FROM employees") == True

    def test_can_process_window_clause(self):
        """测试检测 WINDOW 子句"""
        processor = WindowFunctionsProcessor()
        assert processor.can_process("SELECT SUM(amount) OVER w FROM sales WINDOW w AS (ORDER BY date)") == True
        assert processor.can_process("SELECT ROW_NUMBER() OVER (PARTITION BY dept) FROM emp WINDOW my_win AS (PARTITION BY dept ORDER BY salary)") == True

    def test_cannot_process_basic_select(self):
        """测试不处理普通 SELECT"""
        processor = WindowFunctionsProcessor()
        assert processor.can_process("SELECT a FROM t1") == False
        assert processor.can_process("SELECT a, b FROM t1 JOIN t2 ON t1.id = t2.id") == False
        assert processor.can_process("SELECT COUNT(*) FROM t1 GROUP BY dept") == False

    def test_simple_over(self):
        """测试简单 OVER 格式化"""
        processor = WindowFunctionsProcessor()
        sql = "SELECT ROW_NUMBER() OVER (PARTITION BY dept ORDER BY salary DESC) FROM employees"
        result = processor.process(sql)

        # 验证关键字存在
        assert 'OVER' in result
        assert 'PARTITION BY' in result
        assert 'ORDER BY' in result

        # 验证换行和缩进
        lines = result.split('\n')
        # OVER ( 应该在一行
        assert any('OVER (' in line for line in lines)
        # 应该有独立行
        assert len(lines) > 1

    def test_partition_by(self):
        """测试 PARTITION BY 格式化"""
        processor = WindowFunctionsProcessor()
        sql = "SELECT ROW_NUMBER() OVER (PARTITION BY dept) FROM employees"
        result = processor.process(sql)

        # 验证 PARTITION BY 存在
        assert 'PARTITION BY' in result
        assert 'dept' in result

    def test_partition_by_multiple_columns(self):
        """测试多列 PARTITION BY"""
        processor = WindowFunctionsProcessor()
        sql = "SELECT ROW_NUMBER() OVER (PARTITION BY dept, section, team) FROM employees"
        result = processor.process(sql)

        # 验证所有列都存在
        assert 'dept' in result
        assert 'section' in result
        assert 'team' in result
        # 验证逗号对齐
        assert '     ,' in result or '\n,' in result

    def test_order_by(self):
        """测试 ORDER BY 格式化"""
        processor = WindowFunctionsProcessor()
        sql = "SELECT SUM(amount) OVER (ORDER BY date) FROM sales"
        result = processor.process(sql)

        # 验证 ORDER BY 存在
        assert 'ORDER BY' in result
        assert 'date' in result

    def test_order_by_desc(self):
        """测试 ORDER BY DESC"""
        processor = WindowFunctionsProcessor()
        sql = "SELECT ROW_NUMBER() OVER (ORDER BY salary DESC) FROM employees"
        result = processor.process(sql)

        # 验证 ORDER BY 和 DESC 存在
        assert 'ORDER BY' in result
        assert 'DESC' in result
        assert 'salary' in result

    def test_window_frame(self):
        """测试窗口框架格式化"""
        processor = WindowFunctionsProcessor()
        sql = "SELECT SUM(amount) OVER (ORDER BY date ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING) FROM sales"
        result = processor.process(sql)

        # 验证窗口框架关键字存在
        assert 'ROWS BETWEEN' in result
        assert 'PRECEDING' in result
        assert 'FOLLOWING' in result
        assert 'AND' in result

    def test_window_frame_unbounded(self):
        """测试 UNBOUNDED 窗口框架"""
        processor = WindowFunctionsProcessor()
        sql = "SELECT SUM(amount) OVER (ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) FROM sales"
        result = processor.process(sql)

        # 验证 UNBOUNDED 和 CURRENT ROW 存在
        assert 'UNBOUNDED' in result
        assert 'PRECEDING' in result
        assert 'CURRENT ROW' in result

    def test_window_frame_range(self):
        """测试 RANGE 窗口框架"""
        processor = WindowFunctionsProcessor()
        sql = "SELECT AVG(price) OVER (ORDER BY date RANGE BETWEEN INTERVAL 1 DAY PRECEDING AND CURRENT ROW) FROM prices"
        result = processor.process(sql)

        # 验证 RANGE BETWEEN 存在
        assert 'RANGE BETWEEN' in result

    def test_partition_by_and_order_by(self):
        """测试 PARTITION BY 和 ORDER BY 组合"""
        processor = WindowFunctionsProcessor()
        sql = "SELECT ROW_NUMBER() OVER (PARTITION BY dept ORDER BY salary DESC) FROM employees"
        result = processor.process(sql)

        # 验证两个子句都存在
        assert 'PARTITION BY' in result
        assert 'ORDER BY' in result
        assert 'dept' in result
        assert 'salary' in result

    def test_named_window(self):
        """测试命名窗口 (WINDOW 子句)"""
        processor = WindowFunctionsProcessor()
        sql = "SELECT SUM(amount) OVER w, AVG(amount) OVER w FROM sales WINDOW w AS (ORDER BY date)"
        result = processor.process(sql)

        # 验证 WINDOW 子句存在
        assert 'WINDOW' in result
        assert 'w AS' in result
        assert 'ORDER BY' in result

    def test_named_window_multiple(self):
        """测试多个命名窗口"""
        processor = WindowFunctionsProcessor()
        sql = """SELECT SUM(amount) OVER w1, AVG(amount) OVER w2 FROM sales
                 WINDOW w1 AS (PARTITION BY dept ORDER BY date),
                        w2 AS (PARTITION BY dept ORDER BY date ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING)"""
        result = processor.process(sql)

        # 验证两个窗口定义都存在
        assert 'w1' in result
        assert 'w2' in result
        assert 'WINDOW' in result

    def test_multiple_window_functions(self):
        """测试多个窗口函数"""
        processor = WindowFunctionsProcessor()
        sql = "SELECT ROW_NUMBER() OVER (PARTITION BY dept ORDER BY salary DESC), RANK() OVER (PARTITION BY dept ORDER BY salary DESC) FROM employees"
        result = processor.process(sql)

        # 验证两个窗口函数都被处理
        assert result.count('OVER') >= 2
        assert 'ROW_NUMBER' in result
        assert 'RANK' in result

    def test_nested_window_function(self):
        """测试嵌套窗口函数（窗口函数内嵌套聚合）"""
        processor = WindowFunctionsProcessor()
        sql = "SELECT SUM(COUNT(*)) OVER (PARTITION BY dept) FROM employees GROUP BY dept"
        result = processor.process(sql)

        # 验证基本结构正确
        assert 'OVER' in result
        assert 'PARTITION BY' in result

    def test_empty_over(self):
        """测试空 OVER 子句"""
        processor = WindowFunctionsProcessor()
        sql = "SELECT ROW_NUMBER() OVER () FROM employees"
        result = processor.process(sql)

        # 验证 OVER () 被保留
        assert 'OVER' in result

    def test_window_function_types(self):
        """测试各种窗口函数类型"""
        processor = WindowFunctionsProcessor()

        window_functions = [
            'ROW_NUMBER', 'RANK', 'DENSE_RANK', 'NTILE',
            'LEAD', 'LAG', 'FIRST_VALUE', 'LAST_VALUE',
            'SUM', 'AVG', 'MIN', 'MAX', 'COUNT'
        ]

        for func in window_functions[:5]:  # Test a few
            sql = f"SELECT {func}() OVER (ORDER BY date) FROM sales"
            result = processor.process(sql)
            assert func in result

    def test_case_sensitivity(self):
        """测试大小写处理"""
        processor = WindowFunctionsProcessor()

        # 小写输入
        sql_lower = "select row_number() over (partition by dept order by salary desc) from employees"
        result = processor.process(sql_lower, keyword_case='upper')

        # 验证关键字大写
        assert 'OVER' in result
        assert 'PARTITION BY' in result
        assert 'ORDER BY' in result

    def test_complex_window_spec(self):
        """测试复杂窗口规范"""
        processor = WindowFunctionsProcessor()
        sql = """SELECT ROW_NUMBER() OVER (
                    PARTITION BY dept, section
                    ORDER BY salary DESC, hire_date ASC
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                 ) FROM employees"""
        result = processor.process(sql)

        # 验证所有部分都存在
        assert 'PARTITION BY' in result
        assert 'ORDER BY' in result
        assert 'ROWS BETWEEN' in result
        assert 'UNBOUNDED PRECEDING' in result
        assert 'CURRENT ROW' in result

    def test_window_with_aggregate(self):
        """测试窗口函数与聚合函数结合"""
        processor = WindowFunctionsProcessor()
        sql = "SELECT dept, SUM(salary) AS total_salary, ROW_NUMBER() OVER (ORDER BY SUM(salary) DESC) FROM employees GROUP BY dept"
        result = processor.process(sql)

        # 验证聚合和窗口函数都存在
        assert 'SUM(salary)' in result or 'SUM (salary)' in result
        assert 'OVER' in result
        assert 'ORDER BY' in result

    def test_lead_lag_functions(self):
        """测试 LEAD/LAG 函数"""
        processor = WindowFunctionsProcessor()
        sql = "SELECT LEAD(salary, 1) OVER (PARTITION BY dept ORDER BY salary), LAG(salary, 1) OVER (PARTITION BY dept ORDER BY salary) FROM employees"
        result = processor.process(sql)

        # 验证 LEAD 和 LAG 都存在
        assert 'LEAD' in result
        assert 'LAG' in result
        assert 'OVER' in result
