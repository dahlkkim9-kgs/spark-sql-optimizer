# -*- coding: utf-8 -*-
"""
快速测试脚本 - 用于开发过程中的快速验证
"""
import sys
sys.path.insert(0, 'backend')

from core.formatter_v4_fixed import format_sql_v4_fixed


# 快速测试用例
QUICK_TESTS = {
    "COMMENT空格": "CREATE TABLE t (id STRING COMMENT 'test     ');",
    "子查询缩进": "SELECT * FROM (SELECT a FROM t) x;",
    "CASE WHEN": "SELECT CASE WHEN a=1 THEN 2 END FROM t;",
    "PARTITION": "INSERT INTO t PARTITION(dt='2024') SELECT * FROM s;",
    "多语句": "SELECT * FROM t;INSERT INTO t VALUES (1);",
}


def main():
    print("=" * 50)
    print("Quick Test - SQL Formatter")
    print("=" * 50)

    all_passed = True

    for name, sql in QUICK_TESTS.items():
        try:
            result = format_sql_v4_fixed(sql)
            if result and len(result.strip()) > 0:
                print(f"[PASS] {name}")
            else:
                print(f"[FAIL] {name} - Empty result")
                all_passed = False
        except Exception as e:
            print(f"[FAIL] {name} - {e}")
            all_passed = False

    print("=" * 50)
    if all_passed:
        print("All quick tests passed!")
        return 0
    else:
        print("Some tests failed!")
        return 1


if __name__ == '__main__':
    sys.exit(main())
