# -*- coding: utf-8 -*-
"""
Comment Preserver - Extracts and re-inserts comments during SQL formatting
"""
import re

class CommentPreserver:
    """
    Handles comment preservation during SQL formatting.

    Works in three phases:
    1. extract_comments() - Extract all comments with position info
    2. replace_with_placeholders() - Replace comments with unique placeholders
    3. insert_comments() - Insert comments back into formatted SQL
    """

    def __init__(self):
        self._comments = []
        self._placeholder_prefix = "___COMMENT_"
        self._placeholder_suffix = "___"

    def reset(self):
        """Reset internal state for a new SQL string"""
        self._comments = []

    def extract_comments(self, sql: str) -> list:
        """
        Extract all comments from SQL string.

        Args:
            sql: Original SQL string with comments

        Returns:
            List of comment dictionaries with:
            - id: Unique identifier (001, 002, ...)
            - type: 'line' or 'block'
            - content: Comment text without delimiters
            - start: Start position in original string
            - end: End position in original string
            - placeholder: Unique placeholder string
            - line_number: Line number in original SQL
        """
        self.reset()
        comment_id = 1

        # Extract line comments (-- ...)
        line_pattern = r'--[^\n]*'
        for match in re.finditer(line_pattern, sql):
            comment_text = match.group()
            self._comments.append({
                'id': f'{comment_id:03d}',
                'type': 'line',
                'content': comment_text[2:],  # Remove '--'
                'start': match.start(),
                'end': match.end(),
                'placeholder': f'{self._placeholder_prefix}{comment_id:03d}{self._placeholder_suffix}',
                'line_number': sql[:match.start()].count('\n') + 1
            })
            comment_id += 1

        # Extract block comments (/* ... */)
        block_pattern = r'/\*.*?\*/'
        for match in re.finditer(block_pattern, sql, re.DOTALL):
            comment_text = match.group()
            self._comments.append({
                'id': f'{comment_id:03d}',
                'type': 'block',
                'content': comment_text[2:-2],  # Remove '/*' and '*/'
                'start': match.start(),
                'end': match.end(),
                'placeholder': f'{self._placeholder_prefix}{comment_id:03d}{self._placeholder_suffix}',
                'line_number': sql[:match.start()].count('\n') + 1
            })
            comment_id += 1

        # Sort by position in original SQL
        self._comments.sort(key=lambda c: c['start'])

        return self._comments
