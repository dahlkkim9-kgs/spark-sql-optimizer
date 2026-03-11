#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试格式化器 - 使用新的测试文件
"""
import urllib.request
import urllib.parse
import json

def test_formatter():
    # 读取测试文件
    test_file = r"C:\Users\61586\Desktop\自用工作文件\deepseek\测试文件\测试用例表\GJDG_JRZF_D01_PARALLEL_CWKJB - 副本.sql"

    with open(test_file, 'r', encoding='utf-8') as f:
        original_sql = f.read()

    print(f"原始 SQL 行数: {len(original_sql.splitlines())}")

    # 调用格式化接口
    url = "http://localhost:8888/format/v4fixed"
    data = json.dumps({"sql": original_sql}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            formatted_sql = result.get('formatted', '')
            print(f"格式化后行数: {len(formatted_sql.splitlines())}")

            # 保存结果
            output_file = r"C:\Users\61586\Desktop\自用工作文件\deepseek\测试文件\spark-sql-optimizer\GJDG_PARALLEL_formatted.sql"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(formatted_sql)

            print(f"格式化结果已保存到: {output_file}")
            return formatted_sql
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_formatter()
