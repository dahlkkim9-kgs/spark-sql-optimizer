# -*- coding: utf-8 -*-
"""分析反斜杠边界情况"""

# 分析这个问题
sql = 'ON col = "value\\" WHEN MATCHED'
print('Input:', sql)
print('Length:', len(sql))
print()

# 模拟 _find_keyword_outside_strings 的逻辑
i = 0
in_single_quote = False
in_double_quote = False
n = len(sql)

while i < n:
    char = sql[i]
    print(f'i={i}, char="{char}", in_single_quote={in_single_quote}, in_double_quote={in_double_quote}')

    # 处理转义字符
    if char == '\\' and i + 1 < n:
        print(f'  Found backslash at {i}, skipping to {i+2}')
        # 跳过转义字符和下一个字符
        i += 2
        continue

    # 处理字符串字面量
    if char == "'" and not in_double_quote:
        in_single_quote = not in_single_quote
        i += 1
        continue
    elif char == '"' and not in_single_quote:
        in_double_quote = not in_double_quote
        i += 1
        continue

    # 如果在字符串内，跳过
    if in_single_quote or in_double_quote:
        i += 1
        continue

    # 在字符串外，检查 WHEN
    if sql[i:i+4] == 'WHEN':
        print(f'  Found WHEN at {i}!')
        break

    i += 1
