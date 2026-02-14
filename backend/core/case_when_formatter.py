"""
CASE WHEN formatter - compliant with SQL development standards

规范要求：
1. CASE和END对齐
2. WHEN、THEN、ELSE换行对齐
3. 嵌套CASE需要缩进4个空格
"""

import re


def _find_next_keyword(content: str, start_pos: int = 0) -> int:
    """Find the next SQL keyword (WHEN, THEN, ELSE, END) starting from position"""
    keywords = ['WHEN', 'THEN', 'ELSE', 'END']
    min_pos = -1

    for keyword in keywords:
        pattern = r'\b' + keyword + r'\b'
        match = re.search(pattern, content[start_pos:], re.IGNORECASE)
        if match:
            pos = start_pos + match.start()
            if min_pos == -1 or pos < min_pos:
                min_pos = pos

    return min_pos if min_pos != -1 else len(content)


def _extract_then_value(content: str) -> tuple:
    """
    Extract THEN value until next keyword or end
    Returns (value, remaining_content)
    """
    # Find next keyword position
    next_kw_pos = _find_next_keyword(content)

    # Check for nested CASE in THEN value
    case_match = re.search(r'\bCASE\b', content[:next_kw_pos], re.IGNORECASE)
    if case_match:
        # Find matching END for nested CASE
        depth = 1
        i = case_match.end() - 1  # Start from "CASE" (adjust to after CASE)
        nested_start = case_match.start()

        while i < len(content) and depth > 0:
            char = content[i]
            # Simple check (not handling strings in nested CASE for now)
            if re.search(r'\bCASE\b', content[i:i+4], re.IGNORECASE):
                depth += 1
            elif re.search(r'\bEND\b', content[i:i+3], re.IGNORECASE):
                depth -= 1
            i += 1

        if depth == 0:
            nested_end = i - 1
            return content[:nested_end].strip(), content[nested_end:].strip()

    return content[:next_kw_pos].strip(), content[next_kw_pos:].strip()


def _format_case_recursive(content: str, indent: str) -> tuple:
    """
    Recursively format CASE statement.
    Returns (list of lines, remaining_content_after_END)
    """
    lines = []
    content = content.strip()

    # Skip "CASE" if present
    if content.upper().startswith('CASE '):
        content = content[5:].strip()

    while content:
        content = content.strip()

        # Check for END
        if content.upper().startswith('END'):
            content = content[3:].strip()
            break

        # Check for ELSE (might be at top level after all WHENs)
        if content.upper().startswith('ELSE'):
            else_value = content[4:].strip()
            # Find END after ELSE
            end_match = re.search(r'\bEND\b', else_value, re.IGNORECASE)
            if end_match:
                else_value = else_value[:end_match.start()].strip()
                content = else_value[end_match.end():]
            else:
                content = ''
            lines.append(indent + 'ELSE ' + else_value)
            continue

        # Find WHEN
        when_match = re.search(r'\bWHEN\b', content, re.IGNORECASE)
        if not when_match:
            break

        # Find THEN
        after_when = content[when_match.end():]
        then_match = re.search(r'\bTHEN\b', after_when, re.IGNORECASE)
        if not then_match:
            break

        # Extract WHEN condition
        when_cond = after_when[:then_match.start()].strip()

        # Check if THEN value contains nested CASE
        after_then = after_when[then_match.end():].strip()

        # Look ahead to check for CASE keyword in THEN value
        if after_then.upper().startswith('CASE '):
            # Use parenthesis-style matching for nested CASE
            # We need to find the matching END for the nested CASE
            depth = 1
            i = 5  # Start after "CASE" (the word itself, not including the space)
                   # Actually, we're checking after_then which starts with "CASE "
                   # So i should start at 5 to be after "CASE "

            while i < len(after_then):
                # Look for CASE keyword starting at position i
                # Need to check word boundary
                found_case = False
                found_end = False

                # Check for CASE (need 4 chars for "CASE")
                if i + 4 <= len(after_then):
                    # Check if substring matches CASE pattern with word boundary
                    if re.match(r'^CASE\b', after_then[i:i+5], re.IGNORECASE):
                        depth += 1
                        found_case = True

                # Check for END (need 3 chars for "END")
                if not found_case and i + 3 <= len(after_then):
                    if re.match(r'^END\b', after_then[i:i+4], re.IGNORECASE):
                        depth -= 1
                        found_end = True
                        if depth == 0:
                            # Found the matching END
                            i += 3  # Move past "END"
                            break

                i += 1

            # Extract nested CASE and remaining content
            nested_content = after_then[:i]
            remaining = after_then[i:].strip()

            # Recursively format nested CASE
            nested_lines, _ = _format_case_recursive(nested_content, indent + '    ')

            lines.append(indent + 'WHEN ' + when_cond)
            lines.append(indent + 'THEN')
            lines.extend(nested_lines)

            content = remaining
            continue

        # Not a nested CASE - find next keyword (WHEN, ELSE, END)
        next_when = re.search(r'\bWHEN\b', after_then, re.IGNORECASE)
        next_else = re.search(r'\bELSE\b', after_then, re.IGNORECASE)
        next_end = re.search(r'\bEND\b', after_then, re.IGNORECASE)

        next_pos = len(after_then)
        if next_when and next_when.start() < next_pos:
            next_pos = next_when.start()
        if next_else and next_else.start() < next_pos:
            next_pos = next_else.start()
        if next_end and next_end.start() < next_pos:
            next_pos = next_end.start()

        then_value = after_then[:next_pos].strip()
        content = after_then[next_pos:]

        lines.append(indent + 'WHEN ' + when_cond)
        lines.append(indent + '     THEN ' + then_value)

    return lines, content


def format_case_when(case_field: str, has_comma: bool = False) -> list:
    """
    Format a field containing CASE WHEN expression

    Args:
        case_field: The CASE WHEN expression to format
        has_comma: Whether there's a comma before this field (affects indentation)

    Returns:
        List of formatted lines
    """
    normalized = case_field.strip()

    # Extract inline comment if present (at the very end, after the alias)
    inline_comment = ''
    # Match comment at the end of the string
    comment_match = re.search(r'\s*--\s*[^\'"]*$', normalized)
    if comment_match:
        inline_comment = comment_match.group(0)
        normalized = normalized[:comment_match.start()].rstrip()

    # Extract alias after the outermost END
    # For nested CASE, we need to find the matching END for the outermost CASE
    # Count CASE/END pairs to find the correct outer END
    alias = ''
    case_count = 1  # Start with 1 for the outermost CASE
    i = 5  # Skip "CASE " at the beginning

    while i < len(normalized) and case_count > 0:
        # Check for nested CASE
        if re.search(r'\bCASE\b', normalized[i:i+4], re.IGNORECASE):
            case_count += 1
            i += 4
        # Check for END
        elif re.search(r'\bEND\b', normalized[i:i+3], re.IGNORECASE):
            case_count -= 1
            if case_count == 0:
                # Found the outermost END
                i += 3
                after_end = normalized[i:].strip()
                if after_end:
                    alias = ' ' + after_end
                # Keep only the CASE...END part for formatting
                normalized = normalized[:i].rstrip()
                break
            i += 3
        else:
            i += 1

    # If no END was found (shouldn't happen), try to find any END
    if case_count > 0:
        end_match = re.search(r'\bEND\b', normalized, re.IGNORECASE)
        if end_match:
            after_end = normalized[end_match.end():].strip()
            if after_end:
                alias = ' ' + after_end
            normalized = normalized[:end_match.end()].rstrip()

    # Remove outer parentheses
    if normalized.startswith('(') and normalized.endswith(')'):
        normalized = normalized[1:-1].strip()

    # Base indent (matches the formatter's field indentation)
    base_indent = '            ' if has_comma else '       '

    # Check if this is a CASE expression
    if not normalized.upper().startswith('CASE '):
        # Not a CASE expression, return as-is
        return [base_indent + normalized + alias + inline_comment]

    # Add CASE line
    lines = [base_indent + 'CASE']

    # Use the recursive formatter for all CASE statements (handles both simple and nested)
    formatted_lines, _ = _format_case_recursive(normalized, base_indent + '    ')
    lines.extend(formatted_lines)

    # Add END line with alias and comment
    lines.append(base_indent + 'END' + alias + inline_comment)

    return lines
