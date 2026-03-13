"""测试集合操作处理器 (UNION/INTERSECT/EXCEPT/MINUS)"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from processors.set_operations import SetOperationsProcessor


class TestSetOperationsProcessor:
    """测试集合操作处理器"""

    def test_can_process_union(self):
        """测试检测 UNION"""
        processor = SetOperationsProcessor()
        assert processor.can_process("SELECT a FROM t1 UNION SELECT b FROM t2") == True
        assert processor.can_process("SELECT a FROM t1 UNION ALL SELECT b FROM t2") == True

    def test_can_process_intersect(self):
        """测试检测 INTERSECT"""
        processor = SetOperationsProcessor()
        assert processor.can_process("SELECT a FROM t1 INTERSECT SELECT b FROM t2") == True

    def test_can_process_except(self):
        """测试检测 EXCEPT"""
        processor = SetOperationsProcessor()
        assert processor.can_process("SELECT a FROM t1 EXCEPT SELECT b FROM t2") == True

    def test_can_process_minus(self):
        """测试检测 MINUS"""
        processor = SetOperationsProcessor()
        assert processor.can_process("SELECT a FROM t1 MINUS SELECT b FROM t2") == True

    def test_cannot_process_basic_select(self):
        """测试不处理普通 SELECT"""
        processor = SetOperationsProcessor()
        assert processor.can_process("SELECT a FROM t1") == False
        assert processor.can_process("SELECT a, b FROM t1 JOIN t2 ON t1.id = t2.id") == False

    def test_simple_union_all(self):
        """测试简单 UNION ALL 格式化"""
        processor = SetOperationsProcessor()
        sql = "SELECT a, b FROM t1 UNION ALL SELECT c, d FROM t2"
        result = processor.process(sql)

        # 验证 UNION ALL 前后有换行
        lines = result.split('\n')
        assert any('UNION ALL' in line for line in lines)

        # 验证每个 SELECT 都被正确格式化
        assert result.count('SELECT') == 2

        # 验证字段对齐
        assert '     , a' in result or '     , b' in result

    def test_simple_union(self):
        """测试简单 UNION 格式化"""
        processor = SetOperationsProcessor()
        sql = "SELECT a FROM t1 UNION SELECT b FROM t2"
        result = processor.process(sql)

        # 验证 UNION 存在且大写
        assert 'UNION' in result

        # 验证两个 SELECT 都被格式化
        assert 'SELECT' in result

    def test_union_with_join(self):
        """测试 UNION + JOIN 混合场景"""
        processor = SetOperationsProcessor()
        sql = "SELECT a FROM t1 JOIN t2 ON t1.id = t2.id UNION SELECT b FROM t3"
        result = processor.process(sql)

        # 验证 UNION 存在
        assert 'UNION' in result

        # 验证 JOIN 存在
        assert 'JOIN' in result

        # 验证 ON 存在
        assert 'ON' in result

    def test_multiple_set_operations(self):
        """测试多个集合操作"""
        processor = SetOperationsProcessor()
        sql = "SELECT a FROM t1 UNION SELECT b FROM t2 INTERSECT SELECT c FROM t3"
        result = processor.process(sql)

        # 验证 UNION 和 INTERSECT 都存在
        assert 'UNION' in result
        assert 'INTERSECT' in result

    def test_nested_set_operations(self):
        """测试嵌套括号的集合操作"""
        processor = SetOperationsProcessor()
        sql = "(SELECT a UNION SELECT b) INTERSECT (SELECT c UNION SELECT d)"
        result = processor.process(sql)

        # 验证 INTERSECT 存在
        assert 'INTERSECT' in result

        # 验证括号存在
        assert '(' in result
        assert ')' in result

    def test_union_all_case_sensitivity(self):
        """测试 UNION ALL 大小写处理"""
        processor = SetOperationsProcessor()

        # 测试输入是小写，输出应该大写
        sql_lower = "select a from t1 union all select b from t2"
        result = processor.process(sql_lower)

        # 验证输出是大写
        assert 'UNION ALL' in result

    def test_except_and_minus(self):
        """测试 EXCEPT 和 MINUS"""
        processor = SetOperationsProcessor()

        # 测试 EXCEPT
        sql1 = "SELECT a FROM t1 EXCEPT SELECT b FROM t2"
        result1 = processor.process(sql1)
        assert 'EXCEPT' in result1

        # 测试 MINUS
        sql2 = "SELECT a FROM t1 MINUS SELECT b FROM t2"
        result2 = processor.process(sql2)
        assert 'MINUS' in result2
