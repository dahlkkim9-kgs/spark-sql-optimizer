/* ********************************************
表英文名：RHZF_GRKHJCXX
表中文名：金融基础数据库-个人客户基础信息（两系统客户汇总去重）
所用源表：
数据加载方式： 全量加载
开发人员：WJ
*************************************************/
-----------------------------------------------------------------------------------------------------------------------------------------------------向目标表插入数据
DROP TABLE IF EXISTS rhbs_work.RHZF_GRKHJCXX_$TXDATE_TEMP
;

CREATE TABLE IF NOT EXISTS rhbs_work.RHZF_GRKHJCXX_$TXDATE_TEMP
(
 JRJGDM                           STRING     COMMENT  '金融机构代码            '
,KHZJLX                           STRING     COMMENT  '客户证件类型            '
,KHZJDM                           STRING     COMMENT  '客户证件代码            '
,GJ                               STRING     COMMENT  '国籍                    '
,MZ                               STRING     COMMENT  '民族                    '
,XB                               STRING     COMMENT  '性别                    '
,ZGXL                             STRING     COMMENT  '最高学历                '
,CSRQ                             STRING     COMMENT  '出生日期                '
,DQDM                             STRING     COMMENT  '地区代码                '
,GRNSR                            STRING     COMMENT  '个人年收入              '
,JTNSR                            STRING     COMMENT  '家庭年收入              '
,HYQK                             STRING     COMMENT  '婚姻情况                '
,SFGLF                            STRING     COMMENT  '是否关联方              '
,SXED                             STRING     COMMENT  '授信额度                '
,YYED                             STRING     COMMENT  '已用额度                '
,GRKHSFBS                         STRING     COMMENT  '个人客户身份标识        '
,GTGSHYYZZ                        STRING     COMMENT  '个体工商户营业执照代码  '
,XWQYTYSHXYDM                     STRING     COMMENT  '小微企业统一社会信用代码'
,KHXYJBZDJS                       STRING     COMMENT  '客户信用级别总等级数    '
,KHXYPJ                           STRING     COMMENT  '客户信用评级            '
,KHBH                             STRING     COMMENT  '客户编号                '
,KHMC                             STRING     COMMENT  '客户名称'
,KHJL                             STRING     COMMENT  '客户经理'
,YJFH                             STRING     COMMENT  '一级分行'
,EJFH                             STRING     COMMENT  '二级分行'
,flag                             STRING
,dzmc                             STRING
,dzid                             STRING
,cjrq                             STRING
,flag1                            STRING
,nbjgh                            STRING
)
COMMENT '个人客户基础信息表'
ROW FORMAT DELIMITED NULL DEFINED AS ''
;

-------信用卡客户插入目标表
INSERT INTO TABLE rhbs_work.RHZF_GRKHJCXX_$TXDATE_TEMP
SELECT XYK.JRJGDM
     , XYK.KHZJLX
     , XYK.KHZJDM
     , xyk.GJ
     , '' AS MZ
     , xyk.XB
     , xyk.ZGXL
     , xyk.CSRQ
     , xyk.DQDM
     , xyk.GRNSR
     , '' AS jtnsr
     , xyk.HYQK
     , XYK.SFGLF
     , XYK.SXED
     , XYK.YYED
     , XYK.GRKHSFBS
     , XYK.GTGSHYYZZ
     , XYK.XWQYTYSHXYDM
     , XYK.KHXYJBZDJS
     , XYK.KHXYPJ
     , '' AS KHBH
     , xyk.khmc AS KHMC
     , '' AS KHJL
     , '' AS YJFH
     , '' AS EJFH
     , '信用卡'
     , '' AS dzmc
     , '' AS dzid
     , '' AS cjrq
     , '' AS flag1
     , xyk.nbjgh
FROM (
    SELECT *
    FROM rhbs_work.RHZF_GRKHJCXX_$TXDATE_XYK
        WHERE khzjdm NOT IN (
            SELECT DISTINCT khzjdm
            FROM rhbs_work.RHZF_GRKHJCXX_$TXDATE_XD
        )
) xyk
;

-----信贷客户插入目标表
--全部放到一张表里面
DROP TABLE rhbs_work.rhzf_dkye_$TXDATE
;

CREATE TABLE rhbs_work.rhzf_dkye_$TXDATE AS
SELECT jkrzjdm AS cust_no
     , SUM(dkye) AS DKYE
FROM rhbs_work.rhzf_clgrdkxx_tmp_$TXDATE
    WHERE flag IN ('1','2','3','6')
    GROUP BY jkrzjdm
;

INSERT INTO TABLE rhbs_work.RHZF_GRKHJCXX_$TXDATE_TEMP
SELECT xd.JRJGDM
     , xd.KHZJLX
     , xd.KHZJDM
     , xd.GJ
     , xd.MZ
     , xd.XB
     , xd.ZGXL
     , xd.CSRQ
     , xd.DQDM
     , xd.GRNSR
     , xd.JTNSR
     , xd.HYQK
     , xd.SFGLF
     , xd.SXED
     , CASE
           WHEN NVL(xd.YYED,0)-0<0
                   OR (NVL(xd.YYED,0)-0>NVL(xd.SXED,0)-0 AND NVL(xd.SXED,0)-0>=NVL(b.dkye,0)-0)
           THEN b.dkye
           WHEN NVL(xd.YYED,0)-0<0
                   OR (NVL(xd.YYED,0)-0>NVL(xd.SXED,0)-0 AND NVL(xd.SXED,0)-0<NVL(b.dkye,0)-0)
           THEN xd.sxed
           ELSE xd.YYED
       END
     , xd.GRKHSFBS
     , xd.GTGSHYYZZ
     , xd.XWQYTYSHXYDM
     , xd.KHXYJBZDJS
     , xd.KHXYPJ
     , xd.khbh AS KHBH
     , xd.khmc AS KHMC
     , '' AS KHJL
     , '' AS YJFH
     , '' AS EJFH
     , '信贷'
     , ''
     , ''
     , xd.cjrq
     , ''
     , xd.nbjgh
FROM (
    SELECT *
    FROM rhbs_work.RHZF_GRKHJCXX_$TXDATE_xd
        WHERE khzjdm NOT IN (
            SELECT DISTINCT khzjdm
            FROM rhbs_work.RHZF_GRKHJCXX_$TXDATE_XYK
        )
) xd
    LEFT JOIN rhbs_work.rhzf_dkye_$TXDATE b
        ON xd.khzjdm=b.cust_no
;

--信贷信用卡客户插入目标表
INSERT INTO TABLE rhbs_work.RHZF_GRKHJCXX_$TXDATE_TEMP
SELECT '9111000071093465XC' AS JRJGDM        --金融机构代码
     , CASE
           WHEN SUBSTR(xd.KHZJLX,1,2)='@@'
           THEN xyk.KHZJLX
           ELSE xd.KHZJLX
       END
     , xd.KHZJDM AS                          --客户证件代码
     , CASE
           WHEN (xyk.GJ='' OR xyk.GJ IS NULL OR SUBSTR(xyk.GJ,1,2)='@@')
                   AND (xd.GJ<>'' AND xd.GJ IS NOT NULL AND SUBSTR(xd.GJ,1,2)<>'@@')
           THEN xd.GJ
           ELSE xyk.GJ
       END AS  --国籍
     , xd.mz AS MZ                           --民族
     , CASE
           WHEN (xyk.XB='' OR xyk.XB IS NULL OR SUBSTR(xyk.XB,1,2)='@@')
                   AND (xd.XB<>'' AND xd.XB IS NOT NULL AND SUBSTR(xd.XB,1,2)<>'@@')
           THEN xd.XB
           ELSE xyk.XB
       END AS  --性别
     , CASE
           WHEN (xyk.ZGXL='' OR xyk.ZGXL IS NULL OR SUBSTR(xyk.ZGXL,1,2)='@@')
                   AND (xd.ZGXL<>'' AND xd.ZGXL IS NOT NULL AND SUBSTR(xd.ZGXL,1,2)<>'@@')
           THEN xd.ZGXL
           ELSE xyk.ZGXL
       END AS  --最高学历
     , CASE
           WHEN (xyk.csrq='' OR xyk.csrq IS NULL)
                   AND (xd.csrq<>'' AND xd.csrq IS NOT NULL)
           THEN xd.csrq
           ELSE xyk.csrq
       END AS  --出生日期
     , xd.DQDM AS                            --地区代码
     , CASE
           WHEN xd.grnsr IS NOT NULL
                   AND xd.grnsr<>''
                   AND xd.grnsr-0>0
           THEN xd.grnsr
           WHEN (xd.grnsr IS NULL OR xd.grnsr='' OR xd.grnsr-0<=0)
                   AND xyk.grnsr IS NOT NULL
                   AND xyk.grnsr<>''
                   AND xyk.grnsr-0>0
           THEN xyk.grnsr
           ELSE xd.grnsr
       END AS  --个人年收入
     , xd.JTNSR
     , CASE
           WHEN (xyk.HYQK='' OR xyk.HYQK IS NULL OR SUBSTR(xyk.HYQK,1,2)='@@')
                   AND (xd.HYQK<>'' AND xd.HYQK IS NOT NULL AND SUBSTR(xd.HYQK,1,2)<>'@@')
           THEN xd.HYQK
           ELSE xyk.HYQK
       END AS  --婚姻情况
     , XD.SFGLF AS                           --是否关联方
     , NVL(xd.sxed,0)+NVL(xyk.sxed,0) AS     --授信额度
     , NVL(xd.yyed,0)+NVL(xyk.yyed,0) AS     --已用额度
     , '' AS GRKHSFBS                        --个人客户身份标识  人行反馈暂时无需报送
     , '' AS GTGSHYYZZ                       --个体工商户营业执照代码  人行反馈暂时无需报送
     , '' AS XWQYTYSHXYDM                    --小微企业统一社会信用代码  人行反馈暂时无需报送
     , '' AS KHXYJBZDJS                      --客户信用级别总等级数
     , '' AS KHXYPJ                          --客户信用评级
     , xd.khbh
     , xd.khmc
     , ''
     , ''
     , ''
     , '信贷+信用卡'
     , ''
     , ''
     , xd.cjrq
     , ''
     , xd.nbjgh
     , ''                                    --测试
FROM rhbs_work.RHZF_GRKHJCXX_$TXDATE_XD xd
    JOIN rhbs_work.RHZF_GRKHJCXX_$TXDATE_XYK XYK
        ON xd.khzjdm=XYK.khzjdm
;

--测试with AS 
WITH A AS (SELECT aa,
bb,
cc
FROM  tab_tes WHERE aa='1' AND  bb='2' OR (aa ='2' AND  bb='2' AND cc='3'))
;

--测试CACHE TABLE
CACHE TABLE B AS (SELECT aa,
bb,
cc
FROM  tab_tes WHERE aa='1' AND  bb='2' OR (aa ='2' AND  bb='2' AND cc='3'))
;

--分区综合语句测试
INSERT INTO ra03.temp_ftz210101_direct PARTITION(data_dt)
SELECT SUBSTR(
    t8.cdpt_accno
, 1
, 16
) AS accountno   --主帐号，除历史5个账号报错，保持连续性，5个账号还按之前的报，其他账号取前16位
     , t8.cdpt_accno AS accountno1                                                                     --主帐号1，公司表关联要取完整账号
     , CASE
           WHEN SUBSTR(t8.cdpt_accno,1,3) = 'FTE'
           THEN '01'
           WHEN SUBSTR(t8.cdpt_accno,1,3) = 'FTN'
           THEN '02'
           ELSE ''
       END AS acctype  --类别  fanchunsheng 20250709
     , '1' AS customtype                                                                               --客户类型 单位
     , CASE
           WHEN SUBSTR(t8.cdpt_accno,1,3) = 'FTE'
           THEN '11'
           WHEN SUBSTR(t8.cdpt_accno,1,3) = 'FTN'
           THEN '12'
           ELSE ''
       END AS documenttype  --证件类型  fanchunsheng  20250709
     , t7.zmdm AS currency                                                                             --货币
     , t1.tally_date AS submitdate                                                                     --申报日期
     , CASE
           WHEN t1.inst_no IN ('3199480F','3100500F','3100001F')
           THEN '403290000008'
           ELSE ''
       END AS accorgcode  --开户机构代码
     , LPAD(
    ROW_NUMBER() OVER(PARTITION BY t1.acc, t1.tally_date ORDER BY t1.host_seqno ASC)
, 6
, '0'
) AS seqno   --明细序号
     , CASE
           WHEN t1.itm_no LIKE '1025%'
                   OR t1.itm_no LIKE '3145%'
                   OR t1.itm_no LIKE '3140%'
                   OR t1.itm_no LIKE '3155%'
                   OR t1.itm_no LIKE '3150%'
                   OR t1.itm_no LIKE '3170%'
                   OR t1.itm_no LIKE '3141%'
                   OR t1.itm_no LIKE '2%'
                   OR t1.itm_no LIKE '4%'
                   OR t1.itm_no LIKE '5%'
           THEN (
               CASE
                   WHEN t1.dr_cr_flag = '借'
                   THEN '1'
                   WHEN t1.dr_cr_flag = '贷'
                   THEN '2'
                   ELSE ''
               END
               )
           WHEN t1.itm_no LIKE '1%'
                   OR t1.itm_no LIKE '6%'
                   OR t1.itm_no LIKE '3%'
           THEN (
               CASE
                   WHEN t1.dr_cr_flag = '借'
                   THEN '2'
                   WHEN t1.dr_cr_flag = '贷'
                   THEN '1'
                   ELSE ''
               END
               )
           ELSE ''
       END AS cdflag11  --出入账标志
     , t1.tally_date AS trandate                                                                       --记帐日期
     , '' AS orgtrandate                                                                               --原始交易日期
     , t1.amt AS amount                                                                                --金额
     , '310115' AS districtcode                                                                        --国内地区码
     , '0' AS termlength                                                                               --期限长度  无固定期限
     , '1' AS termunit                                                                                 --期限单位 年
     , '20991231' AS expiredate                                                                        --到期日
     , t1.inst_no AS bank_id                                                                           --机构号
     , 'KJPT' AS data_source                                                                           --数据源
     , '210101单位存款' AS jkmc                                                                            --接口名称
     , t1.host_seqno AS sys_seqno                                                                      --流水号
     , t1.clt_seqno AS clt_seqno                                                                       --系统跟踪号
     , t1.itm_no AS itm_no                                                                             --科目号
     , t1.acc_date AS                                                                                  --会计日期
     , t1.acc_date AS kj_date                                                                          --会计日期2
     , t1.entry_serno AS                                                                               --分录序号
     , t1.curr_type AS                                                                                 --数字币种 
     , '{DATA_DT}' AS data_dt
FROM rbdb.unitrsdb_jg_ftu_dtl t1  --/*modify BY fanchunsheng 20240821*/
    LEFT JOIN ra03.ftzmis_itmno_with_tablename1 t2
        ON t1.itm_no = t2.itm_no_kmhandbm
    LEFT JOIN ra03.ftzmis_itmno_with_tablename1 t3
        ON SUBSTR(t1.itm_no,1,11) = t3.itm_no_kmhandbm
    LEFT JOIN ra03.ftzmis_itmno_with_tablename1 t4
        ON SUBSTR(t1.itm_no,1,9) = t4.itm_no_kmhandbm
    LEFT JOIN ra03.ftzmis_itmno_with_tablename1 t5
        ON SUBSTR(t1.itm_no,1,6) = t5.itm_no_kmhandbm
    LEFT JOIN ra03.ftzmis_itmno_with_tablename1 t6
        ON SUBSTR(t1.itm_no,1,4) = t6.itm_no_kmhandbm
    LEFT JOIN ra03.ftzmis_curr_type_exchange t7
        ON t1.curr_type = t7.szdm
    LEFT JOIN
        (
            SELECT corp_inn_accno
                 , curr_code
                 , cdpt_accno
            FROM rbdb.cdc_cpcddb_tb_cdmst_deppdcon_acc
            WHERE start_dt <= '{DATA_DT}'
                AND end_dt > '{DATA_DT}'
                AND (
                    cdpt_accno LIKE 'FTE%'
                    OR cdpt_accno LIKE 'FTN%'
                )
        ) t8  --存款产品合约账户
        ON t1.acc = CAST(t8.corp_inn_accno AS STRING)
    WHERE t1.etl_load_date = '{DATA_DT}'
        AND t1.inst_no LIKE '%F'
        AND NVL(t1.acc ,'') <> ''
        AND t8.corp_inn_accno IS NOT NULL
        AND (
            t2.tablename = 'FTZ210101'
            OR t3.tablename = 'FTZ210101'
            OR t4.tablename = 'FTZ210101'
            OR t5.tablename = 'FTZ210101'
            OR t6.tablename = 'FTZ210101'
        )
DISTRIBUTE BY CEIL(RAND()*1)
;

--测试建表语句
CREATE TABLE IF NOT EXISTS rhbs_work.kgs_test
(
 aaa                              STRING     COMMENT  '金融机构代码a'
,bbb                              STRING     COMMENT  '金融机构代码b'
,ccc                 DECIMAL(2000000000000,5)     COMMENT  '金融机构代码c'
,ddd                            CHAR (2)     COMMENT  '金融机构代码d'
)
COMMENT '个人客户基础信息表'
PARTITIONED BY
(
aaa                              STRING     COMMENT  '金融机构代码a'
)
ROW FORMAT DELIMITED NULL DEFINED AS ''
;