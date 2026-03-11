# -*- coding: utf-8 -*-
"""Test nested CASE WHEN with proper indentation"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from formatter_v4_fixed import format_sql_v4_fixed


def test_nested_case_with_parens():
    """Test nested CASE with parentheses wrapper"""
    sql = """
    SELECT
        CASE
            WHEN a.cert_type IN ('1070','1181')
            THEN (
                CASE
                    WHEN a.cert_no LIKE 'H%' THEN 'HKG'
                    WHEN a.cert_no LIKE 'M%' THEN 'MAC'
                    ELSE 'ZZZ'
                END
            )
            WHEN a.cert_type='1051' AND b.cd_value1='CHN'
            THEN 'ZZZ'
            ELSE (
                CASE
                    WHEN NVL(b.cd_value1,'') ='' THEN 'ZZZ'
                    ELSE b.cd_value1
                END
            )
        END AS G0302
    FROM table1
    """

    result = format_sql_v4_fixed(sql)

    print("=== Result ===")
    print(result)
    print("=== End ===")

    # 检查内层 CASE 缩进是否正确
    lines = result.split('\n')

    # 找到 THEN ( 所在行
    for i, line in enumerate(lines):
        if 'THEN (' in line:
            # 下一行应该是内层 CASE，缩进应该比外层 WHEN 更深
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                print(f"Line {i}: {repr(line)}")
                print(f"Line {i+1}: {repr(next_line)}")

                # 内层 CASE 应该有额外缩进
                assert next_line.strip().startswith('CASE'), f"Expected nested CASE, got: {next_line}"


if __name__ == '__main__':
    test_nested_case_with_parens()
