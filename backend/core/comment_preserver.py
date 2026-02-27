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

    def replace_with_placeholders(self, sql: str) -> str:
        """
        Replace all comments with unique placeholders.

        Args:
            sql: Original SQL string with comments

        Returns:
            SQL string with comments replaced by placeholders
        """
        result = sql

        # Sort by position descending to replace from end to start
        # This preserves string positions
        sorted_comments = sorted(self._comments, key=lambda c: c['start'], reverse=True)

        for comment in sorted_comments:
            result = result[:comment['start']] + comment['placeholder'] + result[comment['end']:]

        return result

    def get_token_before_placeholder(self, sql: str, placeholder: str) -> str:
        """
        Get the SQL token immediately before a placeholder.

        Args:
            sql: SQL string with placeholders
            placeholder: The placeholder to find

        Returns:
            The token before the placeholder, or empty string if not found
        """
        pos = sql.find(placeholder)
        if pos == -1:
            return ''

        # Get text before placeholder
        before = sql[:pos].rstrip()

        # Find the last token (word, identifier, or keyword)
        # Skip trailing whitespace and find the last word
        tokens = before.split()
        if tokens:
            return tokens[-1]

        return ''

    def insert_comments(self, formatted_sql: str, original_sql: str) -> str:
        """
        Insert comments back into formatted SQL.

        Args:
            formatted_sql: SQL after formatting (may have placeholders)
            original_sql: Original SQL (for reference)

        Returns:
            Formatted SQL with comments restored
        """
        result = formatted_sql

        for comment in self._comments:
            # Find the placeholder in formatted SQL
            if comment['placeholder'] in result:
                # Replace placeholder with original comment
                if comment['type'] == 'line':
                    replacement = '--' + comment['content']
                else:
                    replacement = '/*' + comment['content'] + '*/'

                result = result.replace(comment['placeholder'], replacement)
            else:
                # Placeholder not found - try to find the token and append
                # Get token that was before the comment in original
                sql_with_placeholder = self.replace_with_placeholders(original_sql)
                token = self.get_token_before_placeholder(sql_with_placeholder, comment['placeholder'])

                if token:
                    # Find token in formatted SQL and append comment
                    result = self._append_comment_after_token(result, token, comment)

        return result

    def _append_comment_after_token(self, sql: str, token: str, comment: dict) -> str:
        """Append a comment after the first occurrence of a token on its line"""
        lines = sql.split('\n')

        for i, line in enumerate(lines):
            # Find token in line (not inside a string)
            if token in line:
                # Check if this line already has a comment
                if '--' not in line:
                    # Append comment at end of line
                    if comment['type'] == 'line':
                        lines[i] = line.rstrip() + ' --' + comment['content']
                    else:
                        lines[i] = line.rstrip() + ' /*' + comment['content'] + '*/'
                break

        return '\n'.join(lines)
