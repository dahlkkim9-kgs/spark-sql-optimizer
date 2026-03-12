# SQL 行跳转高亮功能实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 优化分析结果面板的行跳转功能，添加居中滚动、黄色高亮背景和闪烁动画效果

**Architecture:** 修改现有的 `LineNumberEditor` 组件，添加 `highlightLine` 状态，改进 `scrollToLine` 方法实现居中滚动和视觉反馈

**Tech Stack:** React (useState, useEffect, useRef), CSS animations

---

## Task 0: 验证当前状态

**Files:**
- Read: `frontend/src/AppSimple.tsx`

**Step 1: 确认现有跳转功能**

打开前端应用，点击分析结果中的"🔗 第 X 行"按钮，确认：
- 编辑器会滚动
- 但没有高亮效果

---

## Task 1: 添加高亮状态和定时器清理逻辑

**Files:**
- Modify: `frontend/src/AppSimple.tsx:28-33`

**Step 1: 在 LineNumberEditor 组件中添加 highlightLine 状态**

找到 `LineNumberEditor` 组件内的状态定义（约第 32 行），添加高亮状态：

```typescript
const LineNumberEditor = forwardRef<LineNumberEditorRef, { value: string; onChange: (val: string) => void; readOnly?: boolean }>(
  ({ value, onChange, readOnly = false }, ref) => {
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const linesRef = useRef<HTMLDivElement>(null);
    const [lineCount, setLineCount] = useState(1);
    const [highlightLine, setHighlightLine] = useState<number | null>(null);  // 新增
    const highlightTimeoutRef = useRef<NodeJS.Timeout | null>(null);  // 新增
```

**Step 2: 添加定时器清理逻辑**

在现有的 `useEffect` 之后（约第 37 行后）添加清理定时器的 effect：

```typescript
    // 清理高亮定时器
    useEffect(() => {
      return () => {
        if (highlightTimeoutRef.current) {
          clearTimeout(highlightTimeoutRef.current);
        }
      };
    }, []);
```

**Step 3: 提交更改**

```bash
cd frontend && git add src/AppSimple.tsx && git commit -m "feat: add highlightLine state to LineNumberEditor"
```

---

## Task 2: 改进 scrollToLine 方法

**Files:**
- Modify: `frontend/src/AppSimple.tsx:46-63`

**Step 1: 替换现有的 scrollToLine 实现**

找到 `useImperativeHandle` 中的 `scrollToLine` 方法（约第 46-63 行），完整替换为：

```typescript
    useImperativeHandle(ref, () => ({
      scrollToLine: (lineNumber: number) => {
        if (!textareaRef.current) return;

        // 清除之前的高亮定时器
        if (highlightTimeoutRef.current) {
          clearTimeout(highlightTimeoutRef.current);
        }

        // 计算目标行号（边界检查）
        const lines = value.split('\n');
        const targetLine = Math.max(1, Math.min(lineNumber, lines.length));

        // 计算居中位置
        const lineHeight = 21; // 14px * 1.5，与 CSS 一致
        const editorHeight = textareaRef.current.clientHeight;
        const targetLineTop = (targetLine - 1) * lineHeight;
        const scrollTop = Math.max(0, targetLineTop - editorHeight / 2 + lineHeight / 2);

        textareaRef.current.scrollTop = scrollTop;

        // 触发高亮效果
        setHighlightLine(targetLine);

        // 2 秒后清除高亮
        highlightTimeoutRef.current = setTimeout(() => {
          setHighlightLine(null);
        }, 2000);
      }
    }));
```

**Step 2: 提交更改**

```bash
cd frontend && git add src/AppSimple.tsx && git commit -m "feat: improve scrollToLine with center position and highlight"
```

---

## Task 3: 更新行号渲染添加高亮样式

**Files:**
- Modify: `frontend/src/AppSimple.tsx:66-89`

**Step 1: 修改行号渲染逻辑**

找到 `lineNumbers.map` 部分（约第 87-89 行），修改为：

```typescript
    return (
      <div style={{ position: 'relative', display: 'flex', height: '100%' }}>
        {/* 行号 */}
        <div
          ref={linesRef}
          style={{
            backgroundColor: '#2d2d2d',
            color: '#858585',
            padding: '15px 10px',
            textAlign: 'right',
            fontFamily: 'Consolas, Monaco, "Courier New", monospace',
            fontSize: '14px',
            lineHeight: '1.5',
            userSelect: 'none',
            minWidth: '40px',
            overflow: 'hidden',
            borderRight: '1px solid #3e3e3e'
          }}
        >
          {lineNumbers.map((num) => (
            <div
              key={num}
              className={num === highlightLine ? 'line-highlight' : ''}
              style={{ height: '21px' }}
            >
              {num}
            </div>
          ))}
        </div>
```

**Step 2: 提交更改**

```bash
cd frontend && git add src/AppSimple.tsx && git commit -m "feat: add conditional highlight class to line numbers"
```

---

## Task 4: 添加 CSS 高亮样式和动画

**Files:**
- Modify: `frontend/src/App.css`

**Step 1: 在 App.css 文件末尾添加高亮样式**

```css
/* Line Highlight Animation */
.line-highlight {
  background: linear-gradient(90deg, rgba(255, 230, 0, 0.4), rgba(255, 230, 0, 0.15));
  animation: highlight-pulse 3 0.3s ease-in-out;
  border-radius: 0 4px 4px 0;
  margin-left: -10px;
  padding-left: 10px;
}

@keyframes highlight-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
```

**Step 2: 提交更改**

```bash
cd frontend && git add src/App.css && git commit -m "feat: add line highlight animation styles"
```

---

## Task 5: 功能测试

**Files:**
- None (手动测试)

**Step 1: 启动前端开发服务器**

```bash
cd frontend && npm start
```

**Step 2: 测试跳转到第一行**

1. 在编辑器中粘贴一段多行 SQL
2. 点击"📊 分析SQL"按钮
3. 点击分析结果中指向第 1 行的"🔗 第 1 行"按钮
4. **验证**：第 1 行滚动到屏幕中央，背景闪烁 3 次并淡出

**Step 3: 测试跳转到中间行**

1. 点击分析结果中指向中间某行的按钮
2. **验证**：目标行在屏幕中央，高亮效果正常

**Step 4: 测试跳转到最后一行**

1. 点击分析结果中指向最后一行的按钮
2. **验证**：最后一行正确显示在可视区域底部附近

**Step 5: 测试连续跳转**

1. 快速连续点击不同的行号按钮
2. **验证**：高亮正确切换到最新点击的行，旧的高亮立即消失

**Step 6: 测试高亮自动消失**

1. 跳转到某一行后，等待 2 秒
2. **验证**：高亮在 2 秒后完全消失

---

## Task 6: 边界情况测试

**Step 1: 测试空内容**

1. 清空编辑器内容
2. 尝试跳转（不应该有按钮可点）
3. **验证**：不报错

**Step 2: 测试超出行号范围**

如果有测试 SQL，验证代码中的 `Math.max(1, Math.min(lineNumber, lines.length))` 确保不会跳到无效行号。

---

## Task 7: 最终提交和清理

**Step 1: 检查所有更改**

```bash
cd frontend && git diff
```

**Step 2: 最终提交**

```bash
cd frontend && git add -A && git commit -m "feat: complete line jump with highlight animation"
```

**Step 3: 推送到远程（如需要）**

```bash
git push
```

---

## 验收标准

- [ ] 点击"🔗 第 X 行"按钮后，目标行滚动到屏幕中央
- [ ] 目标行显示黄色半透明背景高亮
- [ ] 高亮闪烁 3 次（每次 300ms）
- [ ] 高亮在 2 秒后自动消失
- [ ] 连续点击时高亮正确切换
- [ ] 无控制台错误或警告
- [ ] 定时器正确清理，无内存泄漏

---

## 相关文档

- 设计文档: `docs/plans/2026-03-12-line-jump-highlight-design.md`
- 主文件: `frontend/src/AppSimple.tsx`
- 样式文件: `frontend/src/App.css`
