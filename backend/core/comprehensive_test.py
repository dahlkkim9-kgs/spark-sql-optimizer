"""
SQL格式化器全面测试脚本
测试所有测试用例表中的SQL文件，验证格式化器功能
"""
import sys
import os
from pathlib import Path

# 设置UTF-8编码输出（Windows兼容）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加backend/core目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from formatter_v4_fixed import format_sql_v4_fixed

# 测试用例表目录
TEST_CASE_DIR = Path(__file__).parent.parent.parent.parent / "测试用例表"

# 测试用例文件列表（原始文件和预期格式化文件）
TEST_FILES = [
    {
        "name": "JRJC_MON_B01_T18_GRKHXX",
        "original": "JRJC_MON_B01_T18_GRKHXX.sql",
        "formatted": "JRJC_MON_B01_T18_GRKHXX_formatted.sql"
    },
    {
        "name": "GJDG_JRZF_D01_PARALLEL_CWKJB",
        "original": "GJDG_JRZF_D01_PARALLEL_CWKJB - 副本.sql",
        "formatted": "GJDG_JRZF_D01_PARALLEL_CWKJB - 副本_formatted.sql"
    },
    {
        "name": "GJDG_JRZF_G03",
        "original": "GJDG_JRZF_G03 - 副本.sql",
        "formatted": "GJDG_JRZF_G03 - 副本_formatted.sql"
    }
]


def read_file(file_path: Path) -> str:
    """读取文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"  ❌ 读取文件失败: {e}")
        return None


def format_sql(sql: str) -> str:
    """格式化SQL"""
    try:
        return format_sql_v4_fixed(sql)
    except Exception as e:
        print(f"  ❌ 格式化失败: {e}")
        return None


def compare_output(actual: str, expected: str) -> tuple:
    """
    比较实际输出和预期输出
    返回: (是否匹配, 差异行数)
    """
    if actual is None or expected is None:
        return (False, -1)

    actual_lines = actual.split('\n')
    expected_lines = expected.split('\n')

    if len(actual_lines) != len(expected_lines):
        return (False, abs(len(actual_lines) - len(expected_lines)))

    diff_count = 0
    for i, (a, e) in enumerate(zip(actual_lines, expected_lines)):
        if a != e:
            diff_count += 1

    return (diff_count == 0, diff_count)


def test_file(test_case: dict, verbose: bool = False):
    """测试单个文件"""
    name = test_case["name"]
    original_path = TEST_CASE_DIR / test_case["original"]
    formatted_path = TEST_CASE_DIR / test_case["formatted"]

    print(f"\n{'=' * 70}")
    print(f"测试文件: {name}")
    print(f"{'=' * 70}")

    # 检查文件是否存在
    if not original_path.exists():
        print(f"  ❌ 原始文件不存在: {original_path}")
        return False

    if not formatted_path.exists():
        print(f"  ⚠️  预期格式化文件不存在: {formatted_path}")
        print(f"  将生成新的格式化输出")

    # 读取原始SQL
    print(f"\n📄 读取原始文件: {original_path.name}")
    original_sql = read_file(original_path)
    if original_sql is None:
        return False

    # 格式化SQL
    print(f"🔧 格式化SQL...")
    formatted_sql = format_sql(original_sql)
    if formatted_sql is None:
        return False

    # 如果存在预期格式化文件，进行比较
    if formatted_path.exists():
        print(f"📄 读取预期格式化文件: {formatted_path.name}")
        expected_sql = read_file(formatted_path)
        if expected_sql is None:
            return False

        # 比较输出
        print(f"🔍 比较输出...")
        matches, diff_count = compare_output(formatted_sql, expected_sql)

        if matches:
            print(f"  ✅ 测试通过！输出完全匹配")
            return True
        else:
            print(f"  ❌ 测试失败！发现 {diff_count} 行差异")
            if verbose:
                print(f"\n📋 差异详情:")
                actual_lines = formatted_sql.split('\n')
                expected_lines = expected_sql.split('\n')
                max_lines = max(len(actual_lines), len(expected_lines))
                for i in range(max_lines):
                    actual = actual_lines[i] if i < len(actual_lines) else "<缺失>"
                    expected = expected_lines[i] if i < len(expected_lines) else "<缺失>"
                    if actual != expected:
                        print(f"  行 {i+1}:")
                        print(f"    预期: {repr(expected)}")
                        print(f"    实际: {repr(actual)}")
            return False
    else:
        # 保存格式化输出
        print(f"💾 保存格式化输出到: {formatted_path.name}")
        with open(formatted_path, 'w', encoding='utf-8') as f:
            f.write(formatted_sql)
        print(f"  ✅ 格式化输出已保存")
        return True


def run_tests(verbose: bool = False):
    """运行所有测试"""
    print("=" * 70)
    print("SQL 格式化器全面测试")
    print("=" * 70)
    print(f"测试目录: {TEST_CASE_DIR}")
    print(f"测试文件数: {len(TEST_FILES)}")

    results = []

    for test_case in TEST_FILES:
        try:
            passed = test_file(test_case, verbose)
            results.append({
                "name": test_case["name"],
                "passed": passed
            })
        except Exception as e:
            print(f"  ❌ 测试异常: {e}")
            results.append({
                "name": test_case["name"],
                "passed": False,
                "error": str(e)
            })

    # 打印测试总结
    print(f"\n{'=' * 70}")
    print("测试总结")
    print(f"{'=' * 70}")

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed

    print(f"总测试数: {total}")
    print(f"通过: {passed} ✅")
    print(f"失败: {failed} {'❌' if failed > 0 else ''}")
    print(f"通过率: {passed/total*100:.1f}%")

    if failed > 0:
        print(f"\n失败的测试:")
        for r in results:
            if not r["passed"]:
                error = r.get("error", "")
                print(f"  - {r['name']}: {error}")

    return passed == total


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SQL格式化器全面测试")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="显示详细差异信息")
    args = parser.parse_args()

    success = run_tests(verbose=args.verbose)
    sys.exit(0 if success else 1)
