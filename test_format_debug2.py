#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import urllib.request
import json
import sys

if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# 测试多行逗号前置的 SELECT 语句
sql = """SELECT
 g0301
,g0302
,g0303
FROM t1"""

req = urllib.request.Request(
    'http://127.0.0.1:8888/format/v4fixed',
    data=json.dumps({'sql': sql, 'keyword_case': 'upper'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)

with urllib.request.urlopen(req, timeout=30) as response:
    data = json.loads(response.read().decode('utf-8'))
    if data.get('success'):
        print("=== 多行逗号前置 SELECT 格式化结果 ===")
        result = data.get('formatted', '')
        print(result)
        print()
        print("=== 逐行检查 ===")
        lines = result.split('\n')
        for i, line in enumerate(lines, 1):
            print(f"{i:2d}: [{repr(line)}]")
