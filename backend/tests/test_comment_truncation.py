# -*- coding: utf-8 -*-
"""
测试注释截断问题
"""
import sys
import io
import os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from formatter_v4_fixed import format_sql_v4_fixed

# 测试案例1: 长注释
test1 = """--4. UNION + 嵌套 + CASE
SELECT a FROM t1;"""

# 测试案例2: 注释中间有空格
test2 = """-- 这是一个很长的注释，包含很多文字和符号
SELECT a FROM t1;"""

# 测试案例3: 多个注释
test3 = """-- 第一个注释
-- 第二个注释
SELECT a FROM t1;"""

# 测试案例4: 带特殊字符的注释
test4 = """--4. UNION + 嵌套 + CASE @#$%
SELECT a FROM t1;"""

# 测试案例5: 行内注释
test5 = """SELECT a -- 这是行内注释
FROM t1;"""

def test_comment_preservation():
    print("=" * 80)
    print("注释保留测试")
    print("=" * 80)
    print()

    tests = [
        ("长注释", test1),
        ("注释中间有空格", test2),
        ("多个注释", test3),
        ("带特殊字符的注释", test4),
        ("行内注释", test5),
    ]

    for test_name, test_sql in tests:
        print(f"【测试】{test_name}")
        print("-" * 80)
        print("原始SQL:")
        print(test_sql)
        print()
        result = format_sql_v4_fixed(test_sql)
        print("格式化结果:")
        print(result)
        print()

        # 检查注释是否完整保留
        original_comments = [line for line in test_sql.split('\n') if line.strip().startswith('--')]
        formatted_comments = [line for line in result.split('\n') if line.strip().startswith('--')]

        if len(original_comments) == len(formatted_comments):
            print(f"✅ 注释数量匹配: {len(original_comments)} 个")
            for i, (orig, fmt) in enumerate(zip(original_comments, formatted_comments)):
                if orig.strip() == fmt.strip():
                    print(f"  ✓ 注释 {i+1} 完整保留: {orig}")
                else:
                    print(f"  ❌ 注释 {i+1} 被修改:")
                    print(f"    原始: {orig}")
                    print(f"    格式化: {fmt}")
        else:
            print(f"❌ 注释数量不匹配: 原始 {len(original_comments)} 个，格式化后 {len(formatted_comments)} 个")
        print()

if __name__ == "__main__":
    test_comment_preservation()
