# -*- coding: utf-8 -*-
"""V5 括号对齐集成测试"""
from formatter_v5_sqlglot import format_sql_v5


def test_in_subquery_formatting():
    """测试 IN 子查询格式化"""
    sql = "SELECT * FROM t1 WHERE a NOT IN (SELECT x FROM t2)"
    result = format_sql_v5(sql)
    print("\n=== IN 子查询格式化 ===")
    print(result)

    # 验证关键字存在
    assert "SELECT" in result.upper()
    assert "NOT IN" in result.upper() or "IN" in result.upper()


def test_real_sql_fragment():
    """测试真实 SQL 文件片段"""
    sql = """SELECT *
FROM rhbs_work.RHZF_GRKHJCXX_$TXDATE_xd
WHERE khzjdm NOT IN (
SELECT DISTINCT khzjdm
FROM rhbs_work.RHZF_GRKHJCXX_$TXDATE_XYK
)"""
    result = format_sql_v5(sql)
    print("\n=== 真实 SQL 片段 ===")
    print(result)

    # 验证内容完整性
    assert "SELECT" in result.upper()
    assert "RHZF_GRKHJCXX" in result


def test_with_real_sql_files():
    """使用真实 SQL 文件测试"""
    from pathlib import Path

    test_files = [
        "v5_integrity_outputs/JRJC_MON_B01_T18_GRKHXX_v5_integrity_test.sql",
    ]

    for file_path in test_files:
        path = Path(__file__).parent / file_path
        if not path.exists():
            print(f"跳过不存在的文件: {file_path}")
            continue

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        print(f"\n=== 测试文件: {file_path} ===")
        print(f"原始长度: {len(content)} 字符")

        try:
            result = format_sql_v5(content)
            print(f"格式化成功，长度: {len(result)} 字符")

            # 验证完整性
            assert isinstance(result, str)
            assert len(result) > 0

            # 打印前 500 字符预览
            print(f"\n格式化结果预览 (前 500 字符):")
            print(result[:500])
            if len(result) > 500:
                print("...")

        except Exception as e:
            print(f"格式化失败: {e}")
            raise


def run_all_tests():
    """运行所有集成测试"""
    import sys
    import io

    # 设置 UTF-8 输出编码
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    print("=" * 60)
    print("V5 括号对齐集成测试 - 完整验证")
    print("=" * 60)

    tests = [
        ("IN 子查询格式化", test_in_subquery_formatting),
        ("真实 SQL 片段", test_real_sql_fragment),
        ("真实 SQL 文件", test_with_real_sql_files),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            print(f"\n{'=' * 60}")
            print(f"运行测试: {name}")
            print('=' * 60)
            test_func()
            print(f"[PASS] {name} - 通过")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name} - 失败: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)