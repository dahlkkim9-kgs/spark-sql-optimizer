# -*- coding: utf-8 -*-
"""
使用 JRJC_MON_B01_T18_GRKHXX.sql 全面测试格式化器
检查：注释保留、缩进正确性、语法结构保持
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, '../core')

from formatter_v4_fixed import format_sql_v4_fixed

# 读取测试文件
test_file = r"C:\Users\61586\Desktop\自用工作文件\deepseek\测试文件\测试用例表\JRJC_MON_B01_T18_GRKHXX.sql"

with open(test_file, 'r', encoding='utf-8') as f:
    original_sql = f.read()

print("=" * 80)
print("全面格式化测试 - JRJC_MON_B01_T18_GRKHXX.sql")
print("=" * 80)
print(f"原始文件行数: {len(original_sql.split(chr(10)))}")
print()

# 执行格式化
formatted_sql = format_sql_v4_fixed(original_sql)

# 统计信息
original_lines = original_sql.split('\n')
formatted_lines = formatted_sql.split('\n')

print(f"格式化后行数: {len(formatted_lines)}")
print()

# 检查注释保留
print("=" * 80)
print("注释保留检查")
print("=" * 80)

# 块注释
original_block_comments = [line for line in original_lines if line.strip().startswith('/*') or line.strip().endswith('*/') or ('/*' in line and '*/' in line)]
# 单行注释
original_line_comments = [line for line in original_lines if '--' in line]

formatted_block_comments = [line for line in formatted_lines if '/*' in line]
formatted_line_comments = [line for line in formatted_lines if '--' in line]

print(f"原始块注释数量: {len(original_block_comments)}")
print(f"格式化后块注释数量: {len(formatted_block_comments)}")
print(f"原始单行注释数量: {len(original_line_comments)}")
print(f"格式化后单行注释数量: {len(formatted_line_comments)}")
print()

# 检查关键语句类型
print("=" * 80)
print("关键语句检查")
print("=" * 80)

statements = {
    'DROP TABLE': 'DROP TABLE',
    'CREATE TABLE': 'CREATE TABLE',
    'INSERT INTO': 'INSERT INTO',
    'SELECT': 'SELECT',
    'FROM': 'FROM',
    'WHERE': 'WHERE',
    'LEFT JOIN': 'LEFT JOIN',
    'INNER JOIN': 'INNER JOIN',
    'UNION ALL': 'UNION ALL',
    'WITH AS': 'WITH',
    'CACHE TABLE': 'CACHE TABLE',
    'LATERAL VIEW': 'LATERAL VIEW',
    'OVER': 'OVER',
    'PARTITION BY': 'PARTITION BY',
    'CASE WHEN': 'CASE',
    'GROUP BY': 'GROUP BY',
    'HAVING': 'HAVING',
    'ORDER BY': 'ORDER BY',
    'DISTRIBUTE BY': 'DISTRIBUTE BY'
}

for stmt_name, stmt_keyword in statements.items():
    original_count = sum(1 for line in original_lines if stmt_keyword in line.upper())
    formatted_count = sum(1 for line in formatted_lines if stmt_keyword in line.upper())
    status = "✅" if original_count == formatted_count else "❌"
    print(f"{status} {stmt_name}: 原始={original_count}, 格式化={formatted_count}")

print()
print("=" * 80)
print("缩进分析（前50行）")
print("=" * 80)

for i, line in enumerate(formatted_lines[:50], 1):
    if line.strip():
        indent = len(line) - len(line.lstrip())
        # 显示关键行
        if any(keyword in line.upper() for keyword in ['DROP', 'CREATE', 'INSERT', 'SELECT', 'FROM', 'WHERE', 'JOIN', 'UNION', 'WITH', 'CACHE', 'LATERAL VIEW', 'OVER', 'CASE', 'GROUP', 'HAVING', 'ORDER', 'DISTRIBUTE']) or '--' in line or '/*' in line:
            print(f"行 {i:3d} ({indent:2d}空格): {line[:80]}")

# 输出完整格式化结果到文件
output_file = r"C:\Users\61586\Desktop\自用工作文件\deepseek\测试文件\测试用例表\JRJC_MON_B01_T18_GRKHXX_formatted.sql"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(formatted_sql)

print()
print("=" * 80)
print(f"完整格式化结果已保存到: {output_file}")
print("=" * 80)
