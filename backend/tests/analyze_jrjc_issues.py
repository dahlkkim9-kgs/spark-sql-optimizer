# -*- coding: utf-8 -*-
"""
分析 JRJC 测试文件中的格式化问题
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 读取原始文件
test_file = r"C:\Users\61586\Desktop\自用工作文件\deepseek\测试文件\测试用例表\JRJC_MON_B01_T18_GRKHXX.sql"
with open(test_file, 'r', encoding='utf-8') as f:
    original = f.read()

# 读取格式化后的文件
formatted_file = r"C:\Users\61586\Desktop\自用工作文件\deepseek\测试文件\测试用例表\JRJC_MON_B01_T18_GRKHXX_formatted.sql"
with open(formatted_file, 'r', encoding='utf-8') as f:
    formatted = f.read()

print("=" * 80)
print("问题分析")
print("=" * 80)

# 问题1: LATERAL VIEW 换行
print("\n【问题1】LATERAL VIEW 未正确换行")
print("-" * 80)
print("原始 (486-489行):")
for i in range(485, 490):
    print(f"{i+1:3d}: {original.split(chr(10))[i]}")
print()
print("格式化后 (650-652行):")
for i in range(649, 654):
    print(f"{i+1:3d}: {formatted.split(chr(10))[i]}")
print()
print("❌ 问题: 两个 LATERAL VIEW 被压缩到同一行，应该分成两行")

# 问题2: HAVING 丢失
print("\n【问题2】HAVING 子句丢失")
print("-" * 80)
print("原始 (490-494行):")
for i in range(489, 494):
    print(f"{i+1:3d}: {original.split(chr(10))[i]}")
print()
print("格式化后应该有 HAVING，但:")
if 'HAVING' in formatted[60000:]:  # 检查 LATERAL VIEW + 嵌套部分
    print("✅ 找到 HAVING")
    for i, line in enumerate(formatted.split('\n')[640:660], 641):
        if 'HAVING' in line:
            print(f"  行 {i}: {line}")
else:
    print("❌ HAVING 子句完全丢失！")

# 问题3: GROUP BY 换行
print("\n【问题3】GROUP BY 未正确换行")
print("-" * 80)
print("原始 (490-493行):")
for i in range(489, 494):
    print(f"{i+1:3d}: {original.split(chr(10))[i]}")
print()
print("格式化后 (653行):")
print(f"653: {formatted.split(chr(10))[652]}")
print()
print("❌ 问题: 跨行的 GROUP BY 被压缩成单行")

print("\n" + "=" * 80)
print("总结")
print("=" * 80)
print("需要修复的问题:")
print("1. LATERAL VIEW 应该每个独占一行")
print("2. HAVING 子句必须保留")
print("3. GROUP BY 应该保持跨行格式（如果原始是跨行的）")
