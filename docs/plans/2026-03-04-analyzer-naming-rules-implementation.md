# SQL 分析器命名规范规则实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 Spark SQL 静态分析器添加三条代码规范类规则（表名日期检测、注释分号检测、敏感信息检测）

**Architecture:** 在现有 `analyzer.py` 的 `_init_rules()` 方法中添加三条新规则，使用正则表达式匹配，与现有 16 条规则风格保持一致。

**Tech Stack:** Python 3.14, re (正则表达式), pytest (测试)

---

## Task 1: 添加 TABLE_NAME_WITH_DATE 规则

**Files:**
- Modify: `backend/core/analyzer.py:213` (在 `_init_rules` 方法末尾添加)

**Step 1: 在 rules 列表中添加表名日期检测规则**

在 `_init_rules()` 方法的 rules 列表末尾（第 213 行 `]` 之前）添加：

```python
            # ========== 代码规范规则 ==========
            {
                "name": "TABLE_NAME_WITH_DATE",
                "severity": "HIGH",
                "pattern": r"\b(?:FROM|JOIN|TABLE|INSERT\s+INTO|UPDATE|CREATE\s+TABLE)\s+(?:\w+\.)?\w*[12]\d{3}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\w*",
                "message": "检测到表名中包含日期（如 table_20250102），请检查是否为分区表命名或临时表",
                "suggestion": "建议使用分区表规范命名，如 table_name PARTITION(dt='20250102')，或使用变量替代硬编码日期",
                "rewrite": None
            },
```

**Step 2: 运行基础测试验证语法正确**

```bash
cd backend
python -c "from core.analyzer import StaticAnalyzer; a = StaticAnalyzer(); print('规则数:', len(a.rules))"
```

Expected: 输出 `规则数: 19` (原 16 条 + 新增 1 条)

---

## Task 2: 添加 COMMENT_WITH_SEMICOLON 规则

**Files:**
- Modify: `backend/core/analyzer.py:220` (在 TABLE_NAME_WITH_DATE 规则后添加)

**Step 1: 在 rules 列表中添加注释分号检测规则**

```python
            {
                "name": "COMMENT_WITH_SEMICOLON",
                "severity": "HIGH",
                "pattern": r"--[^;\n]*;",
                "message": "检测到注释行中包含分号（;），可能导致SQL解析错误",
                "suggestion": "请检查注释内容，如果分号是注释说明的一部分，请确保不会影响SQL解析；如果是误写的分号，请删除",
                "rewrite": None
            },
```

**Step 2: 验证规则添加成功**

```bash
cd backend
python -c "from core.analyzer import StaticAnalyzer; a = StaticAnalyzer(); print('规则数:', len(a.rules))"
```

Expected: 输出 `规则数: 20`

---

## Task 3: 添加 SENSITIVE_INFO_DETECTED 规则

**Files:**
- Modify: `backend/core/analyzer.py:227` (在 COMMENT_WITH_SEMICOLON 规则后添加)

**Step 1: 在 rules 列表中添加敏感信息检测规则**

```python
            {
                "name": "SENSITIVE_INFO_DETECTED",
                "severity": "HIGH",
                "pattern": r"\b1[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b|(?:身份证|证件号|id_card|idcard|identity|sfz)",
                "message": "检测到可能的敏感信息（身份证号或相关字段名），请确保符合数据安全规范",
                "suggestion": "建议对敏感字段进行脱敏处理（如 md5/hash），或确保已获得相应授权；检查字段命名是否符合安全规范",
                "rewrite": None
            },
```

**Step 2: 验证所有规则添加成功**

```bash
cd backend
python -c "from core.analyzer import StaticAnalyzer; a = StaticAnalyzer(); print('规则数:', len(a.rules))"
```

Expected: 输出 `规则数: 21`

---

## Task 4: 编写测试用例

**Files:**
- Create: `backend/tests/test_analyzer_naming_rules.py`

**Step 1: 创建测试文件**

```python
"""
命名规范规则测试用例
"""
import pytest
from core.analyzer import StaticAnalyzer


class TestNamingRules:
    """命名规范规则测试"""

    def setup_method(self):
        """每个测试前创建分析器实例"""
        self.analyzer = StaticAnalyzer()

    # ========== TABLE_NAME_WITH_DATE 测试 ==========

    def test_table_name_with_date_suffix(self):
        """测试：表名后缀包含日期"""
        sql = "SELECT * FROM tab_name_20250102"
        result = self.analyzer.analyze(sql)
        assert any(i["rule"] == "TABLE_NAME_WITH_DATE" for i in result["issues"])

    def test_table_name_with_date_middle(self):
        """测试：表名中间包含日期"""
        sql = "SELECT * FROM tab_20250102_xxx"
        result = self.analyzer.analyze(sql)
        assert any(i["rule"] == "TABLE_NAME_WITH_DATE" for i in result["issues"])

    def test_table_name_normal(self):
        """测试：正常表名不应触发"""
        sql = "SELECT * FROM normal_table"
        result = self.analyzer.analyze(sql)
        assert not any(i["rule"] == "TABLE_NAME_WITH_DATE" for i in result["issues"])

    # ========== COMMENT_WITH_SEMICOLON 测试 ==========

    def test_comment_with_semicolon(self):
        """测试：注释包含分号"""
        sql = "-- 这是注释;有问题\nSELECT * FROM table1"
        result = self.analyzer.analyze(sql)
        assert any(i["rule"] == "COMMENT_WITH_SEMICOLON" for i in result["issues"])

    def test_comment_without_semicolon(self):
        """测试：正常注释不应触发"""
        sql = "-- 这是正常注释\nSELECT * FROM table1"
        result = self.analyzer.analyze(sql)
        assert not any(i["rule"] == "COMMENT_WITH_SEMICOLON" for i in result["issues"])

    # ========== SENSITIVE_INFO_DETECTED 测试 ==========

    def test_id_card_18_digit(self):
        """测试：18位身份证号"""
        sql = "SELECT * FROM users WHERE id_card = '110101199001011234'"
        result = self.analyzer.analyze(sql)
        assert any(i["rule"] == "SENSITIVE_INFO_DETECTED" for i in result["issues"])

    def test_id_card_15_digit(self):
        """测试：15位身份证号"""
        sql = "SELECT * FROM users WHERE id_card = '110101900101123'"
        result = self.analyzer.analyze(sql)
        assert any(i["rule"] == "SENSITIVE_INFO_DETECTED" for i in result["issues"])

    def test_sensitive_field_name(self):
        """测试：敏感字段名"""
        sql = "SELECT idcard, identity FROM table1"
        result = self.analyzer.analyze(sql)
        assert any(i["rule"] == "SENSITIVE_INFO_DETECTED" for i in result["issues"])

    def test_normal_sql_no_sensitive(self):
        """测试：正常SQL不应触发敏感信息检测"""
        sql = "SELECT user_id, username, email FROM users"
        result = self.analyzer.analyze(sql)
        assert not any(i["rule"] == "SENSITIVE_INFO_DETECTED" for i in result["issues"])

    # ========== 综合测试 ==========

    def test_combined_rules(self):
        """测试：同时触发多条规则"""
        sql = """
        -- 注释中有分号;
        SELECT idcard
        FROM tab_20250102_data
        WHERE id_card = '110101199001011234'
        """
        result = self.analyzer.analyze(sql)
        rules_found = [i["rule"] for i in result["issues"]]
        assert "TABLE_NAME_WITH_DATE" in rules_found
        assert "COMMENT_WITH_SEMICOLON" in rules_found
        assert "SENSITIVE_INFO_DETECTED" in rules_found
```

**Step 2: 运行测试验证所有失败（因为规则还未实现）**

```bash
cd backend
python -m pytest tests/test_analyzer_naming_rules.py -v
```

Expected: 所有测试失败（规则未添加时）或通过（规则已添加后）

---

## Task 5: 运行完整测试套件

**Files:**
- Test: `backend/tests/`

**Step 1: 运行所有测试确保不破坏现有功能**

```bash
cd backend
python -m pytest tests/ -v --tb=short
```

Expected: 所有现有测试通过 + 新测试通过

---

## Task 6: 手动验证实际SQL

**Files:**
- Create: `backend/tests/manual_test_naming.py`

**Step 1: 创建手动验证脚本**

```python
"""手动验证命名规则"""
from core.analyzer import StaticAnalyzer

analyzer = StaticAnalyzer()

# 测试SQL
test_sqls = [
    ("表名日期检测", "SELECT * FROM tab_name_20250102"),
    ("注释分号检测", "-- 注释; 有问题\nSELECT 1"),
    ("敏感信息检测", "SELECT idcard FROM users"),
]

print("=" * 60)
print("命名规范规则手动验证")
print("=" * 60)

for name, sql in test_sqls:
    print(f"\n【{name}】")
    print(f"SQL: {sql}")
    result = analyzer.analyze(sql)
    print(f"问题数: {result['issue_count']}")
    for issue in result["issues"]:
        print(f"  - {issue['rule']}: {issue['message']}")
```

**Step 2: 运行手动验证**

```bash
cd backend
python tests/manual_test_naming.py
```

---

## Task 7: 提交代码

**Step 1: Git 提交**

```bash
cd spark-sql-optimizer
git add backend/core/analyzer.py backend/tests/test_analyzer_naming_rules.py backend/tests/manual_test_naming.py
git commit -m "feat: 添加命名规范检测规则

- TABLE_NAME_WITH_DATE: 检测表名中的硬编码日期
- COMMENT_WITH_SEMICOLON: 检测注释中的分号
- SENSITIVE_INFO_DETECTED: 检测身份证号和敏感字段名

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## 验收标准

1. ✅ 三条新规则添加到 `_init_rules()` 方法
2. ✅ 所有测试用例通过
3. ✅ 手动验证脚本输出正确
4. ✅ 规则严重级别均为 HIGH
5. ✅ 与现有规则风格一致
