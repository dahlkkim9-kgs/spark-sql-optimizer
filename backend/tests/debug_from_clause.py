# -*- coding: utf-8 -*-
"""调试 FROM 子句处理"""
import sys
import io
import re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 完整的原始 SQL
test_sql = """SELECT *
FROM (
    SELECT *
    FROM rhbs_work.RHZF_GRKHJCXX_$TXDATE_XYK
    WHERE khzjdm NOT IN (
        SELECT DISTINCT khzjdm
        FROM rhbs_work.RHZF_GRKHJCXX_$TXDATE_XD
    )
) xyk;"""

print("=" * 80)
print("FROM 子句处理调试")
print("=" * 80)
print(f"原始SQL:\n{test_sql}\n")

# 第一层：保护子查询
print("第一层: 保护外层子查询")
protected_sql = test_sql
placeholders_1 = {}
paren_depth = 0
paren_start = -1
i = 0

while i < len(protected_sql):
    if protected_sql[i] == '(':
        if paren_depth == 0:
            paren_start = i
        paren_depth += 1
    elif protected_sql[i] == ')':
        paren_depth -= 1
        if paren_depth == 0 and paren_start >= 0:
            paren_content = protected_sql[paren_start:i+1]
            if re.search(r'\bSELECT\b', paren_content, re.IGNORECASE):
                placeholder = f"__SUBQUERY_{len(placeholders_1)}__"
                placeholders_1[placeholder] = paren_content
                protected_sql = protected_sql[:paren_start] + placeholder + protected_sql[i+1:]
                i = -1
                paren_depth = 0
                paren_start = -1
    i += 1

print(f"保护后的SQL: {protected_sql}")
print(f"占位符: {list(placeholders_1.keys())}")
print()

# 解析 FROM 子句
print("解析 FROM 子句:")
clause_pattern = r'\b(SELECT|FROM|LEFT\s+JOIN|RIGHT\s+JOIN|INNER\s+JOIN|CROSS\s+JOIN|JOIN|WHERE|GROUP\s+BY|ORDER\s+BY|DISTRIBUTE\s+BY|HAVING|LIMIT)\b'
matches = list(re.finditer(clause_pattern, protected_sql, re.IGNORECASE))

for i, match in enumerate(matches):
    clause_type = match.group(1).upper()
    if clause_type == 'FROM':
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(protected_sql)
        raw_content = protected_sql[start:end]
        clause_content = raw_content.strip().rstrip(',')

        print(f"FROM 子句内容: {repr(clause_content)}")

        # 这个内容包含 __SUBQUERY_0__ xyk;
        # 需要恢复占位符
        if '__SUBQUERY_' in clause_content:
            print(f"包含子查询占位符")

            for placeholder, original in placeholders_1.items():
                if placeholder in clause_content:
                    print(f"  占位符: {placeholder}")
                    print(f"  原始内容: {repr(original[:100])}")

                    # 查找占位符位置
                    placeholder_pos = clause_content.find(placeholder)
                    before_placeholder = clause_content[:placeholder_pos]
                    after_placeholder = clause_content[placeholder_pos + len(placeholder):]

                    print(f"  占位符前: {repr(before_placeholder)}")
                    print(f"  占位符后: {repr(after_placeholder)}")

                    # 这里 before_placeholder 应该是空的（因为 FROM __SUBQUERY_0__ xyk）
                    # after_placeholder 应该是 'xyk;'

                    # 注意：这里的问题！
                    # 恢复占位符时，会把整个子查询格式化，然后替换回来
                    # 但是 after_placeholder ('xyk;') 应该怎么处理？

                    # 从第 2488-2491 行的代码：
                    # if clause_type == 'FROM' and placeholder_pos == 0:
                    #     subquery_indent = '      '  # 6 个空格
                    #     close_paren_indent = '     '   # 5 个空格

                    # 这里检查 clause_type == 'FROM'，但实际传入的是 'FROM' 字符串，不是 'FROM'
                    # 让我检查一下...

        break
print()

# 检查测试输出中的问题
print("=" * 80)
print("分析实际测试输出的问题:")
print()
print("实际输出:")
actual_output = """SELECT *
FROM (
      SELECT *
      FROM rhbs_work.RHZF_GRKHJCXX_$TXDATE_XYK
      WHERE khzjdm NOT IN (
          SELECT DISTINCT khzjdm
          FROM rhbs_work.RHZF_GRKHJCXX_$TXDATE_XD
         )
      WHERE khzjdm NOT IN (
     ) xyk
 ;"""
print(actual_output)
print()

print("问题分析:")
print("1. 外层子查询格式化后应该包含:")
print("   - SELECT *")
print("   - FROM ...")
print("   - WHERE khzjdm NOT IN (...)")
print("2. 但实际输出中出现了两次 'WHERE khzjdm NOT IN ('")
print("3. 最后的 ') xyk' 应该是外层子查询的闭括号和别名")
print()
print("可能的问题:")
print("- 占位符恢复时，外层子查询的内容没有正确恢复")
print("- 或者递归格式化时，内层子查询的占位符没有被正确恢复")
