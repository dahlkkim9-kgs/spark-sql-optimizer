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
