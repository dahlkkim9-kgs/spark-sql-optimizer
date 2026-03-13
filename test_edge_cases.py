# -*- coding: utf-8 -*-
"""Test edge cases for keyword finding"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'core'))

from processors.data_operations import DataOperationsProcessor

processor = DataOperationsProcessor()

# Test edge cases
test_cases = [
    # Test 1: WHEN in single quote string
    ("ON col = 'WHEN test' WHEN MATCHED", "WHEN in single quote"),

    # Test 2: WHEN in double quote string
    ('ON col = "WHEN test" WHEN MATCHED', "WHEN in double quote"),

    # Test 3: Multiple WHENs
    ("ON col1 = 'WHEN' WHEN MATCHED AND col2 = \"WHEN\" WHEN NOT MATCHED", "Multiple WHENs"),

    # Test 4: Escaped single quote
    (r"ON col = 'It\'s WHEN' WHEN MATCHED", "Escaped single quote"),

    # Test 5: Mixed quotes
    ('ON col = "value\\" WHEN MATCHED', "Double quote with backslash"),
]

for sql, description in test_cases:
    result = processor._find_keyword_outside_strings(sql, r'\bWHEN\s+')
    print(f'{description}:')
    print(f'  Input: {sql}')
    print(f'  WHEN position: {result}')
    if result >= 0:
        print(f'  Found: "{sql[result:result+20]}"')
    print()
