# -*- coding: utf-8 -*-
r"""测试高级转换处理器 (LATERAL VIEW/PIVOT/UNPIVOT/TRANSFORM/CLUSTER BY/DISTRIBUTE BY)"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from processors.advanced_transforms import AdvancedTransformsProcessor


class TestAdvancedTransformsProcessor:
    """测试高级转换处理器"""

    def test_can_process_lateral_view(self):
        """测试检测 LATERAL VIEW"""
        processor = AdvancedTransformsProcessor()
        assert processor.can_process("SELECT id FROM table LATERAL VIEW EXPLODE(col) AS alias") == True
        assert processor.can_process("SELECT * FROM page_views LATERAL VIEW JSON_TUPLE(json, 'a', 'b') AS x, y") == True

    def test_can_process_cluster_by(self):
        """测试检测 CLUSTER BY"""
        processor = AdvancedTransformsProcessor()
        assert processor.can_process("SELECT a FROM t CLUSTER BY a") == True
        assert processor.can_process("SELECT * FROM t WHERE x > 10 CLUSTER BY x") == True

    def test_can_process_distribute_by(self):
        """测试检测 DISTRIBUTE BY"""
        processor = AdvancedTransformsProcessor()
        assert processor.can_process("SELECT a FROM t DISTRIBUTE BY a") == True
        assert processor.can_process("SELECT * FROM t WHERE x > 10 DISTRIBUTE BY x") == True

    def test_cannot_process_basic_select(self):
        """测试不处理普通 SELECT"""
        processor = AdvancedTransformsProcessor()
        assert processor.can_process("SELECT a FROM t1") == False
        assert processor.can_process("SELECT a, b FROM t1 JOIN t2 ON t1.id = t2.id") == False

    def test_lateral_view(self):
        """测试 LATERAL VIEW 格式化"""
        processor = AdvancedTransformsProcessor()
        sql = "SELECT id, category FROM page_views LATERAL VIEW EXPLODE(pages) exploded_table AS category"
        result = processor.process(sql)

        # 验证 LATERAL VIEW 存在且大写
        assert 'LATERAL VIEW' in result
        # 验证 EXPLODE 存在
        assert 'EXPLODE' in result
        # 验证 AS 存在
        assert 'AS' in result

    def test_multiple_lateral_views(self):
        """测试多个 LATERAL VIEW"""
        processor = AdvancedTransformsProcessor()
        sql = """SELECT id FROM page_views
                 LATERAL VIEW EXPLODE(pages) exploded_table AS page
                 LATERAL VIEW EXPLODE(categories) cat_table AS category"""
        result = processor.process(sql)

        # 验证两个 LATERAL VIEW 都存在
        assert result.count('LATERAL VIEW') >= 2

    def test_lateral_view_outer(self):
        """测试 LATERAL VIEW OUTER"""
        processor = AdvancedTransformsProcessor()
        sql = "SELECT id FROM table LATERAL VIEW OUTER EXPLODE(col) AS alias"
        result = processor.process(sql)

        # 验证 LATERAL VIEW OUTER 存在
        assert 'LATERAL VIEW' in result
        assert 'OUTER' in result

    def test_lateral_view_json_tuple(self):
        """测试 LATERAL VIEW JSON_TUPLE"""
        processor = AdvancedTransformsProcessor()
        sql = "SELECT * FROM page_views LATERAL VIEW JSON_TUPLE(json, 'a', 'b') AS x, y"
        result = processor.process(sql)

        # 验证 JSON_TUPLE 存在
        assert 'JSON_TUPLE' in result
        # 验证 LATERAL VIEW 存在
        assert 'LATERAL VIEW' in result

    def test_cluster_by(self):
        """测试 CLUSTER BY 格式化"""
        processor = AdvancedTransformsProcessor()
        sql = "SELECT a, b FROM t1 WHERE c = 1 CLUSTER BY a"
        result = processor.process(sql)

        # 验证 CLUSTER BY 存在且大写
        assert 'CLUSTER BY' in result

    def test_distribute_by(self):
        """测试 DISTRIBUTE BY 格式化"""
        processor = AdvancedTransformsProcessor()
        sql = "SELECT a, b FROM t1 WHERE c = 1 DISTRIBUTE BY a"
        result = processor.process(sql)

        # 验证 DISTRIBUTE BY 存在且大写
        assert 'DISTRIBUTE BY' in result

    def test_lateral_view_case_sensitivity(self):
        """测试 LATERAL VIEW 大小写处理"""
        processor = AdvancedTransformsProcessor()

        # 测试输入是小写，输出应该大写
        sql_lower = "select id from table lateral view explode(col) as alias"
        result = processor.process(sql_lower)

        # 验证输出是大写
        assert 'LATERAL VIEW' in result
        assert 'EXPLODE' in result
        assert 'AS' in result

    def test_cluster_by_case_sensitivity(self):
        """测试 CLUSTER BY 大小写处理"""
        processor = AdvancedTransformsProcessor()

        # 测试输入是小写
        sql_lower = "select a from t cluster by a"
        result = processor.process(sql_lower)

        # 验证输出是大写
        assert 'CLUSTER BY' in result

    def test_lateral_view_with_where(self):
        """测试 LATERAL VIEW + WHERE 子句"""
        processor = AdvancedTransformsProcessor()
        sql = "SELECT id FROM page_views WHERE timestamp > '2020-01-01' LATERAL VIEW EXPLODE(pages) AS page"
        result = processor.process(sql)

        # 验证 LATERAL VIEW 存在
        assert 'LATERAL VIEW' in result
        # 验证 WHERE 存在
        assert 'WHERE' in result

    def test_lateral_view_with_join(self):
        """测试 LATERAL VIEW + JOIN"""
        processor = AdvancedTransformsProcessor()
        sql = """SELECT t1.id, t2.category
                 FROM page_views t1
                 JOIN categories t2 ON t1.cat_id = t2.id
                 LATERAL VIEW EXPLODE(t1.pages) AS page"""
        result = processor.process(sql)

        # 验证 LATERAL VIEW 存在
        assert 'LATERAL VIEW' in result
        # 验证 JOIN 存在
        assert 'JOIN' in result

    def test_formatter_v5_integration(self):
        """测试 formatter_v5 集成"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
        from formatter_v5 import format_sql_v5

        # 测试 LATERAL VIEW
        sql = "SELECT id FROM page_views LATERAL VIEW EXPLODE(pages) AS page"
        result = format_sql_v5(sql)

        # 验证 LATERAL VIEW 存在
        assert 'LATERAL VIEW' in result

        # 测试 CLUSTER BY
        sql = "SELECT a FROM t CLUSTER BY a"
        result = format_sql_v5(sql)

        # 验证 CLUSTER BY 存在
        assert 'CLUSTER BY' in result
