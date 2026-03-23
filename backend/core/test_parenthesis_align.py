# -*- coding: utf-8 -*-
"""括号对齐后处理器测试"""
import pytest
from backend.core.parenthesis_align_post_processor import ParenthesisAlignPostProcessor


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