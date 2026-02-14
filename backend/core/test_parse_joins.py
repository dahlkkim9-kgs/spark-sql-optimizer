"""测试_parse_joins函数"""
import sys
import re
sys.path.insert(0, 'C:/Users/61586/Desktop/自用工作文件/deepseek/测试文件/spark-sql-optimizer/backend')

from core.formatter_v2 import SQLFormatterV2

formatter = SQLFormatterV2()

content = '''rbdb.unitrsdb_jg_ftu_dtl t1 LEFT JOIN ra03.ftzmis_itmno_with_tablename1 t2 ON t1.itm_no = t2.itm_no_kmhandbm LEFT JOIN (SELECT corp_inn_accno,curr_code,cdpt_accno FROM rbdb.cdc_cpcddb_tb_cdmst_deppdcon_acc WHERE start_dt <= '{DATA_DT}' AND end_dt > '{DATA_DT}' AND (cdpt_accno LIKE 'FTE%' OR cdpt_accno LIKE 'FTN%') ) t8 ON t1.acc = CAST(t8.corp_inn_accno AS string)'''

print('Testing _parse_joins function:')
print('Input length:', len(content))
print()

parts = formatter._parse_joins(content)
print(f'Number of parts: {len(parts)}')
print()

for idx, (part_type, value) in enumerate(parts):
    print(f'{idx+1}. {part_type} (length={len(value)}):')
    if part_type == 'SUBQUERY':
        print(f'   {repr(value)}')
        # 测试格式化子查询
        formatted = formatter._format_select(value)
        print(f'   FORMATTED:')
        for line in formatted.split('\n'):
            print(f'     {repr(line)}')
    else:
        print(f'   {repr(value)}')
    print()
