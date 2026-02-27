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


def test_replace_with_placeholders():
    """Test replacing comments with placeholders"""
    preserver = CommentPreserver()
    sql = "SELECT id -- comment\nFROM table"

    comments = preserver.extract_comments(sql)
    result = preserver.replace_with_placeholders(sql)

    assert "___COMMENT_001___" in result
    assert "-- comment" not in result
    assert "SELECT id" in result
    assert "FROM table" in result


def test_replace_preserves_structure():
    """Test that replacement preserves SQL structure"""
    preserver = CommentPreserver()
    sql = "SELECT id, name /* comment */ FROM table"

    preserver.extract_comments(sql)
    result = preserver.replace_with_placeholders(sql)

    # The structure should be preserved
    assert "SELECT id, name" in result
    assert "FROM table" in result


def test_comment_context_field_name():
    """Test that we capture what field a comment follows"""
    preserver = CommentPreserver()
    sql = "SELECT id -- primary key\n     , name -- user name"

    comments = preserver.extract_comments(sql)
    result = preserver.replace_with_placeholders(sql)

    # After replacement, we should be able to find the token before placeholder
    # for mapping purposes during insert
    assert comments[0]['placeholder'] in result
    assert comments[1]['placeholder'] in result


def test_get_token_before_placeholder():
    """Test getting the token immediately before a placeholder"""
    preserver = CommentPreserver()
    sql = "SELECT id -- primary key\nFROM table"

    preserver.extract_comments(sql)
    result = preserver.replace_with_placeholders(sql)

    # Find what comes before the placeholder
    token = preserver.get_token_before_placeholder(result, '___COMMENT_001___')
    assert token == 'id'


def test_insert_comment_after_token():
    """Test inserting comment after finding its token in formatted SQL"""
    preserver = CommentPreserver()
    original = "SELECT id -- primary key"
    formatted_without_comment = "SELECT id\n     \n;"

    preserver.extract_comments(original)
    result = preserver.insert_comments(formatted_without_comment, original)

    assert "-- primary key" in result


def test_insert_multiple_comments():
    """Test inserting multiple comments"""
    preserver = CommentPreserver()
    original = "SELECT id -- primary key\n     , name -- user name"
    formatted = "SELECT id\n     , name\n;"

    preserver.extract_comments(original)
    result = preserver.insert_comments(formatted, original)

    assert "-- primary key" in result
    assert "-- user name" in result
