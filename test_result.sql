INSERT INTO TABLE rhbs_work.RHZF_GRKHJCXX_$TXDATE_TEMP
SELECT '9111000071093465XC'            AS JRJGDM   --金融机构代码
     , CASE
           WHEN SUBSTR(xd.KHZJLX,1,2)='@@'
           THEN xyk.KHZJLX
           ELSE xd.KHZJLX
       END
     , xd.KHZJDM                          --客户证件代码
     , CASE
           WHEN (xyk.GJ='' OR xyk.GJ IS NULL OR SUBSTR(xyk.GJ,1,2)='@@')
                   AND (xd.GJ<>'' AND xd.GJ IS NOT NULL AND SUBSTR(xd.GJ,1,2)<>'@@')
           THEN xd.GJ
           ELSE xyk.GJ
       END AS GJ  --国籍
     , xd.mz                           AS MZ   --民族
     , CASE
           WHEN (xyk.XB='' OR xyk.XB IS NULL OR SUBSTR(xyk.XB,1,2)='@@')
                   AND (xd.XB<>'' AND xd.XB IS NOT NULL AND SUBSTR(xyk.XB,1,2)<>'@@')
           THEN xd.XB
           ELSE xyk.XB
       END AS XB  --性别
     , CASE
           WHEN (xyk.ZGXL='' OR xyk.ZGXL IS NULL OR SUBSTR(xyk.ZGXL,1,2)='@@')
                   AND (xd.ZGXL<>'' AND xd.ZGXL IS NOT NULL AND SUBSTR(xyk.ZGXL,1,2)<>'@@')
           THEN xd.ZGXL
           ELSE xyk.ZGXL
       END AS ZGXL  --最高学历
     , xd.DQDM                            --地区代码
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
       END  --个人年收入
     , xd.JTNSR
     , CASE
           WHEN (xyk.HYQK='' OR xyk.HYQK IS NULL OR SUBSTR(xyk.HYQK,1,2)='@@')
                   AND (xd.HYQK<>'' AND xd.HYQK IS NOT NULL AND SUBSTR(xyk.HYQK,1,2)<>'@@')
           THEN xd.HYQK
           ELSE xyk.HYQK
       END AS HYQK  --婚姻情况
     , XD.SFGLF                           --是否关联方
     , NVL(xd.sxed,0)+NVL(xyk.sxed,0)     --授信额度
     , NVL(xd.yyed,0)+NVL(xyk.yyed,0)     --已用额度
     , ''                              AS GRKHSFBS   --个人客户身份标识  人行反馈暂时无需报送
     , ''                              AS GTGSHYYZZ   --个体工商户营业执照代码  人行反馈暂时无需报送
     , ''                              AS XWQYTYSHXYDM   --小微企业统一社会信用代码  人行反馈暂时无需报送
     , ''                              AS KHXYJBZDJS   --客户信用级别总等级数
     , ''                              AS KHXYPJ   --客户信用评级
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
     , ''                                 --测试
FROM rhbs_work.RHZF_GRKHJCXX_$TXDATE_XD xd
    JOIN rhbs_work.RHZF_GRKHJCXX_$TXDATE_XYK XYK
        ON xd.khzjdm=XYK.khzjdm
;