# -*- coding: utf-8 -*-
"""
SQL Formatter V4 - With Comment Preservation
Wraps formatter_v3 with comment preservation capability.
"""
from formatter_v3 import format_sql_v3, SQLFormatterV3
from comment_preserver import CommentPreserver


def format_sql_v4(sql: str, **options) -> str:
    """
    Format SQL while preserving comments.

    This is a wrapper around formatter_v3 that:
    1. Extracts comments from original SQL
    2. Replaces comments with placeholders
    3. Formats the SQL using v3
    4. Inserts comments back into formatted result

    Args:
        sql: Original SQL string (may contain comments)
        **options: Options passed to formatter_v3
            - keyword_case: upper/lower (default upper)
            - newline: semicolon on new line (default True)
            - semicolon: semicolon on new line (default True)

    Returns:
        Formatted SQL with comments preserved
    """
    preserver = CommentPreserver()

    # Step 1: Extract comments
    comments = preserver.extract_comments(sql)

    # Step 2: Replace with placeholders
    sql_clean = preserver.replace_with_placeholders(sql)

    # Step 3: Format using v3
    formatted = format_sql_v3(sql_clean, **options)

    # Step 4: Insert comments back
    result = preserver.insert_comments(formatted, sql)

    return result


class SQLFormatterV4(SQLFormatterV3):
    """
    SQL Formatter V4 - Extends V3 with comment preservation.
    """

    def __init__(self, indent_spaces: int = 4, max_line_length: int = 250):
        super().__init__(indent_spaces, max_line_length)
        self._preserver = CommentPreserver()

    def format(self, sql: str, **options) -> str:
        """Format SQL while preserving comments"""
        # Extract comments
        self._preserver.extract_comments(sql)

        # Replace with placeholders
        sql_clean = self._preserver.replace_with_placeholders(sql)

        # Format using parent class
        formatted = super().format(sql_clean, **options)

        # Insert comments back
        return self._preserver.insert_comments(formatted, sql)
