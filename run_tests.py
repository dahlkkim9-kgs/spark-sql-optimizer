# -*- coding: utf-8 -*-
"""
SQL格式化工具 - 自动化测试套件
运行: python run_tests.py
"""
import sys
import os
import json
import re
from pathlib import Path

# 添加backend路径
sys.path.insert(0, 'backend')

from core.formatter_v4_fixed import format_sql_v4_fixed


class TestRunner:
    """测试运行器"""

    def __init__(self):
        self.results = {
            'passed': [],
            'failed': [],
            'errors': []
        }
        self.test_count = 0

    def load_test_cases(self, test_dir='test_cases'):
        """加载所有测试用例"""
        test_cases = []
        test_path = Path(test_dir)

        for sql_file in test_path.rglob('*.sql'):
            category = sql_file.parent.name
            test_cases.append({
                'path': sql_file,
                'category': category,
                'name': sql_file.name
            })

        return sorted(test_cases, key=lambda x: (x['category'], x['name']))

    def run_test(self, test_case):
        """运行单个测试用例"""
        self.test_count += 1
        test_path = test_case['path']

        try:
            with open(test_path, 'r', encoding='utf-8') as f:
                sql = f.read()

            # 跳过纯注释文件（如只有 -- 开头的注释）
            sql_content = sql.strip()
            if not sql_content or sql_content.startswith('--'):
                if not sql_content or all(line.strip().startswith('--') for line in sql_content.split('\n') if line.strip()):
                    return {'status': 'skip', 'reason': 'No SQL content'}

            # 格式化
            formatted = format_sql_v4_fixed(sql)

            # 基本验证
            checks = self._validate_formatting(sql, formatted, test_case)

            if all(checks.values()):
                return {'status': 'passed', 'checks': checks}
            else:
                return {'status': 'failed', 'checks': checks, 'formatted': formatted}

        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _validate_formatting(self, original, formatted, test_case):
        """验证格式化结果"""
        checks = {}
        category = test_case['category']
        name = test_case['name']

        # 通用检查
        checks['not_empty'] = len(formatted.strip()) > 0

        # 基础功能检查
        if 'comment' in name.lower():
            # COMMENT空格检查
            original_spaces = original.count(' ') if 'COMMENT' in original else 0
            formatted_spaces = formatted.count(' ') if 'COMMENT' in formatted else 0
            checks['comment_spaces'] = formatted_spaces >= original_spaces * 0.8

        # 复杂场景检查
        # 只有在原始SQL中真正包含子查询时才检查子查询缩进
        # 子查询特征：FROM/JOIN 后面跟着括号内的 SELECT
        has_subquery = (
            'subquery' in name.lower() or
            ('nested' in name.lower()) or
            ('IN (SELECT' in original.upper()) or
            ('EXISTS (SELECT' in original.upper()) or
            (re.search(r'\bFROM\s*\(\s*SELECT', original, re.IGNORECASE)) or
            (re.search(r'\bJOIN\s*\(\s*SELECT', original, re.IGNORECASE))
        )
        if has_subquery:
            # 子查询缩进检查
            checks['subquery_indented'] = '    SELECT' in formatted or '    FROM' in formatted

        if 'case' in name.lower() and 'when' in name.lower():
            # CASE WHEN格式化检查
            checks['case_formatted'] = 'CASE' in formatted and ('WHEN' in formatted or 'THEN' in formatted)

        # Spark特定检查
        if category == 'spark_specific':
            if 'partition' in name.lower():
                checks['partition_handled'] = 'PARTITION' in formatted
            if 'cache' in name.lower():
                checks['cache_handled'] = 'CACHE' in formatted

        return checks

    def print_results(self):
        """打印测试结果"""
        print("\n" + "=" * 70)
        print(f"测试完成: {self.test_count} 个测试用例")
        print("=" * 70)

        # 按类别统计
        categories = {}
        for result in self.results['passed']:
            cat = result['category']
            categories[cat] = categories.get(cat, {'passed': 0, 'failed': 0})
            categories[cat]['passed'] += 1

        for result in self.results['failed']:
            cat = result['category']
            categories[cat] = categories.get(cat, {'passed': 0, 'failed': 0})
            categories[cat]['failed'] += 1

        print("\n各类别测试结果:")
        print("-" * 70)
        for cat, counts in sorted(categories.items()):
            total = counts['passed'] + counts['failed']
            status = "PASS" if counts['failed'] == 0 else "FAIL"
            print(f"  [{status}] {cat:20s}: {counts['passed']:2d}/{total:2d} 通过")

        print("\n" + "=" * 70)
        total_passed = len(self.results['passed'])
        total_failed = len(self.results['failed']) + len(self.results['errors'])
        total = total_passed + total_failed

        if total_failed == 0:
            print(f"结果: 全部通过! ({total_passed}/{total})")
            print("=" * 70)
            return 0
        else:
            print(f"结果: 有测试失败 ({total_passed}/{total} 通过)")
            print("=" * 70)

            # 打印失败详情
            if self.results['failed']:
                print("\nFailed tests:")
                for result in self.results['failed'][:5]:
                    print(f"  - {result['category']}/{result['name']}")
                    for check, passed in result.get('checks', {}).items():
                        if not passed:
                            print(f"    [X] {check}")

            if self.results['errors']:
                print("\n错误的测试:")
                for result in self.results['errors'][:5]:
                    print(f"  - {result['category']}/{result['name']}")
                    print(f"    错误: {result['error']}")

            return 1

    def run_all(self):
        """运行所有测试"""
        print("=" * 70)
        print("SQL格式化工具 - 自动化测试")
        print("=" * 70)

        test_cases = self.load_test_cases()
        print(f"\n加载了 {len(test_cases)} 个测试用例\n")

        for i, test_case in enumerate(test_cases, 1):
            # 简化输出
            result = self.run_test(test_case)
            status_symbol = {
                'passed': '[PASS]',
                'failed': '[FAIL]',
                'error': '[ERROR]',
                'skip': '[SKIP]'
            }.get(result['status'], '[?]')

            if result['status'] == 'passed':
                self.results['passed'].append({**test_case, **result})
                print(f"{status_symbol} {test_case['category']:20s} {test_case['name']}")
            elif result['status'] == 'failed':
                self.results['failed'].append({**test_case, **result})
                print(f"{status_symbol} {test_case['category']:20s} {test_case['name']}")
            elif result['status'] == 'error':
                self.results['errors'].append({**test_case, **result})
                print(f"{status_symbol} {test_case['category']:20s} {test_case['name']} - {result['error'][:40]}")

        return self.print_results()


def main():
    """主函数"""
    runner = TestRunner()
    return runner.run_all()


if __name__ == '__main__':
    sys.exit(main())
