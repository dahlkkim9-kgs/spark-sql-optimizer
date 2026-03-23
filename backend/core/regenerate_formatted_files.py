# -*- coding: utf-8 -*-
"""
重新生成测试用例的预期格式化文件
基于修复后的 formatter_v4_fixed.py
"""
import sys
import os
from pathlib import Path

# 设置UTF-8编码输出
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加backend/core目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from formatter_v4_fixed import format_sql_v4_fixed

# 测试用例表目录
TEST_CASE_DIR = Path(__file__).parent.parent.parent.parent / "测试用例表"

# 测试用例文件列表
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


def regenerate_formatted_files():
    """重新生成所有预期格式化文件"""
    print("=" * 60)
    print("重新生成测试用例预期格式文件")
    print("=" * 60)
    print()

    for test_file in TEST_FILES:
        name = test_file["name"]
        original_file = TEST_CASE_DIR / test_file["original"]
        formatted_file = TEST_CASE_DIR / test_file["formatted"]

        print(f"处理: {name}")
        print(f"  原始文件: {original_file.name}")
        print(f"  格式化文件: {formatted_file.name}")

        # 读取原始文件
        try:
            with open(original_file, 'r', encoding='utf-8') as f:
                original_sql = f.read()
        except Exception as e:
            print(f"  ❌ 读取原始文件失败: {e}")
            continue

        # 格式化SQL
        try:
            formatted_sql = format_sql_v4_fixed(original_sql)
        except Exception as e:
            print(f"  ❌ 格式化失败: {e}")
            continue

        # 写入格式化文件
        try:
            with open(formatted_file, 'w', encoding='utf-8') as f:
                f.write(formatted_sql)
            print(f"  ✅ 已更新: {formatted_file.name}")
        except Exception as e:
            print(f"  ❌ 写入格式化文件失败: {e}")
            continue

        print()

    print("=" * 60)
    print("完成！所有预期格式文件已更新")
    print("=" * 60)


if __name__ == "__main__":
    regenerate_formatted_files()
