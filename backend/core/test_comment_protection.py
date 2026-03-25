# -*- coding: utf-8 -*-
"""测试注释保护功能"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_protect_line_comments():
    """测试 -- 注释保护"""
    from formatter_v5_sqlglot import SQLFormatterV5

    formatter = SQLFormatterV5()
    sql = "SELECT a, --注释\nb FROM t1"

    protected, comments = formatter._protect_line_comments(sql)

    # 验证注释被替换为占位符
    assert "__COMMENT_0__" in protected
    assert "--注释" in comments
    print("✅ 注释保护测试通过")

def test_restore_line_comments():
    """测试注释恢复"""
    from formatter_v5_sqlglot import SQLFormatterV5

    formatter = SQLFormatterV5()

    # 测试恢复 -- 注释（使用实际的保护格式）
    sql_with_placeholder = "SELECT a,  __COMMENT_0__ \nb FROM t1"
    comments = ["--注释"]

    restored = formatter._restore_line_comments(sql_with_placeholder, comments)

    assert "--注释" in restored
    assert "__COMMENT_0__" not in restored
    print("✅ 注释恢复测试通过")

def test_restore_from_sqlglot_format():
    """测试从 sqlglot 的 /* */ 格式恢复"""
    from formatter_v5_sqlglot import SQLFormatterV5

    formatter = SQLFormatterV5()

    # sqlglot 转换后的格式
    sql_with_block_comment = "SELECT a /* 注释 */\nFROM t1"
    comments = []

    restored = formatter._restore_line_comments(sql_with_block_comment, comments)

    # 应该把 /* */ 改回 --
    assert "-- 注释" in restored
    assert "/*" not in restored
    print("✅ sqlglot 格式转换测试通过")

def test_full_protect_restore_cycle():
    """测试完整的保护-恢复循环"""
    from formatter_v5_sqlglot import SQLFormatterV5

    formatter = SQLFormatterV5()

    # 原始 SQL 带 -- 注释
    original_sql = "SELECT a, --这是注释\nb FROM t1"

    # 保护
    protected, comments = formatter._protect_line_comments(original_sql)
    assert "--这是注释" not in protected
    assert "__COMMENT_0__" in protected
    assert "--这是注释" in comments

    # 恢复
    restored = formatter._restore_line_comments(protected, comments)
    assert "--这是注释" in restored
    assert "__COMMENT_0__" not in restored

    print("✅ 完整保护-恢复循环测试通过")

# 在 main 中调用
if __name__ == "__main__":
    test_protect_line_comments()
    test_restore_line_comments()
    test_restore_from_sqlglot_format()
    test_full_protect_restore_cycle()
