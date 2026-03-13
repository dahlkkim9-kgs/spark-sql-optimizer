# -*- coding: utf-8 -*-
r"""
Window Functions Processor - Supports OVER/PARTITION BY/window frames

This processor handles SQL window function syntax including:
- OVER (PARTITION BY ... ORDER BY ...)
- Window frames (ROWS BETWEEN, RANGE BETWEEN)
- Named windows (WINDOW clause)

Examples:
    SELECT ROW_NUMBER() OVER (PARTITION BY dept ORDER BY salary DESC)
    SELECT SUM(amount) OVER (ORDER BY date ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING)
"""

import re
from typing import List, Literal, Tuple, Optional
from .base_processor import BaseProcessor

# Indentation constants
OVER_INDENT = 4  # OVER clause content indentation
WINDOW_FRAME_INDENT = 8  # Window frame indentation


class WindowFunctionsProcessor(BaseProcessor):
    """Window Functions Processor - Supports OVER/PARTITION BY/window frames"""

    def __init__(self):
        super().__init__()
        # Pattern to detect OVER clause
        self.over_pattern = re.compile(r'\bOVER\s*\(', re.IGNORECASE)
        # Pattern to detect WINDOW clause
        self.window_pattern = re.compile(r'\bWINDOW\s+\w+\s+AS\b', re.IGNORECASE)
        # Pattern for window function names
        self.window_func_pattern = re.compile(
            r'\b(ROW_NUMBER|RANK|DENSE_RANK|NTILE|LEAD|LAG|FIRST_VALUE|LAST_VALUE|'
            r'SUM|AVG|MIN|MAX|COUNT|STDDEV|VARIANCE)\s*\(',
            re.IGNORECASE
        )

    def can_process(self, sql: str) -> bool:
        """Check if SQL contains window function syntax"""
        return (
            self.over_pattern.search(sql) is not None or
            self.window_pattern.search(sql) is not None
        )

    def process(
        self,
        sql: str,
        keyword_case: Literal['upper', 'lower', 'capitalize'] = 'upper'
    ) -> str:
        """
        Process SQL with window functions.

        Args:
            sql: SQL statement with window functions
            keyword_case: Keyword case convention

        Returns:
            Formatted SQL with proper window function indentation
        """
        if not sql or not sql.strip():
            return sql

        sql = sql.strip()

        # Check if we have WINDOW clause (named windows)
        if self.window_pattern.search(sql):
            return self._process_named_windows(sql, keyword_case)

        # Process OVER clauses
        return self._process_over_clauses(sql, keyword_case)

    def _process_over_clauses(
        self,
        sql: str,
        keyword_case: str
    ) -> str:
        """Process SQL with OVER clauses"""
        # Find and format each OVER clause
        result = []
        i = 0
        last_end = 0

        for match in self.over_pattern.finditer(sql):
            # Add everything before this OVER clause
            if match.start() > last_end:
                before = sql[last_end:match.start()]
                result.append(before)

            # Extract the complete OVER clause
            over_start = match.start()
            over_content = self._extract_over_clause(sql, over_start)

            if over_content:
                # Format the OVER clause
                formatted_over = self._format_over_clause(
                    over_content,
                    keyword_case
                )
                result.append(formatted_over)
                last_end = over_start + len(over_content)
            else:
                # If extraction failed, add original
                result.append(match.group(0))
                last_end = match.end()

        # Add remaining content
        if last_end < len(sql):
            result.append(sql[last_end:])

        formatted = ''.join(result)

        # Format the base SQL (SELECT list, FROM, etc.)
        return self._format_base_sql(formatted, keyword_case)

    def _extract_over_clause(self, sql: str, start_pos: int) -> Optional[str]:
        """
        Extract the complete OVER clause including nested parentheses.

        Args:
            sql: Full SQL string
            start_pos: Position of 'OVER'

        Returns:
            Complete OVER clause string or None if extraction fails
        """
        # Find the opening parenthesis after OVER
        i = start_pos
        while i < len(sql) and sql[i] != '(':
            i += 1

        if i >= len(sql):
            return None

        # Track parentheses to find the matching closing paren
        paren_depth = 0
        in_string = False
        string_char = None

        while i < len(sql):
            char = sql[i]

            # Handle string literals
            if not in_string and char in ('"', "'"):
                in_string = True
                string_char = char
            elif in_string and char == string_char:
                # Check for escaped quotes
                if i > 0 and sql[i-1] != '\\':
                    in_string = False

            if not in_string:
                if char == '(':
                    paren_depth += 1
                elif char == ')':
                    paren_depth -= 1
                    if paren_depth == 0:
                        # Found the closing paren
                        return sql[start_pos:i+1]

            i += 1

        return None

    def _format_over_clause(
        self,
        over_clause: str,
        keyword_case: str
    ) -> str:
        """
        Format a single OVER clause with proper indentation.

        Args:
            over_clause: The OVER clause string (e.g., "OVER (PARTITION BY dept)")
            keyword_case: Keyword case convention

        Returns:
            Formatted OVER clause
        """
        # Extract content inside parentheses
        match = re.match(r'\s*(OVER)\s*\(\s*(.*?)\s*\)\s*$', over_clause, re.IGNORECASE | re.DOTALL)
        if not match:
            return over_clause

        over_keyword = self._apply_case('OVER', keyword_case)
        content = match.group(2).strip()

        if not content:
            # Empty OVER clause
            return f'{over_keyword} ()'

        # Parse and format the content
        formatted_lines = self._format_over_content(content, keyword_case)

        # Build the formatted OVER clause
        result = [f'{over_keyword} (']
        result.extend(formatted_lines)
        result.append(')')  # Closing paren

        return '\n'.join(result)

    def _format_over_content(
        self,
        content: str,
        keyword_case: str
    ) -> List[str]:
        """
        Format the content inside OVER parentheses.

        Handles:
        - PARTITION BY clauses
        - ORDER BY clauses
        - Window frames (ROWS BETWEEN, RANGE BETWEEN)
        """
        lines = []
        content = content.strip()
        pos = 0

        # Check for PARTITION BY
        if re.match(r'PARTITION\s+BY\b', content[pos:], re.IGNORECASE):
            # Find the end of PARTITION BY clause
            partition_end = self._find_partition_by_end(content, pos)
            partition_clause = content[pos:partition_end].strip()
            formatted = self._format_partition_by(partition_clause, keyword_case)
            lines.append(formatted)
            pos = partition_end

        # Skip whitespace
        while pos < len(content) and content[pos].isspace():
            pos += 1

        # Check for ORDER BY
        if re.match(r'ORDER\s+BY\b', content[pos:], re.IGNORECASE):
            # Find the end of ORDER BY clause
            order_end = self._find_order_by_end(content, pos)
            order_clause = content[pos:order_end].strip()
            formatted = self._format_order_by(order_clause, keyword_case)
            lines.append(formatted)
            pos = order_end

        # Skip whitespace
        while pos < len(content) and content[pos].isspace():
            pos += 1

        # Check for window frame
        if pos < len(content) and re.match(r'(ROWS|RANGE)\s+BETWEEN\b', content[pos:], re.IGNORECASE):
            frame_clause = content[pos:].strip()
            formatted = self._format_window_frame(frame_clause, keyword_case)
            lines.append(formatted)

        return lines

    def _find_partition_by_end(self, content: str, start: int) -> int:
        """Find the end of PARTITION BY clause"""
        i = start
        # Skip "PARTITION BY"
        match = re.match(r'PARTITION\s+BY\s+', content[i:], re.IGNORECASE)
        if match:
            i += match.end()

        # Parse column list - continue until we hit ORDER BY, ROWS BETWEEN, or RANGE BETWEEN
        paren_depth = 0
        in_string = False
        string_char = None

        while i < len(content):
            # Check for next clause keywords first
            if re.match(r'\s+ORDER\s+BY\b', content[i:], re.IGNORECASE) or \
               re.match(r'\s+(ROWS|RANGE)\s+BETWEEN\b', content[i:], re.IGNORECASE):
                return i

            char = content[i]

            # Handle string literals
            if not in_string and char in ('"', "'"):
                in_string = True
                string_char = char
            elif in_string and char == string_char:
                if i > 0 and content[i-1] != '\\':
                    in_string = False

            if not in_string:
                if char == '(':
                    paren_depth += 1
                elif char == ')':
                    paren_depth -= 1

            i += 1

        return len(content)

    def _find_order_by_end(self, content: str, start: int) -> int:
        """Find the end of ORDER BY clause"""
        i = start
        # Skip "ORDER BY"
        match = re.match(r'ORDER\s+BY\s+', content[i:], re.IGNORECASE)
        if match:
            i += match.end()

        # Parse column list
        paren_depth = 0
        in_string = False
        string_char = None

        while i < len(content):
            char = content[i]

            # Handle string literals
            if not in_string and char in ('"', "'"):
                in_string = True
                string_char = char
            elif in_string and char == string_char:
                if i > 0 and content[i-1] != '\\':
                    in_string = False

            if not in_string:
                if char == '(':
                    paren_depth += 1
                elif char == ')':
                    paren_depth -= 1
                elif re.match(r'\s+(ROWS|RANGE)\s+BETWEEN\b', content[i:], re.IGNORECASE):
                    # Found window frame clause
                    return i

            i += 1

        return len(content)

    def _find_clause_end(self, content: str, start: int) -> int:
        """Find the end of a clause (PARTITION BY, ORDER BY, etc.)"""
        i = start
        paren_depth = 0
        in_string = False
        string_char = None

        while i < len(content):
            char = content[i]

            # Handle string literals
            if not in_string and char in ('"', "'"):
                in_string = True
                string_char = char
            elif in_string and char == string_char:
                if i > 0 and content[i-1] != '\\':
                    in_string = False

            if not in_string:
                if char == '(':
                    paren_depth += 1
                elif char == ')':
                    paren_depth -= 1
                elif char == ',' and paren_depth == 0:
                    # Found a comma at top level, end of clause
                    return i

            i += 1

        return len(content)

    def _format_partition_by(self, clause: str, keyword_case: str) -> str:
        """Format PARTITION BY clause"""
        # Normalize the clause
        partition_by = self._apply_case('PARTITION BY', keyword_case)

        # Extract partition columns
        match = re.match(
            r'PARTITION\s+BY\s+(.+)$',
            clause,
            re.IGNORECASE
        )

        indent = ' ' * OVER_INDENT
        if match:
            columns_str = match.group(1).strip()
            # Parse columns (handle commas)
            columns = self._parse_column_list(columns_str)
            # Format column list with alignment
            formatted_columns = self._format_column_list(columns)
            return f'{indent}{partition_by} {formatted_columns}'
        else:
            # Fallback: just add keyword and indent
            result = re.sub(
                r'PARTITION\s+BY',
                f'{indent}{partition_by}',
                clause,
                flags=re.IGNORECASE
            )
            return result.strip()

    def _format_order_by(self, clause: str, keyword_case: str) -> str:
        """Format ORDER BY clause"""
        order_by = self._apply_case('ORDER BY', keyword_case)

        # Extract order columns
        match = re.match(
            r'ORDER\s+BY\s+(.+)$',
            clause,
            re.IGNORECASE
        )

        indent = ' ' * OVER_INDENT
        if match:
            columns_str = match.group(1).strip()
            # Parse columns (handle commas)
            columns = self._parse_column_list(columns_str)
            # Format column list with alignment
            formatted_columns = self._format_column_list(columns)
            return f'{indent}{order_by} {formatted_columns}'
        else:
            # Fallback
            result = re.sub(
                r'ORDER\s+BY',
                f'{indent}{order_by}',
                clause,
                flags=re.IGNORECASE
            )
            return result.strip()

    def _parse_column_list(self, columns_str: str) -> List[str]:
        """Parse a column list string into individual column definitions"""
        columns = []
        current = []
        paren_depth = 0
        in_string = False
        string_char = None

        for char in columns_str:
            # Handle string literals
            if not in_string and char in ('"', "'"):
                in_string = True
                string_char = char
                current.append(char)
            elif in_string and char == string_char:
                if len(current) > 0 and current[-1] != '\\':
                    in_string = False
                current.append(char)
            elif not in_string:
                if char == '(':
                    paren_depth += 1
                    current.append(char)
                elif char == ')':
                    paren_depth -= 1
                    current.append(char)
                elif char == ',' and paren_depth == 0:
                    # Found a comma at top level
                    columns.append(''.join(current).strip())
                    current = []
                else:
                    current.append(char)
            else:
                current.append(char)

        if current:
            columns.append(''.join(current).strip())

        return [col for col in columns if col]

    def _format_window_frame(self, clause: str, keyword_case: str) -> str:
        """Format window frame (ROWS BETWEEN, RANGE BETWEEN)"""
        # Apply case to keywords
        result = clause
        result = re.sub(
            r'\b(ROWS|RANGE)\b',
            lambda m: self._apply_case(m.group(1), keyword_case),
            result,
            flags=re.IGNORECASE
        )
        result = re.sub(
            r'\b(BETWEEN|AND|PRECEDING|FOLLOWING|CURRENT\s+ROW|UNBOUNDED)\b',
            lambda m: self._apply_case(m.group(1), keyword_case),
            result,
            flags=re.IGNORECASE
        )

        indent = ' ' * WINDOW_FRAME_INDENT
        return f'{indent}{result.strip()}'

    def _format_column_list(self, columns: List[str]) -> str:
        """Format a column list with proper alignment"""
        if not columns:
            return ''

        if len(columns) == 1:
            return columns[0]

        # Align columns
        result = [columns[0]]
        for col in columns[1:]:
            result.append(f'                             , {col}')

        return '\n'.join(result)

    def _process_named_windows(
        self,
        sql: str,
        keyword_case: str
    ) -> str:
        """Process SQL with named WINDOW clause"""
        # Split at WINDOW clause
        window_match = re.search(
            r'\bWINDOW\b(.+?)(?:;|$)',
            sql,
            re.IGNORECASE | re.DOTALL
        )

        if not window_match:
            return self._process_over_clauses(sql, keyword_case)

        # Extract main query and WINDOW definitions
        main_query = sql[:window_match.start()].strip()
        window_def = window_match.group(0)

        # Format main query (may contain OVER clauses referencing named windows)
        formatted_main = self._process_over_clauses(main_query, keyword_case)

        # Format WINDOW clause
        formatted_window = self._format_named_window_clause(window_def, keyword_case)

        # Combine
        return f'{formatted_main}\n{formatted_window}'

    def _format_named_window_clause(self, window_clause: str, keyword_case: str) -> str:
        """Format the WINDOW clause with named window definitions"""
        window_keyword = self._apply_case('WINDOW', keyword_case)

        # Extract window definitions
        match = re.match(r'WINDOW\s+(.+)', window_clause, re.IGNORECASE | re.DOTALL)
        if not match:
            return window_clause

        definitions = match.group(1)

        # Split by comma (top level only)
        defs = self._split_top_level(definitions, ',')

        # Format each definition
        formatted_defs = []
        for i, definition in enumerate(defs):
            definition = definition.strip()
            # Extract window name and AS (window_spec)
            def_match = re.match(
                r'(\w+)\s+AS\s+\((.+)\)\s*$',
                definition,
                re.IGNORECASE | re.DOTALL
            )
            if def_match:
                name = def_match.group(1)
                spec = def_match.group(2).strip()
                as_keyword = self._apply_case('AS', keyword_case)
                spec_formatted = self._format_over_content(spec, keyword_case)

                if i == 0:
                    formatted_defs.append(f'{window_keyword} {name} {as_keyword} (')
                else:
                    formatted_defs.append(f'          , {name} {as_keyword} (')

                # Add formatted spec
                for line in spec_formatted:
                    formatted_defs.append(line)

                formatted_defs.append('                           )')
            else:
                # Fallback
                if i == 0:
                    formatted_defs.append(f'{window_keyword} {definition}')
                else:
                    formatted_defs.append(f'          , {definition}')

        return '\n'.join(formatted_defs)

    def _split_top_level(self, text: str, delimiter: str) -> List[str]:
        """Split text by delimiter, ignoring nested parentheses"""
        parts = []
        current = []
        paren_depth = 0
        in_string = False
        string_char = None

        for char in text:
            # Handle string literals
            if not in_string and char in ('"', "'"):
                in_string = True
                string_char = char
            elif in_string and char == string_char:
                if len(current) > 0 and current[-1] != '\\':
                    in_string = False

            if not in_string:
                if char == '(':
                    paren_depth += 1
                elif char == ')':
                    paren_depth -= 1
                elif char == delimiter and paren_depth == 0:
                    parts.append(''.join(current))
                    current = []
                    continue

            current.append(char)

        if current:
            parts.append(''.join(current))

        return parts

    def _format_base_sql(self, sql: str, keyword_case: str) -> str:
        """Format the base SQL (SELECT, FROM, WHERE, etc.)"""
        # For now, use v4_fixed to format the base structure
        # This is a simplified approach - ideally we'd preserve OVER clause formatting
        try:
            # Use v4_fixed but be careful not to mess up our OVER formatting
            # Split out the OVER clauses, format base, then re-insert
            return self._format_base_preserving_over(sql, keyword_case)
        except Exception:
            # Fallback: return as-is
            return sql

    def _format_base_preserving_over(self, sql: str, keyword_case: str) -> str:
        """Format base SQL while preserving OVER clause formatting"""
        # This is a placeholder - for now, we'll return the SQL as-is
        # A full implementation would:
        # 1. Extract OVER clauses
        # 2. Format base SQL with v4_fixed
        # 3. Re-insert formatted OVER clauses

        # For now, just apply keyword case to main keywords
        result = sql

        # Apply case to main SQL keywords (but not inside OVER clauses)
        keywords = [
            'SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING',
            'ORDER BY', 'LIMIT', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN',
            'INNER JOIN', 'OUTER JOIN', 'ON', 'AND', 'OR'
        ]

        for keyword in keywords:
            # Only replace if not already in OVER clause (simplified check)
            result = re.sub(
                r'\b' + keyword + r'\b',
                lambda m: self._apply_case(m.group(0), keyword_case),
                result
            )

        return result

    def _apply_case(self, text: str, case_type: str) -> str:
        """Apply case transformation to text"""
        if case_type == 'upper':
            return text.upper()
        elif case_type == 'lower':
            return text.lower()
        elif case_type == 'capitalize':
            return text.capitalize()
        return text
