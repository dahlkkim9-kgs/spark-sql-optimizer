# -*- coding: utf-8 -*-
import re

# 简单的测试
select_content = " 'A' ACTIONTYPE, 'B' ACTIONDESC\n,2 d0115__COMMENT_0__\n"

print(f'select_content: {repr(select_content)}')
print(f'select_content 长度: {len(select_content)}')
print()

# 分割字段
fields = []
current = ''
paren_depth = 0
in_string = False
string_char = None
iteration = 0
max_iterations = 1000

i = 0
while i < len(select_content) and iteration < max_iterations:
    iteration += 1
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
            # 跳过逗号后面的空白字符
            while i < len(select_content) and select_content[i].isspace():
                i += 1
            # 如果到达末尾
            if i >= len(select_content):
                field = current.strip()
                if field:
                    fields.append(field)
                current = ''
                break
            # 回退一个字符
            i -= 1
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

print(f'迭代次数: {iteration}')
print('=== 分割后的字段 ===')
for i, field in enumerate(fields):
    print(f'字段 {i+1}: {repr(field)}')

if iteration >= max_iterations:
    print('警告: 达到最大迭代次数！')
