#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试前端显示功能"""
import urllib.request
import json
import sys

# 设置标准输出编码为 UTF-8
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# 读取测试文件
with open('C:/Users/61586/Desktop/自用工作文件/deepseek/测试文件/测试用例表/JRJC_MON_B01_T18_GRKHXX.sql', 'r', encoding='utf-8') as f:
    original_sql = f.read()

original_lines = original_sql.count('\n') + 1
print(f"原始 SQL 行数: {original_lines}")
print(f"原始 SQL 长度: {len(original_sql)} 字符")
print()

# 测试格式化
print("正在格式化...")
req = urllib.request.Request(
    'http://127.0.0.1:8888/format/v4fixed',
    data=json.dumps({'sql': original_sql, 'keyword_case': 'upper'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req, timeout=60) as response:
        data = json.loads(response.read().decode('utf-8'))
        if data.get('success'):
            formatted_sql = data.get('formatted', '')
            formatted_lines = formatted_sql.count('\n') + 1
            print(f"[OK] 格式化成功")
            print(f"格式化后行数: {formatted_lines}")
            print(f"格式化后长度: {len(formatted_sql)} 字符")
            print()

            # 检查格式化结果的完整性
            print("检查格式化结果完整性:")
            print(f"  - 原始文件包含的关键字:")
            keywords = ['SELECT', 'INSERT', 'CREATE', 'DROP', 'FROM', 'WHERE', 'JOIN']
            for kw in keywords:
                orig_count = original_sql.upper().count(kw)
                fmt_count = formatted_sql.upper().count(kw)
                match = "[OK]" if orig_count == fmt_count else "[FAIL]"
                print(f"    {match} {kw}: 原始={orig_count}, 格式化={fmt_count}")
            print()

            # 显示格式化结果的前50行
            print("格式化结果预览（前50行）:")
            print("=" * 80)
            lines = formatted_sql.split('\n')
            for i, line in enumerate(lines[:50], 1):
                print(f"{i:3d}: {line}")
            print("=" * 80)
            print(f"... (共 {len(lines)} 行)")

            # 保存格式化结果到文件
            with open('test_formatted_output.sql', 'w', encoding='utf-8') as out:
                out.write(formatted_sql)
            print(f"\n格式化结果已保存到: test_formatted_output.sql")
        else:
            print(f"[FAIL] 格式化失败: {data.get('error')}")
except Exception as e:
    print(f"[ERROR] API 错误: {e}")
    import traceback
    traceback.print_exc()
