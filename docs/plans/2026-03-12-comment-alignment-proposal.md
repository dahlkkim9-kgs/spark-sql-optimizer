# SQL 行尾注释对齐优化方案

> **日期**: 2026-03-12
> **问题**: SQL 格式化后行尾注释显示杂乱无序

## 问题示例

```sql
-- 格式化前（原始SQL）
WHEN a.summ_name LIKE '%医保款%' THEN '6' --20230407新加
-- when  a.summ_name like '%公益款%'   then '6'
WHEN a.summ_name LIKE '%冲正%' THEN '9'
-- when  a.summ_name like '%取消%'     then '9'
-- when  a.summ_name like '%ETC%'      then '4' --20230407新加
WHEN a.summ_name LIKE '%储债认购%' THEN '6' --20230506新加

-- 格式化后（当前效果）
WHEN a.summ_name LIKE '%医保款%' THEN '6'       --20230407新加
-- when  a.summ_name like '%公益款%'   then '6'
WHEN a.summ_name LIKE '%冲正%' THEN '9'
                                                          -- when  a.summ_name like '%取消%'     then '9'
-- when  a.summ_name like '%ETC%'      then '4'      --20230407新加
WHEN a.summ_name LIKE '%储债认购%' THEN '6'             --20230506新加
```

### 问题点

1. **行尾注释列对齐不统一** - 注释分散在不同列位置
2. **独立注释行缩进混乱** - 有些缩进很深（如第4行）
3. **注释内容格式不统一** - 大小写、空格、风格不一致

## 优化方案

### 方案 A：代码块内注释对齐（推荐）

**思路**: 在同一个 WHEN/THEN 代码块内，将行尾注释对齐到同一列。

```sql
-- 优化后效果
WHEN a.summ_name LIKE '%医保款%' THEN '6'                      -- 20230407新加
-- WHEN a.summ_name LIKE '%公益款%' THEN '6'
WHEN a.summ_name LIKE '%冲正%' THEN '9'                         -- 冲正标识
-- WHEN a.summ_name LIKE '%取消%' THEN '9'
-- WHEN a.summ_name LIKE '%ETC%' THEN '4'                       -- 20230407新加
WHEN a.summ_name LIKE '%储债认购%' THEN '6'                     -- 20230506新加
```

**规则**:
1. 检测代码块边界（WHEN...THEN，SELECT 字段列表等）
2. 计算块内代码行的最大长度
3. 将行尾注释对齐到 `max_length + padding`（如 +4 空格）
4. 独立注释行保持与代码块相同的缩进

**优点**:
- 注释对齐美观
- 保留注释与代码的关联
- 不改变注释内容

**缺点**:
- 需要识别代码块边界
- 代码较长时注释可能对齐到很远的位置

### 方案 B：固定列对齐

**思路**: 所有行尾注释对齐到固定列（如第 60 列）。

```sql
-- 优化后效果（固定 60 列对齐）
WHEN a.summ_name LIKE '%医保款%' THEN '6'              -- 20230407新加
-- WHEN a.summ_name LIKE '%公益款%' THEN '6'
WHEN a.summ_name LIKE '%冲正%' THEN '9'                -- 冲正标识
-- WHEN a.summ_name LIKE '%取消%' THEN '9'
-- WHEN a.summ_name LIKE '%ETC%' THEN '4'               -- 20230407新加
WHEN a.summ_name LIKE '%储债认购%' THEN '6'            -- 20230506新加
```

**规则**:
1. 配置固定对齐列（如 60）
2. 行尾注释统一对齐到该列
3. 如果代码超过对齐列，注释放在代码后 + 固定间距

**优点**:
- 实现简单
- 对齐一致

**缺点**:
- 代码短时有很多空格
- 代码长时注释可能错位

### 方案 C：智能对齐（A + B 结合）

**思路**: 代码块内优先对齐，超出阈值时换行。

```sql
-- 优化后效果
WHEN a.summ_name LIKE '%医保款%' THEN '6'              -- 20230407新加
-- WHEN a.summ_name LIKE '%公益款%' THEN '6'
WHEN a.summ_name LIKE '%冲正%' THEN '9'                -- 冲正标识
-- WHEN a.summ_name LIKE '%取消%' THEN '9'
-- WHEN a.summ_name LIKE '%ETC%' THEN '4'               -- 20230407新加
WHEN a.summ_name LIKE '%储债认购%' THEN '6'            -- 20230506新加
```

**规则**:
1. 代码块内注释对齐到 `min(max_code_length + 4, fixed_column)`
2. 独立注释行保持合理缩进

### 方案 D：注释分类处理（最完善）

**思路**: 区分行尾注释和独立注释行，分别处理。

```sql
-- 优化后效果
-- 医保款类型
WHEN a.summ_name LIKE '%医保款%' THEN '6'              -- 20230407新加
-- 已废弃：公益款类型
-- WHEN a.summ_name LIKE '%公益款%' THEN '6'
WHEN a.summ_name LIKE '%冲正%' THEN '9'                -- 冲正标识
-- 已废弃：取消类型
-- WHEN a.summ_name LIKE '%取消%' THEN '9'
WHEN a.summ_name LIKE '%ETC%' THEN '4'                 -- 20230407新加
WHEN a.summ_name LIKE '%储债认购%' THEN '6'            -- 20230506新加
```

**规则**:
1. **行尾注释**: 对齐到代码块内最长的代码行 + 固定间距
2. **独立注释行**:
   - 纯注释行（说明文字）：保持与代码块相同的缩进
   - 注释掉的代码：可以统一缩进或"降级"处理

## 推荐实施方案

### 阶段 1: 方案 A（代码块内对齐）

**优先级**: 高
**工作量**: 中等

1. 添加 `_align_line_comments_in_block()` 函数
2. 识别代码块边界（WHEN/THEN，SELECT 字段列表等）
3. 计算块内最长代码行
4. 对齐行尾注释

### 阶段 2: 独立注释行处理

**优先级**: 中
**工作量**: 低

1. 规范化独立注释行的缩进
2. 可选：统一注释掉代码的大小写

### 阶段 3: 配置选项

**优先级**: 低
**工作量**: 低

1. 添加配置项：
   - `align_comments`: true/false
   - `comment_align_column`: 固定列（如 60）
   - `comment_padding`: 间距（如 4）

## 实施步骤

### Step 1: 创建测试用例

```python
# tests/test_comment_alignment.py
def test_case_when_comment_alignment():
    sql = """
    CASE
        WHEN a.summ_name LIKE '%医保款%' THEN '6' --20230407新加
        -- when  a.summ_name like '%公益款%'   then '6'
        WHEN a.summ_name LIKE '%冲正%' THEN '9'
    END
    """
    expected = """
    CASE
        WHEN a.summ_name LIKE '%医保款%' THEN '6'    -- 20230407新加
        -- WHEN a.summ_name LIKE '%公益款%' THEN '6'
        WHEN a.summ_name LIKE '%冲正%' THEN '9'
    END
    """
```

### Step 2: 实现对齐函数

```python
def _align_line_comments_in_block(sql: str) -> str:
    """
    对齐代码块内的行尾注释

    Args:
        sql: SQL 代码块

    Returns:
        对齐后的 SQL
    """
    lines = sql.split('\n')
    code_lines = []
    comment_lines = []

    # 分离代码行和纯注释行
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('--'):
            comment_lines.append(line)
        else:
            code_lines.append(line)

    # 计算代码部分的最大长度
    max_length = 0
    parsed_lines = []
    for line in code_lines:
        if '--' in line:
            code_part = line[:line.index('--')].rstrip()
            comment_part = line[line.index('--'):]
            max_length = max(max_length, len(code_part))
            parsed_lines.append((code_part, comment_part))
        else:
            parsed_lines.append((line, None))

    # 对齐注释
    aligned_lines = []
    for code_part, comment_part in parsed_lines:
        if comment_part is not None:
            aligned_lines.append(f"{code_part}{' ' * (max_length - len(code_part))}{comment_part}")
        else:
            aligned_lines.append(code_part)

    return '\n'.join(aligned_lines)
```

### Step 3: 集成到格式化流程

在 `_format_case_recursive()` 和其他格式化函数中调用对齐函数。

## 待确认问题

1. **对齐列位置**: 使用代码块内最长行 + 间距，还是固定列？
2. **独立注释行**: 是否需要处理注释掉的代码行？
3. **注释内容**: 是否需要规范化注释内容（大小写、空格）？
4. **配置选项**: 是否需要可配置的对齐规则？
