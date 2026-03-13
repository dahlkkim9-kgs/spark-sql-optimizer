# -*- coding: utf-8 -*-
"""
Unit tests for SQL Classifier
"""

import pytest
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.parser.sql_classifier import SQLClassifier


class TestSQLClassifier:
    """Test cases for SQLClassifier"""

    def test_classify_union(self):
        """Test UNION detection"""
        # UNION ALL
        sql = """
        SELECT a, b FROM t1
        UNION ALL
        SELECT c, d FROM t2
        """
        result = SQLClassifier.classify(sql)
        assert 'set_operations' in result

        # UNION (without ALL)
        sql = """
        SELECT a, b FROM t1
        UNION
        SELECT c, d FROM t2
        """
        result = SQLClassifier.classify(sql)
        assert 'set_operations' in result

        # UNION with different case
        sql = "select * from t1 union select * from t2"
        result = SQLClassifier.classify(sql)
        assert 'set_operations' in result

    def test_classify_basic_select(self):
        """Test basic SELECT classification"""
        sql = """
        SELECT
            a,
            b,
            c
        FROM table1
        WHERE a > 10
        """
        result = SQLClassifier.classify(sql)
        assert result == ['basic']

        # SELECT with JOIN
        sql = """
        SELECT t1.a, t2.b
        FROM table1 t1
        JOIN table2 t2 ON t1.id = t2.id
        """
        result = SQLClassifier.classify(sql)
        assert result == ['basic']

    def test_classify_merge(self):
        """Test MERGE INTO detection"""
        sql = """
        MERGE INTO target_table AS target
        USING source_table AS source
        ON target.id = source.id
        WHEN MATCHED THEN
            UPDATE SET target.value = source.value
        """
        result = SQLClassifier.classify(sql)
        assert 'data_operations' in result

        # MERGE with different case
        sql = "merge into target using source on target.id = source.id"
        result = SQLClassifier.classify(sql)
        assert 'data_operations' in result

    def test_classify_insert_overwrite(self):
        """Test INSERT OVERWRITE detection"""
        sql = """
        INSERT OVERWRITE TABLE target_table
        SELECT * FROM source_table
        """
        result = SQLClassifier.classify(sql)
        assert 'data_operations' in result

        # INSERT OVERWRITE without TABLE keyword
        sql = "INSERT OVERWRITE target_table SELECT * FROM source"
        result = SQLClassifier.classify(sql)
        assert 'data_operations' in result

    def test_classify_window_function(self):
        """Test OVER clause detection"""
        sql = """
        SELECT
            a,
            ROW_NUMBER() OVER (PARTITION BY b ORDER BY c) AS rn
        FROM table1
        """
        result = SQLClassifier.classify(sql)
        assert 'window_functions' in result

        # WINDOW definition
        sql = """
        SELECT
            a,
            SUM(b) OVER w AS total
        FROM table1
        WINDOW w AS (PARTITION BY c)
        """
        result = SQLClassifier.classify(sql)
        assert 'window_functions' in result

    def test_classify_lateral_view(self):
        """Test LATERAL VIEW detection"""
        sql = """
        SELECT
            a,
            col
        FROM table1
        LATERAL VIEW EXPLODE(array_col) exploded_table AS col
        """
        result = SQLClassifier.classify(sql)
        assert 'advanced_transforms' in result

    def test_classify_pivot(self):
        """Test PIVOT detection"""
        sql = """
        SELECT * FROM table1
        PIVOT (
            SUM(value)
            FOR category IN ('A', 'B', 'C')
        )
        """
        result = SQLClassifier.classify(sql)
        assert 'advanced_transforms' in result

    def test_classify_unpivot(self):
        """Test UNPIVOT detection"""
        sql = """
        SELECT * FROM table1
        UNPIVOT (
            value FOR category IN (col_a, col_b, col_c)
        )
        """
        result = SQLClassifier.classify(sql)
        assert 'advanced_transforms' in result

    def test_classify_intersect(self):
        """Test INTERSECT detection"""
        sql = """
        SELECT a FROM t1
        INTERSECT
        SELECT a FROM t2
        """
        result = SQLClassifier.classify(sql)
        assert 'set_operations' in result

    def test_classify_except(self):
        """Test EXCEPT detection"""
        sql = """
        SELECT a FROM t1
        EXCEPT
        SELECT a FROM t2
        """
        result = SQLClassifier.classify(sql)
        assert 'set_operations' in result

    def test_classify_minus(self):
        """Test MINUS detection (Oracle-style)"""
        sql = """
        SELECT a FROM t1
        MINUS
        SELECT a FROM t2
        """
        result = SQLClassifier.classify(sql)
        assert 'set_operations' in result

    def test_classify_mixed_syntax(self):
        """Test mixed syntax detection"""
        # UNION with window functions
        sql = """
        SELECT
            a,
            ROW_NUMBER() OVER (ORDER BY b) AS rn
        FROM t1
        UNION ALL
        SELECT c, d FROM t2
        """
        result = SQLClassifier.classify(sql)
        assert 'set_operations' in result
        assert 'window_functions' in result

        # MERGE with window function (in subquery)
        sql = """
        MERGE INTO target USING (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY id) AS rn
            FROM source
        ) src ON target.id = src.id
        """
        result = SQLClassifier.classify(sql)
        assert 'data_operations' in result
        # Window function in subquery should also be detected
        assert 'window_functions' in result

    def test_classify_empty_sql(self):
        """Test empty SQL handling"""
        result = SQLClassifier.classify("")
        assert result == []

        result = SQLClassifier.classify("   ")
        assert result == []

        result = SQLClassifier.classify(None)
        assert result == []

    def test_get_primary_type(self):
        """Test get_primary_type method"""
        # Data operations should have highest priority
        sql = """
        MERGE INTO target USING (
            SELECT * FROM t1 UNION SELECT * FROM t2
        ) src ON target.id = src.id
        """
        result = SQLClassifier.get_primary_type(sql)
        assert result == 'data_operations'

        # Set operations higher than window functions
        sql = """
        SELECT ROW_NUMBER() OVER (ORDER BY a) FROM t1
        UNION
        SELECT b FROM t2
        """
        result = SQLClassifier.get_primary_type(sql)
        assert result == 'set_operations'

        # Window functions higher than advanced transforms
        sql = """
        SELECT a, ROW_NUMBER() OVER () AS rn
        FROM t1
        LATERAL VIEW EXPLODE(col) exploded AS a
        """
        result = SQLClassifier.get_primary_type(sql)
        assert result == 'window_functions'

        # Basic select
        sql = "SELECT * FROM t1"
        result = SQLClassifier.get_primary_type(sql)
        assert result == 'basic'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
