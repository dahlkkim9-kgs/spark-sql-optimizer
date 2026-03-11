#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import urllib.request
import json
import sys

if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# 测试原始用户SQL（去掉注释）
sql = """CREATE TABLE IF NOT EXISTS RA03.CTB_CREDIT_G03_jjk_sumg0306_{DATA_DT} AS
SELECT
 g0301
,g0302
,g0303
,g0304
,g0305
,SUM(g0306) G0306
FROM RA03.CTB_CREDIT_G03_temp_type_new_{DATA_DT} a
WHERE g0305  IN ('0','1','2','3','4','5','6','7','8','9','10','11','12','13')
AND G0306<>0
AND g0302 NOT IN ('ZZZ','BVT','UMI','PCN','IOT','SGS','ATA','HMD','ATF')
GROUP BY
 g0301
,g0302
,g0303
,g0304
,g0305
"""

req = urllib.request.Request(
    'http://127.0.0.1:8888/format/v4fixed',
    data=json.dumps({'sql': sql, 'keyword_case': 'upper'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)

with urllib.request.urlopen(req, timeout=30) as response:
    data = json.loads(response.read().decode('utf-8'))
    if data.get('success'):
        print("=== 用户原始 SQL 格式化结果 ===")
        result = data.get('formatted', '')
        print(result)
        print()
        print("=== 逐行检查（前30行）===")
        lines = result.split('\n')
        for i, line in enumerate(lines[:30], 1):
            print(f"{i:2d}: [{repr(line)}]")
