# -*- coding: utf-8 -*-
"""使用真实 SQL 文件测试 v5"""
from formatter_v5_sqlglot import format_sql_v5
from pathlib import Path


def test_with_real_sql_files():
    """使用项目中的真实 SQL 文件测试"""
    # 查找测试用例表目录
    test_case_dir = Path(__file__).parent.parent.parent.parent / "测试用例表"

    if not test_case_dir.exists():
        print(f"测试用例目录不存在: {test_case_dir}")
        return

    # 查找所有 .sql 文件
    sql_files = list(test_case_dir.glob("*.sql"))

    if not sql_files:
        print(f"未找到 SQL 文件在: {test_case_dir}")
        return

    # 只测试前 3 个文件
    for file_path in sql_files[:3]:
        print(f"\n=== 测试文件: {file_path.name} ===")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            print(f"原始长度: {len(content)} 字符")

            result = format_sql_v5(content)
            print(f"格式化长度: {len(result)} 字符")

            # 显示前 500 字符
            print(f"前 500 字符:\n{result[:500]}")

            # 基本验证
            assert isinstance(result, str)
            assert len(result) > 0

            print("✅ 格式化成功")

        except Exception as e:
            print(f"❌ 格式化失败: {e}")


if __name__ == "__main__":
    test_with_real_sql_files()
