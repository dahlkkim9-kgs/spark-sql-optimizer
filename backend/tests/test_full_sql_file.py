# -*- coding: utf-8 -*-
"""
使用真实SQL文件对格式化器进行全面测试
测试文件: JRJC_MON_B01_T18_GRKHXX.sql
"""
import sys
import io
import os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加路径 - 指向core目录
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))


def analyze_formatting_results(original, formatted, version):
    """分析格式化结果中的问题"""
    original_lines = original.split('\n')
    formatted_lines = formatted.split('\n')

    issues = []

    # 1. 检查 UNION ALL 是否被改成 UNION
    original_union_all_count = original.upper().count('UNION ALL')
    formatted_union_all_count = formatted.upper().count('UNION ALL')

    if original_union_all_count > 0:
        if formatted_union_all_count < original_union_all_count:
            issues.append(f"❌ UNION ALL 丢失: 原始 {original_union_all_count} 个，格式化后 {formatted_union_all_count} 个")
        else:
            print(f"  ✅ UNION ALL 保留正确: {formatted_union_all_count} 个")

    # 2. 检查注释保留情况
    original_single_comments = len([line for line in original_lines if line.strip().startswith('--')])
    formatted_single_comments = len([line for line in formatted_lines if line.strip().startswith('--')])

    print(f"  📝 单行注释: 原始 {original_single_comments} 行，格式化后 {formatted_single_comments} 行")

    if original_single_comments > formatted_single_comments:
        issues.append(f"❌ 单行注释丢失: {original_single_comments - formatted_single_comments} 行")

    # 3. 检查特定注释
    test_comments = [
        '--4. UNION + 嵌套 + CASE',
        '--1. 嵌套子查询（WHERE 子句中）',
        '--2. 多层嵌套 FROM 子查询',
        '--3. 窗口函数 + 嵌套子查询',
        '--5. CTE + 多层嵌套',
    ]

    for comment in test_comments:
        if comment in original:
            if comment in formatted:
                print(f"  ✅ 注释保留: {comment}")
            else:
                issues.append(f"❌ 特定注释丢失: {comment}")

    # 4. 检查关键语法保留
    key_syntax = [
        ('WITH AS', 'CTE语法'),
        ('CACHE TABLE', 'CACHE TABLE语法'),
        ('OVER (', '窗口函数'),
        ('LATERAL VIEW', 'LATERAL VIEW语法'),
        ('PARTITION BY', 'PARTITION BY语法'),
        ('DISTRIBUTE BY', 'DISTRIBUTE BY语法'),
    ]

    for syntax, name in key_syntax:
        if syntax in original:
            if syntax in formatted:
                print(f"  ✅ {name} 保留正确")
            else:
                issues.append(f"❌ {name} 丢失")

    # 5. 检查CASE WHEN格式化
    case_count = formatted.upper().count('CASE WHEN')
    print(f"  📊 CASE WHEN 语句: {case_count} 个")

    return issues


def test_full_sql_file():
    """主测试函数"""
    from formatter_v4_fixed import format_sql_v4_fixed

    # 读取测试文件
    test_file = r'C:\Users\61586\Desktop\自用工作文件\deepseek\测试文件\测试用例表\JRJC_MON_B01_T18_GRKHXX.sql'

    print("=" * 100)
    print("SQL格式化器全面测试")
    print("=" * 100)
    print(f"测试文件: {test_file}")
    print()

    with open(test_file, 'r', encoding='utf-8') as f:
        original_sql = f.read()

    print(f"原始SQL长度: {len(original_sql)} 字符")
    print(f"原始SQL行数: {len(original_sql.split(chr(10)))} 行")
    print()

    # 测试格式化器
    print("-" * 100)
    print("测试 V4 Fixed 格式化器 (format_sql_v4_fixed)")
    print("-" * 100)

    try:
        result = format_sql_v4_fixed(original_sql)
        print("✅ 格式化成功")
        print(f"结果长度: {len(result)} 字符")
        print(f"结果行数: {len(result.split(chr(10)))} 行")
        print()
    except Exception as e:
        print(f"❌ 格式化失败: {e}")
        import traceback
        traceback.print_exc()
        result = None
        print()

    # 分析结果
    if result:
        print("=" * 100)
        print("格式化结果详细分析")
        print("=" * 100)
        print()

        issues = analyze_formatting_results(original_sql, result, "V4_Fixed")

        print()
        if issues:
            print(f"发现 {len(issues)} 个问题:")
            for issue in issues:
                print(f"  {issue}")
        else:
            print("✅ 所有检查通过！")

        print()
        print("=" * 100)
        print("格式化结果预览（前200行）")
        print("=" * 100)
        lines = result.split('\n')
        for i, line in enumerate(lines[:200], 1):
            if line.strip():
                spaces = len(line) - len(line.lstrip())
                print(f"{i:4d} ({spaces:2d}空格): {line}")
        if len(lines) > 200:
            print(f"... (还有 {len(lines) - 200} 行)")

    # 保存结果到文件
    if result:
        output_file = test_file.replace('.sql', '_formatted.sql')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result)
        print()
        print(f"✅ 格式化结果已保存到: {output_file}")


if __name__ == "__main__":
    test_full_sql_file()
