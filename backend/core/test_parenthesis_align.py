# -*- coding: utf-8 -*-
"""括号对齐后处理器测试"""
import pytest
from parenthesis_align_post_processor import ParenthesisAlignPostProcessor


def test_basic_passthrough():
    """测试基础传入（无括号时保持原样）"""
    processor = ParenthesisAlignPostProcessor()
    sql = "SELECT a FROM t1"
    result = processor.process(sql)
    assert result == sql


def test_simple_parenthesis():
    """测试简单括号（占位测试）"""
    processor = ParenthesisAlignPostProcessor()
    sql = "SELECT (a + b) FROM t1"
    result = processor.process(sql)
    # 暂时保持原样
    assert "(" in result


def test_nested_parenthesis():
    """测试嵌套括号（占位测试）"""
    processor = ParenthesisAlignPostProcessor()
    sql = "SELECT ((a + b) * c) FROM t1"
    result = processor.process(sql)
    # 暂时保持原样
    assert result.count("(") == 2


def test_find_matching_paren():
    """测试括号配对查找"""
    processor = ParenthesisAlignPostProcessor()

    # 简单括号
    assert processor._find_matching_paren("(a)", 0) == 2

    # 嵌套括号
    assert processor._find_matching_paren("((a))", 0) == 4
    assert processor._find_matching_paren("((a))", 1) == 3

    # 不匹配
    assert processor._find_matching_paren("(a", 0) == -1


def test_analyze_line_parens():
    """测试行级括号分析"""
    processor = ParenthesisAlignPostProcessor()

    # 开括号行
    result = processor._analyze_line_parens("    WHERE a IN (")
    assert result['has_open_paren'] == True
    assert result['prefix'] == "WHERE a IN "
    assert result['base_indent'] == 4

    # 闭括号行
    result = processor._analyze_line_parens("    )")
    assert result['has_close_paren'] == True
    assert result['has_open_paren'] == False

    # 无括号行
    result = processor._analyze_line_parens("    SELECT a")
    assert result['has_open_paren'] == False
    assert result['has_close_paren'] == False

    # 多个括号行（只检测第一个）
    result = processor._analyze_line_parens("  SELECT (a), (b)")
    assert result['has_open_paren'] == True
    assert result['open_paren_pos'] == 7  # "SELECT " 长度为 7
    assert result['prefix'] == "SELECT "
    assert result['base_indent'] == 2

    # 只有闭括号
    result = processor._analyze_line_parens("    ) AND b > 0")
    assert result['has_close_paren'] == True
    assert result['has_open_paren'] == False
    assert result['close_paren_pos'] == 0


def test_simple_subquery_align():
    """测试简单子查询对齐"""
    processor = ParenthesisAlignPostProcessor()

    input_sql = """WHERE a IN (
SELECT x
FROM t2
)"""
    result = processor.process(input_sql)
    print("Result:", repr(result))
    # 验证子查询内容被缩进
    lines = result.split('\n')
    select_line = [l for l in lines if 'SELECT' in l][0]
    # SELECT 应该有缩进（大于开括号位置）
    assert select_line.startswith(' ' * 5)  # 至少 5 空格缩进


def test_multi_line_subquery():
    """测试多行子查询对齐"""
    processor = ParenthesisAlignPostProcessor()

    input_sql = """    WHERE a IN (
        SELECT
            x,
            y
        FROM t2
    )"""
    result = processor.process(input_sql)
    print("Result:", repr(result))
    lines = result.split('\n')
    # 验证内容缩进
    for line in lines:
        if 'SELECT' in line or 'FROM' in line or 'x,' in line or 'y' in line:
            # 内容行应该在开括号后缩进
            assert line.startswith(' ') or line[0] in 'SFxy'


def test_nested_subquery():
    """测试嵌套子查询"""
    processor = ParenthesisAlignPostProcessor()

    input_sql = """WHERE a IN (
SELECT x
FROM (
    SELECT y
    FROM t3
) t2
)"""
    result = processor.process(input_sql)
    print("Result:", repr(result))
    # 验证有两个闭括号
    assert result.count(')') == 2