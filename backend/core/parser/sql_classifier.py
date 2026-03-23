# -*- coding: utf-8 -*-
r"""
SQL Classifier

Identifies SQL statement types and dispatches to appropriate processors.

Supported syntax types:
- 'data_operations': MERGE, INSERT OVERWRITE (highest priority)
- 'set_operations': UNION, INTERSECT, EXCEPT, MINUS
- 'window_functions': OVER clause, WINDOW definition
- 'advanced_transforms': PIVOT, UNPIVOT, LATERAL VIEW
- 'basic': Basic SELECT (default)
"""

import re
from typing import List


class SQLClassifier:
    r"""
    Classifies SQL statements by syntax type.

    Detection rules (in priority order):
    1. MERGE: ^\s*MERGE\s+INTO\b
    2. INSERT OVERWRITE: INSERT\s+OVERWRITE\s+(?:TABLE\s+)?\S+
    3. Set operations: \bUNION\s+(?:ALL\s+)?\b, \bINTERSECT\b, \bEXCEPT\b, \bMINUS\b
    4. Window functions: \bOVER\s*\(
    5. PIVOT/LATERAL VIEW: \bPIVOT\b, \bUNPIVOT\b, \bLATERAL\s+VIEW\b
    """

    # Regex patterns for syntax detection
    PATTERNS = {
        'data_operations': [
            # MERGE INTO (highest priority)
            r'^\s*MERGE\s+INTO\b',
            # INSERT OVERWRITE [TABLE] table_name
            r'INSERT\s+OVERWRITE\s+(?:TABLE\s+)?\S+',
        ],
        'set_operations': [
            # UNION [ALL]
            r'\bUNION\s+(?:ALL\s+)?\b',
            # INTERSECT
            r'\bINTERSECT\b',
            # EXCEPT
            r'\bEXCEPT\b',
            # MINUS (Oracle-style)
            r'\bMINUS\b',
        ],
        'window_functions': [
            # OVER (
            r'\bOVER\s*\(',
            # WINDOW window_name AS
            r'\bWINDOW\s+\w+\s+AS\b',
        ],
        'advanced_transforms': [
            # PIVOT
            r'\bPIVOT\b',
            # UNPIVOT
            r'\bUNPIVOT\b',
            # LATERAL VIEW
            r'\bLATERAL\s+VIEW\b',
        ],
    }

    @classmethod
    def _remove_comments(cls, sql: str) -> str:
        """
        Remove SQL comments to avoid false positives in pattern matching.

        Handles both line comments (--) and block comments (/* */).

        Args:
            sql: SQL statement

        Returns:
            SQL with comments removed
        """
        import re

        # Remove block comments /* ... */
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)

        # Remove line comments -- ...
        # Need to be careful with strings that might contain --
        in_string = False
        string_char = None
        result = []
        i = 0

        while i < len(sql):
            char = sql[i]

            # Handle strings
            if not in_string and char in ('"', "'"):
                in_string = True
                string_char = char
                result.append(char)
            elif in_string and char == string_char:
                # Check if escaped
                if i > 0 and sql[i - 1] != '\\':
                    in_string = False
                    string_char = None
                result.append(char)
            elif in_string:
                result.append(char)
            # Handle line comments
            elif char == '-' and i + 1 < len(sql) and sql[i + 1] == '-':
                # Skip until end of line
                while i < len(sql) and sql[i] != '\n':
                    i += 1
                # Keep the newline
                if i < len(sql):
                    result.append(sql[i])
            else:
                result.append(char)

            i += 1

        return ''.join(result)

    @classmethod
    def classify(cls, sql: str) -> List[str]:
        """
        Classify SQL statement by syntax type.

        Args:
            sql: SQL statement to classify

        Returns:
            List of syntax types found in the SQL.
            Returns ['basic'] if no special syntax is detected.
        """
        if not sql or not sql.strip():
            return []

        # Remove comments before pattern matching to avoid false positives
        # e.g., "--4. UNION + test" should not be classified as set_operations
        sql_without_comments = cls._remove_comments(sql)

        detected = []

        # Check data operations (highest priority)
        if cls._check_patterns(sql_without_comments, cls.PATTERNS['data_operations']):
            detected.append('data_operations')

        # Check set operations
        if cls._check_patterns(sql_without_comments, cls.PATTERNS['set_operations']):
            detected.append('set_operations')

        # Check window functions
        if cls._check_patterns(sql_without_comments, cls.PATTERNS['window_functions']):
            detected.append('window_functions')

        # Check advanced transforms
        if cls._check_patterns(sql_without_comments, cls.PATTERNS['advanced_transforms']):
            detected.append('advanced_transforms')

        # Default to basic if no special syntax detected
        if not detected:
            detected.append('basic')

        return detected

    @classmethod
    def _check_patterns(cls, sql: str, patterns: List[str]) -> bool:
        """
        Check if SQL matches any of the given patterns.

        Args:
            sql: SQL statement to check
            patterns: List of regex patterns

        Returns:
            True if any pattern matches, False otherwise
        """
        for pattern in patterns:
            if re.search(pattern, sql, re.IGNORECASE | re.MULTILINE):
                return True
        return False

    @classmethod
    def get_primary_type(cls, sql: str) -> str:
        """
        Get the primary (first detected) syntax type.

        Priority order:
        1. data_operations
        2. set_operations
        3. window_functions
        4. advanced_transforms
        5. basic

        Args:
            sql: SQL statement to classify

        Returns:
            Primary syntax type
        """
        types = cls.classify(sql)
        return types[0] if types else 'basic'
