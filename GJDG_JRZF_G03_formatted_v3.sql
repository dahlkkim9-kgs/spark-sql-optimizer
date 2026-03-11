--# -*- coding: utf-8 -*-
--
--#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#
--#脚本名称  : GJDG_JRZF_G03.py
--#加载策略  ：（1.单日增量  2.全量 3.区间全量  4多日增量 ）
--#源表类型  ：（1.历史拉链  2.区间流水）
--#源  表    : ra03.tmp_sm_{DATA_DT}B01_feijumin_tx_xinhexin_last
--#           1  ngc_ngcc_card                                        卡片资料表
--#           2  ngc_ngcc_transaction_detail  已入账交易流水表
--#           1  ngc_ngcc_custr                                       客户基本资料
--#           1  ngc_ngcc_trantype_father     交易类型分类参数表
--#           1  ice_ngc_ngcc_inst_order             分期订单表
--#           1  ncf_ppers001db_sp01_cust_info       客户信息平台客户基本信息表
--#            
--#            
--#            
--#            
--#功能描述  非居民持有境内银行卡的收入支出   
--#开发人员/复核人员  ：zhangjiaqi/qiuyelong
--#创建日期  ：2023/07/12
--#修改历史及标识  ：--/*modify by xxx 日期*/
--#{
--#1： qiuyelong在2024年02月28日， 修改内容为:1.增加新版外国人永久居留身份证获取逻辑；
--#                                        2.添加无人地区过滤；   
--#                                        3.增加报表逻辑修改，交易类型字段为10-境外支出或13-境外收入且银行卡清算渠道字段为7-本行清算的交易，
--#                                          若存在此类数据则统一将银行卡清算渠道字段改为8-其他    --/*modify by qyl 20240228*/
--#                                        4.维护mcc码3998，新增非居民国籍过滤不报送，新增摘要兜底，新增万事达清算渠道判断逻辑.--/*modify by qyl 20240522*/
--#2： qiuyelong在2024年07月24日， 修改内容为:1.新增兜底内容;

--#                                        2.备份汇总借记卡部分金额数据
--#                                        3.删除70-外国人永久居留证，不再报送该类证件的客户
--#3： qiuyelong在2024年08月21日， 修改内容为:1.修改60、63、61、64证件类型国籍获取逻辑;

--#                                        2.兜底摘要新增账户兑换-结售汇(不报送)。
--#4： qiuyelong在2024年09月29日， 修改内容为:1.更新信用卡逻辑;

--#                                        2.兜底摘要新增热力费-6、便民服务-6、卷烟进货-1、代收社保-6、保费代收-6、国库缴税-6、欠费补扣-9、
--#                                                      汽车分期-1、社保税银-6、通存通兑-9。--/*modify by qyl 20241008*/
--#5： qiuyelong在2024年10月15日， 修改内容为:1.更新信用卡逻辑为信用卡新核心相关表和字段;

--#6： qiuyelong在2024年12月11日， 修改内容为:1.兜底摘要新增,汽车租金-6、ACS充值-9、大病保险-6。--/*modify by qyl 20241211*/
--#7.  Modify by qiuyelong 20250310, 变更缓冲层表名rbdb.ngc_ngcc_custr 为 rbdb.ice_ngc_ngcc_custr --/*modify by qiuyelong 20250310*/
--#8.  Modify by qiuyelong 20250331, 变更缓冲层表名rbdb.ngc_ngcc_card 为 rbdb.ice_ngc_ngcc_card --/*modify by qiuyelong 20250331*/
--#9.  Modify by qiuyelong 20250611, 变更缓冲层表名rbdb.ngc_ngcc_inst_order 为 rbdb.ice_ngc_ngcc_inst_order --/*modify by qiuyelong 20250611*/
--#10. Modify by qiuyelong 20250625, 新增摘要兜底：购房验资-9 缴存退回-9 主动积存-6 基本医疗-6 养老保险-6 --/*modify by qiuyelong 20250625*/
--#11. Modify by qiuyelong 20250827, 外管局1.4规范改造，新增mcc码值表ra03.t_code_g03_mcc_14add作为辅助赋值 --/*modify by qiuyelong 20250827*/
--#12. Modify by qiuyelong 20250924, 客户信息平台改造后用新的证件类型判断持卡人国家地区代码 --/*modify by qiuyelong 20250924*/
--#13. Modify by qiuyelong 20251022, 新增摘要兜底：保管箱-6 还信用卡-9 --/*modify by qiuyelong 20251022*/
--#14. Modify by qiuyelong 20251105, 币种码表t_xykzx_curr更新为T_CS_6100_2017_0642_CURR,币种码表T_CS_6100_2017_0642_CURR添加三个码值 930-STD 924-ZWD 925-SLL --/*modify by qiuyelong 20251105*/
--#15. Modify by qiuyelong 20251119, 配套信用卡新核心客户信息表中三位字母转换为二位字母改造，通过客户号关联客户信息平台中客户基本信息表获取二位国家地区代码，在通过国家地区码表转换出三位字母国家地区代码 --/*modify by qiuyelong 20251119*/
--# 
--#}
--#备注  ：    
--#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#*#
--
--# 调优参数（调优人员填写）
--spark_set = {}
--# 调优参数（调优人员填写）
--
--# sql语句x
--Sql = [
--[
--'sql',
--'''
--创建结果表
CREATE TABLE IF NOT EXISTS RA03.T_GJDG_JRZF_G03(
ACTIONTYPE    VARCHAR(1)      COMMENT'操作类型'
,ACTIONDESC   VARCHAR(128)    COMMENT'删除原因'
,SNOCODE      VARCHAR(36)     COMMENT'数据自编码'
,OBJCODE      VARCHAR(18)     COMMENT'申报主体代码'
,BUOCMONTH    decimal(6,0)    COMMENT'报告期'
,G0301        INT             COMMENT'银行卡清算渠道'
,G0302        VARCHAR(3)      COMMENT'持卡人所属国家/地区'
,G0303        VARCHAR(3)      COMMENT'交易原币'
,G0304        INT             COMMENT'收支类型'
,G0305        INT             COMMENT'交易类型'
,G0306        decimal(22,2)   COMMENT'交易金额'
,REMARK       VARCHAR(512)    COMMENT'备注'
,data_source  VARCHAR(18)     COMMENT'数据来源'
,bank_id      VARCHAR(18)     COMMENT'机构号'
,ownusr       STRING          COMMENT'柜员号'
,falpers      STRING          COMMENT'报送人'
,faldept      STRING          COMMENT'报送部门'
 ) COMMENT 'G03非居民持有境内银行卡的收入支出'
PARTITIONED BY (DATA_DT STRING)
;

--初步加工
DROP TABLE IF EXISTS RA03.CTB_CREDIT_G03_temp_{DATA_DT}
;

CREATE TABLE IF NOT EXISTS RA03.CTB_CREDIT_G03_temp_{DATA_DT} AS
SELECT 'A'                                                                                                                    AS ACTIONTYPE
     , ''                                                                                                                     AS ACTIONDESC
     , CONCAT('110000013000aaaaaa', 'G03aa', SUBSTR('{DATA_DT}', 1, 6), LPAD(ROW_NUMBER() OVER(PARTITION BY 1 ORDER BY 1), 7, 0)) AS SNOCODE   --数据自编码
     , '110000013000'                                                                                                         AS OBJCODE   --申报主体代码
     , SUBSTR('{DATA_DT}', 1, 6)                                                                                              AS BUOCMONTH   --报告期
     , CASE
           WHEN a.chnl_kind_code='22'
           THEN '1'
           WHEN a.start_sys_or_cmpt_no='99600010000'
           THEN '1'  --      WHEN a.start_sys_or_cmpt_no='99100140000' THEN '8'            --三方支付给8,20230607去掉
           WHEN (a.chnl_kind_code='42' AND a.start_sys_or_cmpt_no='99350000000')
                   OR a.chnl_kind_code='58'
           THEN '3'  --20240506  添加万事达逻辑
           WHEN a.ibank_flag='0'
           THEN '7'                                   --是否跨行标志为0的代表行内
           ELSE '8'
       END AS G0301  --银行卡清算渠道
     , CASE
           WHEN a.cert_type IN ('1070','1181')
           THEN
(CASE WHEN a.cert_no LIKE 'H%'  THEN 'HKG'  --若证件类型是港澳居民往来内地通行证，证件号码是H开头，国籍赋值为HKG   --/*modify by qiuyelong 20250924*/
                                                            WHEN a.cert_no LIKE 'M%'  THEN 'MAC'  --若证件类型是港澳居民往来内地通行证，证件号码是M开头，国籍赋值为MAC
                                                            WHEN a.cert_no LIKE '81%' THEN 'HKG'  --若证件类型是港澳居民居住证，证件号码是81开头，国籍赋值为HKG
                                                            WHEN a.cert_no LIKE '82%' THEN 'MAC'  --若证件类型是港澳居民居住证，证件号码是82开头，国籍赋值为MAC
                                                            WHEN a.cert_no LIKE 'h%'  THEN 'HKG'  --若证件类型是港澳居民往来内地通行证，证件号码是H开头，国籍赋值为HKG
                                                            WHEN a.cert_no LIKE 'm%'  THEN 'MAC'  --若证件类型是港澳居民往来内地通行证，证件号码是M开头，国籍赋值为MAC
                                                            WHEN a.cert_no LIKE '83%' THEN 'TWN'  --若证件类型是台湾居民居住证，国籍赋值为TWN
                                                            ELSE 'ZZZ'
                                                       END
                                                      ) --20240729修改
           WHEN a.cert_type IN ('1080','1182')
           THEN
(CASE WHEN a.cert_no LIKE 'H%'  THEN 'HKG'  --若证件类型是港澳居民往来内地通行证，证件号码是H开头，国籍赋值为HKG
                                                   WHEN a.cert_no LIKE 'M%'  THEN 'MAC'  --若证件类型是港澳居民往来内地通行证，证件号码是M开头，国籍赋值为MAC
                                                   WHEN a.cert_no LIKE '81%' THEN 'HKG'  --若证件类型是港澳居民居住证，证件号码是81开头，国籍赋值为HKG
                                                   WHEN a.cert_no LIKE '82%' THEN 'MAC'  --若证件类型是港澳居民居住证，证件号码是82开头，国籍赋值为MAC
                                                   WHEN a.cert_no LIKE 'h%'  THEN 'HKG'  --若证件类型是港澳居民往来内地通行证，证件号码是H开头，国籍赋值为HKG
                                                   WHEN a.cert_no LIKE 'm%'  THEN 'MAC'  --若证件类型是港澳居民往来内地通行证，证件号码是M开头，国籍赋值为MAC
                                                   WHEN a.cert_no LIKE '83%' THEN 'TWN'  --若证件类型是台湾居民居住证，国籍赋值为TWN
                                                   ELSE 'TWN'
                                              END
                                             ) --20240729修改
           WHEN a.cert_type='1051'
                   AND b.cd_value1='CHN'
           THEN 'ZZZ'  --若证件类型是外国护照，国籍属于CN的，赋值ZZZ
           ELSE
(CASE WHEN NVL(b.cd_value1,'') ='' THEN 'ZZZ' ELSE  b.cd_value1   END)     --当国籍是空的时候转其他
       END AS G0302  --持卡人所属国家/地区
     , a.curr_suoxie                                                                                                          AS G0303   --交易原币
     , a.dw_flag_code                                                                                                         AS G0304   --收支类型
     , CASE
           WHEN a.summ_name LIKE '%活转定%'
           THEN '活转定'                               --20230508确认放下面加工，20230607又重新确认最开始刷成汉字（为了把dw_flag_code为1的也刷成汉字）
           WHEN a.summ_name LIKE '%定转活%'
           THEN
--20230508确认放下面加工，20230607又重新确认最开始刷成汉字（为了把dw_flag_code为1的也刷成汉字）
           CASE WHEN a.txamt_tp_cd ='0002' THEN '12'                                 --20240724增加逻辑
                ELSE '定转活'
           END
           WHEN a.summ_name LIKE '%部提存入%'
                   AND a.txamt_tp_cd ='0001'
           THEN '定转活'     --20240724增加逻辑
           WHEN a.summ_name LIKE '%账户结汇%'
           THEN '账户结汇'                             --20230508确认放下面加工，20230607又重新确认最开始刷成汉字（为了把dw_flag_code为1的也刷成汉字）
           WHEN a.summ_name LIKE '%售汇%'
           THEN '售汇'                                --20230508确认放下面加工，20230607又重新确认最开始刷成汉字（为了把dw_flag_code为1的也刷成汉字）
           WHEN a.summ_name LIKE '%外币兑回%'
           THEN '外币兑回'                             --20230508确认放下面加工，20230607又重新确认最开始刷成汉字（为了把dw_flag_code为1的也刷成汉字）
           WHEN a.summ_name LIKE '%钞汇互转%'
           THEN '钞汇互转'                             --20230508确认放下面加工，20230607又重新确认最开始刷成汉字（为了把dw_flag_code为1的也刷成汉字）
           WHEN a.summ_name LIKE '%卡内互转%'
           THEN '卡内互转'                             --20230607又重新确认最开始刷成汉字（为了把dw_flag_code为1的也刷成汉字）
           WHEN a.summ_name LIKE '%账户兑换%'
           THEN '结售汇'                               --20240729增加逻辑
           WHEN a.dw_flag_code='1'
           THEN (
               CASE
                   WHEN a.summ_name LIKE '%工资%'
                   THEN '11'
                   WHEN a.tx_remark LIKE '%工资%'
                   THEN '11'
                   WHEN a.tx_remark LIKE '%薪%'
                   THEN '11'
                   WHEN a.tx_remark LIKE '%奖金%'
                   THEN '11'
                   WHEN a.tx_remark LIKE '%劳务%'
                   THEN '11'
                   WHEN dmst_ovsea_flag_code='1'
                   THEN '13'
                   ELSE '12'
               END
               )
           WHEN a.dw_flag_code='2'
                   AND a.summ_name LIKE '%卡现金取%'
           THEN '7'    --取现
           WHEN a.dw_flag_code='2'
                   AND a.summ_name LIKE '%折现金取%'
           THEN '7'    --取现
           WHEN a.dw_flag_code='2'
                   AND a.summ_name LIKE '%现金销户%'
           THEN '7'    --取现
           WHEN a.dw_flag_code='2'
                   AND a.summ_name LIKE '%ATM取款%'
           THEN '7'    --取现
           WHEN a.dw_flag_code='2'
                   AND a.summ_name LIKE '%ATM跨取%'
           THEN '7'    --取现
           WHEN a.dw_flag_code='2'
                   AND a.summ_name LIKE '%跨境取款%'
           THEN '7'    --取现
           WHEN a.dw_flag_code='2'
                   AND a.summ_name LIKE '%卡转取%'
           THEN '7'    --取现
           WHEN a.dw_flag_code='2'
                   AND a.summ_name LIKE '%跨行取款%'
           THEN '7'    --取现
           WHEN a.dw_flag_code='2'
                   AND a.summ_name LIKE '%折转取%'
           THEN '7'    --取现
           WHEN a.dw_flag_code='2'
                   AND a.summ_name LIKE '%助农取款%'
           THEN '7'    --取现
           WHEN a.dw_flag_code='2'
                   AND a.summ_name LIKE '%费用%'
                   AND a.start_sys_or_cmpt_no='1043199'
           THEN '6'    --其他支出
           WHEN a.dw_flag_code='2'
                   AND a.mer_desc  LIKE '%医院%'
           THEN '8'        --8-医疗保健
           WHEN a.dw_flag_code='2'
                   AND a.mer_desc  LIKE '%药店%'
           THEN '8'        --8-医疗保健
           WHEN a.dw_flag_code='2'
                   AND a.mer_desc  LIKE '%药房%'
           THEN '8'        --8-医疗保健
           WHEN a.dw_flag_code='2'
                   AND a.mer_desc  LIKE '%交通%'
           THEN '4'        --4-当地交通
           WHEN a.dw_flag_code='2'
                   AND a.mer_desc  LIKE '%铁路%'
           THEN '4'        --4-当地交通
           WHEN a.dw_flag_code='2'
                   AND a.mer_desc  LIKE '%航空%'
           THEN '4'        --4-当地交通
           WHEN a.dw_flag_code='2'
                   AND a.tx_remark LIKE '%高速%'
           THEN '4'        --4-当地交通
           WHEN a.dw_flag_code='2'
                   AND a.tx_remark LIKE '%交通%'
           THEN '4'        --4-当地交通  20240724增加
           WHEN a.dw_flag_code='2'
                   AND a.tx_remark LIKE '%铁路%'
           THEN '4'        --4-当地交通  20240724增加
           WHEN a.dw_flag_code='2'
                   AND a.tx_remark LIKE '%航空%'
           THEN '4'        --4-当地交通  20240724增加
           WHEN a.dw_flag_code='2'
                   AND a.summ_name LIKE '%ETC%'
           THEN '4'        --4-当地交通  20230407新加
           WHEN a.dw_flag_code='2'
                   AND a.tx_remark LIKE '%ETC%'
           THEN '4'        --4-当地交通  20230607新加
           WHEN ((a.chnl_kind_code='42' AND a.start_sys_or_cmpt_no='99350000000') OR a.chnl_kind_code='58')
                   AND a.mer_type_no = '3998'
           THEN '2'  --20240506  添加3998时万事达逻辑
           WHEN NVL(c.jylx,'') <> ''
           THEN c.jylx  --用新码表进行赋值赋值/*modify by qiuyelong 20250827*/
           ELSE CAST(NVL(mccadd.req,'') AS STRING)
       END AS g0305  --交易类型
     , a.tx_amt                                                                                                               AS G0306   --交易金额
     , a.tx_remark                                                                                                            AS REMARK   --备注
     , 'XHX'                                                                                                                  AS data_source
     , '11005293'                                                                                                             AS bank_id
     , a.pers_inner_accno
     , a.summ_name
     , a.cert_type
     , a.global_busi_track_no
     , a.subtx_no
     , A.mer_type_no
     , a.mer_desc
     , a.medium_no
     , a.cert_no
     , a.ibank_flag
     , a.dmst_ovsea_flag_code
FROM ra03.tmp_sm_{DATA_DT}B01_feijumin_tx_xinhexin_last a
    LEFT JOIN ra03.wgj_send_country b  --外管局码表
        ON a.country_code=b.std_cd_value
    LEFT JOIN ra03.G03_jylx_code c  --交易类型码表
        ON a.mer_type_no =c.mcc
    LEFT JOIN ra03.t_code_g03_mcc_14add mccadd  --新增码表/*modify by qiuyelong 20250827*/
        ON a.mer_type_no = mccadd.mer_cat_cd
    LEFT JOIN ra03.wgj_send_country ct  --外管局码表,将新版外国人永久居留证中3位数字国家地区编码转换为3位字母 /*modify by qyl 20240124*/
        ON ct.std_cd_value = SUBSTR(a.cert_no,4,3)
;

--处理交易类型不覆盖
DROP TABLE IF EXISTS RA03.CTB_CREDIT_G03_temp_dont_overwrite_{DATA_DT}
;

CREATE TABLE IF NOT EXISTS  RA03.CTB_CREDIT_G03_temp_dont_overwrite_{DATA_DT} AS
SELECT a.actiontype
     , a.actiondesc
     , a.snocode
     , a.objcode
     , a.buocmonth
     , a.g0301
     , a.g0302
     , a.g0303
     , a.g0304
     , CASE
           WHEN NVL(G0305,'')=''
                   AND a.G0304='2'
           THEN (
               CASE
                   WHEN a.summ_name LIKE '%短信扣费%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%快捷支付%'
                   THEN '1'
                   WHEN a.summ_name LIKE '%跨行汇出%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%转账汇出%'
                   THEN '9'
                                                           --WHEN  a.summ_name LIKE '%ETC通行%'  THEN '4'
                   WHEN a.summ_name LIKE '%批量扣款%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%集中代收%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%公共事业%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%延迟转账%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%定投扣款%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%电费%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%跨行退款%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%通讯费%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%人行代收%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%理财购买%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%社保医保%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%银转证%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%强制销户%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%营业款%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%商业保险%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%水费%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%贷款还款%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%费用%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%消费金融%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%预授完成%'
                   THEN '1'
                   WHEN a.summ_name LIKE '%物业费%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%基金申购%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%网关支付%'
                   THEN '1'
                   WHEN a.summ_name LIKE '%邮益宝申%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%银联代收%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%银联快捷%'
                   THEN '1'
                   WHEN a.summ_name LIKE '%基金认购%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%商户扣账%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%行内收款%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%网银代发%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%账户发汇%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%支取数币%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%餐费%'
                   THEN '3'
                   WHEN a.summ_name LIKE '%资管购买%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%计划积存%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%消费%'
                   THEN '1'
                   WHEN a.summ_name LIKE '%自扣还款%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%烟草款%'
                   THEN '1'
                   WHEN a.summ_name LIKE '%扣款%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%归集汇出%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%教育%'
                   THEN '5'
                   WHEN a.summ_name LIKE '%燃气费%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%销户转存%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%有线电视%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%扣划转出%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%餐杂费%'
                   THEN '3'
                   WHEN a.summ_name LIKE '%公积金%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%国库收款%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%校园卡%'
                   THEN '5'
                   WHEN a.summ_name LIKE '%预约转账%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%调整%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%圈存充值%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%同城支付%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%学费%'
                   THEN '5'
                   WHEN a.summ_name LIKE '%房租%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%批量销户%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%圈提转出%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%私转公%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%投资理财%'
                   THEN '6'
                   WHEN a.summ_name LIKE '%医疗费%'
                   THEN '8'
                   WHEN a.summ_name LIKE '%转账销户%'
                   THEN '9'
                   WHEN a.summ_name LIKE '%批量代收%'
                   THEN '6'       --20230407新加
                   WHEN a.summ_name LIKE '%代收费%'
                   THEN '6'       --20230407新加
                   WHEN a.summ_name LIKE '%购实物金%'
                   THEN '6'       --20230407新加
                   WHEN a.summ_name LIKE '%水电费%'
                   THEN '6'       --20230407新加
                   WHEN a.summ_name LIKE '%凭债购买%'
                   THEN '6'       --20230407新加
                   WHEN a.summ_name LIKE '%受托支付%'
                   THEN '6'       --20230407新加
                   WHEN a.summ_name LIKE '%医保款%'
                   THEN '6'       --20230407新加
-- WHEN  a.summ_name LIKE '%公益款%'   THEN '6'
                   WHEN a.summ_name LIKE '%冲正%'
                   THEN '9'
                                                          -- WHEN  a.summ_name LIKE '%取消%'     THEN '9'
-- WHEN  a.summ_name LIKE '%ETC%'      THEN '4'      --20230407新加
                   WHEN a.summ_name LIKE '%储债认购%'
                   THEN '6'             --20230506新加
                   WHEN a.summ_name LIKE '%银转两融%'
                   THEN '6'             --20230506新加
                   WHEN a.summ_name LIKE '%组织收款%'
                   THEN '6'             --20230506新加
                   WHEN a.summ_name LIKE '%卡内互转%'
                   THEN '卡内互转'      --20230506新加
                   WHEN a.summ_name LIKE '%定转活%'
                   THEN '定活互转'      --20230506新加
                   WHEN a.summ_name LIKE '%活转定%'
                   THEN '定活互转'      --20230506新加
                   WHEN a.summ_name LIKE '%账户结汇%'
                   THEN '结售汇'        --20230506新加
                   WHEN a.summ_name LIKE '%售汇%'
                   THEN '结售汇'        --20230506新加
                   WHEN a.summ_name LIKE '%凭债扣费%'
                   THEN '6'           --20230607新加
                   WHEN a.summ_name LIKE '%移出%'
                   THEN '9'           --20230607新加
                   WHEN a.summ_name LIKE '%公益款%'
                   THEN '6'           --20230607新加
                   WHEN a.summ_name LIKE '%跨行代收%'
                   THEN '6'           --20230705新加
                   WHEN a.summ_name LIKE '%密码汇出%'
                   THEN '9'           --20230705新加
                   WHEN a.summ_name LIKE '%受让存单%'
                   THEN '9'           --20231115新加
                   WHEN a.summ_name LIKE '%按址汇出%'
                   THEN '9'           --20231115新加
                   WHEN a.summ_name LIKE '%房屋资金%'
                   THEN '9'           --20231115新加
                   WHEN a.summ_name LIKE '%培训费%'
                   THEN '6'           --20231115新加
                   WHEN a.summ_name LIKE '%保证金%'
                   THEN '6'           --20240522新加
                   WHEN a.summ_name LIKE '%工会费%'
                   THEN '6'           --20240522新加
                   WHEN a.summ_name LIKE '%服务费%'
                   THEN '6'           --20240522新加
                   WHEN a.summ_name LIKE '%捐款%'
                   THEN '9'           --20240522新加
                   WHEN a.summ_name LIKE '%财政收款%'
                   THEN '6'           --20240522新加
                   WHEN a.summ_name LIKE '%融资租赁%'
                   THEN '6'           --20240522新加
                   WHEN a.summ_name LIKE '%万联代收%'
                   THEN '6'           --20240522新加
                   WHEN a.summ_name LIKE '%公交卡%'
                   THEN '4'           --20240724新加
                   WHEN a.summ_name LIKE '%汇兑汇出%'
                   THEN '9'           --20240724新加
                   WHEN a.summ_name LIKE '%热力费%'
                   THEN '6'           --20240929新加
                   WHEN a.summ_name LIKE '%便民服务%'
                   THEN '6'           --20241008新加
                   WHEN a.summ_name LIKE '%卷烟进货%'
                   THEN '1'           --20241008新加
                   WHEN a.summ_name LIKE '%代收社保%'
                   THEN '6'           --20241008新加
                   WHEN a.summ_name LIKE '%保费代收%'
                   THEN '6'           --20241008新加
                   WHEN a.summ_name LIKE '%国库缴税%'
                   THEN '6'           --20241008新加
                   WHEN a.summ_name LIKE '%欠费补扣%'
                   THEN '9'           --20241008新加
                   WHEN a.summ_name LIKE '%汽车分期%'
                   THEN '1'           --20241008新加
                   WHEN a.summ_name LIKE '%社保税银%'
                   THEN '6'           --20241008新加
                   WHEN a.summ_name LIKE '%通存通兑%'
                   THEN '9'           --20241008新加
                   WHEN a.summ_name LIKE '%汽车租金%'
                   THEN '6'           --20241211新加
                   WHEN a.summ_name LIKE '%ACS充值%'
                   THEN '9'           --20241211新加
                   WHEN a.summ_name LIKE '%大病保险%'
                   THEN '6'           --20241211新加
                   WHEN a.summ_name LIKE '%购房验资%'
                   THEN '9'           --20250625新加 
                   WHEN a.summ_name LIKE '%缴存退回%'
                   THEN '9'           --20250625新加 
                   WHEN a.summ_name LIKE '%主动积存%'
                   THEN '6'           --20250625新加 
                   WHEN a.summ_name LIKE '%基本医疗%'
                   THEN '6'           --20250625新加 
                   WHEN a.summ_name LIKE '%养老保险%'
                   THEN '6'           --20250625新加 
                   WHEN a.summ_name LIKE '%保管箱%'
                   THEN '6'           --新加/*modify by qiuyelong 20251022*/
                   WHEN a.summ_name LIKE '%还信用卡%'
                   THEN '9'           --新加/*modify by qiuyelong 20251022*/
               END
               )
           ELSE A.G0305
       END AS g0305
     , a.g0306
     , a.remark
     , a.data_source
     , a.bank_id
     , a.pers_inner_accno
     , a.summ_name
     , a.cert_type
     , a.global_busi_track_no
     , a.subtx_no
     , A.mer_type_no
     , a.medium_no
     , a.cert_no
     , a.ibank_flag
     , a.dmst_ovsea_flag_code
FROM RA03.CTB_CREDIT_G03_temp_{DATA_DT} a
;

--处理外国人永久居留证及转换金额为负的收支类型及交易类型
DROP TABLE IF EXISTS RA03.CTB_CREDIT_G03_temp_type_{DATA_DT}
;

CREATE TABLE IF NOT EXISTS RA03.CTB_CREDIT_G03_temp_type_{DATA_DT} AS
SELECT actiontype
     , actiondesc
     , snocode
     , objcode
     , buocmonth
     , g0301
     , CASE
           WHEN NVL(b.cd_value1,'')=''
           THEN 'ZZZ'  --    WHEN SUBSTR(G0302,1,3) rlike '[\0-9]' THEN 'ZZZ'
           ELSE G0302
       END AS g0302
     , g0303
     , CASE
           WHEN G0306<0
                   AND g0304='1'
           THEN '2'
           WHEN G0306<0
                   AND g0304='2'
           THEN '1'
           ELSE g0304
       END
     , CASE
           WHEN G0306<0
                   AND g0304='1'
           THEN '9'
           WHEN G0306<0
                   AND g0304='2'
           THEN '12'
           ELSE g0305
       END
     , CASE
           WHEN G0306<0
           THEN -g0306
           ELSE g0306
       END
     , remark
     , data_source
     , bank_id
     , a.pers_inner_accno
     , a.summ_name
     , a.cert_type
     , a.global_busi_track_no
     , a.subtx_no
     , A.mer_type_no
     , a.medium_no
     , a.cert_no
     , a.ibank_flag
     , a.dmst_ovsea_flag_code
FROM RA03.CTB_CREDIT_G03_temp_dont_overwrite_{DATA_DT} a
    LEFT JOIN
        (
            SELECT DISTINCT cd_value1
            FROM ra03.wgj_send_country b
        ) b  --外管局码表
        ON a.G0302=b.cd_value1
;

--20230628提出，20230703新加（对于支出，并且境外标志是1，支出类别赋值为10）
DROP TABLE IF EXISTS RA03.CTB_CREDIT_G03_temp_type_new_{DATA_DT}
;

CREATE TABLE IF NOT EXISTS RA03.CTB_CREDIT_G03_temp_type_new_{DATA_DT} AS
SELECT actiontype
     , actiondesc
     , snocode
     , objcode
     , buocmonth
     , CASE
           WHEN (G0305='10' OR G0305='13')
                   AND g0301='7'
           THEN '8' --202312外管局提出问题
           ELSE g0301
       END
     , g0302
     , g0303
     , g0304
     , CASE
           WHEN g0304='2'
                   AND dmst_ovsea_flag_code='1'
                   AND summ_name<>'费用'
           THEN '10'
           ELSE g0305
       END
     , g0306
     , remark
     , data_source
     , bank_id
     , pers_inner_accno
     , summ_name
     , cert_type
     , global_busi_track_no
     , subtx_no
     , mer_type_no
     , medium_no
     , cert_no
FROM RA03.CTB_CREDIT_G03_temp_type_{DATA_DT}
;

--监管调阅所需表，放的明细
DROP TABLE IF EXISTS RA03.CTB_CREDIT_G03_morning_{DATA_DT}
;

CREATE TABLE IF NOT EXISTS RA03.CTB_CREDIT_G03_morning_{DATA_DT} AS
SELECT ACTIONTYPE
     , ACTIONDESC
     , SNOCODE
     , OBJCODE
     , BUOCMONTH
     , G0301
     , G0302
     , G0303
     , G0304
     , G0305
     , G0306
     , REMARK
     , data_source
     , bank_id
     , a.medium_no
     , a.cert_type
     , a.cert_no
FROM RA03.CTB_CREDIT_G03_temp_type_new_{DATA_DT} a
    WHERE G0305 IN ('0','1','2','3','4','5','6','7','8','9','10','11','12','13')
        AND g0302<>'ZZZ'
;

--对借记卡金额独立进行求和存储 20240724新增
DROP TABLE IF EXISTS RA03.CTB_CREDIT_G03_jjk_sumg0306_{DATA_DT}
;

CREATE TABLE IF NOT EXISTS RA03.CTB_CREDIT_G03_jjk_sumg0306_{DATA_DT} AS
SELECT g0301
     , g0302
     , g0303
     , g0304
     , g0305
     , SUM(g0306) AS G0306
FROM RA03.CTB_CREDIT_G03_temp_type_new_{DATA_DT} a
    WHERE g0305 IN ('0','1','2','3','4','5','6','7','8','9','10','11','12','13')
        AND G0306<>0  --20230607  morning私聊加的
        AND g0302 NOT IN ('ZZZ','BVT','UMI','PCN','IOT','SGS','ATA','HMD','ATF')  --20240506  需求单要求新增四个无人区
    GROUP BY g0301 ,g0302 ,g0303 ,g0304 ,g0305
;

--开始信用卡的加工逻辑
DROP TABLE IF EXISTS ra03.cs_6100_2024_0411_1
;

CREATE TABLE IF NOT EXISTS ra03.cs_6100_2024_0411_1 AS
SELECT t1.card_no          AS card_nbr   --卡号
     , t2.personal_cert_no AS custr_nbr   --客户证件号码
     , t2.per_cert_tp_cd   AS race_code   --证件类型
     , ct.cd_value1        AS nation_cd   --国家英文代码
FROM rbdb.ice_ngc_ngcc_card t1  --卡片资料表
    INNER JOIN rbdb.ice_ngc_ngcc_custr t2  --客户基本资料 
        ON t1.cust_no = t2.cust_no
        AND t2.per_cert_tp_cd IN ('1070' --港澳居民往来内地通行证 ,'1080' --台湾居民往来内地通行证 ,'1051' --外籍人士护照 ,'1181' --港澳居民居住证 ,'1182' --台湾居民居住证 ,'1181' --香港居民居住证 ,'1181' --澳门居民居住证 ,'1140' --香港身份证 )
    LEFT JOIN rbdb.ncf_ppers001db_sp01_cust_info ci
        ON t2.cust_no = ci.ecif_cust_no
        AND ci.start_dt <= '{DATA_DT}'
        AND ci.end_dt > '{DATA_DT}'
    LEFT JOIN ra03.wgj_standard_county_hs ct
        ON ci.natnl_regn_cd = ct.cd_value2
    WHERE t1.start_dt <='{DATA_DT}'
        AND t1.end_dt>'{DATA_DT}'
        AND t2.start_dt <='{DATA_DT}'
        AND t2.end_dt>'{DATA_DT}'
;

DROP TABLE IF EXISTS ra03.cs_6100_2024_0411_4
;

CREATE TABLE IF NOT EXISTS ra03.cs_6100_2024_0411_4 AS
SELECT t0.custr_nbr
     , t0.race_code
     , t0.nation_cd
     , t1.card_no                                    AS card_nbr   --卡号
     , t1.dmst_ovsea_flag_code                       AS osflag   --境内外标识
     , t1.tx_type_no                                 AS trans_type   --交易类型
     , t1.crcard_card_tp_no                          AS card_plan   --卡片类型
     , CAST(LPAD(t1.tx_curr_cd, 3, '0') AS VARCHAR(3)) AS currncy_cd
     , t1.crcard_mer_categ_no                        AS mer_cat_cd   --商户类别
     , CASE
           WHEN t1.crcard_dc_dirc_cd = 'C'
           THEN -CAST(ROUND(t1.tx_amt,2) AS DECIMAL(22,2))
           ELSE CAST(ROUND(t1.tx_amt,2) AS DECIMAL(22,2))
       END AS cal_amt
     , SUBSTR(t1.create_stamp, 1, 8)                 AS inp_date   --交易记录日期
     , CASE
           WHEN t1.crcard_dc_dirc_cd = 'C'
           THEN -t1.inacc_amt
           ELSE t1.inacc_amt
       END AS bill_amt  --交易金额
     , t1.crcard_mng_accno                           AS acctnbr   --账号
     , t1.mer_seq_no                                 AS merch_seq   --商户序号
     , TRIM(t1.crcard_tx_src_cd)                     AS trans_src   --交易来源
     , t1.crcard_acq_mer_no                          AS merchant   --收单商户代码
     , t1.MASTER_CARD_POS_DATA                       AS mcpos_data   --万事达卡POS数据
     , CAST('EVENT' AS VARCHAR(8))                   AS src
FROM ra03.cs_6100_2024_0411_1 t0
    INNER JOIN rbdb.ngc_ngcc_transaction_detail t1  --已入账交易流水表
        ON t0.card_nbr = t1.card_no
        AND t1.tx_type_no <> '8130'
    WHERE SUBSTR(t1.create_stamp,1,8) >= '{CUR_MONTH_FIRST}'
        AND SUBSTR(t1.create_stamp,1,8) <= '{DATA_DT}'
        AND t1.etl_load_date >= '{CUR_MONTH_FIRST}'
        AND t1.etl_load_date <= '{DATA_DT}'
;

INSERT INTO ra03.cs_6100_2024_0411_4
SELECT t0.custr_nbr
     , t0.race_code
     , t0.nation_cd
     , t1.card_no                                       AS card_nbr   --卡号
     , 0                                                AS osflag
     , t1.tx_type_no                                    AS trans_type   --交易类型
     , t1.crcard_card_tp_no                             AS card_plan   --卡片类型
     , CAST(LPAD(t1.inacc_curr_cd, 3, '0') AS VARCHAR(3)) AS currncy_cd   --交易币种
     , t1.crcard_mer_categ_no                           AS mer_cat_cd   --商户类别
     , CASE
           WHEN t1.crcard_dc_dirc_cd = 'C'
           THEN -t1.inacc_amt
           ELSE t1.inacc_amt
       END AS cal_amt
     , SUBSTR(t1.create_stamp, 1, 8)                    AS inp_date   --交易记录日期
     , CASE
           WHEN t1.crcard_dc_dirc_cd = 'C'
           THEN -t1.inacc_amt
           ELSE t1.inacc_amt
       END AS bill_amt
     , t1.crcard_mng_accno                              AS acctnbr   --账号
     , t1.mer_seq_no                                    AS merch_seq   --商户序号
     , TRIM(t1.crcard_tx_src_cd)                        AS trans_src   --交易来源
     , t1.crcard_acq_mer_no                             AS merchant   --收单商户代码
     , ''                                               AS mcpos_data
     , CAST('MPTR' AS VARCHAR(8))                       AS src
FROM ra03.cs_6100_2024_0411_1 t0
    INNER JOIN rbdb.ngc_ngcc_transaction_detail t1 --已入账交易流水表
        ON t0.card_nbr = t1.card_no
        AND t1.tx_type_no = '8130'
    INNER JOIN rbdb.ngc_ngcc_trantype_father t2  --交易类型分类参数表 
        ON t1.tx_type_no = t2.tx_type_no
        AND t2.crcard_tx_statis_lvl1_tp_no = '40001'
    WHERE SUBSTR(t1.create_stamp,1,8) >= '{CUR_MONTH_FIRST}'
        AND SUBSTR(t1.create_stamp,1,8) <= '{DATA_DT}'
        AND t1.etl_load_date >= '{CUR_MONTH_FIRST}'
        AND t1.etl_load_date <= '{DATA_DT}'
        AND t2.start_dt <= '{DATA_DT}'
        AND t2.end_dt > '{DATA_DT}'
;

DROP TABLE IF EXISTS ra03.cs_6100_2024_0411_2_pre
;

CREATE TABLE IF NOT EXISTS ra03.cs_6100_2024_0411_2_pre AS
SELECT ROW_NUMBER() OVER(PARTITION BY 1 ORDER BY 1) AS rid
     , t1.custr_nbr
     , t1.race_code
     , t1.nation_cd
     , t1.card_nbr
     , t1.osflag
     , t1.trans_type
     , t1.card_plan
     , t1.currncy_cd
     , t1.mer_cat_cd
     , t1.cal_amt
     , t1.inp_date
     , t1.bill_amt
     , t1.acctnbr
     , t1.merch_seq
     , t1.trans_src
     , t1.merchant
     , t1.mcpos_data
     , t1.src
     , CASE
           WHEN (t1.osflag = 1 OR (t1.trans_src = 'INTERIN' AND t1.currncy_cd <> '156'))
                   AND t4.crcard_tx_statis_lvl1_tp_no = '30001'
           THEN 1
           WHEN t1.osflag = 0
                   AND t1.currncy_cd = '156'
                   AND SUBSTRING(t1.mcpos_data,9,8) NOT IN ('00010344','00010446')
                   AND (t4.crcard_tx_statis_lvl1_tp_no IN ('10001','30001','50001','60001','90001') OR t4.crcard_tx_statis_lvl2_tp_no='200011')
           THEN 2
           WHEN t4.crcard_tx_statis_lvl1_tp_no = '40001'
           THEN 3
           ELSE 0
       END AS trantype
     , SUBSTR('{DATA_DT}', 1, 6)                    AS yyyymm
     , CASE
           WHEN t1.race_code IN ('1080','1182')
           THEN 'TWN'
           WHEN t1.race_code IN ('1070','1181')
           THEN
               CASE
                   WHEN NVL(t1.nation_cd,'') IN ('HKG','MAC')
                   THEN NVL(t1.nation_cd,'')
                   ELSE
                       CASE
                           WHEN SUBSTR(t1.custr_nbr,1,1) = 'H'
                                   OR SUBSTR(t1.custr_nbr,1,2) = '81'
                           THEN 'HKG'
                           WHEN SUBSTR(t1.custr_nbr,1,1) = 'M'
                                   OR SUBSTR(t1.custr_nbr,1,2) = '82'
                           THEN 'MAC'
                           ELSE
                               CASE
                                   WHEN NVL(t1.nation_cd,'') IN ('','CHN')
                                   THEN 'ZZZ'
                                   ELSE t1.nation_cd
                               END
                       END
               END
           ELSE
               CASE
                   WHEN NVL(t1.nation_cd,'') IN ('','CHN')
                   THEN 'ZZZ'
                   ELSE t1.nation_cd
               END
       END AS G0302
     , NVL(t3.var_a1,'NUL')                         AS G0303
     , CASE
           WHEN t1.cal_amt > 0
           THEN 2
           ELSE 1
       END AS G0304
     , CASE
           WHEN t1.cal_amt <= 0
           THEN 12
           WHEN t1.cal_amt > 0
           THEN
               CASE
                   WHEN t1.osflag = 1
                   THEN 10
                   WHEN NVL(t2.req,'') <> ''
                   THEN t2.req   --用新增mcc码表辅助赋值/*modify by qiuyelong 20250827*/
                   ELSE NVL(mccadd.req,6)
               END
           ELSE 6
       END AS G0305
     , ABS(t1.cal_amt)                              AS G0306
     , ABS(t1.bill_amt)                             AS billamt
FROM ra03.cs_6100_2024_0411_4 t1
    LEFT JOIN ra03.t_cs_6100_2015_0453_mcc t2
        ON t1.mer_cat_cd = CAST(t2.mer_cat_cd AS DECIMAL(4,0))
    LEFT JOIN ra03.t_code_g03_mcc_14add mccadd  --新增mcc码表/*modify by qiuyelong 20250827*/
        ON t1.mer_cat_cd = CAST(mccadd.mer_cat_cd AS DECIMAL(4,0))
    LEFT JOIN ra03.t_cs_6100_2017_0642_curr t3
        ON t1.currncy_cd = t3.code_value
    LEFT JOIN rbdb.ngc_ngcc_trantype_father t4  --交易类型分类参数表
        ON t1.trans_type = t4.tx_type_no
    WHERE t1.cal_amt <> 0
        AND t4.start_dt <= '{DATA_DT}'
        AND t4.end_dt > '{DATA_DT}'
;

DROP TABLE IF EXISTS ra03.cs_6100_2024_0411_2
;

CREATE TABLE IF NOT EXISTS ra03.cs_6100_2024_0411_2 AS
SELECT rid
     , custr_nbr
     , race_code
     , nation_cd
     , card_nbr
     , osflag
     , trans_type
     , card_plan
     , currncy_cd
     , mer_cat_cd
     , cal_amt
     , inp_date
     , bill_amt
     , acctnbr
     , merch_seq
     , trans_src
     , merchant
     , mcpos_data
     , src
     , trantype
     , yyyymm
     , G0302
     , G0303
     , G0304
     , G0305
     , G0306
     , billamt
FROM ra03.cs_6100_2024_0411_2_pre
    WHERE trantype <> 0
;

DROP TABLE IF EXISTS ra03.cs_6100_2024_0411_3_pre
;

CREATE TABLE IF NOT EXISTS ra03.cs_6100_2024_0411_3_pre AS
SELECT t1.rid
     , t1.custr_nbr
     , t1.race_code
     , t1.nation_cd
     , t1.card_nbr
     , t1.osflag
     , t1.trans_type
     , t1.card_plan
     , t1.currncy_cd
     , t1.mer_cat_cd
     , t1.cal_amt
     , t1.inp_date
     , t1.bill_amt
     , t1.acctnbr
     , t1.merch_seq
     , t1.trans_src
     , t1.merchant
     , t1.mcpos_data
     , t1.src
     , t1.trantype
     , t1.yyyymm
     , t1.g0302
     , t1.g0303
     , t1.g0304
     , t1.g0305
     , t1.g0306
     , t1.billamt
     , NVL(t2.instal_tp_cd,'') AS mp_types
     , CASE
           WHEN NVL(t2.instal_tp_cd,'') IN ('Y','B','A','D')
                   OR (NVL(t2.instal_tp_cd,'') = 'L' AND SUBSTRING(NVL(t2.instal_prodt_no,''),1,3) = '979')
           THEN 1
           ELSE 0
       END AS mp_flag
     , CASE
           WHEN t1.trantype = 3
           THEN
               CASE
                   WHEN NVL(t2.instal_tp_cd,'') = 'H'
                   THEN 1
                   ELSE 7
               END
           WHEN t1.trantype <> 3
           THEN
               CASE
                   WHEN t1.trans_src IN ('CUPIO','CUPPROCE')
                   THEN 1
                   WHEN t1.trans_src = 'INTERIN'
                           AND t1.card_plan = 'V'
                   THEN 2
                   WHEN t1.trans_src = 'INTERIN'
                           AND t1.card_plan = 'M'
                   THEN 3
                   WHEN t1.trans_src = 'INTERIN'
                           AND t1.card_plan = 'A'
                   THEN 4
                   WHEN t1.trans_src = 'INTERIN'
                           AND t1.card_plan = 'J'
                   THEN 6
                   WHEN t1.trans_src IN ('MBKIO','CADJT','CADJ1','CADVC','PURJT','MBKERR','DFERR-OR','DFERR')
                           AND SUBSTR(t1.merchant,1,3)<>'DSF'
                   THEN 7
                   ELSE 8
               END
           ELSE 8
       END AS G0301
FROM ra03.cs_6100_2024_0411_2 t1
    LEFT JOIN rbdb.ice_ngc_ngcc_inst_order t2
        ON t1.acctnbr = t2.crcard_mng_accno
        AND t1.merch_seq = t2.itlm_order_no
        AND t2.start_dt <= '{DATA_DT}'
        AND t2.end_dt > '{DATA_DT}'
;

DROP TABLE IF EXISTS ra03.cs_6100_2024_0411_3
;

CREATE TABLE IF NOT EXISTS ra03.cs_6100_2024_0411_3 AS
SELECT rid
     , custr_nbr
     , race_code
     , nation_cd
     , card_nbr
     , osflag
     , trans_type
     , card_plan
     , currncy_cd
     , mer_cat_cd
     , cal_amt
     , inp_date
     , bill_amt
     , acctnbr
     , merch_seq
     , trans_src
     , merchant
     , mcpos_data
     , src
     , trantype
     , yyyymm
     , g0302
     , g0303
     , g0304
     , g0305
     , g0306
     , billamt
     , mp_types
     , mp_flag
     , G0301
FROM ra03.cs_6100_2024_0411_3_pre
    WHERE !(trantype = 3 AND mp_flag <> 0)
;

CREATE TABLE IF NOT EXISTS ra03.cs_6100_2024_0411_g03_his(
     rid             INT               COMMENT 'RID'
    ,custr_nbr       varchar(19)       COMMENT '客户证件号码'
    ,race_code       varchar(2)        COMMENT '证件类型'
    ,nation_cd       varchar(3)        COMMENT '国籍代码'
    ,card_nbr        varchar(19)       COMMENT '卡号'
    ,osflag          decimal(1,0)      COMMENT '境内外标识'
    ,trans_type      STRING            COMMENT '交易类型'
    ,card_plan       varchar(1)        COMMENT '卡片类型'
    ,currncy_cd      varchar(3)        COMMENT '原始货币'
    ,mer_cat_cd      STRING            COMMENT '商户类别'
    ,cal_amt         decimal(22,2)     COMMENT '原始币种金额'
    ,inp_date        STRING            COMMENT '交易记录日期'
    ,bill_amt        decimal(11,2)     COMMENT '交易金额'
    ,acctnbr         STRING            COMMENT '账号'
    ,merch_seq       STRING            COMMENT '商户序号'
    ,trans_src       STRING            COMMENT '交易来源'
    ,merchant        varchar(15)       COMMENT '收单商户代码'
    ,mcpos_data      varchar(26)       COMMENT '万事达卡POS数据'
    ,src             varchar(8)        COMMENT '源表'
    ,trantype        INT               COMMENT '交易种类'
    ,yyyymm          STRING            COMMENT '报告期'
    ,g0302           STRING            COMMENT '持卡人所属国家/地区'
    ,g0303           STRING            COMMENT '持卡人所属国家/地区'
    ,g0304           INT               COMMENT '交易原币'
    ,g0305           INT               COMMENT '交易类型'
    ,g0306           decimal(22,2)     COMMENT '交易类型'
    ,billamt         decimal(11,2)     COMMENT '交易金额'
    ,mp_types        STRING            COMMENT '分期付款类型'
    ,mp_flag         INT               COMMENT '分期标志'
    ,g0301           INT               COMMENT '银行卡清算渠道'
) COMMENT 'G03非居民持有境内银行卡的收入支出信用卡明细表'
PARTITIONED BY (DATA_DT STRING)
;

ALTER TABLE ra03.cs_6100_2024_0411_g03_his DROP IF EXISTS PARTITION(DATA_DT='{DATA_DT}')
;

INSERT INTO ra03.cs_6100_2024_0411_g03_his PARTITION (DATA_DT='{DATA_DT}')
SELECT rid
     , custr_nbr
     , race_code
     , nation_cd
     , card_nbr
     , osflag
     , trans_type
     , card_plan
     , currncy_cd
     , mer_cat_cd
     , cal_amt
     , inp_date
     , bill_amt
     , acctnbr
     , merch_seq
     , trans_src
     , merchant
     , mcpos_data
     , src
     , trantype
     , yyyymm
     , g0302
     , g0303
     , g0304
     , g0305
     , g0306
     , billamt
     , mp_types
     , mp_flag
     , g0301
FROM ra03.cs_6100_2024_0411_3
;

DROP TABLE IF EXISTS ra03.cs_6100_2024_0411_res2_pre
;

CREATE TABLE IF NOT EXISTS ra03.cs_6100_2024_0411_res2_pre AS
SELECT CAST('A' AS VARCHAR(1))             AS c01
     , CAST('' AS VARCHAR(128))            AS c02
     , CAST('' AS VARCHAR(36))             AS c03
     , CAST('110000013000' AS VARCHAR(18)) AS c04
     , CAST(yyyymm AS VARCHAR(6))          AS c05
     , CAST(g0301 AS DECIMAL(2,0))         AS c06
     , CAST(g0302 AS VARCHAR(3))           AS c07
     , CAST(G0303 AS VARCHAR(3))           AS c08
     , CAST(G0304 AS DECIMAL(2,0))         AS c09
     , CAST(G0305 AS DECIMAL(2,0))         AS c10
     , CAST(G0306 AS DECIMAL(22,2))        AS c11
     , CAST('' AS VARCHAR(512))            AS c12
     , CAST(bill_amt AS DECIMAL(22,2))     AS c13
FROM ra03.cs_6100_2024_0411_3
;

DROP TABLE IF EXISTS ra03.cs_6100_2024_0411_res2
;

CREATE TABLE IF NOT EXISTS ra03.cs_6100_2024_0411_res2 AS
SELECT c01                             AS c01
     , c02                             AS c02
     , c03                             AS c03
     , c04                             AS c04
     , c05                             AS c05
     , c06                             AS c06
     , c07                             AS c07
     , c08                             AS c08
     , c09                             AS c09
     , c10                             AS c10
     , CAST(SUM(c11) AS DECIMAL(22, 2)) AS c11
     , c12                             AS c12
     , CAST(SUM(c13) AS DECIMAL(22, 2)) AS c13
FROM ra03.cs_6100_2024_0411_res2_pre
    GROUP BY C01,C02,C03,C04,C05,C06,C07,C08,C09,C10,C12
    ORDER BY C01,C02,C03,C04,C05,C06,C07,C08,C09,C10,C12
;

DROP TABLE IF EXISTS ra03.t_gjdg_jrzf_g03_xyk_tmp
;

CREATE TABLE IF NOT EXISTS ra03.t_gjdg_jrzf_g03_xyk_tmp(
 g0301        INT             COMMENT'银行卡清算渠道'
,g0302        VARCHAR(3)      COMMENT'持卡人所属国家/地区'
,g0303        VARCHAR(3)      COMMENT'交易原币'
,g0304        INT             COMMENT'收支类型'
,g0305        INT             COMMENT'交易类型'
,g0306        DECIMAL(22,2)   COMMENT'交易金额'
,remark       VARCHAR(512)    COMMENT'备注'
 ) COMMENT 'G03非居民持有境内银行卡的收入支出_信用卡'
;

INSERT INTO ra03.t_gjdg_jrzf_g03_xyk_tmp
SELECT c06 AS g0301
     , c07 AS g0302
     , c08 AS g0303
     , c09 AS g0304
     , c10 AS g0305
     , c11 AS g0306
     , ''  AS remark
FROM ra03.cs_6100_2024_0411_res2
;

CREATE TABLE IF NOT EXISTS ra03.t_gjdg_jrzf_g03_xyk_tmp_his(
     g0301        INT             COMMENT'银行卡清算渠道'
    ,g0302        VARCHAR(3)      COMMENT'持卡人所属国家/地区'
    ,g0303        VARCHAR(3)      COMMENT'交易原币'
    ,g0304        INT             COMMENT'收支类型'
    ,g0305        INT             COMMENT'交易类型'
    ,g0306        DECIMAL(22,2)   COMMENT'交易金额'
    ,remark       VARCHAR(512)    COMMENT'备注'
) COMMENT 'G03非居民持有境内银行卡的收入支出_信用卡聚合历史表'
PARTITIONED BY (DATA_DT STRING)
;

ALTER TABLE ra03.t_gjdg_jrzf_g03_xyk_tmp_his DROP IF EXISTS PARTITION(DATA_DT='{DATA_DT}')
;

INSERT INTO ra03.t_gjdg_jrzf_g03_xyk_tmp_his PARTITION (DATA_DT='{DATA_DT}')
SELECT c06 AS g0301
     , c07 AS g0302
     , c08 AS g0303
     , c09 AS g0304
     , c10 AS g0305
     , c11 AS g0306
     , ''  AS remark
FROM ra03.cs_6100_2024_0411_res2
;

DROP TABLE IF EXISTS ra03.t_gjdg_jrzf_g03_xyk_err_tmp
;

CREATE TABLE IF NOT EXISTS ra03.t_gjdg_jrzf_g03_xyk_err_tmp(
 g0301        INT             COMMENT'银行卡清算渠道'
,g0302        VARCHAR(3)      COMMENT'持卡人所属国家/地区'
,g0303        VARCHAR(3)      COMMENT'交易原币'
,g0304        INT             COMMENT'收支类型'
,g0305        INT             COMMENT'交易类型'
,g0306        DECIMAL(22,2)   COMMENT'交易金额'
,remark       VARCHAR(512)    COMMENT'备注'
,errms        VARCHAR(100)    COMMENT'错误信息'
 ) COMMENT 'G03非居民持有境内银行卡的收入支出_信用卡'
;

INSERT INTO ra03.t_gjdg_jrzf_g03_xyk_err_tmp
SELECT g0301
     , g0302
     , g0303
     , g0304
     , g0305
     , g0306
     , remark
     , '金额应大于0'
FROM ra03.t_gjdg_jrzf_g03_xyk_tmp
    WHERE g0306<=0
;

INSERT INTO ra03.t_gjdg_jrzf_g03_xyk_err_tmp
SELECT g0301
     , g0302
     , g0303
     , g0304
     , g0305
     , g0306
     , remark
     , '币种应存在于外管局币种代码表中'
FROM ra03.t_gjdg_jrzf_g03_xyk_tmp
    WHERE g0303 NOT IN (
    SELECT var_a1
    FROM ra03.T_CS_6100_2017_0642_CURR
)
;

INSERT INTO RA03.CTB_CREDIT_G03_temp_type_new_{DATA_DT}
SELECT ''
     , ''
     , ''
     , ''
     , ''
     , g0301
     , g0302
     , g0303
     , g0304
     , CAST(g0305 AS STRING) AS g0305   --防止P+中断/*modify by qiuyelong 20250827*/
     , g0306
     , remark
     , 'XYK'                 AS data_source
     , '11005293'            AS bank_id
     , ''
     , ''
     , ''
     , ''
     , ''
     , ''
     , ''
     , ''
FROM ra03.t_gjdg_jrzf_g03_xyk_tmp
;

--对金额进行求和
DROP TABLE IF EXISTS RA03.CTB_CREDIT_G03_sumg0306_{DATA_DT}
;

CREATE TABLE IF NOT EXISTS RA03.CTB_CREDIT_G03_sumg0306_{DATA_DT} AS
SELECT g0301
     , g0302
     , g0303
     , g0304
     , g0305
     , SUM(g0306) AS G0306
FROM RA03.CTB_CREDIT_G03_temp_type_new_{DATA_DT} a
    GROUP BY g0301 ,g0302 ,g0303 ,g0304 ,g0305
;

--去掉交易类型为汉字和国家地区代码是ZZZ的数据插入结果表
ALTER TABLE RA03.T_GJDG_JRZF_G03 DROP IF EXISTS PARTITION(DATA_DT='{DATA_DT}')
;

INSERT INTO RA03.T_GJDG_JRZF_G03 PARTITION (DATA_DT='{DATA_DT}')
SELECT 'A'
     , ''
     , CONCAT('110000013000aaaaaa', 'G03aa', SUBSTR('{DATA_DT}', 1, 6), LPAD(ROW_NUMBER() OVER(PARTITION BY 1 ORDER BY 1), 7, 0))              --数据自编码
     , '110000013000'                                                                                                                          --申报主体代码
     , SUBSTR('{DATA_DT}', 1, 6)                                                                                                               --报告期
     , a.g0301
     , a.g0302
     , a.g0303
     , a.g0304
     , CAST(a.g0305 AS INT)                                                                                                   AS g0305   --防止P+中断/*modify by qiuyelong 20250827*/
     , a.g0306
     , ''
     , 'XHX'                                                                                                                  AS data_source
     , '11005293'                                                                                                             AS bank_id
     , '20200512630/20210715710'
     , '牟宁/林先梅'
     , '个人金融部/信用卡中心'
FROM RA03.CTB_CREDIT_G03_sumg0306_{DATA_DT} a
    WHERE g0305 IN ('0','1','2','3','4','5','6','7','8','9','10','11','12','13')
        AND G0306<>0  --20230607  morning私聊加的
        AND g0302 NOT IN ('ZZZ','BVT','UMI','PCN','IOT','SGS','ATA','HMD','ATF')  --20240506  需求单要求新增四个无人区
;