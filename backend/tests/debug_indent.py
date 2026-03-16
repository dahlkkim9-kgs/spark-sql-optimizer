# -*- coding: utf-8 -*-
"""调试括号对齐计算"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 测试字符串
before_placeholder = "WHERE customer_id IN "
print(f"before_placeholder: '{before_placeholder}'")
print(f"长度: {len(before_placeholder)}")
print(f"位置: ", end="")
for i, char in enumerate(before_placeholder):
    print(f"{i}:{char} ", end="")
print()

# 模拟计算
open_paren_pos = len(before_placeholder)
print(f"开括号位置: {open_paren_pos}")

# 预期缩进
subquery_indent = ' ' * (open_paren_pos + 1)
print(f"缩进空格数: {len(subquery_indent)}")
print(f"缩进字符串: '{subquery_indent}'")

# 实际输出应该是在前面加上 WHERE 子句的缩进（0）
# 所以总缩进 = 0 + open_paren_pos + 1 = 22
print(f"总缩进应该是: {0 + open_paren_pos + 1} 个空格")
