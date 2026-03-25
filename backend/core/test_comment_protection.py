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

if __name__ == "__main__":
    test_protect_line_comments()
