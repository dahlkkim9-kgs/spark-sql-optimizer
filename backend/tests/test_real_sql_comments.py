import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from formatter_v4 import format_sql_v4

def test_real_world_sql_ftz():
    """Test with real FTZ SQL"""
    sql = """SELECT t1.id -- 账号ID
     , t1.name -- 账户名称
     , t2.amount -- 交易金额
FROM ra03.account_info t1 -- 账户信息表
    LEFT JOIN ra03.transaction t2 -- 交易流水表
        ON t1.id = t2.account_id
WHERE t1.status = '1' -- 有效账户
    AND t2.tx_date >= '20240101' -- 2024年交易
;"""

    result = format_sql_v4(sql)

    # Verify all Chinese comments are preserved
    assert "-- 账号ID" in result
    assert "-- 账户名称" in result
    assert "-- 交易金额" in result
    assert "-- 账户信息表" in result
    assert "-- 交易流水表" in result
    assert "-- 有效账户" in result
    assert "-- 2024年交易" in result

    # Verify formatting is applied
    assert "LEFT JOIN" in result
    assert "WHERE" in result


def test_real_world_sql_with_case():
    """Test with SQL containing CASE with comments"""
    sql = """SELECT
    CASE
        WHEN cert_type = '1070' THEN 'HK' -- 港澳通行证
        WHEN cert_type = '1080' THEN 'TW' -- 台湾通行证
        ELSE 'OTHER' -- 其他证件
    END AS cert_type_desc
FROM users"""

    result = format_sql_v4(sql)

    assert "-- 港澳通行证" in result
    assert "-- 台湾通行证" in result
    assert "-- 其他证件" in result
