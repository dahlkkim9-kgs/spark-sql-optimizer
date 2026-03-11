--# -*- coding: utf-8 -*-
--
--#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#
--#脚本名称      : GJDG_JRZF_D01_PARALLEL_CWKJB.py
--#加载策略      : (1.单日增量  2.全量 3.区间全量  4多日增量)
--#源表类型      : (1.历史拉链  2.区间流水)
--#源    表        :   
--#  1       ACCGLDB_T_ACC_INST_DVLP                 会计平台_核算机构总账表(业务套账机构总帐表)
--#功能描述      : D01表：货币与存款（含存放银行同业和联行）（资产）             财务会计部
--#开发人员/复核人员: guotao/kuangshichao
--#创建日期      : 2022/08/24
--#修改历史及标识: --/*modify by xxx 日期*/
--#{
--#               1,20220831 首次上线
--#               2,20221227 范春生  增加三个字段：OWNUSR、FALPERS、FALDEPT--/*modify by fanchunsheng 20221227*/
--#               3,20230717 qiuyelong  增加财务会计部加工逻辑--/*modify by qiuyelong 20230717*/
--#               4,20231025 qiuyelong  拆分出财务会计部加工逻辑至新的一个独立脚本中--/*modify by qiuyelong 20231018*/
--#               5,20250828 qiuyelong  配套外管局1.4规范改造，新增三个字段： d0115 INT COMMENT '是否存在风险转移',                  
--#                                                                           d0116 varchar(3) COMMENT '风险转往国家/地区',          
--#                                                                           d0117 INT COMMENT '风险转往部门'                --/*modify by qiuyelong 20250828*/
--#               5,20251112 qiuyelong  将财务会计部和数字人民币部加工逻辑合并,并获取统一监管上月末数据 --/*modify by qiuyelong 20251112*/
--#}
--#备注            :
--#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#
--建临时报送表
CREATE TABLE IF NOT EXISTS RA03.T_GJDG_JRZF_D01_TMP_CWKJB(
     ACTIONTYPE         VARCHAR(1)              COMMENT     '删除原因'
    ,ACTIONDESC         STRING                  COMMENT     '操作类型'
    ,SNOCODE            VARCHAR(36)             COMMENT     '数据自编码'
    ,OBJCODE            VARCHAR(18)             COMMENT     '申报主体代码'
    ,BUOCMONTH          VARCHAR(6)              COMMENT     '报告期'
    ,D0101              VARCHAR(1)              COMMENT     '业务类别'
    ,D0102              VARCHAR(3)              COMMENT     '对方国家/地区'
    ,D0103              VARCHAR(1)              COMMENT     '对方部门'
    ,D0104              VARCHAR(1)              COMMENT     '对方与本机构的关系'
    ,D0105              VARCHAR(1)              COMMENT     '原始期限'
    ,D0106              VARCHAR(3)              COMMENT     '原始币种'
    ,D0107              DECIMAL(22,2)           COMMENT     '上月末本金金额'
    ,D0108              DECIMAL(22,2)           COMMENT     '上月末应收利息金额'
    ,D0109              DECIMAL(22,2)           COMMENT     '本月末本金金额'
    ,D0110              DECIMAL(22,2)           COMMENT     '本月末本金金额：其中剩余期限在一年及以下'
    ,D0111              DECIMAL(22,2)           COMMENT     '本月末应收利息余额'
    ,D0112              DECIMAL(22,2)           COMMENT     '本月非交易变动'
    ,D0113              DECIMAL(22,2)           COMMENT     '本月净发生额'
    ,D0114              DECIMAL(22,2)           COMMENT     '本月利息收入'
    ,REMARK             STRING                  COMMENT     '备注'
    ,DATA_SOURCE        STRING                  COMMENT     '数据源:XGJ表示新一代国际结算系统,CWKJB表示财务会计部'
    ,bank_id            VARCHAR(8)              COMMENT     '机构号'
    ,ownusr             STRING                  COMMENT     '柜员号              '
    ,falpers            STRING                  COMMENT     '报送人             '
    ,faldept            STRING                  COMMENT     '上月末市值报送部门   '
    ,d0115              INT                     COMMENT     '是否存在风险转移'
    ,d0116              VARCHAR(3)              COMMENT     '风险转往国家/地区'
    ,d0117              INT                     COMMENT     '风险转往部门'
) COMMENT 'D01财务会计部临时表'
 PARTITIONED BY (data_dt STRING)
;

--创建目标表
CREATE TABLE IF NOT EXISTS RA03.T_GJDG_JRZF_D01_PARALLEL (
     ACTIONTYPE         VARCHAR(1)              COMMENT     '删除原因'
    ,ACTIONDESC         STRING                  COMMENT     '操作类型'
    ,SNOCODE            VARCHAR(36)             COMMENT     '数据自编码'
    ,OBJCODE            VARCHAR(18)             COMMENT     '申报主体代码'
    ,BUOCMONTH          VARCHAR(6)              COMMENT     '报告期'
    ,D0101              VARCHAR(1)              COMMENT     '业务类别'
    ,D0102              VARCHAR(3)              COMMENT     '对方国家/地区'
    ,D0103              VARCHAR(1)              COMMENT     '对方部门'
    ,D0104              VARCHAR(1)              COMMENT     '对方与本机构的关系'
    ,D0105              VARCHAR(1)              COMMENT     '原始期限'
    ,D0106              VARCHAR(3)              COMMENT     '原始币种'
    ,D0107              DECIMAL(22,2)           COMMENT     '上月末本金金额'
    ,D0108              DECIMAL(22,2)           COMMENT     '上月末应收利息金额'
    ,D0109              DECIMAL(22,2)           COMMENT     '本月末本金金额'
    ,D0110              DECIMAL(22,2)           COMMENT     '本月末本金金额：其中剩余期限在一年及以下'
    ,D0111              DECIMAL(22,2)           COMMENT     '本月末应收利息余额'
    ,D0112              DECIMAL(22,2)           COMMENT     '本月非交易变动'
    ,D0113              DECIMAL(22,2)           COMMENT     '本月净发生额'
    ,D0114              DECIMAL(22,2)           COMMENT     '本月利息收入'
    ,REMARK             STRING                  COMMENT     '备注'
    ,bank_id            VARCHAR(8)              COMMENT     '机构号'
    ,ownusr             STRING                  COMMENT     '柜员号              '
    ,falpers            STRING                  COMMENT     '报送人             '
    ,faldept            STRING                  COMMENT     '上月末市值报送部门   '
    ,d0115              INT                     COMMENT     '是否存在风险转移'
    ,d0116              VARCHAR(3)              COMMENT     '风险转往国家/地区'
    ,d0117              INT                     COMMENT     '风险转往部门'
) COMMENT 'D01货币与存款（含存放银行同业和联行）报送表'
 PARTITIONED BY ( month STRING ,data_source STRING COMMENT '数据源:XGJ表示新一代国际结算系统,CWKJB表示财务会计部' ,data_dt STRING)
;

ALTER TABLE RA03.T_GJDG_JRZF_D01_TMP_CWKJB DROP IF EXISTS PARTITION (data_dt='{DATA_DT}')
;

INSERT INTO RA03.T_GJDG_JRZF_D01_TMP_CWKJB PARTITION(data_dt='{DATA_DT}')
SELECT 'A'                                                                              AS ACTIONTYPE   --操作类型
     , ''                                                                               AS ACTIONDESC   --删除原因
     , CONCAT('110000013000aaaaaaD01aa',
              SUBSTRING('{DATA_DT}',1,6),
              '2',
              LPAD(ROW_NUMBER() OVER(PARTITION BY 1 ORDER BY dvlp.curr_type),6,'0')
              )                                                                       AS SNOCODE   --数据自编码
     , '110000013000'                                                                   AS OBJCODE   --申报主体代码
     , CAST(SUBSTRING('{DATA_DT}',1,6) AS VARCHAR(6))                                   AS BUOCMONTH   --报告期
     , '0'                                                                              AS D0101   --业务类别
     , country.d0102                                                                    AS D0102   --对方国家/地区
     , '2'                                                                              AS D0103   --对方部门
     , '4'                                                                              AS D0104   --对方与本机构的关系
     , '1'                                                                              AS D0105   --原始期限
     , curr.cd_value1                                                                   AS D0106   --原始币种
     , NVL(ld01.d0109,0.00)                                                             AS D0107   --上月末本金金额
     , NVL(ld01.d0111,0.00)                                                             AS D0108   --上月末应收利息金额
     , dvlp.su_bal                                                                      AS D0109   --本月末本金金额
     , dvlp.su_bal                                                                      AS D0110   --本月末本金金额：其中剩余期限在一年及以下
     , dvlp.D0111                                                                       AS D0111   --本月末应收利息余额
     , dvlp.D0112                                                                       AS D0112   --本月非交易变动
     , (dvlp.su_bal+dvlp.D0111)-(NVL(ld01.d0109,0.00)+NVL(ld01.d0111,0.00))-dvlp.D0112  AS D0113   --本月净发生额 =（本月末本金余额+本月末应收利息余额）-（上月末本金余额+上月末应收利息余额）-本月非交易变动
     , dvlp.D0114                                                                       AS D0114   --本月利息收入
     , ''                                                                               AS REMARK   --备注
     , 'CWKJB'                                                                          AS DATA_SOURCE   --数据来源
     , '11005293'                                                                       AS BANK_ID   --机构代码号
     , '20070709380'                                                                    AS OWNUSR   --柜员号
     , '郝坤'                                                                             AS FALPERS   --报送人
     , '财务会计部'                                                                          AS FALDEPT   --报送部门
     , 2                                                                                AS d0115 --是否存在风险转移
     , NULL                                                                             AS d0116 --风险转往国家/地区
     , NULL d0117 --风险转往部门 FROM (SELECT curr_type                                 curr_type    --数字形式码值
            ,SUM(dr_crt_bal)                           su_bal       --本月末本金金额
            ,CAST(0.00 AS DECIMAL(22,2))               D0111        --本月末应收利息余额
            ,CAST(0.00 AS DECIMAL(22,2))               D0112        --本月非交易变动 
            ,CAST(0.00 AS DECIMAL(22,2))               D0114        --本月利息收入
      FROM rbdb.accgldb_t_acc_inst_dvlp --会计平台_核算机构总账表(业务套账机构总帐表)
      WHERE itm_no IN ('1001','1002') --科目号
      AND curr_type NOT IN ('156','RMB','USD')
      AND start_dt<='{DATA_DT}' --获取月末日期
      AND end_dt>'{DATA_DT}' --获取月末日期
      GROUP BY curr_type
      )                                              AS dvlp
    LEFT JOIN ra03.wgj_send_curr curr
        ON dvlp.curr_type=curr.std_cd_value
    LEFT JOIN ra03.d01_cwkj_cc country
        ON country.d0106=curr.cd_value1
    LEFT JOIN RA03.T_GJDG_JRZF_D01_TMP_CWKJB ld01
        ON country.d0106=ld01.D0106
        AND ld01.data_dt=date_format(
                                   date_add(
                                            concat(SUBSTR('{DATA_DT}',1,4),'-',SUBSTR('{DATA_DT}',5,2),'-','01'),
                                            -1
                                           )
                                   ,'yyyyMMdd'
                                  )  --获取上月末统计结果
        AND ld01.data_source='CWKJB'  --数据源为财务会计部
    WHERE ld01.d0109<>0.00
    OR ld01.d0111<>0.00
    OR dvlp.su_bal<>0.00
    OR dvlp.su_bal<>0.00
    OR dvlp.D0111<>0.00
    OR dvlp.D0112<>0.00
    OR (dvlp.su_bal+dvlp.D0111)-(NVL(ld01.d0109,0.00)+NVL(ld01.d0111,0.00))-dvlp.D0112<>0.00
    OR dvlp.D0114<>0.00
;

INSERT INTO RA03.T_GJDG_JRZF_D01_TMP_CWKJB PARTITION(data_dt='{DATA_DT}')
SELECT 'A'                                                           AS ACTIONTYPE   --操作类型
     , ''                                                            AS ACTIONDESC   --删除原因
     , CONCAT('110000013000aaaaaaD01aa',
              SUBSTRING('{DATA_DT}',1,6),
              '3',
              LPAD(ROW_NUMBER() OVER(PARTITION BY 1 ORDER BY dvlp.wallet_aval_bal),6,'0')
              )                                                    AS SNOCODE   --数据自编码
     , '110000013000'                                                AS OBJCODE   --申报主体代码
     , CAST(SUBSTRING('{DATA_DT}',1,6) AS VARCHAR(6))                AS BUOCMONTH   --报告期
     , '0'                                                           AS D0101   --业务类别
     , 'HKG'                                                         AS D0102   --对方国家/地区
     , '2'                                                           AS D0103   --对方部门
     , '4'                                                           AS D0104   --对方与本机构的关系
     , '1'                                                           AS D0105   --原始期限
     , 'HKD'                                                         AS D0106   --原始币种
     , NVL(ld01.d0109,0.00)                                          AS D0107   --上月末本金金额
     , 0.00                                                          AS D0108   --上月末应收利息金额
     , dvlp.wallet_aval_bal                                          AS D0109   --本月末本金金额
     , dvlp.wallet_aval_bal                                          AS D0110   --本月末本金金额：其中剩余期限在一年及以下
     , 0.00                                                          AS D0111   --本月末应收利息余额
     , 0.00                                                          AS D0112   --本月非交易变动
     , (dvlp.wallet_aval_bal+0.00)-(NVL(ld01.d0109,0.00)+0.00)-0.00  AS D0113   --本月净发生额 =（本月末本金余额+本月末应收利息余额）-（上月末本金余额+上月末应收利息余额）-本月非交易变动
     , 0.00                                                          AS D0114   --本月利息收入
     , ''                                                            AS REMARK   --备注
     , 'SZRMBB'                                                      AS DATA_SOURCE   --数据来源
     , '11005293'                                                    AS BANK_ID   --机构代码号
     , '20190510900'                                                 AS OWNUSR   --柜员号
     , '于鑫芳'                                                         AS FALPERS   --报送人
     , '数字人民币部'                                                      AS FALDEPT   --报送部门
     , 2                                                             AS d0115 --是否存在风险转移
     , NULL                                                          AS d0116 --风险转往国家/地区
     , NULL                                                          AS d0117 --风险转往部门
FROM rbdb.dcs_pcomm001db_mbridge_wlt_bal_dayend_reg dvlp --数字人民币部_货币桥钱包余额日终记录表
    LEFT JOIN RA03.T_GJDG_JRZF_D01_TMP_CWKJB ld01
        ON ld01.data_dt=date_format(
                                   date_add(
                                            concat(SUBSTR('{DATA_DT}',1,4),'-',SUBSTR('{DATA_DT}',5,2),'-','01'),
                                            -1
                                           )
                                   ,'yyyyMMdd'
                                  )  --获取上月末统计结果
        AND ld01.D0106 = dvlp.acc_bal_curr_cd
        AND ld01.data_source='SZRMBB'  --数据源为数字人民币部
    WHERE dvlp.start_dt<='{DATA_DT}' --获取月末日期
        AND dvlp.end_dt>'{DATA_DT}' --获取月末日期
        AND dvlp.tx_date = date_format(
                                 date_add(
                                          concat(SUBSTR('{DATA_DT}',1,4),'-',SUBSTR('{DATA_DT}',5,2),'-',SUBSTR('{DATA_DT}',7,2)),
                                          1
                                         )
                                 ,'yyyyMMdd'
                                )
        AND dvlp.acc_bal_curr_cd='HKD'
;

DROP TABLE IF EXISTS ra03.t_gjdg_jrzf_d01_tmp01
;

CREATE TABLE IF NOT EXISTS ra03.t_gjdg_jrzf_d01_tmp01 AS
SELECT ACTIONTYPE                                                                      AS ACTIONTYPE                --操作类型
      ,ACTIONDESC                                                                      AS ACTIONDESC                --删除原因
      ,CONCAT('110000013000aaaaaaD01aa',
              SUBSTRING('{DATA_DT}',1,6),
              '2',
              LPAD(ROW_NUMBER() OVER(PARTITION BY 1 ORDER BY D0106),6,'0')
              )                                                                        AS SNOCODE                    --数据自编码
      ,OBJCODE                                                                         AS OBJCODE                    --申报主体代码
      ,BUOCMONTH                                                                       AS BUOCMONTH                  --报告期
      ,D0101                                                                           AS D0101                      --业务类别
      ,D0102                                                                           AS D0102                      --对方国家/地区
      ,D0103                                                                           AS D0103                      --对方部门
      ,D0104                                                                           AS D0104                      --对方与本机构的关系
      ,D0105                                                                           AS D0105                      --原始期限
      ,D0106                                                                           AS D0106                      --原始币种
      ,SUM(D0107)                                                                      AS D0107                      --上月末本金金额
      ,SUM(D0108)                                                                      AS D0108                      --上月末应收利息金额
      ,SUM(D0109)                                                                      AS D0109                      --本月末本金金额
      ,SUM(D0110)                                                                      AS D0110                      --本月末本金金额：其中剩余期限在一年及以下
      ,SUM(D0111)                                                                      AS D0111                      --本月末应收利息余额
      ,SUM(D0112)                                                                      AS D0112                      --本月非交易变动
      ,SUM(D0113)                                                                      AS D0113                      --本月净发生额 =（本月末本金余额+本月末应收利息余额）-（上月末本金余额+上月末应收利息余额）-本月非交易变动
      ,SUM(D0114)                                                                      AS D0114                      --本月利息收入
      ,REMARK                                                                          AS REMARK                     --备注
      ,'CWKJB'                                                                         AS DATA_SOURCE                --数据来源
      ,BANK_ID                                                                         AS BANK_ID                    --机构代码号
      ,'20070709380/20190510900'                                                       AS OWNUSR                      --柜员号
      ,'郝坤/于鑫芳'                                                                   AS FALPERS                    --报送人
      ,'财务会计部/数字人民币部'                                                       AS FALDEPT                    --报送部门
      ,d0115                                                                           AS d0115                      --是否存在风险转移
      ,d0116                                                                           AS d0116                      --风险转往国家/地区
      ,d0117                                                                           AS d0117                      --风险转往部门
FROM RA03.T_GJDG_JRZF_D01_TMP_CWKJB
WHERE data_dt='{DATA_DT}'
GROUP BY  ACTIONTYPE
         ,ACTIONDESC
         ,OBJCODE
         ,BUOCMONTH
         ,D0101
         ,D0102
         ,D0103
         ,D0104
         ,D0105
         ,D0106
         ,REMARK
         ,BANK_ID
         ,d0115
         ,d0116
         ,d0117
;

--向最终报送表插入财务会计部和数字人民币部合并数据
ALTER TABLE RA03.T_GJDG_JRZF_D01_PARALLEL DROP IF EXISTS PARTITION (month='{DATA_DT_1DAY}' ,data_source='CWKJB' )
;

INSERT INTO RA03.T_GJDG_JRZF_D01_PARALLEL PARTITION ( month='{DATA_DT_1DAY}' ,data_source='CWKJB', DATA_DT='{DATA_DT}' )
SELECT a.ACTIONTYPE                                                           AS ACTIONTYPE   --删除原因
     , a.ACTIONDESC                                                           AS ACTIONDESC   --操作类型
     , a.SNOCODE                                                              AS SNOCODE   --数据自编码
     , a.OBJCODE                                                              AS OBJCODE   --申报主体代码
     , a.BUOCMONTH                                                            AS BUOCMONTH   --报告期
     , a.D0101                                                                AS D0101   --业务类别
     , a.D0102                                                                AS D0102   --对方国家/地区
     , a.D0103                                                                AS D0103   --对方部门
     , a.D0104                                                                AS D0104   --对方与本机构的关系
     , a.D0105                                                                AS D0105   --原始期限
     , a.D0106                                                                AS D0106   --原始币种
     , NVL(ld01.D0109,0.00)                                                   AS D0107   --上月末本金金额
     , NVL(ld01.D0111,0.00)                                                   AS D0108   --上月末应收利息金额
     , a.D0109                                                                AS D0109   --本月末本金金额
     , a.D0110                                                                AS D0110   --本月末本金金额：其中剩余期限在一年及以下
     , a.D0111                                                                AS D0111   --本月末应收利息余额
     , a.D0112                                                                AS D0112   --本月非交易变动
     , (a.D0109+a.D0111)-(NVL(ld01.D0109,0.00)+NVL(ld01.D0111,0.00))-a.D0112  AS D0113   --本月净发生额 =（本月末本金余额+本月末应收利息余额）-（上月末本金余额+上月末应收利息余额）-本月非交易变动
     , a.D0114                                                                AS D0114   --本月利息收入
     , a.REMARK                                                               AS REMARK   --备注
     , a.BANK_ID                                                              AS BANK_ID   --机构代码号
     , a.OWNUSR                                                               AS OWNUSR   --柜员号
     , a.FALPERS                                                              AS FALPERS   --报送人
     , a.FALDEPT                                                              AS FALDEPT   --报送部门
     , a.d0115                                                                AS d0115   --是否存在风险转移
     , a.d0116                                                                AS d0116   --风险转往国家/地区
     , a.d0117                                                                AS d0117   --风险转往部门
FROM RA03.t_gjdg_jrzf_d01_tmp01 a
    LEFT JOIN pg_work.wgj_falda_hbyck ld01
        ON ld01.buocmonth=SUBSTRING(date_format(
                                             date_add(
                                                      concat(SUBSTR('{DATA_DT}',1,4),'-',SUBSTR('{DATA_DT}',5,2),'-','01'),
                                                      -1
                                                     )
                                             ,'yyyyMMdd'
                                            )
                                 ,1
                                 ,6
                                )  --获取上月末统计结果
        AND ld01.D0106 = a.D0106  --根据币种关联
        AND ld01.FALDEPT='财务会计部/数字人民币部'  --部门为财务会计部和数字人民币部
        AND ld01.sfysb='Y'
        AND ld01.sxbz='1'
        AND ld01.sfzx='Y'
;