# -*- coding: utf-8 -*-
import re
import sys

# 清除模块缓存
for mod in list(sys.modules.keys()):
    if 'backend' in mod or 'formatter' in mod:
        del sys.modules[mod]

from backend.core.formatter_v4_fixed import _normalize_single_field

# 实际的 select_content
select_content = " 'A' ACTIONTYPE, 'B' ACTIONDESC\n,2 d0115__COMMENT_0__\n,NULL d0116__COMMENT_1__\n,NULL d0117__COMMENT_2__\n"

print(f'select_content: {repr(select_content)}')
print(f'select_content 长度: {len(select_content)}')
print()

# 分割字段
fields = []
current = ''
paren_depth = 0
in_string = False
string_char = None

i = 0
while i < len(select_content):
    char = select_content[i]

    if char in ("'", '"') and (i == 0 or select_content[i-1] != '\\'):
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

    if char == '(':
        paren_depth += 1
        current += char
    elif char == ')':
        paren_depth -= 1
        current += char
    elif char == ',' and paren_depth == 0:
        rest = select_content[i + 1:]
        comment_match = re.match(r'\s*([^\n]*--.*)', rest)
        comment_placeholder_match = re.match(r'\s*(__COMMENT_\d+__)', rest)
        if comment_match:
            current += char + comment_match.group(0)
            i += len(comment_match.group(0)) + 1
        elif comment_placeholder_match:
            current += char + comment_placeholder_match.group(0)
            i += len(comment_placeholder_match.group(0)) + 1
        else:
            current += char
            i += 1
        field = current.strip()
        if field:
            fields.append(field)
        current = ''
        continue
    else:
        current += char
    i += 1

if current.strip():
    fields.append(current.strip())

print('=== 分割后的字段 ===')
for i, field in enumerate(fields):
    print(f'字段 {i+1}: {repr(field)}')

# 处理每个字段
normalized_fields = []
for field in fields:
    normalized = _normalize_single_field(field)
    normalized_fields.append(normalized)

print()
print('=== 处理后的字段 ===')
for i, field in enumerate(normalized_fields):
    print(f'字段 {i+1}: {repr(field)}')
