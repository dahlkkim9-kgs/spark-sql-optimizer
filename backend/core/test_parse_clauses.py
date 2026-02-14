"""测试_parse_clauses函数"""
import sys
import re
sys.path.insert(0, 'C:/Users/61586/Desktop/自用工作文件/deepseek/测试文件/spark-sql-optimizer/backend')

from core.formatter_v2 import SQLFormatterV2

formatter = SQLFormatterV2()

# 测试完整的SELECT语句
full_select = '''SELECT t1.id FROM rbdb.unitrsdb_jg_ftu_dtl t1 LEFT JOIN ra03.ftzmis_itmno_with_tablename1 t2 ON t1.itm_no = t2.itm_no_kmhandbm LEFT JOIN (SELECT corp_inn_accno,curr_code,cdpt_accno FROM rbdb.cdc_cpcddb_tb_cdmst_deppdcon_acc WHERE start_dt <= '{DATA_DT}' AND end_dt > '{DATA_DT}' AND (cdpt_accno LIKE 'FTE%' OR cdpt_accno LIKE 'FTN%') ) t8 ON t1.acc = CAST(t8.corp_inn_accno AS string) WHERE t1.etl_load_date = '{DATA_DT}' AND t1.inst_no LIKE '%F' AND NVL(t1.acc ,'') <> '' AND t8.corp_inn_accno IS NOT NULL'''

print('Testing _parse_clauses with full SELECT statement:')
print('Input:', full_select[:100], '...')
print()

clauses = formatter._parse_clauses(full_select)
print(f'Number of clauses: {len(clauses)}')
print()

for idx, (clause_type, content) in enumerate(clauses):
    print(f'{idx+1}. {clause_type}:')
    content_preview = content[:100] if len(content) > 100 else content
    print(f'   {repr(content_preview)}')
    print()
