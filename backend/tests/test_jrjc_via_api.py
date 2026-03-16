# -*- coding: utf-8 -*-
"""
通过 /format/v5 API 端点测试 JRJC SQL 文件
"""
import sys
import io
import urllib.request
import json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 读取测试文件
test_file = r"C:\Users\61586\Desktop\自用工作文件\deepseek\测试文件\测试用例表\JRJC_MON_B01_T18_GRKHXX.sql"
with open(test_file, 'r', encoding='utf-8') as f:
    original_sql = f.read()

print("通过 /format/v5 API 端点测试 JRJC SQL 文件")
print("=" * 80)

# 调用 API
data = json.dumps({'sql': original_sql, 'keyword_case': 'upper'}).encode('utf-8')
req = urllib.request.Request(
    'http://127.0.0.1:8888/format/v5',
    data=data,
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req, timeout=60) as response:
        result = json.loads(response.read().decode('utf-8'))

        if result.get('success'):
            formatted_sql = result['formatted']

            # 保存结果
            output_file = r"C:\Users\61586\Desktop\自用工作文件\deepseek\测试文件\测试用例表\JRJC_MON_B01_T18_GRKHXX_v5_api.sql"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(formatted_sql)

            print(f"✅ 格式化成功")
            print(f"✅ 结果已保存到: {output_file}")

            # 检查关键元素
            original_lines = original_sql.split('\n')
            formatted_lines = formatted_sql.split('\n')

            print()
            print("关键元素检查:")
            print(f"  HAVING: 原始={sum(1 for l in original_lines if 'HAVING' in l.upper())}, 格式化={sum(1 for l in formatted_lines if 'HAVING' in l.upper())}")
            print(f"  LATERAL VIEW: 原始={sum(1 for l in original_lines if 'LATERAL VIEW' in l.upper())}, 格式化={sum(1 for l in formatted_lines if 'LATERAL VIEW' in l.upper())}")
            print(f"  GROUP BY: 原始={sum(1 for l in original_lines if 'GROUP BY' in l.upper())}, 格式化={sum(1 for l in formatted_lines if 'GROUP BY' in l.upper())}")

            # 检查 LATERAL VIEW + 嵌套部分
            print()
            print("LATERAL VIEW + 嵌套部分:")
            for i, line in enumerate(formatted_lines[630:660], 631):
                if 'LATERAL VIEW' in line or 'GROUP BY' in line or 'HAVING' in line:
                    print(f"  行 {i}: {line}")
        else:
            print(f"❌ 格式化失败: {result.get('error')}")
except Exception as e:
    print(f"❌ API 调用失败: {e}")
