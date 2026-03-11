--原始代码
SELECT  SUBSTR(t8.cdpt_accno,1,16) AS accountno  --主帐号，除历史5个账号报错，保持连续性，5个账号还按之前的报，其他账号取前16位
       ,t8.cdpt_accno AS accountno1 --主帐号1，公司表关联要取完整账号
       ,CASE WHEN SUBSTR(t8.cdpt_accno,1,3) = 'FTE'  THEN '01' WHEN SUBSTR(t8.cdpt_accno,1,3) = 'FTN'  THEN '02' ELSE '' END AS acctype       --类别  fanchunsheng 20250709
       ,'1' AS customtype      --客户类型 单位
       ,CASE WHEN SUBSTR(t8.cdpt_accno,1,3) = 'FTE'  THEN '11' WHEN SUBSTR(t8.cdpt_accno,1,3) = 'FTN'  THEN '12' ELSE '' END  AS documenttype --证件类型  fanchunsheng  20250709
       ,t7.zmdm AS currency   --货币
       ,t1.tally_date AS submitdate --申报日期
       ,CASE WHEN t1.inst_no IN ('3199480F','3100500F','3100001F') THEN '403290000008'   ELSE '' END AS accorgcode   --开户机构代码
       ,LPAD(ROW_NUMBER() OVER(PARTITION BY t1.acc,t1.tally_date ORDER BY t1.host_seqno ASC),6,'0') AS seqno --明细序号
       ,CASE WHEN t1.itm_no LIKE '1025%' OR t1.itm_no LIKE '3145%' OR t1.itm_no LIKE '3140%' OR t1.itm_no LIKE '3155%' OR t1.itm_no LIKE '3150%' OR t1.itm_no LIKE '3170%' OR t1.itm_no LIKE '3141%' OR t1.itm_no LIKE '2%' OR t1.itm_no LIKE '4%' OR t1.itm_no LIKE '5%' THEN (CASE WHEN t1.dr_cr_flag = '借' THEN '1' WHEN t1.dr_cr_flag = '贷' THEN '2' ELSE '' END ) WHEN t1.itm_no LIKE '1%' OR t1.itm_no LIKE '6%' OR  t1.itm_no LIKE '3%' THEN (CASE WHEN t1.dr_cr_flag = '借'  THEN '2' WHEN t1.dr_cr_flag = '贷'  THEN '1'  ELSE '' END) ELSE '' END AS cdflag11  --出入账标志
        ,t1.tally_date AS trandate  --记帐日期
        ,'' AS orgtrandate        --原始交易日期
        ,t1.amt AS amount      --金额
        ,'310115' AS districtcode --国内地区码
        ,'0' AS termlength    --期限长度  无固定期限
        ,'1' AS termunit      --期限单位 年
        ,'20991231' AS expiredate   --到期日
        ,t1.inst_no AS bank_id    --机构号
        ,'KJPT' AS data_source    --数据源
        ,'210101单位存款'                       AS jkmc       --接口名称
        ,t1.host_seqno                          AS sys_seqno  --流水号
        ,t1.clt_seqno                           AS clt_seqno  --系统跟踪号
        ,t1.itm_no                              AS itm_no     --科目号
        ,t1.acc_date                                          --会计日期
        ,t1.acc_date    AS kj_date              --会计日期2
        ,t1.entry_serno  --分录序号
        ,t1.curr_type  --数字币种
        ,'{DATA_DT}' AS data_dt
FROM rbdb.unitrsdb_jg_ftu_dtl t1 --/*modify BY fanchunsheng 20240821*/
LEFT JOIN ra03.ftzmis_itmno_with_tablename1 t2 ON t1.itm_no = t2.itm_no_kmhandbm
LEFT JOIN ra03.ftzmis_itmno_with_tablename1 t3 ON SUBSTR(t1.itm_no,1,11) = t3.itm_no_kmhandbm
LEFT JOIN ra03.ftzmis_itmno_with_tablename1 t4 ON SUBSTR(t1.itm_no,1,9)  = t4.itm_no_kmhandbm
LEFT JOIN ra03.ftzmis_itmno_with_tablename1 t5 ON SUBSTR(t1.itm_no,1,6)  = t5.itm_no_kmhandbm
LEFT JOIN ra03.ftzmis_itmno_with_tablename1 t6 ON SUBSTR(t1.itm_no,1,4)  = t6.itm_no_kmhandbm
LEFT JOIN ra03.ftzmis_curr_type_exchange t7 ON t1.curr_type = t7.szdm
LEFT JOIN (SELECT corp_inn_accno,curr_code,cdpt_accno FROM rbdb.cdc_cpcddb_tb_cdmst_deppdcon_acc WHERE start_dt <= '{DATA_DT}' AND end_dt > '{DATA_DT}' AND (cdpt_accno LIKE 'FTE%' OR cdpt_accno LIKE 'FTN%') ) t8 ON t1.acc = CAST(t8.corp_inn_accno AS string) --存款产品合约账户
WHERE t1.etl_load_date = '{DATA_DT}' AND t1.inst_no LIKE '%F' AND NVL(t1.acc ,'') <> '' AND t8.corp_inn_accno IS NOT NULL
AND (t2.tablename = 'FTZ210101'
OR   t3.tablename = 'FTZ210101'
OR   t4.tablename = 'FTZ210101'
OR   t5.tablename = 'FTZ210101'
OR   t6.tablename = 'FTZ210101')
DISTRIBUTE BY ceil(rand()*1)
;
