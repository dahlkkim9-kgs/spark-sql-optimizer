import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from comment_preserver import CommentPreserver

def test_comment_preserver_exists():
    """Test that CommentPreserver class can be instantiated"""
    preserver = CommentPreserver()
    assert preserver is not None


def test_extract_single_line_comment():
    """Test extraction of single -- comment"""
    preserver = CommentPreserver()
    sql = "SELECT id -- this is a comment"

    comments = preserver.extract_comments(sql)

    assert len(comments) == 1
    assert comments[0]['content'] == ' this is a comment'
    assert comments[0]['type'] == 'line'
    assert comments[0]['placeholder'] == '___COMMENT_001___'


def test_extract_multiple_line_comments():
    """Test extraction of multiple -- comments"""
    preserver = CommentPreserver()
    sql = """SELECT id -- first comment
     , name -- second comment"""

    comments = preserver.extract_comments(sql)

    assert len(comments) == 2
    assert comments[0]['content'] == ' first comment'
    assert comments[1]['content'] == ' second comment'


def test_extract_block_comment():
    """Test extraction of /* */ block comment"""
    preserver = CommentPreserver()
    sql = "SELECT id /* this is a block comment */"

    comments = preserver.extract_comments(sql)

    assert len(comments) == 1
    assert comments[0]['content'] == ' this is a block comment '
    assert comments[0]['type'] == 'block'


def test_extract_mixed_comments():
    """Test extraction of both line and block comments"""
    preserver = CommentPreserver()
    sql = """SELECT id -- line comment
     , name /* block comment */"""

    comments = preserver.extract_comments(sql)

    assert len(comments) == 2
    assert comments[0]['type'] == 'line'
    assert comments[1]['type'] == 'block'
