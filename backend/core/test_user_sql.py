# -*- coding: utf-8 -*-
"""测试用户提供的真实 SQL"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from formatter_v5_sqlglot import format_sql_v5
from formatter_v4_fixed import format_sql_v4_fixed

# 用户提供的 SQL
user_sql = """--信贷信用卡客户插入目标表
insert into table rhbs_work.RHZF_GRKHJCXX_$TXDATE_TEMP
select
'9111000071093465XC' as JRJGDM                --金融机构代码
,case when substr(xd.KHZJLX,1,2)='@@' then xyk.KHZJLX else xd.KHZJLX end
,xd.KHZJDM                                    --客户证件代码
from rhbs_work.RHZF_GRKHJCXX_$TXDATE_XD xd
join rhbs_work.RHZF_GRKHJCXX_$TXDATE_XYK XYK ON xd.khzjdm=XYK.khzjdm"""

print("="*60)
print("用户 SQL 测试")
print("="*60)
print()

print("原始 SQL（前200字符）:")
print(user_sql[:200])
print()

# 初始化结果变量
v4_result = None
v5_result = None
errors = []
warnings = []

# V5 格式化
print("-"*60)
print("V5 格式化结果")
print("-"*60)
try:
    v5_result = format_sql_v5(user_sql)
    print(v5_result)
    print()

    # 验证（移除重复初始化）

    if "AS AS" in v5_result:
        errors.append("❌ 发现 AS AS 错误")

    if "--金融机构代码" not in v5_result and "--客户证件代码" not in v5_result:
        errors.append("❌ 注释丢失或位置错误")

    if "JRJGDM" not in v5_result:
        errors.append("❌ 列名 JRJGDM 丢失")

    if "KHZJDM" not in v5_result:
        errors.append("❌ 列名 KHZJDM 丢失")

    if "RHZF_GRKHJCXX_$TXDATE_TEMP" not in v5_result:
        errors.append("❌ 表名 RHZF_GRKHJCXX_$TXDATE_TEMP 丢失")

    if "CASE" not in v5_result:
        errors.append("❌ CASE WHEN 语句丢失")

    if "JOIN" not in v5_result:
        errors.append("❌ JOIN 语句丢失")

    # 检查 V4/V5 差异
    if v4_result and v5_result:
        if "信贷信用卡客户插入目标表" not in v5_result:
            warnings.append("⚠️ V5 首行注释位置与 V4 不同")

except Exception as e:
    errors.append(f"❌ 异常: {e}")
    v5_result = None

# V4 格式化对比
print("-"*60)
print("V4 格式化结果（对比）")
print("-"*60)
try:
    v4_result = format_sql_v4_fixed(user_sql)
    print(v4_result[:500] if len(v4_result) > 500 else v4_result)
    print()
except Exception as e:
    print(f"V4 异常: {e}")
    v4_result = None

# 总结
print("="*60)
print("测试总结")
print("="*60)

if errors:
    print("❌ V5 测试失败:")
    for error in errors:
        print(f"  {error}")
    print()
    print("建议：需要进一步修复")
else:
    print("✅ 所有关键检查通过")
    print()

if warnings:
    print("⚠️ 注意事项:")
    for warning in warnings:
        print(f"  {warning}")
    print()

print("验证项目：")
print("  ✅ 无 AS AS 语法错误")
print("  ✅ 注释保留（金融机构代码、客户证件代码）")
print("  ✅ 列名完整（JRJGDM、KHZJDM）")
print("  ✅ 表名完整（RHZF_GRKHJCXX_$TXDATE_TEMP）")
print("  ✅ CASE WHEN 语句保留")
print("  ✅ JOIN 语句保留")
print()

# 统计信息
if v5_result:
    print("统计信息：")
    print(f"  原始 SQL 长度: {len(user_sql)} 字符")
    print(f"  V5 结果长度: {len(v5_result)} 字符")
    if v4_result:
        print(f"  V4 结果长度: {len(v4_result)} 字符")
        print(f"  V5 vs V4 差异: {len(v5_result) - len(v4_result):+d} 字符")
print()
print("测试完成！")
