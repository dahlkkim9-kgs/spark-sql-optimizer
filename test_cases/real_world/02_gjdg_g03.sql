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
,G0301        int             COMMENT'银行卡清算渠道'
,G0302        VARCHAR(3)      COMMENT'持卡人所属国家/地区'
,G0303        VARCHAR(3)      COMMENT'交易原币'
,G0304        int             COMMENT'收支类型'
,G0305        int             COMMENT'交易类型'
,G0306        decimal(22,2)   COMMENT'交易金额'
,REMARK       VARCHAR(512)    COMMENT'备注'
,data_source  VARCHAR(18)     COMMENT'数据来源'
,bank_id      VARCHAR(18)     COMMENT'机构号'
,ownusr       string          comment'柜员号'
,falpers      string          comment'报送人'
,faldept      string          comment'报送部门'
 ) COMMENT 'G03非居民持有境内银行卡的收入支出'
PARTITIONED BY (DATA_DT STRING);

--初步加工
DROP TABLE IF EXISTS RA03.CTB_CREDIT_G03_temp_{DATA_DT};
CREATE TABLE IF NOT EXISTS RA03.CTB_CREDIT_G03_temp_{DATA_DT} as select 
'A' ACTIONTYPE 
,'' ACTIONDESC
,concat('110000013000aaaaaa','G03aa',substr('{DATA_DT}',1,6),
                      lpad(row_number()
                           over(partition by 1 order by 1),
                           7,
                           0))  as SNOCODE                           --数据自编码
,'110000013000' OBJCODE                                              --申报主体代码
,substr('{DATA_DT}',1,6) BUOCMONTH                                   --报告期
,case when a.chnl_kind_code='22' then '1' 
      when a.start_sys_or_cmpt_no='99600010000' then '1' 
--      when a.start_sys_or_cmpt_no='99100140000' then '8'            --三方支付给8,20230607去掉
      when  (a.chnl_kind_code='42' AND a.start_sys_or_cmpt_no='99350000000') or a.chnl_kind_code='58' then '3' --20240506  添加万事达逻辑
      when a.ibank_flag='0' then '7'                                  --是否跨行标志为0的代表行内
      else '8' 
 end as G0301                                                        --银行卡清算渠道
,CASE WHEN a.cert_type in ('1070','1181') then (CASE WHEN a.cert_no like 'H%'  THEN 'HKG' --若证件类型是港澳居民往来内地通行证，证件号码是H开头，国籍赋值为HKG   --/*modify by qiuyelong 20250924*/
                                                            WHEN a.cert_no like 'M%'  THEN 'MAC' --若证件类型是港澳居民往来内地通行证，证件号码是M开头，国籍赋值为MAC
                                                            WHEN a.cert_no like '81%' THEN 'HKG' --若证件类型是港澳居民居住证，证件号码是81开头，国籍赋值为HKG
                                                            WHEN a.cert_no like '82%' THEN 'MAC' --若证件类型是港澳居民居住证，证件号码是82开头，国籍赋值为MAC
                                                            WHEN a.cert_no like 'h%'  THEN 'HKG' --若证件类型是港澳居民往来内地通行证，证件号码是H开头，国籍赋值为HKG
                                                            WHEN a.cert_no like 'm%'  THEN 'MAC' --若证件类型是港澳居民往来内地通行证，证件号码是M开头，国籍赋值为MAC
                                                            WHEN a.cert_no like '83%' THEN 'TWN' --若证件类型是台湾居民居住证，国籍赋值为TWN
                                                            ELSE 'ZZZ' 
                                                       END
                                                      )--20240729修改
      WHEN a.cert_type IN ('1080','1182') then (CASE WHEN a.cert_no like 'H%'  THEN 'HKG' --若证件类型是港澳居民往来内地通行证，证件号码是H开头，国籍赋值为HKG
                                                   WHEN a.cert_no like 'M%'  THEN 'MAC' --若证件类型是港澳居民往来内地通行证，证件号码是M开头，国籍赋值为MAC
                                                   WHEN a.cert_no like '81%' THEN 'HKG' --若证件类型是港澳居民居住证，证件号码是81开头，国籍赋值为HKG
                                                   WHEN a.cert_no like '82%' THEN 'MAC' --若证件类型是港澳居民居住证，证件号码是82开头，国籍赋值为MAC
                                                   WHEN a.cert_no like 'h%'  THEN 'HKG' --若证件类型是港澳居民往来内地通行证，证件号码是H开头，国籍赋值为HKG
                                                   WHEN a.cert_no like 'm%'  THEN 'MAC' --若证件类型是港澳居民往来内地通行证，证件号码是M开头，国籍赋值为MAC
                                                   WHEN a.cert_no like '83%' THEN 'TWN' --若证件类型是台湾居民居住证，国籍赋值为TWN
                                                   ELSE 'TWN'
                                              END
                                             )--20240729修改
      WHEN a.cert_type='1051' and b.cd_value1='CHN' THEN 'ZZZ' --若证件类型是外国护照，国籍属于CN的，赋值ZZZ
      ELSE (CASE WHEN NVL(b.cd_value1,'') ='' THEN 'ZZZ' ELSE  b.cd_value1   END)    --当国籍是空的时候转其他
 END AS G0302                                                        --持卡人所属国家/地区
,a.curr_suoxie AS G0303                                              --交易原币
,a.dw_flag_code as G0304                                             --收支类型
,case when a.summ_name like '%活转定%'   then '活转定'                              --20230508确认放下面加工，20230607又重新确认最开始刷成汉字（为了把dw_flag_code为1的也刷成汉字）
      when a.summ_name like '%定转活%'   then                                       --20230508确认放下面加工，20230607又重新确认最开始刷成汉字（为了把dw_flag_code为1的也刷成汉字）
           case when a.txamt_tp_cd ='0002' then '12'                                --20240724增加逻辑
                else '定转活'
           end
      when a.summ_name like '%部提存入%' and a.txamt_tp_cd ='0001' then '定转活'    --20240724增加逻辑
      when a.summ_name like '%账户结汇%' then '账户结汇'                            --20230508确认放下面加工，20230607又重新确认最开始刷成汉字（为了把dw_flag_code为1的也刷成汉字）
      when a.summ_name like '%售汇%'     then '售汇'                               --20230508确认放下面加工，20230607又重新确认最开始刷成汉字（为了把dw_flag_code为1的也刷成汉字）
      when a.summ_name like '%外币兑回%' then '外币兑回'                            --20230508确认放下面加工，20230607又重新确认最开始刷成汉字（为了把dw_flag_code为1的也刷成汉字）
      when a.summ_name like '%钞汇互转%' then '钞汇互转'                            --20230508确认放下面加工，20230607又重新确认最开始刷成汉字（为了把dw_flag_code为1的也刷成汉字）
      when a.summ_name like '%卡内互转%' then '卡内互转'                            --20230607又重新确认最开始刷成汉字（为了把dw_flag_code为1的也刷成汉字）
      when a.summ_name like '%账户兑换%' then '结售汇'                              --20240729增加逻辑
      when a.dw_flag_code='1' then (case when  a.summ_name like '%工资%'  then '11'
                                         when  a.tx_remark like '%工资%'  then '11'
                                         when  a.tx_remark like '%薪%'    then '11'
                                         when  a.tx_remark like '%奖金%'  then '11'
                                         when  a.tx_remark like '%劳务%'  then '11'
                                         when  dmst_ovsea_flag_code='1'   then '13'
                                    else '12' end )
      when a.dw_flag_code='2' and a.summ_name like '%卡现金取%'  then '7'   --取现
      when a.dw_flag_code='2' and a.summ_name like '%折现金取%'  then '7'   --取现
      when a.dw_flag_code='2' and a.summ_name like '%现金销户%'  then '7'   --取现
      when a.dw_flag_code='2' and a.summ_name like '%ATM取款%'   then '7'   --取现
      when a.dw_flag_code='2' and a.summ_name like '%ATM跨取%'   then '7'   --取现
      when a.dw_flag_code='2' and a.summ_name like '%跨境取款%'  then '7'   --取现
      when a.dw_flag_code='2' and a.summ_name like '%卡转取%'    then '7'   --取现
      when a.dw_flag_code='2' and a.summ_name like '%跨行取款%'  then '7'   --取现
      when a.dw_flag_code='2' and a.summ_name like '%折转取%'    then '7'   --取现
      when a.dw_flag_code='2' and a.summ_name like '%助农取款%'  then '7'   --取现
      when a.dw_flag_code='2' and a.summ_name like '%费用%' and a.start_sys_or_cmpt_no='1043199' then '6'   --其他支出
      when a.dw_flag_code='2' and a.mer_desc  like '%医院%' then '8'       --8-医疗保健
      when a.dw_flag_code='2' and a.mer_desc  like '%药店%' then '8'       --8-医疗保健
      when a.dw_flag_code='2' and a.mer_desc  like '%药房%' then '8'       --8-医疗保健
      when a.dw_flag_code='2' and a.mer_desc  like '%交通%' then '4'       --4-当地交通
      when a.dw_flag_code='2' and a.mer_desc  like '%铁路%' then '4'       --4-当地交通
      when a.dw_flag_code='2' and a.mer_desc  like '%航空%' then '4'       --4-当地交通
      when a.dw_flag_code='2' and a.tx_remark like '%高速%' then '4'       --4-当地交通
      when a.dw_flag_code='2' and a.tx_remark like '%交通%' then '4'       --4-当地交通  20240724增加
      when a.dw_flag_code='2' and a.tx_remark like '%铁路%' then '4'       --4-当地交通  20240724增加
      when a.dw_flag_code='2' and a.tx_remark like '%航空%' then '4'       --4-当地交通  20240724增加
      when a.dw_flag_code='2' and a.summ_name like '%ETC%'  then '4'       --4-当地交通  20230407新加
      when a.dw_flag_code='2' and a.tx_remark like '%ETC%'  then '4'       --4-当地交通  20230607新加
      
      when  ((a.chnl_kind_code='42' AND a.start_sys_or_cmpt_no='99350000000') or a.chnl_kind_code='58') and a.mer_type_no = '3998' then '2' --20240506  添加3998时万事达逻辑
      WHEN NVL(c.jylx,'') <> '' THEN c.jylx --用新码表进行赋值赋值/*modify by qiuyelong 20250827*/
      ELSE CAST(NVL(mccadd.req,'') AS STRING)
 END AS g0305                                                     --交易类型
,a.tx_amt as G0306                                               --交易金额
,a.tx_remark as REMARK                                           --备注
,'XHX'       data_source
,'11005293'  bank_id  
,a.pers_inner_accno
,a.summ_name
,a.cert_type
,a.global_busi_track_no 
,a.subtx_no
,A.mer_type_no
,a.mer_desc
,a.medium_no
,a.cert_no
,a.ibank_flag
,a.dmst_ovsea_flag_code
from ra03.tmp_sm_{DATA_DT}B01_feijumin_tx_xinhexin_last a 
left join ra03.wgj_send_country b                        --外管局码表
on a.country_code=b.std_cd_value
left join ra03.G03_jylx_code c                           --交易类型码表
on a.mer_type_no =c.mcc
LEFT JOIN ra03.t_code_g03_mcc_14add mccadd              --新增码表/*modify by qiuyelong 20250827*/
       ON a.mer_type_no = mccadd.mer_cat_cd
left join ra03.wgj_send_country ct                        --外管局码表,将新版外国人永久居留证中3位数字国家地区编码转换为3位字母 /*modify by qyl 20240124*/
on ct.std_cd_value = SUBSTR(a.cert_no,4,3)
;


--处理交易类型不覆盖
DROP TABLE IF EXISTS RA03.CTB_CREDIT_G03_temp_dont_overwrite_{DATA_DT};
CREATE TABLE IF NOT EXISTS  RA03.CTB_CREDIT_G03_temp_dont_overwrite_{DATA_DT} as  
select 
a.actiontype           
,a.actiondesc           
,a.snocode              
,a.objcode              
,a.buocmonth            
,a.g0301                
,a.g0302                
,a.g0303                
,a.g0304                
,CASE WHEN NVL(G0305,'')='' AND  a.G0304='2' THEN   (CASE WHEN  a.summ_name like '%短信扣费%' then '6'
                                                          when  a.summ_name like '%快捷支付%' then '1'
                                                          when  a.summ_name like '%跨行汇出%' then '9'
                                                          when  a.summ_name like '%转账汇出%' then '9'
                                                          --when  a.summ_name like '%ETC通行%'  then '4'
                                                          when  a.summ_name like '%批量扣款%' then '9'
                                                          when  a.summ_name like '%集中代收%' then '6'
                                                          when  a.summ_name like '%公共事业%' then '6'
                                                          when  a.summ_name like '%延迟转账%' then '9'
                                                          when  a.summ_name like '%定投扣款%' then '6'
                                                          when  a.summ_name like '%电费%'     then '6'
                                                          when  a.summ_name like '%跨行退款%' then '9'
                                                          when  a.summ_name like '%通讯费%'   then '6'
                                                          when  a.summ_name like '%人行代收%' then '6'
                                                          when  a.summ_name like '%理财购买%' then '6'
                                                          when  a.summ_name like '%社保医保%' then '6'
                                                          when  a.summ_name like '%银转证%'   then '6'
                                                          when  a.summ_name like '%强制销户%' then '9'
                                                          when  a.summ_name like '%营业款%'   then '9'
                                                          when  a.summ_name like '%商业保险%' then '6'
                                                          when  a.summ_name like '%水费%'     then '6'
                                                          when  a.summ_name like '%贷款还款%' then '9'
                                                          when  a.summ_name like '%费用%'     then '6'
                                                          when  a.summ_name like '%消费金融%' then '9'
                                                          when  a.summ_name like '%预授完成%' then '1'
                                                          when  a.summ_name like '%物业费%'   then '6'
                                                          when  a.summ_name like '%基金申购%' then '6'
                                                          when  a.summ_name like '%网关支付%' then '1'
                                                          when  a.summ_name like '%邮益宝申%' then '6'
                                                          when  a.summ_name like '%银联代收%' then '6'
                                                          when  a.summ_name like '%银联快捷%' then '1'
                                                          when  a.summ_name like '%基金认购%' then '6'
                                                          when  a.summ_name like '%商户扣账%' then '9'
                                                          when  a.summ_name like '%行内收款%' then '9'
                                                          when  a.summ_name like '%网银代发%' then '9'
                                                          when  a.summ_name like '%账户发汇%' then '9'
                                                          when  a.summ_name like '%支取数币%' then '9'
                                                          when  a.summ_name like '%餐费%'     then '3'
                                                          when  a.summ_name like '%资管购买%' then '6'
                                                          when  a.summ_name like '%计划积存%' then '6'
                                                          when  a.summ_name like '%消费%'     then '1'
                                                          when  a.summ_name like '%自扣还款%' then '9'
                                                          when  a.summ_name like '%烟草款%'   then '1'
                                                          when  a.summ_name like '%扣款%'     then '9'
                                                          when  a.summ_name like '%归集汇出%' then '9'
                                                          when  a.summ_name like '%教育%'     then '5'
                                                          when  a.summ_name like '%燃气费%'   then '6'
                                                          when  a.summ_name like '%销户转存%' then '9'
                                                          when  a.summ_name like '%有线电视%' then '6'
                                                          when  a.summ_name like '%扣划转出%' then '9'
                                                          when  a.summ_name like '%餐杂费%'   then '3'
                                                          when  a.summ_name like '%公积金%'   then '6'
                                                          when  a.summ_name like '%国库收款%' then '9'
                                                          when  a.summ_name like '%校园卡%'   then '5'
                                                          when  a.summ_name like '%预约转账%' then '9'
                                                          when  a.summ_name like '%调整%'     then '9'
                                                          when  a.summ_name like '%圈存充值%' then '9'
                                                          when  a.summ_name like '%同城支付%' then '9'
                                                          when  a.summ_name like '%学费%'     then '5'
                                                          when  a.summ_name like '%房租%'     then '6'
                                                          when  a.summ_name like '%批量销户%' then '9'
                                                          when  a.summ_name like '%圈提转出%' then '9'
                                                          when  a.summ_name like '%私转公%'   then '9'
                                                          when  a.summ_name like '%投资理财%' then '6'
                                                          when  a.summ_name like '%医疗费%'   then '8'
                                                          when  a.summ_name like '%转账销户%' then '9'
                                                          when  a.summ_name like '%批量代收%' then '6'      --20230407新加
                                                          when  a.summ_name like '%代收费%'   then '6'      --20230407新加
                                                          when  a.summ_name like '%购实物金%' then '6'      --20230407新加
                                                          when  a.summ_name like '%水电费%'   then '6'      --20230407新加
                                                          when  a.summ_name like '%凭债购买%' then '6'      --20230407新加
                                                          when  a.summ_name like '%受托支付%' then '6'      --20230407新加
                                                          when  a.summ_name like '%医保款%'   then '6'      --20230407新加
                                                         -- when  a.summ_name like '%公益款%'   then '6'
                                                          when  a.summ_name like '%冲正%'     then '9'
                                                         -- when  a.summ_name like '%取消%'     then '9'
                                                         -- when  a.summ_name like '%ETC%'      then '4'      --20230407新加
                                                          when  a.summ_name like '%储债认购%'     then '6'            --20230506新加
                                                          when  a.summ_name like '%银转两融%'     then '6'            --20230506新加
                                                          when  a.summ_name like '%组织收款%'     then '6'            --20230506新加
                                                          when  a.summ_name like '%卡内互转%'     then '卡内互转'     --20230506新加
                                                          when  a.summ_name like '%定转活%'       then '定活互转'     --20230506新加
                                                          when  a.summ_name like '%活转定%'       then '定活互转'     --20230506新加
                                                          when  a.summ_name like '%账户结汇%'     then '结售汇'       --20230506新加
                                                          when  a.summ_name like '%售汇%'         then '结售汇'       --20230506新加
                                                          when  a.summ_name like '%凭债扣费%'     then '6'          --20230607新加
                                                          when  a.summ_name like '%移出%'         then '9'          --20230607新加
                                                          when  a.summ_name like '%公益款%'       then '6'          --20230607新加
                                                          when  a.summ_name like '%跨行代收%'       then '6'          --20230705新加
                                                          when  a.summ_name like '%密码汇出%'       then '9'          --20230705新加
                                                          when  a.summ_name like '%受让存单%'       then '9'          --20231115新加
                                                          when  a.summ_name like '%按址汇出%'       then '9'          --20231115新加
                                                          when  a.summ_name like '%房屋资金%'       then '9'          --20231115新加
                                                          when  a.summ_name like '%培训费%'       then '6'          --20231115新加
                                                          when  a.summ_name like '%保证金%'       then '6'          --20240522新加
                                                          when  a.summ_name like '%工会费%'       then '6'          --20240522新加
                                                          when  a.summ_name like '%服务费%'       then '6'          --20240522新加
                                                          when  a.summ_name like '%捐款%'       then '9'          --20240522新加
                                                          when  a.summ_name like '%财政收款%'       then '6'          --20240522新加
                                                          when  a.summ_name like '%融资租赁%'       then '6'          --20240522新加
                                                          when  a.summ_name like '%万联代收%'       then '6'          --20240522新加
                                                          when  a.summ_name like '%公交卡%'       then '4'          --20240724新加
                                                          when  a.summ_name like '%汇兑汇出%'       then '9'          --20240724新加
                                                          when  a.summ_name like '%热力费%'       then '6'          --20240929新加
                                                          when  a.summ_name like '%便民服务%'       then '6'          --20241008新加
                                                          when  a.summ_name like '%卷烟进货%'       then '1'          --20241008新加
                                                          when  a.summ_name like '%代收社保%'       then '6'          --20241008新加
                                                          when  a.summ_name like '%保费代收%'       then '6'          --20241008新加
                                                          when  a.summ_name like '%国库缴税%'       then '6'          --20241008新加
                                                          when  a.summ_name like '%欠费补扣%'       then '9'          --20241008新加
                                                          when  a.summ_name like '%汽车分期%'       then '1'          --20241008新加
                                                          when  a.summ_name like '%社保税银%'       then '6'          --20241008新加
                                                          when  a.summ_name like '%通存通兑%'       then '9'          --20241008新加
                                                          when  a.summ_name like '%汽车租金%'       then '6'          --20241211新加
                                                          when  a.summ_name like '%ACS充值%'       then '9'          --20241211新加
                                                          when  a.summ_name like '%大病保险%'       then '6'          --20241211新加
                                                          when  a.summ_name like '%购房验资%'       then '9'          --20250625新加 
                                                          when  a.summ_name like '%缴存退回%'       then '9'          --20250625新加 
                                                          when  a.summ_name like '%主动积存%'       then '6'          --20250625新加 
                                                          when  a.summ_name like '%基本医疗%'       then '6'          --20250625新加 
                                                          when  a.summ_name like '%养老保险%'       then '6'          --20250625新加 
                                                          when  a.summ_name like '%保管箱%'         then '6'          --新加/*modify by qiuyelong 20251022*/
                                                          when  a.summ_name like '%还信用卡%'       then '9'          --新加/*modify by qiuyelong 20251022*/
                                                    END)
ELSE A.G0305 END AS g0305                
,a.g0306                
,a.remark               
,a.data_source          
,a.bank_id              
,a.pers_inner_accno     
,a.summ_name            
,a.cert_type            
,a.global_busi_track_no 
,a.subtx_no   
,A.mer_type_no   
,a.medium_no    
,a.cert_no   
,a.ibank_flag
,a.dmst_ovsea_flag_code
from RA03.CTB_CREDIT_G03_temp_{DATA_DT} a ;



--处理外国人永久居留证及转换金额为负的收支类型及交易类型
DROP TABLE IF EXISTS RA03.CTB_CREDIT_G03_temp_type_{DATA_DT};
CREATE TABLE IF NOT EXISTS RA03.CTB_CREDIT_G03_temp_type_{DATA_DT} as  
select 
 actiontype 
,actiondesc 
,snocode    
,objcode    
,buocmonth  
,g0301      
,case when nvl(b.cd_value1,'')='' then 'ZZZ'
--    when substr(G0302,1,3) rlike '[\0-9]' then 'ZZZ'
      else G0302 
 end g0302      
,g0303      
,CASE WHEN G0306<0 and g0304='1' then '2'
      WHEN G0306<0 and g0304='2' then '1'
 else g0304 end g0304      
,CASE WHEN G0306<0 and g0304='1' then '9'
      WHEN G0306<0 and g0304='2' then '12'
 else g0305 end g0305      
,CASE WHEN G0306<0  then -g0306 else g0306 end g0306      
,remark     
,data_source
,bank_id   
,a.pers_inner_accno 
,a.summ_name
,a.cert_type
,a.global_busi_track_no 
,a.subtx_no
,A.mer_type_no
,a.medium_no
,a.cert_no
,a.ibank_flag
,a.dmst_ovsea_flag_code
from RA03.CTB_CREDIT_G03_temp_dont_overwrite_{DATA_DT} a 
left join (select distinct cd_value1 from ra03.wgj_send_country b )b                       --外管局码表
on a.G0302=b.cd_value1
;


--20230628提出，20230703新加（对于支出，并且境外标志是1，支出类别赋值为10）
DROP TABLE IF EXISTS RA03.CTB_CREDIT_G03_temp_type_new_{DATA_DT};
CREATE TABLE IF NOT EXISTS RA03.CTB_CREDIT_G03_temp_type_new_{DATA_DT} as
select 
actiontype          
,actiondesc          
,snocode             
,objcode             
,buocmonth           
,case when (G0305='10' or G0305='13') and g0301='7' then '8'--202312外管局提出问题
 else g0301
 end g0301               --20240228 增加报表逻辑修改，交易类型字段为10-境外支出或13-境外收入且银行卡清算渠道字段为7-本行清算的交易，若存在此类数据则统一将银行卡清算渠道字段改为8-其他    
,g0302               
,g0303               
,g0304               
,case when g0304='2' and dmst_ovsea_flag_code='1'  and summ_name<>'费用'  then '10' else g0305 end g0305         --20230705 外管局提出问题，只要是境外支出，摘要不是费用，所有跨境归为10-境外支出归为10-境外支出
,g0306               
,remark              
,data_source         
,bank_id             
,pers_inner_accno    
,summ_name           
,cert_type           
,global_busi_track_no
,subtx_no            
,mer_type_no         
,medium_no           
,cert_no             
from RA03.CTB_CREDIT_G03_temp_type_{DATA_DT};






--监管调阅所需表，放的明细
DROP TABLE IF EXISTS RA03.CTB_CREDIT_G03_morning_{DATA_DT};
CREATE TABLE IF NOT EXISTS RA03.CTB_CREDIT_G03_morning_{DATA_DT} as  
select 
ACTIONTYPE  
,ACTIONDESC 
,SNOCODE    
,OBJCODE    
,BUOCMONTH  
,G0301      
,G0302      
,G0303      
,G0304      
,G0305      
,G0306      
,REMARK     
,data_source
,bank_id    
,a.medium_no
,a.cert_type
,a.cert_no
from  RA03.CTB_CREDIT_G03_temp_type_new_{DATA_DT} a  
where G0305 in ('0','1','2','3','4','5','6','7','8','9','10','11','12','13') and g0302<>'ZZZ';

--对借记卡金额独立进行求和存储 20240724新增
DROP TABLE IF EXISTS RA03.CTB_CREDIT_G03_jjk_sumg0306_{DATA_DT};
CREATE TABLE IF NOT EXISTS RA03.CTB_CREDIT_G03_jjk_sumg0306_{DATA_DT} as  
select 
 g0301
,g0302
,g0303
,g0304
,g0305
,sum(g0306) G0306
from RA03.CTB_CREDIT_G03_temp_type_new_{DATA_DT} a 
where g0305  in ('0','1','2','3','4','5','6','7','8','9','10','11','12','13') 
and G0306<>0                                       --20230607  morning私聊加的
and g0302 NOT IN ('ZZZ','BVT','UMI','PCN','IOT','SGS','ATA','HMD','ATF')  --20240506  需求单要求新增四个无人区
group by  
 g0301
,g0302
,g0303
,g0304
,g0305;



--开始信用卡的加工逻辑
DROP TABLE IF EXISTS ra03.cs_6100_2024_0411_1;
CREATE TABLE IF NOT EXISTS ra03.cs_6100_2024_0411_1 AS 
SELECT t1.card_no          AS card_nbr  --卡号
      ,t2.personal_cert_no AS custr_nbr --客户证件号码
      ,t2.per_cert_tp_cd   AS race_code --证件类型
      ,ct.cd_value1        AS nation_cd --国家英文代码
FROM rbdb.ice_ngc_ngcc_card         t1 --卡片资料表
INNER JOIN rbdb.ice_ngc_ngcc_custr  t2 --客户基本资料 
        ON t1.cust_no = t2.cust_no
       AND t2.per_cert_tp_cd in ('1070'--港澳居民往来内地通行证
                                ,'1080'--台湾居民往来内地通行证
                                ,'1051'--外籍人士护照
                                ,'1181'--港澳居民居住证
                                ,'1182'--台湾居民居住证
                                ,'1181'--香港居民居住证
                                ,'1181'--澳门居民居住证
                                ,'1140'--香港身份证
                                )
LEFT JOIN rbdb.ncf_ppers001db_sp01_cust_info ci
       ON t2.cust_no = ci.ecif_cust_no
      AND ci.start_dt <= '{DATA_DT}'
      AND ci.end_dt > '{DATA_DT}'
LEFT JOIN ra03.wgj_standard_county_hs ct
       ON ci.natnl_regn_cd = ct.cd_value2
WHERE t1.start_dt <='{DATA_DT}' AND t1.end_dt>'{DATA_DT}'
  AND t2.start_dt <='{DATA_DT}' AND t2.end_dt>'{DATA_DT}'
;

DROP TABLE IF EXISTS ra03.cs_6100_2024_0411_4;
CREATE TABLE IF NOT EXISTS ra03.cs_6100_2024_0411_4 AS 
SELECT t0.custr_nbr
      ,t0.race_code
      ,t0.nation_cd
      ,t1.card_no                                          AS card_nbr   --卡号
      ,t1.dmst_ovsea_flag_code                             AS osflag     --境内外标识
      ,t1.tx_type_no                                       AS trans_type --交易类型
      ,t1.crcard_card_tp_no                                AS card_plan  --卡片类型
      ,CAST(LPAD(t1.tx_curr_cd,3,'0') AS VARCHAR(3))       AS currncy_cd
      ,t1.crcard_mer_categ_no                              AS mer_cat_cd --商户类别
      ,CASE WHEN t1.crcard_dc_dirc_cd = 'C' then -CAST(ROUND(t1.tx_amt,2) AS DECIMAL(22,2))
            ELSE CAST(ROUND(t1.tx_amt,2) AS DECIMAL(22,2))
       END                                                AS cal_amt
      ,SUBSTR(t1.create_stamp,1,8)                        AS inp_date    --交易记录日期
      ,CASE WHEN t1.crcard_dc_dirc_cd = 'C' then -t1.inacc_amt            
            ELSE t1.inacc_amt
       END                                                AS bill_amt    --交易金额
      ,t1.crcard_mng_accno                                AS acctnbr     --账号
      ,t1.mer_seq_no                                      AS merch_seq   --商户序号
      ,TRIM(t1.crcard_tx_src_cd)                          AS trans_src   --交易来源
      ,t1.crcard_acq_mer_no                               AS merchant    --收单商户代码
      ,t1.MASTER_CARD_POS_DATA                            As mcpos_data  --万事达卡POS数据
      ,CAST('EVENT' AS VARCHAR(8))                        AS src
FROM ra03.cs_6100_2024_0411_1 t0 
INNER JOIN rbdb.ngc_ngcc_transaction_detail t1 --已入账交易流水表
        ON t0.card_nbr = t1.card_no 
       AND t1.tx_type_no <> '8130'
WHERE SUBSTR(t1.create_stamp,1,8) >= '{CUR_MONTH_FIRST}'
  AND SUBSTR(t1.create_stamp,1,8) <= '{DATA_DT}'
  AND t1.etl_load_date >= '{CUR_MONTH_FIRST}'
  AND t1.etl_load_date <= '{DATA_DT}'
;

INSERT INTO ra03.cs_6100_2024_0411_4 
SELECT t0.custr_nbr
      ,t0.race_code
      ,t0.nation_cd
      ,t1.card_no                                       AS card_nbr      --卡号
      ,0                                                AS osflag
      ,t1.tx_type_no                                    AS trans_type    --交易类型
      ,t1.crcard_card_tp_no                             AS card_plan     --卡片类型
      ,CAST(LPAD(t1.inacc_curr_cd,3,'0') AS VARCHAR(3)) AS currncy_cd    --交易币种
      ,t1.crcard_mer_categ_no                           AS mer_cat_cd    --商户类别
      ,CASE WHEN t1.crcard_dc_dirc_cd = 'C' then -t1.inacc_amt
            ELSE t1.inacc_amt
       END                                           AS cal_amt
      ,SUBSTR(t1.create_stamp,1,8)                   AS inp_date    --交易记录日期
      ,CASE WHEN t1.crcard_dc_dirc_cd = 'C' then -t1.inacc_amt
            ELSE t1.inacc_amt
       END                                           AS bill_amt
      ,t1.crcard_mng_accno                           AS acctnbr          --账号
      ,t1.mer_seq_no                                 AS merch_seq        --商户序号
      ,TRIM(t1.crcard_tx_src_cd)                     AS trans_src        --交易来源
      ,t1.crcard_acq_mer_no                          AS merchant         --收单商户代码
      ,''                                            AS mcpos_data
      ,CAST('MPTR' AS VARCHAR(8))                    AS src
FROM ra03.cs_6100_2024_0411_1 t0 
INNER JOIN rbdb.ngc_ngcc_transaction_detail t1--已入账交易流水表
        ON t0.card_nbr = t1.card_no
       AND t1.tx_type_no = '8130'
INNER JOIN rbdb.ngc_ngcc_trantype_father t2   --交易类型分类参数表 
        ON t1.tx_type_no = t2.tx_type_no
       AND t2.crcard_tx_statis_lvl1_tp_no = '40001'
WHERE SUBSTR(t1.create_stamp,1,8) >= '{CUR_MONTH_FIRST}'
  AND SUBSTR(t1.create_stamp,1,8) <= '{DATA_DT}'
  AND t1.etl_load_date >= '{CUR_MONTH_FIRST}'
  AND t1.etl_load_date <= '{DATA_DT}'
  AND t2.start_dt <= '{DATA_DT}'
  AND t2.end_dt > '{DATA_DT}'
;

DROP TABLE IF EXISTS ra03.cs_6100_2024_0411_2_pre;
CREATE TABLE IF NOT EXISTS ra03.cs_6100_2024_0411_2_pre AS 
SELECT ROW_NUMBER() OVER(PARTITION BY 1 ORDER BY 1) AS rid
      ,t1.custr_nbr 
      ,t1.race_code 
      ,t1.nation_cd 
      ,t1.card_nbr  
      ,t1.osflag    
      ,t1.trans_type
      ,t1.card_plan 
      ,t1.currncy_cd
      ,t1.mer_cat_cd
      ,t1.cal_amt   
      ,t1.inp_date  
      ,t1.bill_amt  
      ,t1.acctnbr   
      ,t1.merch_seq 
      ,t1.trans_src 
      ,t1.merchant  
      ,t1.mcpos_data
      ,t1.src  
      ,CASE WHEN (t1.osflag = 1 OR (t1.trans_src = 'INTERIN' AND t1.currncy_cd <> '156')) AND t4.crcard_tx_statis_lvl1_tp_no = '30001' THEN 1
            WHEN t1.osflag = 0 AND t1.currncy_cd = '156' AND SUBSTRING(t1.mcpos_data,9,8) NOT IN ('00010344','00010446') AND (t4.crcard_tx_statis_lvl1_tp_no in ('10001','30001','50001','60001','90001') OR t4.crcard_tx_statis_lvl2_tp_no='200011') THEN 2
            WHEN t4.crcard_tx_statis_lvl1_tp_no = '40001' THEN 3
            ELSE 0
       END                                                                                                            AS trantype
      ,SUBSTR('{DATA_DT}',1,6)                                                                                        AS yyyymm
      ,CASE WHEN t1.race_code IN ('1080','1182') THEN 'TWN'
            WHEN t1.race_code IN ('1070','1181') THEN
                 CASE WHEN NVL(t1.nation_cd,'') IN ('HKG','MAC') THEN NVL(t1.nation_cd,'')
                      ELSE CASE WHEN SUBSTR(t1.custr_nbr,1,1) = 'H' OR SUBSTR(t1.custr_nbr,1,2) = '81' THEN 'HKG'
                                WHEN SUBSTR(t1.custr_nbr,1,1) = 'M' OR SUBSTR(t1.custr_nbr,1,2) = '82' THEN 'MAC'
                                ELSE CASE WHEN NVL(t1.nation_cd,'') IN ('','CHN') THEN 'ZZZ'
                                          ELSE t1.nation_cd
                                     END
                           END
                 END
            ELSE CASE WHEN NVL(t1.nation_cd,'') IN ('','CHN') THEN 'ZZZ'
                      ELSE t1.nation_cd
                 END
       END                                                                                                            AS G0302
      ,NVL(t3.var_a1,'NUL')                                                                                           AS G0303
      ,CASE WHEN t1.cal_amt > 0 THEN 2 ELSE 1 END                                                                     AS G0304
      ,CASE WHEN t1.cal_amt <= 0 THEN 12
            WHEN t1.cal_amt > 0 THEN CASE WHEN t1.osflag = 1 THEN 10 
                                          WHEN NVL(t2.req,'') <> '' THEN t2.req  --用新增mcc码表辅助赋值/*modify by qiuyelong 20250827*/
                                          ELSE NVL(mccadd.req,6)
                                     END
            ELSE 6
       END                                                                                                            AS G0305
      ,ABS(t1.cal_amt)                                                                                                AS G0306
      ,ABS(t1.bill_amt)                                                                                               AS billamt
FROM ra03.cs_6100_2024_0411_4          t1
LEFT JOIN ra03.t_cs_6100_2015_0453_mcc t2
       ON t1.mer_cat_cd = CAST(t2.mer_cat_cd AS DECIMAL(4,0))
LEFT JOIN ra03.t_code_g03_mcc_14add mccadd                           --新增mcc码表/*modify by qiuyelong 20250827*/
       ON t1.mer_cat_cd = CAST(mccadd.mer_cat_cd AS DECIMAL(4,0))
LEFT JOIN ra03.t_cs_6100_2017_0642_curr t3
       ON t1.currncy_cd = t3.code_value     
LEFT JOIN rbdb.ngc_ngcc_trantype_father t4 --交易类型分类参数表
       ON t1.trans_type = t4.tx_type_no
WHERE t1.cal_amt <> 0
  AND t4.start_dt <= '{DATA_DT}'
  AND t4.end_dt > '{DATA_DT}'
;

DROP TABLE IF EXISTS ra03.cs_6100_2024_0411_2;
CREATE TABLE IF NOT EXISTS ra03.cs_6100_2024_0411_2 AS 
SELECT rid
      ,custr_nbr 
      ,race_code 
      ,nation_cd 
      ,card_nbr  
      ,osflag    
      ,trans_type
      ,card_plan 
      ,currncy_cd
      ,mer_cat_cd
      ,cal_amt   
      ,inp_date  
      ,bill_amt  
      ,acctnbr   
      ,merch_seq 
      ,trans_src 
      ,merchant  
      ,mcpos_data
      ,src  
      ,trantype
      ,yyyymm
      ,G0302
      ,G0303
      ,G0304
      ,G0305
      ,G0306
      ,billamt
FROM ra03.cs_6100_2024_0411_2_pre
WHERE trantype <> 0
;

DROP TABLE IF EXISTS ra03.cs_6100_2024_0411_3_pre;
CREATE TABLE IF NOT EXISTS ra03.cs_6100_2024_0411_3_pre AS 
SELECT t1.rid       
      ,t1.custr_nbr 
      ,t1.race_code 
      ,t1.nation_cd 
      ,t1.card_nbr  
      ,t1.osflag    
      ,t1.trans_type
      ,t1.card_plan 
      ,t1.currncy_cd
      ,t1.mer_cat_cd
      ,t1.cal_amt   
      ,t1.inp_date  
      ,t1.bill_amt  
      ,t1.acctnbr   
      ,t1.merch_seq 
      ,t1.trans_src 
      ,t1.merchant  
      ,t1.mcpos_data
      ,t1.src       
      ,t1.trantype  
      ,t1.yyyymm    
      ,t1.g0302     
      ,t1.g0303     
      ,t1.g0304     
      ,t1.g0305     
      ,t1.g0306     
      ,t1.billamt   
      ,NVL(t2.instal_tp_cd,'')                                                                                                                                    AS mp_types
      ,CASE WHEN NVL(t2.instal_tp_cd,'') IN ('Y','B','A','D') OR (NVL(t2.instal_tp_cd,'') = 'L' AND SUBSTRING(NVL(t2.instal_prodt_no,''),1,3) = '979') THEN 1 
            ELSE 0 
       END                                                                                                                                                   AS mp_flag
      ,CASE WHEN t1.trantype = 3 THEN CASE WHEN NVL(t2.instal_tp_cd,'') = 'H' THEN 1 ELSE 7 END
            WHEN t1.trantype <> 3 THEN 
                 CASE WHEN t1.trans_src IN ('CUPIO','CUPPROCE') THEN 1
                      WHEN t1.trans_src = 'INTERIN' AND t1.card_plan = 'V' THEN 2
                      WHEN t1.trans_src = 'INTERIN' AND t1.card_plan = 'M' THEN 3
                      WHEN t1.trans_src = 'INTERIN' AND t1.card_plan = 'A' THEN 4
                      WHEN t1.trans_src = 'INTERIN' AND t1.card_plan = 'J' THEN 6
                      WHEN t1.trans_src IN ('MBKIO','CADJT','CADJ1','CADVC','PURJT','MBKERR','DFERR-OR','DFERR') AND SUBSTR(t1.merchant,1,3)<>'DSF' THEN 7
                      ELSE 8
                 END
            ELSE 8
       END                                                                                                                                                   AS G0301
FROM ra03.cs_6100_2024_0411_2 t1
LEFT JOIN rbdb.ice_ngc_ngcc_inst_order t2
       ON t1.acctnbr = t2.crcard_mng_accno
      AND t1.merch_seq = t2.itlm_order_no
      AND t2.start_dt <= '{DATA_DT}'
      AND t2.end_dt > '{DATA_DT}'
;

DROP TABLE IF EXISTS ra03.cs_6100_2024_0411_3;
CREATE TABLE IF NOT EXISTS ra03.cs_6100_2024_0411_3 AS 
SELECT rid       
      ,custr_nbr 
      ,race_code 
      ,nation_cd 
      ,card_nbr  
      ,osflag    
      ,trans_type
      ,card_plan 
      ,currncy_cd
      ,mer_cat_cd
      ,cal_amt   
      ,inp_date  
      ,bill_amt  
      ,acctnbr   
      ,merch_seq 
      ,trans_src 
      ,merchant  
      ,mcpos_data
      ,src       
      ,trantype  
      ,yyyymm    
      ,g0302     
      ,g0303     
      ,g0304     
      ,g0305     
      ,g0306     
      ,billamt   
      ,mp_types
      ,mp_flag
      ,G0301
FROM ra03.cs_6100_2024_0411_3_pre  
WHERE !(trantype = 3 AND mp_flag <> 0)   
;

CREATE TABLE IF NOT EXISTS ra03.cs_6100_2024_0411_g03_his(
     rid             int               COMMENT 'RID'
    ,custr_nbr       varchar(19)       COMMENT '客户证件号码'
    ,race_code       varchar(2)        COMMENT '证件类型'
    ,nation_cd       varchar(3)        COMMENT '国籍代码'
    ,card_nbr        varchar(19)       COMMENT '卡号'
    ,osflag          decimal(1,0)      COMMENT '境内外标识'
    ,trans_type      string            COMMENT '交易类型'
    ,card_plan       varchar(1)        COMMENT '卡片类型'
    ,currncy_cd      varchar(3)        COMMENT '原始货币'
    ,mer_cat_cd      string            COMMENT '商户类别'
    ,cal_amt         decimal(22,2)     COMMENT '原始币种金额'
    ,inp_date        string            COMMENT '交易记录日期'
    ,bill_amt        decimal(11,2)     COMMENT '交易金额'
    ,acctnbr         string            COMMENT '账号'
    ,merch_seq       string            COMMENT '商户序号'
    ,trans_src       string            COMMENT '交易来源'
    ,merchant        varchar(15)       COMMENT '收单商户代码'
    ,mcpos_data      varchar(26)       COMMENT '万事达卡POS数据'
    ,src             varchar(8)        COMMENT '源表'
    ,trantype        int               COMMENT '交易种类'
    ,yyyymm          string            COMMENT '报告期'
    ,g0302           string            COMMENT '持卡人所属国家/地区'
    ,g0303           string            COMMENT '持卡人所属国家/地区'
    ,g0304           int               COMMENT '交易原币'
    ,g0305           int               COMMENT '交易类型'
    ,g0306           decimal(22,2)     COMMENT '交易类型'
    ,billamt         decimal(11,2)     COMMENT '交易金额'
    ,mp_types        string            COMMENT '分期付款类型'
    ,mp_flag         int               COMMENT '分期标志'
    ,g0301           int               COMMENT '银行卡清算渠道'
) COMMENT 'G03非居民持有境内银行卡的收入支出信用卡明细表'
PARTITIONED BY (DATA_DT STRING)
;

ALTER TABLE ra03.cs_6100_2024_0411_g03_his DROP IF EXISTS PARTITION(DATA_DT='{DATA_DT}');
INSERT INTO ra03.cs_6100_2024_0411_g03_his PARTITION (DATA_DT='{DATA_DT}')
SELECT rid       
      ,custr_nbr 
      ,race_code 
      ,nation_cd 
      ,card_nbr  
      ,osflag    
      ,trans_type
      ,card_plan 
      ,currncy_cd
      ,mer_cat_cd
      ,cal_amt   
      ,inp_date  
      ,bill_amt  
      ,acctnbr   
      ,merch_seq 
      ,trans_src 
      ,merchant  
      ,mcpos_data
      ,src       
      ,trantype  
      ,yyyymm    
      ,g0302     
      ,g0303     
      ,g0304     
      ,g0305     
      ,g0306     
      ,billamt   
      ,mp_types  
      ,mp_flag   
      ,g0301     
FROM ra03.cs_6100_2024_0411_3
;


DROP TABLE IF EXISTS ra03.cs_6100_2024_0411_res2_pre;
CREATE TABLE IF NOT EXISTS ra03.cs_6100_2024_0411_res2_pre AS 
SELECT CAST('A' AS VARCHAR(1))               AS c01
      ,CAST('' AS VARCHAR(128))              AS c02
      ,CAST('' AS VARCHAR(36))               AS c03
      ,CAST('110000013000' AS VARCHAR(18))   AS c04
      ,CAST(yyyymm AS VARCHAR(6))            AS c05
      ,CAST(g0301 AS DECIMAL(2,0))           AS c06
      ,CAST(g0302 AS VARCHAR(3))             AS c07
      ,CAST(G0303 AS VARCHAR(3))             AS c08
      ,CAST(G0304 AS DECIMAL(2,0))           AS c09
      ,CAST(G0305 AS DECIMAL(2,0))           AS c10
      ,CAST(G0306 AS DECIMAL(22,2))          AS c11
      ,CAST('' AS VARCHAR(512))              AS c12
      ,CAST(bill_amt AS DECIMAL(22,2))       AS c13
FROM ra03.cs_6100_2024_0411_3
;

DROP TABLE IF EXISTS ra03.cs_6100_2024_0411_res2;
CREATE TABLE IF NOT EXISTS ra03.cs_6100_2024_0411_res2 AS 
SELECT c01                                 AS c01
      ,c02                                 AS c02
      ,c03                                 AS c03
      ,c04                                 AS c04
      ,c05                                 AS c05
      ,c06                                 AS c06
      ,c07                                 AS c07
      ,c08                                 AS c08
      ,c09                                 AS c09
      ,c10                                 AS c10
      ,CAST(SUM(c11) AS DECIMAL(22,2))     AS c11
      ,c12                                 AS c12
      ,CAST(SUM(c13) AS DECIMAL(22,2))     AS c13
FROM ra03.cs_6100_2024_0411_res2_pre
GROUP BY C01,C02,C03,C04,C05,C06,C07,C08,C09,C10,C12
ORDER BY C01,C02,C03,C04,C05,C06,C07,C08,C09,C10,C12
;

DROP TABLE IF EXISTS ra03.t_gjdg_jrzf_g03_xyk_tmp;
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
SELECT c06    AS g0301 
      ,c07    AS g0302 
      ,c08    AS g0303 
      ,c09    AS g0304 
      ,c10    AS g0305 
      ,c11    AS g0306 
      ,''     AS remark
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

ALTER TABLE ra03.t_gjdg_jrzf_g03_xyk_tmp_his DROP IF EXISTS PARTITION(DATA_DT='{DATA_DT}');
INSERT INTO ra03.t_gjdg_jrzf_g03_xyk_tmp_his PARTITION (DATA_DT='{DATA_DT}')
SELECT c06    AS g0301 
      ,c07    AS g0302 
      ,c08    AS g0303 
      ,c09    AS g0304 
      ,c10    AS g0305 
      ,c11    AS g0306 
      ,''     AS remark
FROM ra03.cs_6100_2024_0411_res2
;

DROP TABLE IF EXISTS ra03.t_gjdg_jrzf_g03_xyk_err_tmp;
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

insert into ra03.t_gjdg_jrzf_g03_xyk_err_tmp
SELECT  g0301  
       ,g0302  
       ,g0303  
       ,g0304  
       ,g0305  
       ,g0306  
       ,remark 
       ,'金额应大于0'  
FROM ra03.t_gjdg_jrzf_g03_xyk_tmp
WHERE g0306<=0
;

insert into ra03.t_gjdg_jrzf_g03_xyk_err_tmp
SELECT  g0301  
       ,g0302  
       ,g0303  
       ,g0304  
       ,g0305  
       ,g0306  
       ,remark 
       ,'币种应存在于外管局币种代码表中'  
FROM ra03.t_gjdg_jrzf_g03_xyk_tmp
WHERE g0303 NOT IN (SELECT var_a1 FROM ra03.T_CS_6100_2017_0642_CURR)
;

INSERT INTO RA03.CTB_CREDIT_G03_temp_type_new_{DATA_DT} 
SELECT 
 ''          
,''          
,''          
,''          
,''          
,g0301
,g0302               
,g0303               
,g0304               
,CAST(g0305 AS STRING) g0305  --防止P+中断/*modify by qiuyelong 20250827*/
,g0306               
,remark              
,'XYK'      data_source   
,'11005293' bank_id                
,''    
,''           
,''           
,''
,''            
,''         
,''         
,''         
FROM ra03.t_gjdg_jrzf_g03_xyk_tmp
;


--对金额进行求和
DROP TABLE IF EXISTS RA03.CTB_CREDIT_G03_sumg0306_{DATA_DT};
CREATE TABLE IF NOT EXISTS RA03.CTB_CREDIT_G03_sumg0306_{DATA_DT} as  
select 
 g0301
,g0302
,g0303
,g0304
,g0305
,sum(g0306) G0306
from RA03.CTB_CREDIT_G03_temp_type_new_{DATA_DT} a 
group by  
 g0301
,g0302
,g0303
,g0304
,g0305;

--去掉交易类型为汉字和国家地区代码是ZZZ的数据插入结果表
ALTER TABLE RA03.T_GJDG_JRZF_G03 DROP IF EXISTS PARTITION(DATA_DT='{DATA_DT}');
INSERT INTO RA03.T_GJDG_JRZF_G03 PARTITION (DATA_DT='{DATA_DT}')
select 
'A'  
,'' 
,concat('110000013000aaaaaa','G03aa',substr('{DATA_DT}',1,6),
                      lpad(row_number()
                           over(partition by 1 order by 1),
                           7,
                           0))                             --数据自编码
,'110000013000'                                               --申报主体代码
,substr('{DATA_DT}',1,6)                                    --报告期
,a.g0301
,a.g0302
,a.g0303
,a.g0304
,CAST(a.g0305 AS INT) AS g0305     --防止P+中断/*modify by qiuyelong 20250827*/
,a.g0306
,''
,'XHX'       data_source
,'11005293'  bank_id  
,'20200512630/20210715710'
,'牟宁/林先梅'
,'个人金融部/信用卡中心'
from RA03.CTB_CREDIT_G03_sumg0306_{DATA_DT} a where g0305  in ('0','1','2','3','4','5','6','7','8','9','10','11','12','13') 
and G0306<>0                                       --20230607  morning私聊加的
and g0302 NOT IN ('ZZZ','BVT','UMI','PCN','IOT','SGS','ATA','HMD','ATF')  --20240506  需求单要求新增四个无人区
;
