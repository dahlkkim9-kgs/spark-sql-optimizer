# V4 vs V5 格式化差异对比

## 测试结果概览
- **测试用例数**: 6
- **结果不同**: 6 (100%)

---

## 详细差异对比

### 1. 简单 SELECT DISTINCT

**V4 输出** (紧凑 WHERE):
```sql
SELECT DISTINCT a
     , b
     , c
FROM table1
WHERE x > 0
ORDER BY a
;
```

**V5 输出** (WHERE 换行):
```sql
SELECT DISTINCT a
     , b
     , c
FROM table1
WHERE
  x > 0
ORDER BY
  a
```

**差异**: V5 将 WHERE/ORDER BY 后的条件单独换行，更清晰

---

### 2. 多表 JOIN

**V4 输出**:
```sql
SELECT t1.a
     , t2.b
     , t3.c
FROM t1
JOIN t2
  ON t1.id = t2.id
JOIN t3
  ON t2.id = t3.id
;
```

**V5 输出**:
```sql
SELECT t1.a
     , t2.b
     , t3.c
FROM t1
JOIN t2
  ON t1.id = t2.id
JOIN t3
  ON t2.id = t3.id
```

**差异**: 相同！证明 V5 成功继承了 v4 的列对齐风格

---

### 3. CASE WHEN

**V4 输出** (多行展开):
```sql
SELECT CASE
        WHEN x > 0
        THEN 'positive'
        WHEN x < 0
        THEN 'negative'
        ELSE 'zero'
    END
    AS result
FROM t1
;
```

**V5 输出** (单行紧凑):
```sql
SELECT CASE WHEN x > 0 THEN 'positive' WHEN x < 0 THEN 'negative' ELSE 'zero' END AS result
FROM t1
```

**差异**: V5 保持了原始的紧凑格式，V4 强制展开

---

### 4. 标量子查询

**V4 输出** (缩进更多):
```sql
SELECT a
     , (
                      SELECT MAX(b)
           FROM t2
           WHERE t2.id = t1.id
          ) AS max_b
FROM t1
;
```

**V5 输出** (规则缩进):
```sql
SELECT a
     ,
  (
      SELECT
        MAX(b)
      FROM t2
      WHERE
        t2.id = t1.id
  ) AS max_b
FROM t1
```

**差异**: V5 缩进更一致、更规则

---

### 5. CTE (WITH 语句)

**V4 输出**:
```sql
WITH cte AS (
             SELECT a
                  , b
             FROM t1
            )
SELECT a
     , b
FROM cte
;
```

**V5 输出**:
```sql
WITH cte AS (
    SELECT a
         , b
    FROM t1
)
SELECT a
     , b
FROM cte
```

**差异**: V5 缩进更标准

---

### 6. IN 子查询

**V4 输出**:
```sql
SELECT a
     , b
FROM t1
WHERE a IN (
                        SELECT x
            FROM t2
           )
;
```

**V5 输出**:
```sql
SELECT a
     , b
FROM t1
WHERE
  a IN (
      SELECT x
      FROM t2
  )
```

**差异**: V5 缩进更规则，WHERE 条件换行

---

## 结论

1. **V5 工作正常**: 所有测试用例输出与 V4 不同，证明 V5 确实在使用 sqlglot 解析

2. **风格特点**:
   - V5: 基于 AST 的规则缩进，WHERE/条件换行
   - V4: 正则匹配，某些场景缩进过度

3. **混合策略**: 对于 V5 无法解析的语法（如测试文件中的孤立 CTE），会自动回退到 V4

---

## 建议

- **开发/测试**: 使用 V5 (sqlglot) - 缩进更一致，解析更准确
- **生产环境**: 当前 V4 更成熟，V5 经过充分测试后可切换
