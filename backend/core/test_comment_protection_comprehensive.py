# -*- coding: utf-8 -*-
"""测试注释保护功能 - 全面测试"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from formatter_v5_sqlglot import SQLFormatterV5

def test_protect_line_comments():
    """测试 -- 注释保护"""
    formatter = SQLFormatterV5()

    # 测试 1: 基本注释
    sql = "SELECT a, --注释\nb FROM t1"
    protected, comments = formatter._protect_line_comments(sql)
    assert "__COMMENT_0__" in protected
    assert "--注释" in comments
    print("✅ 测试1: 基本注释 - 通过")

    # 测试 2: 多个注释
    sql = "SELECT a, --注释1\nb, --注释2\nFROM t1"
    protected, comments = formatter._protect_line_comments(sql)
    assert "__COMMENT_0__" in protected
    assert "__COMMENT_1__" in protected
    assert len(comments) == 2
    assert "--注释1" in comments
    assert "--注释2" in comments
    print("✅ 测试2: 多个注释 - 通过")

    # 测试 3: 字符串内的 -- 不是注释
    sql = "SELECT 'text--inside', a, --这是注释\nb FROM t1"
    protected, comments = formatter._protect_line_comments(sql)
    assert "__COMMENT_0__" in protected
    assert len(comments) == 1
    assert "text--inside" in protected  # 字符串内容保留
    print("✅ 测试3: 字符串内的 -- 不是注释 - 通过")

    # 测试 4: 空注释
    sql = "SELECT a, --\nb FROM t1"
    protected, comments = formatter._protect_line_comments(sql)
    assert "__COMMENT_0__" in protected
    assert "--" in comments
    print("✅ 测试4: 空注释 - 通过")

    # 测试 5: 注释后跟换行符
    sql = "SELECT a, --注释\r\nb FROM t1"
    protected, comments = formatter._protect_line_comments(sql)
    assert "__COMMENT_0__" in protected
    assert "--注释" in comments
    print("✅ 测试5: 注释后跟换行符 - 通过")

    # 测试 6: 无注释
    sql = "SELECT a, b FROM t1"
    protected, comments = formatter._protect_line_comments(sql)
    assert "__COMMENT_" not in protected
    assert len(comments) == 0
    print("✅ 测试6: 无注释 - 通过")

    print("\n🎉 所有测试通过！")

if __name__ == "__main__":
    test_protect_line_comments()
