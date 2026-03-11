# -*- coding: utf-8 -*-
"""
SQL格式化工具 - 简化版测试脚本
专注于基本功能验证
"""
import sys
sys.path.insert(0, 'backend')

from core.formatter_v4_fixed import format_sql_v4_fixed
from pathlib import Path


def run_test_file(sql_file):
    """运行单个测试文件"""
    try:
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql = f.read()

        # 跳过空文件或纯注释
        content = sql.strip()
        if not content:
            return True, "Empty"

        # 尝试格式化
        formatted = format_sql_v4_fixed(sql)

        # 基本检查：格式化不应该抛异常，结果不应该为空
        if not formatted or len(formatted.strip()) == 0:
            return False, "Empty result"

        return True, "OK"

    except Exception as e:
        return False, str(e)


def main():
    print("=" * 60)
    print("SQL Formatter - Test Suite")
    print("=" * 60)

    test_dir = Path('test_cases')
    if not test_dir.exists():
        print("Error: test_cases directory not found")
        return 1

    # 收集所有测试文件
    test_files = list(test_dir.rglob('*.sql'))

    # 按类别分组
    by_category = {}
    for f in test_files:
        cat = f.parent.name
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(f)

    print(f"\nFound {len(test_files)} test files\n")

    total_passed = 0
    total_failed = 0

    # 运行测试
    for category in sorted(by_category.keys()):
        files = sorted(by_category[category])
        print(f"\n{category.upper()}:")

        for f in files:
            passed, msg = run_test_file(f)
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {status} {f.name}")
            if passed:
                total_passed += 1
            else:
                total_failed += 1
                if msg != "OK":
                    print(f"         Error: {msg}")

    # 汇总
    print("\n" + "=" * 60)
    total = total_passed + total_failed
    print(f"Results: {total_passed}/{total} passed")

    if total_failed == 0:
        print("All tests passed!")
        return 0
    else:
        print(f"{total_failed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
