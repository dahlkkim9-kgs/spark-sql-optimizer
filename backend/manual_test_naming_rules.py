"""
手动验证命名规则
"""
from core.analyzer import StaticAnalyzer

analyzer = StaticAnalyzer()

# 测试SQL
test_cases = [
    ("表名日期检测", "SELECT * FROM tab_name_20250102"),
    ("注释分号检测", "-- 注释; 有问题\nSELECT 1"),
    ("敏感信息检测-18位身份证", "SELECT * FROM users WHERE id_card = '110101199001011234'"),
    ("敏感信息检测-敏感字段", "SELECT idcard, identity FROM table1"),
    ("综合测试", """
        -- 注释中有分号;
        SELECT idcard
        FROM tab_20250102_data
        WHERE id_card = '110101199001011234'
    """),
]

print("=" * 70)
print(" SQL 分析器 - 命名规范规则手动验证")
print("=" * 70)

for name, sql in test_cases:
    print(f"\n{'='*70}")
    print(f"【{name}】")
    print(f"{'='*70}")
    print(f"SQL:\n{sql.strip()}")
    print(f"\n{'-'*70}")
    result = analyzer.analyze(sql)
    print(f"问题数: {result['issue_count']}")

    # 只显示我们新增的三条规则
    new_rules = ["TABLE_NAME_WITH_DATE", "COMMENT_WITH_SEMICOLON", "SENSITIVE_INFO_DETECTED"]
    for issue in result["issues"]:
        if issue["rule"] in new_rules:
            print(f"\n  [!!] 规则: {issue['rule']}")
            print(f"       严重级别: {issue['severity']}")
            print(f"       消息: {issue['message']}")
            print(f"       行号: {issue['line']}")
            print(f"       建议: {issue['suggestion']}")

    if not any(i["rule"] in new_rules for i in result["issues"]):
        print("  [OK] 未触发命名规范规则")

print(f"\n{'='*70}")
print(" 验证完成！")
print("=" * 70)
