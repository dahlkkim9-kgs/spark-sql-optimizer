-- 测试嵌套 CASE WHEN 格式化
SELECT
    id,
    CASE WHEN NVL(G0305,'')='' AND a.G0304='2' THEN (CASE WHEN a.summ_name like '%短信扣费%' THEN '6' WHEN a.summ_name like '%快捷支付%' THEN '1' WHEN a.summ_name like '%跨行汇出%' THEN '9' ELSE '0' END)
    ELSE A.G0305
    END AS g0305,
    CASE
        WHEN type = 'A' THEN
            (CASE
                WHEN subtype = 'A1' THEN 'Type A1'  -- 子类型A1
                WHEN subtype = 'A2' THEN 'Type A2'  -- 子类型A2
                ELSE 'Unknown A'  -- 未知A类型
            END)
        WHEN type = 'B' THEN 'Type B'  -- B类型
        ELSE 'Other'
    END AS type_desc
FROM table1;
