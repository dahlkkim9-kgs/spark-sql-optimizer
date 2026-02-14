import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from comment_preserver import CommentPreserver

def test_comment_preserver_exists():
    """Test that CommentPreserver class can be instantiated"""
    preserver = CommentPreserver()
    assert preserver is not None
