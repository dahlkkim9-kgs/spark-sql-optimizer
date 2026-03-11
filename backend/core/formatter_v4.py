# -*- coding: utf-8 -*-
"""
SQL Formatter V4 - Enhanced with Comment Preservation and Nested CASE Support
"""
import re
from typing import List, Dict, Tuple


def format_sql_v4(sql: str, **options) -> str:
    """
    Format SQL with:
    1. Inline comment preservation
    2. Proper nested CASE WHEN formatting
    3. Comma-first style (逗号前置)
    """
    keyword_case = options.get('keyword_case', 'upper')

    # Step 1: Extract and store inline comments with their positions
    comments = _extract_comments(sql)

    # Step 2: Protect comments before parsing (replace with placeholders)
    sql_protected, comment_map = _protect_comments(sql)

    # Step 3: Parse and format SQL structure
    formatted = _format_sql_structure(sql_protected, keyword_case)

    # Step 4: Restore comments from placeholders
    result = _restore_protected_comments(formatted, comment_map)

    # Step 5: Add semicolon on new line
    result = result.rstrip(';').strip() + '\n;'

    return result


def _protect_comments(sql: str) -> tuple:
    """Replace comments with placeholders to protect them during parsing"""
    comment_map = {}
    protected = sql
    counter = [0]

    def replace_comment(match):
        placeholder = f"__COMMENT_{counter[0]}__"
        comment_map[placeholder] = match.group(0)
        counter[0] += 1
        return placeholder

    # Protect line comments
    protected = re.sub(r'--[^\n]*', replace_comment, protected)

    # Protect block comments
    protected = re.sub(r'/\*.*?\*/', replace_comment, protected, flags=re.DOTALL)

    return protected, comment_map


def _restore_protected_comments(sql: str, comment_map: dict) -> str:
    """Restore comments from placeholders"""
    result = sql
    for placeholder, comment in comment_map.items():
        result = result.replace(placeholder, comment)
    return result


def _extract_comments(sql: str) -> List[Dict]:
    """Extract all comments with their context (preceding token/line)"""
    comments = []

    lines = sql.split('\n')

    for line_num, line in enumerate(lines):
        # Extract line-end comments (-- ...)
        line_comment_match = re.search(r'--([^\n]*)$', line)
        if line_comment_match:
            comment_text = line_comment_match.group(0)  # Keep the -- prefix
            # Get the SQL part before the comment
            sql_part = line[:line_comment_match.start()].strip()
            comments.append({
                'type': 'line',
                'content': comment_text,
                'line_num': line_num,
                'sql_before': sql_part,
                'keywords': _extract_keywords(sql_part)
            })

        # Extract block comments (/* ... */)
        for match in re.finditer(r'/\*.*?\*/', line, re.DOTALL):
            comments.append({
                'type': 'block',
                'content': match.group(),
                'line_num': line_num,
                'sql_before': line[:match.start()].strip(),
                'keywords': _extract_keywords(line[:match.start()])
            })

    return comments


def _extract_keywords(sql_part: str) -> set:
    """Extract SQL keywords/identifiers from a SQL fragment for matching"""
    # Remove AS aliases and extract the main expression
    sql_part = re.sub(r'\s+AS\s+\w+', '', sql_part, flags=re.IGNORECASE)
    # Extract words that look like identifiers
    words = re.findall(r'[\w\.]+', sql_part)
    return set(w.lower() for w in words if len(w) > 2)


def _remove_comments(sql: str) -> str:
    """Remove all comments from SQL"""
    result = re.sub(r'--[^\n]*', '', sql)
    result = re.sub(r'/\*.*?\*/', '', result, flags=re.DOTALL)
    # Clean up multiple empty lines
    result = re.sub(r'\n\s*\n', '\n', result)
    return result


def _format_sql_structure(sql: str, keyword_case: str = 'upper') -> str:
    """Format SQL structure without comments"""

    # Normalize whitespace
    sql = ' '.join(sql.split())

    # Parse SQL clauses
    parts = _parse_sql_parts(sql)

    # Format each part
    lines = []

    # SELECT clause
    if parts['select']:
        select_lines = _format_select_clause(parts['select'])
        lines.extend(select_lines)

    # FROM clause
    if parts['from']:
        lines.append(f'\nFROM {parts["from"]}')

    # JOIN clauses
    for join in parts['joins']:
        join_lines = _format_join_clause(join)
        lines.extend(join_lines)

    # WHERE clause
    if parts['where']:
        where_lines = _format_where_clause(parts['where'])
        lines.extend(where_lines)

    # GROUP BY clause
    if parts['group_by']:
        lines.append(f'\n    GROUP BY {parts["group_by"]}')

    # ORDER BY clause
    if parts['order_by']:
        lines.append(f'\n    ORDER BY {parts["order_by"]}')

    # DISTRIBUTE BY clause
    if parts['distribute_by']:
        lines.append(f'\nDISTRIBUTE BY {parts["distribute_by"]}')

    result = '\n'.join(lines)

    # Uppercase keywords if requested
    if keyword_case == 'upper':
        result = _uppercase_keywords(result)

    return result


def _parse_sql_parts(sql: str) -> Dict:
    """Parse SQL into its component parts"""
    parts = {
        'select': [],
        'from': '',
        'joins': [],
        'where': '',
        'group_by': '',
        'order_by': '',
        'distribute_by': ''
    }

    # First, identify and protect subqueries and window functions
    protected_sql = sql
    placeholders = {}

    # Protect OVER(...) window functions - handle nested parens
    i = 0
    while i < len(protected_sql):
        # Look for OVER keyword
        if protected_sql[i:i+4].upper() == 'OVER' and (i + 4 >= len(protected_sql) or not protected_sql[i+4].isalnum()):
            # Find the opening parenthesis
            j = i + 4
            while j < len(protected_sql) and protected_sql[j] in ' \t\n':
                j += 1
            if j < len(protected_sql) and protected_sql[j] == '(':
                # Find matching closing parenthesis
                paren_start = j
                paren_depth = 1
                k = j + 1
                while k < len(protected_sql) and paren_depth > 0:
                    if protected_sql[k] == '(':
                        paren_depth += 1
                    elif protected_sql[k] == ')':
                        paren_depth -= 1
                    k += 1
                # Extract OVER(...) and replace with placeholder
                over_content = protected_sql[i:k]
                placeholder = f"__OVER_{len(placeholders)}__"
                placeholders[placeholder] = over_content
                protected_sql = protected_sql[:i] + placeholder + protected_sql[k:]
                continue
        i += 1

    # Protect subqueries in parentheses that contain SELECT
    paren_depth = 0
    paren_start = -1
    i = 0
    while i < len(protected_sql):
        if protected_sql[i] == '(':
            if paren_depth == 0:
                paren_start = i
            paren_depth += 1
        elif protected_sql[i] == ')':
            paren_depth -= 1
            if paren_depth == 0 and paren_start >= 0:
                paren_content = protected_sql[paren_start:i+1]
                if re.search(r'\bSELECT\b', paren_content, re.IGNORECASE):
                    placeholder = f"__SUBQUERY_{len(placeholders)}__"
                    placeholders[placeholder] = paren_content
                    protected_sql = protected_sql[:paren_start] + placeholder + protected_sql[i+1:]
                    i = -1
                    paren_depth = 0
                    paren_start = -1
        i += 1

    # Now parse the protected SQL
    # Pattern to find clause boundaries at the TOP LEVEL only
    clause_pattern = r'\b(SELECT|FROM|LEFT\s+JOIN|RIGHT\s+JOIN|INNER\s+JOIN|CROSS\s+JOIN|JOIN|WHERE|GROUP\s+BY|ORDER\s+BY|DISTRIBUTE\s+BY|HAVING|LIMIT)\b'

    matches = list(re.finditer(clause_pattern, protected_sql, re.IGNORECASE))

    for i, match in enumerate(matches):
        clause_type = match.group(1).upper().replace(' ', '_')
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(protected_sql)
        clause_content = protected_sql[start:end].strip().rstrip(',')

        # Restore placeholders in content
        for placeholder, original in placeholders.items():
            clause_content = clause_content.replace(placeholder, original)

        if clause_type == 'SELECT':
            parts['select'] = _parse_select_fields(clause_content)
        elif clause_type == 'FROM':
            parts['from'] = clause_content
        elif 'JOIN' in clause_type:
            parts['joins'].append({
                'type': match.group(1).upper(),
                'content': clause_content
            })
        elif clause_type == 'WHERE':
            parts['where'] = clause_content
        elif clause_type == 'GROUP_BY':
            parts['group_by'] = clause_content
        elif clause_type == 'ORDER_BY':
            parts['order_by'] = clause_content
        elif clause_type == 'DISTRIBUTE_BY':
            parts['distribute_by'] = clause_content

    return parts


def _parse_select_fields(fields_str: str) -> List[str]:
    """Parse SELECT fields, handling nested parentheses"""
    fields = []
    current_field = ''
    paren_depth = 0

    for char in fields_str:
        if char == '(':
            paren_depth += 1
            current_field += char
        elif char == ')':
            paren_depth -= 1
            current_field += char
        elif char == ',' and paren_depth == 0:
            fields.append(current_field.strip())
            current_field = ''
        else:
            current_field += char

    if current_field.strip():
        fields.append(current_field.strip())

    return fields


def _format_select_clause(fields: List[str]) -> List[str]:
    """Format SELECT clause with comma-first style"""
    lines = []

    for i, field in enumerate(fields):
        formatted_field = _format_field(field, is_first=(i == 0))

        if i == 0:
            lines.append(f'SELECT {formatted_field}')
        else:
            # Comma-first style: align with SELECT
            lines.append(f'     , {formatted_field}')

    return lines


def _format_field(field: str, is_first: bool = False) -> str:
    """Format a single field, handling CASE expressions"""
    field = field.strip()

    # Check if field contains CASE expression
    if re.search(r'\bCASE\b', field, re.IGNORECASE):
        return _format_case_expression(field, base_indent=0 if not is_first else 4)

    return field


def _format_case_expression(case_sql: str, base_indent: int = 0) -> str:
    """Format CASE expression with proper indentation for nested CASEs"""

    # Extract alias if present (handle comment placeholders too)
    # Pattern: AS alias followed by optional comment placeholder or nothing
    # Also handle case where CASE is wrapped in parentheses
    alias_match = re.search(r'\s+AS\s+(\w+)(?:\s*(__COMMENT_\d+__)\s*)?$', case_sql, re.IGNORECASE)
    alias = alias_match.group(1) if alias_match else None
    alias_comment = ''
    if alias_match:
        alias_comment = alias_match.group(2) or ''
        case_sql = case_sql[:alias_match.start()].strip()

    # Remove outer parentheses if they wrap the entire CASE expression
    # But only if they are balanced and contain a CASE
    if case_sql.startswith('(') and case_sql.endswith(')'):
        inner = case_sql[1:-1].strip()
        if re.search(r'^CASE\b', inner, re.IGNORECASE):
            # Check if parentheses are balanced
            paren_depth = 0
            balanced = True
            for i, char in enumerate(inner):
                if char == '(':
                    paren_depth += 1
                elif char == ')':
                    paren_depth -= 1
                    if paren_depth < 0:
                        balanced = False
                        break
            if balanced and paren_depth == 0:
                case_sql = inner

    # Format the CASE expression
    # For comma-first style (base_indent=0), use special indentation
    formatted = _format_case_recursive(case_sql, base_indent=base_indent)

    if alias:
        # For comma-first style (base_indent=0), put AS on same line as END
        if base_indent == 0:
            formatted = formatted.rstrip() + f' AS {alias}'
            if alias_comment:
                formatted += f' {alias_comment}'
        else:
            formatted += f'\n    AS {alias}'
            if alias_comment:
                formatted += f' {alias_comment}'

    return formatted


def _format_case_recursive(case_sql: str, base_indent: int = 0) -> str:
    """Recursively format CASE expressions including nested ones"""
    indent = ' ' * base_indent

    # For comma-first style (base_indent=0), use 11 spaces for WHEN/THEN/ELSE
    # and 7 spaces for END (to align with CASE after "     , ")
    if base_indent == 0:
        inner_indent = ' ' * 11  # Align content nicely under comma-first style
        end_indent = ' ' * 7     # END aligns with CASE
    else:
        inner_indent = ' ' * (base_indent + 4)
        end_indent = indent

    # Remove CASE and END wrapper
    case_sql = case_sql.strip()

    # Find CASE ... END boundaries - handle nested CASE properly
    if not case_sql.upper().startswith('CASE'):
        return case_sql

    # Find the matching END for this CASE
    depth = 0
    end_pos = -1
    content_start = 4  # After 'CASE'

    for i in range(len(case_sql)):
        if case_sql[i:i+4].upper() == 'CASE' and (i == 0 or not case_sql[i-1].isalnum()):
            depth += 1
        elif case_sql[i:i+3].upper() == 'END' and (i+3 >= len(case_sql) or not case_sql[i+3].isalnum()):
            depth -= 1
            if depth == 0:
                end_pos = i
                break

    if end_pos == -1:
        case_match = re.match(r'CASE\s+(.+?)\s+END$', case_sql, re.IGNORECASE | re.DOTALL)
        if not case_match:
            return case_sql
        inner_content = case_match.group(1)
    else:
        inner_content = case_sql[content_start:end_pos].strip()

    # Parse WHEN-THEN pairs and ELSE
    parts = _parse_case_parts(inner_content)

    lines = [f'{indent}CASE']

    for when_cond, then_val in parts['whens']:
        # Format WHEN condition - split OR conditions if multiple
        when_formatted = _format_when_condition(when_cond.strip(), inner_indent)
        lines.append(f'{inner_indent}WHEN {when_formatted}')

        then_stripped = then_val.strip()
        # Check if THEN value is wrapped in parentheses containing a CASE
        has_paren_wrapper = False
        inner_then = then_stripped
        if then_stripped.startswith('(') and then_stripped.endswith(')'):
            inner_then = then_stripped[1:-1].strip()
            if re.search(r'^CASE\b', inner_then, re.IGNORECASE):
                has_paren_wrapper = True

        if re.search(r'\bCASE\b', then_stripped, re.IGNORECASE):
            # For nested CASE in comma-first style, use indent of 15 (11+4)
            nested_base = 15 if base_indent == 0 else base_indent + 8
            # Use the content inside parentheses if wrapped, otherwise use as-is
            nested_content = inner_then if has_paren_wrapper else then_stripped
            nested_formatted = _format_case_recursive(nested_content, nested_base)

            if has_paren_wrapper:
                # 原始有括号，保留括号
                lines.append(f'{inner_indent}THEN (')
                for nested_line in nested_formatted.split('\n'):
                    lines.append(nested_line)
                lines.append(f'{inner_indent}    )')
            else:
                # 原始没有括号，不加括号
                lines.append(f'{inner_indent}THEN')
                for nested_line in nested_formatted.split('\n'):
                    lines.append(nested_line)
        else:
            lines.append(f'{inner_indent}THEN {then_stripped}')

    if parts['else']:
        else_val = parts['else'].strip()
        # Check if ELSE value is wrapped in parentheses containing a CASE
        has_paren_wrapper = False
        inner_else = else_val
        if else_val.startswith('(') and else_val.endswith(')'):
            inner_else = else_val[1:-1].strip()
            if re.search(r'^CASE\b', inner_else, re.IGNORECASE):
                has_paren_wrapper = True

        if re.search(r'\bCASE\b', else_val, re.IGNORECASE):
            nested_base = 15 if base_indent == 0 else base_indent + 8
            # Use the content inside parentheses if wrapped, otherwise use as-is
            nested_content = inner_else if has_paren_wrapper else else_val
            nested_formatted = _format_case_recursive(nested_content, nested_base)

            if has_paren_wrapper:
                # 原始有括号，保留括号
                lines.append(f'{inner_indent}ELSE (')
                for nested_line in nested_formatted.split('\n'):
                    lines.append(nested_line)
                lines.append(f'{inner_indent}    )')
            else:
                # 原始没有括号，不加括号
                lines.append(f'{inner_indent}ELSE')
                for nested_line in nested_formatted.split('\n'):
                    lines.append(nested_line)
        else:
            lines.append(f'{inner_indent}ELSE {else_val}')

    lines.append(f'{end_indent}END')

    return '\n'.join(lines)


def _format_when_condition(condition: str, base_indent: str) -> str:
    """Format WHEN condition, splitting OR/AND if there are multiple"""
    # Split by OR at top level
    or_parts = _split_by_logical_op(condition, 'OR')

    if len(or_parts) <= 1:
        # Check for AND
        and_parts = _split_by_logical_op(condition, 'AND')
        if len(and_parts) <= 1:
            return condition

        # Multiple ANDs - format on separate lines
        lines = [and_parts[0].strip()]
        or_indent = ' ' * (len(base_indent) + 8)  # Additional indent for OR/AND
        for part in and_parts[1:]:
            lines.append(f'{or_indent}AND {part.strip()}')
        return '\n'.join(lines)

    # Multiple ORs - format on separate lines
    lines = [or_parts[0].strip()]
    or_indent = ' ' * (len(base_indent) + 8)  # Additional indent for OR
    for part in or_parts[1:]:
        # Check if this part has ANDs
        and_parts = _split_by_logical_op(part.strip(), 'AND')
        if len(and_parts) > 1:
            and_lines = [and_parts[0].strip()]
            and_indent = ' ' * (len(base_indent) + 16)
            for ap in and_parts[1:]:
                and_lines.append(f'{and_indent}AND {ap.strip()}')
            lines.append(f'{or_indent}OR {and_lines[0]}')
            for al in and_lines[1:]:
                lines.append(al)
        else:
            lines.append(f'{or_indent}OR {part.strip()}')

    return '\n'.join(lines)


def _parse_case_parts(content: str) -> Dict:
    """Parse CASE content into WHEN-THEN pairs and ELSE"""
    parts = {
        'whens': [],
        'else': ''
    }

    # Split by WHEN while preserving structure
    # This is tricky because of nested CASEs
    i = 0
    current_when = ''
    current_then = ''
    in_when = False
    in_then = False
    paren_depth = 0
    case_depth = 0

    tokens = re.split(r'(\bWHEN\b|\bTHEN\b|\bELSE\b|\bCASE\b|\bEND\b|\(|\))', content, flags=re.IGNORECASE)

    i = 0
    while i < len(tokens):
        token = tokens[i]
        token_upper = token.upper() if token else ''

        if token_upper == 'CASE':
            case_depth += 1
            if in_when:
                current_when += token
            elif in_then:
                current_then += token
        elif token_upper == 'END':
            case_depth -= 1
            if in_when:
                current_when += token
            elif in_then:
                current_then += token
        elif token_upper == 'WHEN' and case_depth == 0:
            if current_when and current_then:
                parts['whens'].append((current_when.strip(), current_then.strip()))
            current_when = ''
            current_then = ''
            in_when = True
            in_then = False
        elif token_upper == 'THEN' and case_depth == 0:
            in_when = False
            in_then = True
        elif token_upper == 'ELSE' and case_depth == 0:
            if current_when and current_then:
                parts['whens'].append((current_when.strip(), current_then.strip()))
            current_when = ''
            current_then = ''
            in_when = False
            in_then = False
            # Collect rest as ELSE
            else_content = ''
            j = i + 1
            while j < len(tokens):
                else_token = tokens[j]
                else_token_upper = else_token.upper() if else_token else ''
                if else_token_upper == 'CASE':
                    case_depth += 1
                elif else_token_upper == 'END':
                    case_depth -= 1
                if case_depth < 0:
                    break
                else_content += else_token
                j += 1
            parts['else'] = else_content.strip()
            i = j - 1
        else:
            if in_when:
                current_when += token
            elif in_then:
                current_then += token

        i += 1

    # Don't forget the last WHEN-THEN pair
    if current_when.strip() and current_then.strip():
        parts['whens'].append((current_when.strip(), current_then.strip()))

    return parts


def _format_join_clause(join: Dict) -> List[str]:
    """Format JOIN clause"""
    lines = []
    join_type = join['type']
    content = join['content']

    # Check for subquery (SELECT ... FROM ...)
    # Find balanced parentheses for the subquery
    subquery_start = content.find('(SELECT')
    if subquery_start == -1:
        subquery_start = content.find('( SELECT')
    if subquery_start == -1:
        subquery_start = content.find('(__COMMENT_')  # Protected comment before SELECT
    if subquery_start == -1:
        match = re.search(r'\(\s*(__COMMENT_\d+__\s*)?SELECT\b', content, re.IGNORECASE)
        if match:
            subquery_start = match.start()

    if subquery_start is not None and subquery_start >= 0:
        # Find the matching closing parenthesis
        paren_depth = 0
        subquery_end = -1
        for i in range(subquery_start, len(content)):
            if content[i] == '(':
                paren_depth += 1
            elif content[i] == ')':
                paren_depth -= 1
                if paren_depth == 0:
                    subquery_end = i
                    break

        if subquery_end > 0:
            # Extract subquery content (without outer parens)
            subquery_full = content[subquery_start+1:subquery_end].strip()

            # Get alias and ON condition after the subquery
            after_subquery = content[subquery_end+1:].strip()

            # Parse and format the subquery
            subquery_formatted = _format_subquery(subquery_full)

            # Split alias+comment from ON condition
            # Pattern: alias [comment] ON condition
            # First, extract trailing comment (if any) - it should go with alias
            trailing_comment_match = re.search(r'(__COMMENT_\d+__)\s*$', after_subquery)
            trailing_comment = ''
            after_subquery_clean = after_subquery
            if trailing_comment_match:
                trailing_comment = ' ' + trailing_comment_match.group(1)
                after_subquery_clean = after_subquery[:trailing_comment_match.start()].strip()

            on_match = re.search(r'\bON\b\s+', after_subquery_clean, re.IGNORECASE)
            alias_part = after_subquery_clean
            on_condition = ''

            if on_match:
                alias_part = after_subquery_clean[:on_match.start()].strip()
                on_condition = after_subquery_clean[on_match.end():].strip()

            # Add trailing comment to alias
            alias_part = alias_part + trailing_comment

            lines.append(f'    {join_type}')
            lines.append(f'        (')
            lines.append(f'{subquery_formatted}')
            lines.append(f'        ) {alias_part}')
            if on_condition:
                lines.append(f'        ON {on_condition}')
            return lines

    # No subquery - handle regular table with ON condition
    on_match = re.search(r'\bON\b\s+(.+)$', content, re.IGNORECASE | re.DOTALL)

    if on_match:
        table = content[:on_match.start()].strip()
        on_condition = on_match.group(1).strip()

        lines.append(f'    {join_type} {table}')
        lines.append(f'        ON {on_condition}')
    else:
        lines.append(f'    {join_type} {content}')

    return lines


def _format_subquery(subquery: str) -> str:
    """Format a subquery with proper indentation"""
    # Parse the subquery parts
    parts = _parse_sql_parts(subquery)

    lines = []

    # Format SELECT clause
    if parts['select']:
        select_lines = _format_select_clause(parts['select'])
        for sl in select_lines:
            lines.append('            ' + sl)

    # Format FROM clause
    if parts['from']:
        lines.append(f'            FROM {parts["from"]}')

    # Format WHERE clause with proper indentation
    if parts['where']:
        where_conditions = _split_by_logical_op(parts['where'], 'AND')
        first_cond = where_conditions[0].strip()

        # Check if first condition has OR
        or_parts = _split_by_logical_op(first_cond, 'OR')
        if len(or_parts) > 1:
            lines.append(f'            WHERE {or_parts[0].strip()}')
            for op in or_parts[1:]:
                lines.append(f'                OR {op.strip()}')
        else:
            lines.append(f'            WHERE {first_cond}')

        for cond in where_conditions[1:]:
            cond = cond.strip()
            # Check for parenthesized OR group
            if cond.startswith('(') and cond.endswith(')'):
                inner = cond[1:-1].strip()
                or_parts = _split_by_logical_op(inner, 'OR')
                if len(or_parts) > 1:
                    lines.append(f'                AND (')
                    lines.append(f'                    {or_parts[0].strip()}')
                    for op in or_parts[1:]:
                        lines.append(f'                    OR {op.strip()}')
                    lines.append(f'                )')
                    continue
            # Check for OR in this condition
            or_parts = _split_by_logical_op(cond, 'OR')
            if len(or_parts) > 1:
                lines.append(f'                AND {or_parts[0].strip()}')
                for op in or_parts[1:]:
                    lines.append(f'                OR {op.strip()}')
            else:
                lines.append(f'                AND {cond}')

    return '\n'.join(lines)


def _format_where_clause(where: str) -> List[str]:
    """Format WHERE clause with AND on new lines"""
    lines = []

    # Split by AND while respecting parentheses
    conditions = _split_by_logical_op(where, 'AND')

    if conditions:
        # Format first condition (may contain ORs)
        first_formatted = _format_condition_with_ors(conditions[0].strip(), 4)
        lines.append(f'    WHERE {first_formatted}')

        for cond in conditions[1:]:
            cond_formatted = _format_condition_with_ors(cond.strip(), 8)
            lines.append(f'        AND {cond_formatted}')

    return lines


def _format_condition_with_ors(condition: str, base_indent: int) -> str:
    """Format a condition that may contain multiple ORs"""
    import re

    # Check if this is a parenthesized group with multiple ORs
    # Handle case where there's a comment after the closing parenthesis
    trailing_comment = ''
    core_condition = condition

    if condition.startswith('('):
        # Find the matching closing parenthesis
        paren_depth = 0
        close_paren_pos = -1
        for i, char in enumerate(condition):
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
                if paren_depth == 0:
                    close_paren_pos = i
                    break

        if close_paren_pos > 0:
            # Extract trailing comment (if any)
            after_paren = condition[close_paren_pos + 1:].strip()
            if after_paren:
                # Check if it's a comment placeholder
                comment_match = re.match(r'^(__COMMENT_\d+__)', after_paren)
                if comment_match:
                    trailing_comment = ' ' + comment_match.group(1)
                    core_condition = condition[:close_paren_pos + 1]
                elif after_paren.startswith('--'):
                    trailing_comment = ' ' + after_paren
                    core_condition = condition[:close_paren_pos + 1]

    # Now check if core_condition is a parenthesized group
    if core_condition.startswith('(') and core_condition.endswith(')'):
        inner = core_condition[1:-1].strip()
        # Check if inner has multiple ORs at top level
        or_parts = _split_by_logical_op(inner, 'OR')
        if len(or_parts) > 1:
            # Format as multi-line OR group
            lines = ['(']
            for i, part in enumerate(or_parts):
                part_formatted = _format_condition_with_ands(part.strip(), base_indent + 4)
                if i == 0:
                    lines.append(f'{" " * (base_indent + 4)}{part_formatted}')
                else:
                    lines.append(f'{" " * (base_indent + 4)}OR {part_formatted}')
            lines.append(f'{" " * base_indent}){trailing_comment}')
            return '\n'.join(lines)

    # Check for multiple ORs without parens
    or_parts = _split_by_logical_op(condition, 'OR')
    if len(or_parts) > 2:  # More than 2 ORs, format on separate lines
        lines = []
        for i, part in enumerate(or_parts):
            if i == 0:
                lines.append(part.strip())
            else:
                lines.append(f'{" " * base_indent}OR {part.strip()}')
        return '\n'.join(lines)

    return condition


def _format_condition_with_ands(condition: str, base_indent: int) -> str:
    """Format a condition that may contain multiple ANDs"""
    and_parts = _split_by_logical_op(condition, 'AND')
    if len(and_parts) > 2:  # More than 2 ANDs, format on separate lines
        lines = []
        for i, part in enumerate(and_parts):
            if i == 0:
                lines.append(part.strip())
            else:
                lines.append(f'{" " * base_indent}AND {part.strip()}')
        return '\n'.join(lines)
    return condition


def _split_by_logical_op(sql: str, op: str) -> List[str]:
    """Split SQL by AND or OR, respecting parentheses and CASE blocks"""
    conditions = []
    current = ''
    paren_depth = 0
    case_depth = 0

    # Tokenize while preserving the operators
    tokens = re.split(rf'(\b{op}\b|\(|\)|\bCASE\b|\bEND\b)', sql, flags=re.IGNORECASE)

    for token in tokens:
        token_upper = token.upper() if token else ''

        if token == '(':
            paren_depth += 1
            current += token
        elif token == ')':
            paren_depth -= 1
            current += token
        elif token_upper == 'CASE':
            case_depth += 1
            current += token
        elif token_upper == 'END':
            case_depth -= 1
            current += token
        elif token_upper == op and paren_depth == 0 and case_depth == 0:
            if current.strip():
                conditions.append(current.strip())
            current = ''
        else:
            current += token

    if current.strip():
        conditions.append(current.strip())

    return conditions


def _split_by_and(sql: str) -> List[str]:
    """Split SQL by AND, respecting parentheses (kept for compatibility)"""
    return _split_by_logical_op(sql, 'AND')


def _reinsert_comments(formatted: str, comments: List[Dict]) -> str:
    """Re-insert comments at appropriate positions in formatted SQL"""
    if not comments:
        return formatted

    lines = formatted.split('\n')

    for comment in comments:
        sql_before = comment['sql_before']
        comment_text = comment['content']

        # Try to find a matching line in formatted output
        best_match_idx = -1
        best_match_score = 0

        for i, line in enumerate(lines):
            # Calculate similarity score
            score = _calculate_match_score(sql_before, line)
            if score > best_match_score:
                best_match_score = score
                best_match_idx = i

        # Insert comment if we found a good match
        if best_match_idx >= 0 and best_match_score > 0.3:
            line = lines[best_match_idx]
            # Don't add comment if line already has one
            if '--' not in line and '/*' not in line:
                lines[best_match_idx] = line.rstrip() + '  ' + comment_text

    return '\n'.join(lines)


def _calculate_match_score(original: str, formatted: str) -> float:
    """Calculate how well the formatted line matches the original SQL fragment"""
    # Extract key identifiers
    orig_words = set(re.findall(r'[\w\.]+', original.lower()))
    form_words = set(re.findall(r'[\w\.]+', formatted.lower()))

    # Remove common SQL keywords
    keywords = {'select', 'from', 'where', 'and', 'or', 'as', 'case', 'when', 'then', 'else', 'end', 'on', 'join', 'left', 'right', 'inner'}
    orig_words -= keywords
    form_words -= keywords

    if not orig_words:
        return 0

    # Calculate Jaccard similarity
    intersection = orig_words & form_words
    union = orig_words | form_words

    if not union:
        return 0

    return len(intersection) / len(union)


def _uppercase_keywords(sql: str) -> str:
    """Convert SQL keywords to uppercase"""
    keywords = [
        'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'EXISTS',
        'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN', 'JOIN', 'ON',
        'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'DISTRIBUTE BY',
        'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'AS', 'IS', 'NULL',
        'LIKE', 'BETWEEN', 'DISTINCT', 'OVER', 'PARTITION BY',
        'ASC', 'DESC', 'NVL', 'CAST', 'SUBSTR', 'SUBSTRING',
        'LPAD', 'RPAD', 'ROW_NUMBER', 'COALESCE', 'RAND', 'CEIL'
    ]

    result = sql
    for keyword in sorted(keywords, key=len, reverse=True):
        pattern = r'\b' + re.escape(keyword) + r'\b'
        result = re.sub(pattern, keyword.upper(), result, flags=re.IGNORECASE)

    return result


def _split_by_semicolon(sql: str) -> List[str]:
    """按分号分割SQL，尊重括号和字符串"""
    statements = []
    current = ''
    depth = 0
    in_string = False
    string_char = None
    i = 0

    while i < len(sql):
        char = sql[i]

        # 处理字符串
        if char in ("'", '"') and (i == 0 or sql[i-1] != '\\'):
            if not in_string:
                in_string = True
                string_char = char
            elif char == string_char:
                in_string = False
            current += char
            i += 1
            continue

        if in_string:
            current += char
            i += 1
            continue

        # 处理括号
        if char == '(':
            depth += 1
            current += char
        elif char == ')':
            depth -= 1
            current += char
        elif char == ';' and depth == 0:
            if current.strip():
                statements.append(current.strip())
            current = ''
        else:
            current += char

        i += 1

    if current.strip():
        statements.append(current.strip())

    return statements


# For compatibility with existing code
class SQLFormatterV4:
    """SQL Formatter V4 - Enhanced version"""

    def __init__(self, indent_spaces: int = 4, max_line_length: int = 250):
        self.indent_spaces = indent_spaces
        self.max_line_length = max_line_length

    def format(self, sql: str, **options) -> str:
        return format_sql_v4(sql, **options)
