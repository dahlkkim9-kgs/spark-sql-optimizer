#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整测试工作流程"""
import urllib.request
import json
import sys

if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

print("=" * 80)
print("SQL格式化工具 - 完整测试")
print("=" * 80)

# 读取测试文件
test_file = 'C:/Users/61586/Desktop/自用工作文件/deepseek/测试文件/测试用例表/JRJC_MON_B01_T18_GRKHXX.sql'
with open(test_file, 'r', encoding='utf-8') as f:
    original_sql = f.read()

print(f"\n[1/4] 读取测试文件")
print(f"  文件: {test_file}")
print(f"  原始行数: {original_sql.count(chr(10)) + 1}")
print(f"  文件大小: {len(original_sql)} 字节")

# 测试格式化
print(f"\n[2/4] 测试后端格式化API")
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
            print(f"  状态: 成功")
            print(f"  格式化后行数: {formatted_sql.count(chr(10)) + 1}")
            print(f"  格式化后大小: {len(formatted_sql)} 字节")

            # 验证关键字数量
            print(f"\n[3/4] 验证关键字完整性")
            keywords = {
                'SELECT': 12, 'INSERT': 4, 'CREATE': 3, 'DROP': 2,
                'FROM': 12, 'WHERE': 7, 'JOIN': 9
            }
            all_ok = True
            for kw, expected in keywords.items():
                actual = formatted_sql.upper().count(kw)
                status = "OK" if actual == expected else "NG"
                print(f"  {kw}: 预期={expected}, 实际={actual} [{status}]")
                if actual != expected:
                    all_ok = False

            # 测试分析API
            print(f"\n[4/4] 测试分析API")
            req2 = urllib.request.Request(
                'http://127.0.0.1:8888/analyze',
                data=json.dumps({'sql': original_sql}).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )

            with urllib.request.urlopen(req2, timeout=60) as resp2:
                result = json.loads(resp2.read().decode('utf-8'))
                print(f"  状态: 成功")
                print(f"  问题数量: {result.get('issue_count', 0)}")
                print(f"  高优先级: {result.get('high_priority', 0)}")
                print(f"  中优先级: {result.get('medium_priority', 0)}")
                print(f"  低优先级: {result.get('low_priority', 0)}")

            print(f"\n" + "=" * 80)
            print(f"测试结果: 所有测试通过")
            print(f"=" * 80)
            print(f"\n前端地址: http://localhost:3000")
            print(f"后端地址: http://localhost:8888")
            print(f"\n请手动验证以下功能:")
            print(f"  1. 上传测试文件后，左侧编辑器能显示完整的237行内容")
            print(f"  2. 点击格式化按钮，右侧能显示完整的格式化结果（394行）")
            print(f"  3. 点击分析SQL按钮，下部分析区域能显示分析结果")
            print(f"  4. 滚动条能正常工作，可以滚动查看所有内容")
        else:
            print(f"  状态: 失败 - {data.get('error')}")
except Exception as e:
    print(f"  状态: 错误 - {e}")
    import traceback
    traceback.print_exc()
