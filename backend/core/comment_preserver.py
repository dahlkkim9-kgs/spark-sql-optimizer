# -*- coding: utf-8 -*-
"""
Comment Preserver - Extracts and re-inserts comments during SQL formatting
"""

class CommentPreserver:
    """
    Handles comment preservation during SQL formatting.

    Works in three phases:
    1. extract_comments() - Extract all comments with position info
    2. replace_with_placeholders() - Replace comments with unique placeholders
    3. insert_comments() - Insert comments back into formatted SQL
    """

    def __init__(self):
        self._comments = []
        self._placeholder_prefix = "___COMMENT_"
        self._placeholder_suffix = "___"

    def reset(self):
        """Reset internal state for a new SQL string"""
        self._comments = []
