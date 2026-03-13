# -*- coding: utf-8 -*-
"""测试数据操作处理器 (MERGE/INSERT OVERWRITE)"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from processors.data_operations import DataOperationsProcessor


class TestDataOperationsProcessor:
    """测试数据操作处理器"""

    def test_can_process_merge(self):
        """测试检测 MERGE"""
        processor = DataOperationsProcessor()
        assert processor.can_process("MERGE INTO target USING source ON target.id = source.id") == True
        assert processor.can_process("  merge into target using source on t.id = s.id") == True

    def test_can_process_insert_overwrite(self):
        """测试检测 INSERT OVERWRITE"""
        processor = DataOperationsProcessor()
        assert processor.can_process("INSERT OVERWRITE TABLE target SELECT * FROM source") == True
        assert processor.can_process("INSERT OVERWRITE target SELECT * FROM source") == True

    def test_cannot_process_basic_select(self):
        """测试不处理普通 SELECT"""
        processor = DataOperationsProcessor()
        assert processor.can_process("SELECT a FROM t1") == False
        assert processor.can_process("SELECT a, b FROM t1 JOIN t2 ON t1.id = t2.id") == False

    def test_cannot_process_simple_insert(self):
        """测试不处理简单 INSERT（非 OVERWRITE）"""
        processor = DataOperationsProcessor()
        assert processor.can_process("INSERT INTO target SELECT * FROM source") == False

    def test_simple_merge(self):
        """测试简单 MERGE 格式化"""
        processor = DataOperationsProcessor()
        sql = """MERGE INTO target USING source ON target.id = source.id WHEN MATCHED THEN UPDATE SET target.val = source.val WHEN NOT MATCHED THEN INSERT (id, val) VALUES (source.id, source.val)"""
        result = processor.process(sql)

        # 验证关键字存在
        assert 'MERGE INTO' in result
        assert 'USING' in result
        assert 'ON' in result
        assert 'WHEN MATCHED THEN' in result
        assert 'WHEN NOT MATCHED THEN' in result

        # 验证换行
        lines = result.split('\n')
        assert len(lines) >= 6  # 至少 6 行

        # 验证缩进
        assert '    UPDATE SET' in result or '    UPDATE' in result

    def test_merge_with_delete(self):
        """测试 MERGE with DELETE"""
        processor = DataOperationsProcessor()
        sql = """MERGE INTO target USING source ON target.id = source.id WHEN MATCHED AND target.is_deleted = 1 THEN DELETE WHEN NOT MATCHED THEN INSERT (id) VALUES (source.id)"""
        result = processor.process(sql)

        # 验证 DELETE 存在
        assert 'DELETE' in result

        # 验证 AND 条件存在
        assert 'AND' in result

    def test_merge_with_multiple_when_clauses(self):
        """测试 MERGE with multiple WHEN clauses"""
        processor = DataOperationsProcessor()
        sql = """MERGE INTO target USING source ON target.id = source.id WHEN MATCHED AND target.type = 'A' THEN UPDATE SET target.val = source.val WHEN MATCHED AND target.type = 'B' THEN DELETE WHEN NOT MATCHED THEN INSERT (id) VALUES (source.id)"""
        result = processor.process(sql)

        # 验证多个 WHEN 分支
        assert result.count('WHEN') >= 3

    def test_insert_overwrite(self):
        """测试 INSERT OVERWRITE 格式化"""
        processor = DataOperationsProcessor()
        sql = "INSERT OVERWRITE TABLE target SELECT a, b, c FROM source WHERE d = 1"
        result = processor.process(sql)

        # 验证关键字存在
        assert 'INSERT OVERWRITE' in result
        assert 'SELECT' in result
        assert 'FROM' in result

        # 验证换行
        lines = result.split('\n')
        assert len(lines) >= 3

    def test_insert_overwrite_without_table_keyword(self):
        """测试 INSERT OVERWRITE without TABLE keyword"""
        processor = DataOperationsProcessor()
        sql = "INSERT OVERWRITE target SELECT a, b FROM source"
        result = processor.process(sql)

        # 验证关键字存在
        assert 'INSERT OVERWRITE' in result
        assert 'SELECT' in result

    def test_insert_overwrite_with_partition(self):
        """测试 INSERT OVERWRITE with PARTITION"""
        processor = DataOperationsProcessor()
        sql = "INSERT OVERWRITE TABLE target PARTITION (dt='2024-01-01') SELECT a, b FROM source"
        result = processor.process(sql)

        # 验证 PARTITION 存在
        assert 'PARTITION' in result

    def test_merge_case_sensitivity(self):
        """测试 MERGE 大小写处理"""
        processor = DataOperationsProcessor()

        # 测试输入是小写，输出应该大写（默认）
        sql_lower = "merge into target using source on t.id = s.id when matched then update set t.val = s.val"
        result = processor.process(sql_lower)

        # 验证输出是大写
        assert 'MERGE INTO' in result
        assert 'USING' in result
        assert 'ON' in result
        assert 'WHEN MATCHED THEN' in result

    def test_merge_lower_case(self):
        """测试 MERGE 输出小写"""
        processor = DataOperationsProcessor()
        sql = "MERGE INTO target USING source ON t.id = s.id WHEN MATCHED THEN UPDATE SET t.val = s.val"
        result = processor.process(sql, keyword_case='lower')

        # 验证输出是小写
        assert 'merge into' in result
        assert 'using' in result
        assert 'on' in result
        assert 'when matched then' in result

    def test_insert_overwrite_case_sensitivity(self):
        """测试 INSERT OVERWRITE 大小写处理"""
        processor = DataOperationsProcessor()

        # 测试输入是小写，输出应该大写（默认）
        sql_lower = "insert overwrite table target select a, b from source"
        result = processor.process(sql_lower)

        # 验证输出是大写
        assert 'INSERT OVERWRITE' in result
        assert 'TABLE' in result

    def test_insert_overwrite_lower_case(self):
        """测试 INSERT OVERWRITE 输出小写"""
        processor = DataOperationsProcessor()
        sql = "INSERT OVERWRITE TABLE target SELECT a, b FROM source"
        result = processor.process(sql, keyword_case='lower')

        # 验证输出是小写
        assert 'insert overwrite' in result
        assert result.count('table') > 0

    def test_complex_merge_with_subquery(self):
        """测试复杂 MERGE with subquery"""
        processor = DataOperationsProcessor()
        sql = """MERGE INTO target USING (SELECT id, val FROM source WHERE active = 1) src ON target.id = src.id WHEN MATCHED THEN UPDATE SET target.val = src.val"""
        result = processor.process(sql)

        # 验证关键字存在
        assert 'MERGE INTO' in result
        assert 'USING' in result
        assert 'ON' in result
        assert 'WHEN MATCHED THEN' in result

        # 验证子查询存在
        assert 'SELECT' in result

    def test_merge_with_string_literal(self):
        """测试 ON 条件中包含字符串字面量"""
        processor = DataOperationsProcessor()
        sql = "MERGE INTO target USING src ON target.name = 'WHEN xyz' WHEN MATCHED THEN DELETE"
        result = processor.process(sql)

        # 验证字符串字面量被保留
        assert "'WHEN xyz'" in result
        # 验证 WHEN 关键字仍然存在
        assert "WHEN MATCHED" in result
        # 验证基本结构
        assert "MERGE INTO" in result
        assert "USING" in result
        assert "ON" in result

    def test_merge_with_double_quoted_string(self):
        """测试 ON 条件中包含双引号字符串字面量"""
        processor = DataOperationsProcessor()
        sql = 'MERGE INTO target USING src ON target.name = "WHEN xyz" WHEN MATCHED THEN DELETE'
        result = processor.process(sql)

        # 验证字符串字面量被保留
        assert '"WHEN xyz"' in result
        # 验证 WHEN 关键字仍然存在
        assert "WHEN MATCHED" in result

    def test_merge_with_escaped_quote(self):
        """测试 ON 条件中包含转义引号"""
        processor = DataOperationsProcessor()
        sql = r"MERGE INTO target USING src ON target.name = 'It\'s WHEN time' WHEN MATCHED THEN DELETE"
        result = processor.process(sql)

        # 验证字符串字面量被保留（转义字符可能被处理）
        assert "WHEN MATCHED" in result
        assert "MERGE INTO" in result

    def test_merge_with_single_line_comment(self):
        """测试 MERGE 语句包含单行注释"""
        processor = DataOperationsProcessor()
        sql = """MERGE INTO target
-- This is a comment
USING src ON t.id = src.id WHEN MATCHED THEN DELETE"""
        result = processor.process(sql)

        # 验证基本结构被保留
        assert "MERGE INTO" in result
        assert "USING" in result
        assert "WHEN MATCHED" in result
        # 验证注释被保留
        assert "-- This is a comment" in result

    def test_merge_with_multi_line_comment(self):
        """测试 MERGE 语句包含多行注释"""
        processor = DataOperationsProcessor()
        sql = """MERGE INTO target
/* This is a
multi-line comment */
USING src ON t.id = src.id WHEN MATCHED THEN DELETE"""
        result = processor.process(sql)

        # 验证基本结构被保留
        assert "MERGE INTO" in result
        assert "USING" in result
        assert "WHEN MATCHED" in result
        # 验证注释被保留
        assert "/*" in result
        assert "*/" in result
        assert "multi-line comment" in result

    def test_merge_with_comment_in_when(self):
        """测试 WHEN 子句中包含注释"""
        processor = DataOperationsProcessor()
        sql = """MERGE INTO target USING src ON t.id = src.id
-- Update matched records
WHEN MATCHED THEN UPDATE SET t.val = src.val"""
        result = processor.process(sql)

        # 验证基本结构被保留
        assert "MERGE INTO" in result
        assert "USING" in result
        assert "WHEN MATCHED" in result
        assert "UPDATE" in result
        # 验证注释被保留
        assert "-- Update matched records" in result
