--测试with AS

WITH A AS (SELECT aa,bb,cc FROM tab_tes WHERE aa='1' AND bb='2' OR (aa ='2' AND bb='2' AND cc='3'));

--测试CACHE TABLE

CACHE TABLE B AS (SELECT aa,bb,cc FROM tab_tes WHERE aa='1' AND bb='2' OR (aa ='2' AND bb='2' AND cc='3'));

--测试子查询是否正常格式化
CREATE table aaatab as  
select *
FROM (SELECT * FROM rhbs_work.RHZF_GRKHJCXX_$TXDATE_xd WHERE khzjdm NOT IN (SELECT DISTINCT khzjdm FROM rhbs_work.RHZF_GRKHJCXX_$TXDATE_XYK)) xd
    LEFT JOIN rhbs_work.rhzf_dkye_$TXDATE b
        ON xd.khzjdm=b.cust_no;
