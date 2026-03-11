# -*- coding: utf-8 -*-
import re
import sys

# 清除模块缓存
for mod in list(sys.modules.keys()):
    if 'backend' in mod or 'formatter' in mod:
        del sys.modules[mod]

from backend.core.formatter_v4_fixed import _normalize_single_field

# 输入
select_content = " 'A' ACTIONTYPE, 'B' ACTIONDESC\n,2 d0115__COMMENT_0__\n,NULL d0116__COMMENT_1__\n,NULL d0117__COMMENT_2__\n"
from_keyword = 'FROM'
rest_of_sql = ' (SELECT curr_type curr_type, SUM(dr_crt_bal) su_bal\nFROM table2)'

# 分割字段（简化版，假设已经处理完成）
# 直接使用处理后的字段
normalized_fields = [
    "'A' AS ACTIONTYPE",
    "'B' AS ACTIONDESC",
    '2 AS d0115__COMMENT_0__',
    'NULL AS d0116__COMMENT_1__',
    'NULL AS d0117  __COMMENT_2__'
]

print('=== 处理后的字段 ===')
for i, field in enumerate(normalized_fields):
    print(f'字段 {i+1}: {repr(field)}')

# 重组
result = 'SELECT '
for i, field in enumerate(normalized_fields):
    if i == 0:
        result += field
    else:
        if field.strip().startswith(','):
            result += field
        else:
            result += ',\n' + field

print()
print('=== 重组后的 SELECT 部分 ===')
print(repr(result))

print()
print('=== 添加 FROM 后 ===')
result += f' {from_keyword} {rest_of_sql}'
print(result)
