# -*- coding: utf-8 -*-
r"""
SQL Formatter V5 - New Architecture Entry Point

This is the new formatter entry point that:
1. Uses SQLClassifier to identify SQL syntax types
2. Dispatches to appropriate processors based on classification
3. Falls back to formatter_v4_fixed for basic SELECT statements

Architecture:
- SQLClassifier: Identifies syntax types (set_operations, data_operations, etc.)
- SetOperationsProcessor: Handles UNION/INTERSECT/EXCEPT/MINUS
- WindowFunctionsProcessor: Handles OVER/PARTITION BY/Window Frames
- DataOperationsProcessor: Handles MERGE/INSERT OVERWRITE
- AdvancedTransformsProcessor: Handles LATERAL VIEW/CLUSTER BY/DISTRIBUTE BY
- formatter_v4_fixed: Handles basic SELECT statements (default)
"""

from typing import Literal, List

# 使用相对导入
from parser.sql_classifier import SQLClassifier
from processors.set_operations import SetOperationsProcessor
from processors.window_functions import WindowFunctionsProcessor
from processors.data_operations import DataOperationsProcessor
from processors.advanced_transforms import AdvancedTransformsProcessor
from formatter_v4_fixed import format_sql_v4_fixed


def format_sql_v5(
    sql: str,
    keyword_case: Literal['upper', 'lower', 'capitalize'] = 'upper'
) -> str:
    r"""
    Format SQL using the new architecture approach.

    This function:
    1. Classifies the SQL to identify syntax types
    2. Dispatches to appropriate processor based on classification
    3. Falls back to formatter_v4_fixed for basic SELECT statements

    Args:
        sql: The SQL statement to format
        keyword_case: Keyword case convention ('upper', 'lower', 'capitalize')

    Returns:
        Formatted SQL string

    Examples:
        >>> sql = "SELECT a FROM t1 UNION ALL SELECT b FROM t2"
        >>> formatted = format_sql_v5(sql)
        >>> print(formatted)
        SELECT a
             , b
        FROM t1
        UNION ALL
        SELECT b
             , c
        FROM t2

        >>> sql = "SELECT a, b FROM t1 WHERE c = 1"
        >>> formatted = format_sql_v5(sql, keyword_case='lower')
        >>> print(formatted)
        select a
             , b
        from t1
            where c = 1
    """
    if not sql or not sql.strip():
        return sql

    # Step 1: Classify the SQL
    syntax_types: List[str] = SQLClassifier.classify(sql)

    # Step 2: Dispatch to appropriate processor
    # Priority order (highest to lowest):
    # 1. data_operations (MERGE, INSERT OVERWRITE)
    # 2. set_operations (UNION, INTERSECT, EXCEPT, MINUS)
    # 3. window_functions (OVER clause)
    # 4. advanced_transforms (PIVOT, UNPIVOT, LATERAL VIEW)
    # 5. basic (default)

    if 'data_operations' in syntax_types:
        # Handle MERGE, INSERT OVERWRITE
        processor = DataOperationsProcessor()
        return processor.process(sql, keyword_case=keyword_case)

    elif 'set_operations' in syntax_types:
        # Handle UNION/INTERSECT/EXCEPT/MINUS
        processor = SetOperationsProcessor()
        return processor.process(sql, keyword_case=keyword_case)

    elif 'window_functions' in syntax_types:
        # Handle OVER clause, PARTITION BY, window frames
        processor = WindowFunctionsProcessor()
        return processor.process(sql, keyword_case=keyword_case)

    elif 'advanced_transforms' in syntax_types:
        # Handle PIVOT/UNPIVOT/LATERAL VIEW/CLUSTER BY/DISTRIBUTE BY
        processor = AdvancedTransformsProcessor()
        return processor.process(sql, keyword_case=keyword_case)

    else:
        # Basic SELECT statement - use formatter_v4_fixed
        return format_sql_v4_fixed(sql, keyword_case=keyword_case)


# Compatibility alias for gradual migration
format_sql_v5_new = format_sql_v5
