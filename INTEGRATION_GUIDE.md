# SQL格式化器V2集成指南

## 概述

新的SQL格式化器(`formatter_v2.py`)已按照《大数据SQL开发规范》实现，提供以下功能：

### 规范符合性检查清单

| 规范要求 | 实现状态 | 说明 |
|---------|---------|------|
| SQL保留字大写 | ✅ 已实现 | SELECT, FROM, WHERE, INSERT等关键字大写 |
| 内置函数名大写 | ✅ 已实现 | NVL, TRIM, COUNT, SUM等函数大写 |
| 字段名/表名/别名小写 | ⚠️ 部分实现 | 可在调用时指定lower_tables选项 |
| 关键字另起一行左对齐 | ✅ 已实现 | SELECT, FROM, WHERE等关键字单独一行 |
| 逗号前置（左对齐） | ✅ 已实现 | 字段列表逗号在行首 |
| 4个空格缩进 | ✅ 已实现 | 统一使用4空格缩进 |
| WHERE条件AND右对齐 | ✅ 已实现 | AND与WHERE右对齐 |
| JOIN条件ON右对齐 | ✅ 已实现 | ON与JOIN右对齐，每个条件单独一行 |
| CASE WHEN格式化 | ✅ 已实现 | WHEN独立一行，CASE与END对齐 |
| 分号另起一行 | ✅ 已实现 | SQL结束时分号单独一行 |

## 集成步骤

### 方案A：直接替换（推荐）

修改 `analyzer.py` 中的 `format_sql` 方法，使用新的格式化器：

```python
# analyzer.py 顶部导入
from core.formatter_v2 import format_sql_v2

class StaticAnalyzer:
    # ... 其他代码 ...

    def format_sql(self, sql: str, **options) -> str:
        """
        格式化SQL语句（符合《大数据SQL开发规范》）

        Args:
            sql: 原始SQL语句
            **options: 格式化选项
                - keyword_case: 'upper'（规范要求）
                - indent: 4（规范要求）
                - comma_start: True（规范要求）
                - semicolon_newline: True（规范要求）

        Returns:
            格式化后的SQL字符串
        """
        # 使用新的V2格式化器
        format_options = {
            'keyword_case': options.get('keyword_case', 'upper'),
            'indent': options.get('indent', 4),
            'comma_start': options.get('comma_start', True),
            'semicolon_newline': options.get('semicolon_newline', True),
        }

        try:
            return format_sql_v2(sql, **format_options)
        except Exception as e:
            print(f"格式化失败: {e}")
            import traceback
            traceback.print_exc()
            return sql
```

### 方案B：保留旧版本，添加版本选择

在API中添加格式化器版本选项：

```python
# main.py 修改 FormatRequest 模型
class FormatRequest(BaseModel):
    sql: str
    keyword_case: Optional[str] = "upper"
    indent: Optional[int] = 4
    comma_start: Optional[bool] = True
    semicolon: Optional[bool] = False
    formatter_version: Optional[str] = "v2"  # 新增：v1或v2

# main.py 修改 /format 端点
@app.post("/format", response_model=FormatResult)
def format_sql(request: FormatRequest):
    """格式化SQL语句"""
    if request.formatter_version == "v2":
        from core.formatter_v2 import format_sql_v2
        formatted = format_sql_v2(
            request.sql,
            keyword_case=request.keyword_case,
            indent=request.indent,
            comma_start=request.comma_start,
            semicolon_newline=request.semicolon
        )
    else:
        formatted = analyzer.format_sql(
            request.sql,
            keyword_case=request.keyword_case,
            indent=request.indent,
            comma_start=request.comma_start,
            semicolon=request.semicolon
        )

    return {
        "original_sql": request.sql,
        "formatted_sql": formatted
    }
```

## 格式化示例

### 示例1：基本SELECT

**输入:**
```sql
select id, name, age from users where age > 18
```

**输出:**
```sql
SELECT
       id
     , name
     , age
FROM
      users
WHERE
      age > 18
;
```

### 示例2：JOIN多条件

**输入:**
```sql
SELECT a.id, b.name FROM table1 a LEFT JOIN table2 b ON a.id = b.id AND a.dt = b.dt WHERE a.dt = '2024-01-01'
```

**输出:**
```sql
SELECT
       a.id
     , b.name
FROM
      table1 a

      LEFT JOIN
      table2 b
       ON a.id = b.id
          AND a.dt = b.dt
WHERE
      a.dt = '2024-01-01'
;
```

### 示例3：复杂查询

**输入:**
```sql
INSERT OVERWRITE TABLE target_table
SELECT a.cust_id, a.cust_name, NVL(b.amount, 0) AS amount
FROM source_table a
LEFT JOIN trade_table b ON a.id = b.id AND a.dt = b.dt
WHERE a.dt = '${bizdate}' AND a.status = '1'
GROUP BY a.cust_id, a.cust_name
```

**输出:**
```sql
INSERT OVERWRITE TABLE target_table
SELECT
       a.cust_id
     , a.cust_name
     , NVL(b.amount, 0) AS amount
FROM
      source_table a

      LEFT JOIN
      trade_table b
       ON a.id = b.id
          AND a.dt = b.dt
WHERE
      a.dt = '${bizdate}'
     AND a.status = '1'
GROUP BY
         a.cust_id
       , a.cust_name
;
```

## 前端调整（可选）

如果需要在前端添加格式化选项，可以修改 `AppSimple.tsx`：

```typescript
// AppSimple.tsx
const formatSQL = async () => {
  // ...
  const response = await fetch('http://127.0.0.1:8888/format', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sql,
      keyword_case: 'upper',      // 规范要求
      indent: 4,                   // 规范要求
      comma_start: true,           // 逗号前置
      semicolon_newline: true,     // 分号另起一行
      formatter_version: 'v2'      // 使用V2格式化器
    })
  });
  // ...
};
```

## 测试验证

运行测试文件验证格式化器：

```bash
cd backend/core
python test_formatter_v2.py
```

预期输出应显示10个测试用例，所有格式化结果符合《大数据SQL开发规范》。

## 注意事项

1. **向后兼容**：旧格式化器(`formatter.py`)仍然保留，可以平滑迁移
2. **性能**：新格式化器使用正则表达式解析，性能与旧版本相当
3. **扩展性**：如需添加新的格式化规则，可在`formatter_v2.py`中扩展
4. **子查询**：复杂子查询的格式化可能需要进一步优化

## 后续改进建议

1. **完善子查询格式化**：当前对嵌套子查询的处理可以进一步优化
2. **添加更多函数**：FUNCTIONS集合可以继续扩展
3. **WITH子句支持**：添加对CTE（WITH子句）的格式化支持
4. **注释保留**：改进对SQL注释的保留和格式化
5. **配置选项**：提供更多可配置的格式化选项

## 联系方式

如有问题或建议，请通过以下方式反馈：
- 项目仓库：spark-sql-optimizer
- 文档位置：backend/core/formatter_v2.py
