# -*- coding: utf-8 -*-
"""测试列对齐逻辑修复"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_column_alignment_with_comment():
    """测试带注释的列对齐"""
    from formatter_v5_sqlglot import SQLFormatterV5

    formatter = SQLFormatterV5()

    # sqlglot 输出格式（模拟）
    sql = """SELECT
  a, /* comment */
  b
FROM t1"""

    result = formatter._apply_v4_column_style(sql)

    # 验证：没有 AS AS
    assert "AS AS" not in result, f"发现 AS AS 错误: {repr(result)}"
    # 验证：注释保留
    assert "/* comment */" in result or "-- comment" in result
    # 验证：没有重复的逗号
    assert result.count(',') <= 2, f"逗号数量异常: {repr(result)}"
    print("✅ 列对齐测试通过")
    print(f"结果:\n{result}")

def test_column_alignment_with_dash_comment():
    """测试带 -- 注释的列对齐"""
    from formatter_v5_sqlglot import SQLFormatterV5

    formatter = SQLFormatterV5()

    # -- 注释格式
    sql = """SELECT
  a, -- comment
  b
FROM t1"""

    result = formatter._apply_v4_column_style(sql)

    # 验证：没有 AS AS
    assert "AS AS" not in result, f"发现 AS AS 错误: {repr(result)}"
    # 验证：注释保留
    assert "-- comment" in result
    print("✅ -- 注释列对齐测试通过")
    print(f"结果:\n{result}")

def test_multiple_columns_with_comments():
    """测试多列带注释"""
    from formatter_v5_sqlglot import SQLFormatterV5

    formatter = SQLFormatterV5()

    sql = """SELECT
  a, /* comment 1 */
  b, /* comment 2 */
  c
FROM t1"""

    result = formatter._apply_v4_column_style(sql)

    # 验证：没有 AS AS
    assert "AS AS" not in result, f"发现 AS AS 错误: {repr(result)}"
    # 验证：注释保留
    assert "/* comment 1 */" in result
    assert "/* comment 2 */" in result
    print("✅ 多列注释测试通过")
    print(f"结果:\n{result}")

if __name__ == "__main__":
    print("=" * 60)
    print("测试列对齐逻辑修复")
    print("=" * 60)
    print()

    try:
        test_column_alignment_with_comment()
        print()
        test_column_alignment_with_dash_comment()
        print()
        test_multiple_columns_with_comments()
        print()
        print("=" * 60)
        print("所有测试通过！")
        print("=" * 60)
    except AssertionError as e:
        print(f"❌ 测试失败: {e}")
        sys.exit(1)
