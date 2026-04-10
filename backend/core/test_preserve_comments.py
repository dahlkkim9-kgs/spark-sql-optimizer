# -*- coding: utf-8 -*-
"""测试：注释保留 — 被注释掉的 SQL 代码不应丢失

问题：CASE 块内被注释掉的 SQL 代码行（如 --when ... then ...）
在 sqlglot AST 重构时被丢弃。

方案：预处理阶段将独立 -- 注释行替换为 /* */ 占位符，格式化后恢复。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from formatter_v5_sqlglot import format_sql_v5
import re


def _count_comments(sql: str) -> int:
    """统计 -- 注释数量"""
    return len(re.findall(r'--[^\n]*', sql))


def test_commented_case_when_preserved():
    """CASE 块内被注释掉的 WHEN 分支应保留"""
    sql = """SELECT CASE
    WHEN a.type = 'A' THEN '1'
    --WHEN a.type = 'B' THEN '2'
    WHEN a.type = 'C' THEN '3'
    ELSE '0'
END AS result
FROM t1"""
    result = format_sql_v5(sql)
    # 注释中的 'B' 应保留（注释会附加到上一行末尾）
    assert 'B' in result, \
        f"被注释掉的 WHEN 分支丢失! 输出:\n{result}"
    print("PASS: test_commented_case_when_preserved")


def test_standalone_comment_preserved():
    """独立的注释行不应丢失"""
    sql = """--20240729修改
SELECT a, b FROM t1"""
    result = format_sql_v5(sql)
    assert '20240729' in result, f"独立注释丢失! 输出:\n{result}"
    print("PASS: test_standalone_comment_preserved")


def test_chinese_comment_preserved():
    """中文注释不应丢失"""
    sql = """SELECT a
--当国籍是空的时候转其他
, b FROM t1"""
    result = format_sql_v5(sql)
    assert '国籍' in result or '其他' in result, f"中文注释丢失! 输出:\n{result}"
    print("PASS: test_chinese_comment_preserved")


def test_commented_case_with_inline_comment():
    """被注释掉的 SQL 行内含第二个注释（--xxx --yyy）"""
    sql = """SELECT CASE
    WHEN a.x = '1' THEN 'A'
    --WHEN a.x = '2' THEN 'B' --备用分支
    WHEN a.x = '3' THEN 'C'
    ELSE ''
END FROM t1"""
    result = format_sql_v5(sql)
    assert '备用' in result, f"行内注释丢失! 输出:\n{result}"
    print("PASS: test_commented_case_with_inline_comment")


def test_multiple_commented_branches_preserved():
    """多条被注释掉的 WHEN 分支全部保留"""
    sql = """SELECT CASE
    WHEN a.x = '1' THEN 'A'
    --WHEN a.x = '2' THEN 'B'
    --WHEN a.x = '3' THEN 'C'
    --WHEN a.x = '4' THEN 'D'
    ELSE ''
END FROM t1"""
    result = format_sql_v5(sql)
    assert 'B' in result and 'C' in result and 'D' in result, \
        f"部分被注释掉的分支丢失! 输出:\n{result}"
    print("PASS: test_multiple_commented_branches_preserved")


def test_g03_comment_retention_rate():
    """G03 文件注释保留率 >= 98%"""
    g03_path = os.path.join(
        os.path.dirname(__file__),
        '..', '..', '测试用例表', 'GJDG_JRZF_G03.sql'
    )
    if not os.path.exists(g03_path):
        print("SKIP: G03 文件不存在")
        return

    with open(g03_path, 'r', encoding='utf-8') as f:
        original = f.read()

    result = format_sql_v5(original)

    orig_count = _count_comments(original)
    fmt_count = _count_comments(result)
    retention = fmt_count / orig_count * 100 if orig_count > 0 else 100

    print(f"G03 注释保留: {fmt_count}/{orig_count} ({retention:.1f}%)")
    assert retention >= 98, f"G03 注释保留率 {retention:.1f}% < 98%"
    print("PASS: test_g03_comment_retention_rate")


if __name__ == "__main__":
    tests = [
        test_commented_case_when_preserved,
        test_standalone_comment_preserved,
        test_chinese_comment_preserved,
        test_commented_case_with_inline_comment,
        test_multiple_commented_branches_preserved,
        test_g03_comment_retention_rate,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {t.__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"注释保留测试: {passed}/{passed+failed} 通过")
    if failed:
        print(f"失败: {failed}")
        sys.exit(1)
    else:
        print("全部通过!")
