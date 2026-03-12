# SQL 行跳转高亮功能设计文档

**创建日期**: 2026-03-12
**项目**: Spark SQL 优化工具
**设计目标**: 优化分析结果面板的行跳转功能，添加视觉反馈

---

## 1. 概述

### 1.1 目标
优化现有的 SQL 行跳转功能，在用户点击分析结果中的"🔗 第 X 行"按钮时，提供清晰的视觉反馈：
- 目标行自动滚动到屏幕中央
- 黄色半透明背景高亮
- 3 次闪烁动画效果
- 2 秒后自动消失

### 1.2 设计原则
- **非侵入式**: 仅修改现有组件，不新增文件
- **轻量级**: 使用纯 CSS 动画，无外部依赖
- **用户友好**: 提供清晰的视觉反馈

---

## 2. 当前状态分析

### 2.1 现有实现

文件: `frontend/src/AppSimple.tsx`

**已有功能**:
- `LineNumberEditor` 组件暴露 `scrollToLine` 方法
- 分析结果面板有"🔗 第 X 行"按钮，可点击跳转

**存在问题**:
```typescript
// 第 46-63 行 - scrollToLine 实现不完整
scrollToLine: (lineNumber: number) => {
  // ...
  textareaRef.current.scrollTop = scrollTop;
  // 添加高亮效果
  const highlightId = `line-highlight-${Date.now()}`;  // ⚠️ 创建了但没使用
  const existingHighlight = textareaRef.current.parentElement?.querySelector('.line-highlight');
  if (existingHighlight) {
    existingHighlight.remove();  // ⚠️ 只删除了，没创建新的
  }
  // ❌ 代码结束，没有实际添加高亮
}
```

### 2.2 问题总结
| 问题 | 描述 |
|------|------|
| 高亮代码不完整 | 创建了 ID 但没有实际添加高亮元素 |
| 无视觉反馈 | 跳转后用户可能看不清跳到了哪一行 |
| 滚动位置不理想 | 滚动到顶部，目标行可能在屏幕边缘 |

---

## 3. 设计方案

### 3.1 效果预览

```
点击 "🔗 第 42 行"
    ↓
编辑器自动滚动，第 42 行显示在屏幕中央
    ↓
第 42 行背景变为黄色半透明，并闪烁 3 次
    ↓
2 秒后高亮淡出消失
```

### 3.2 技术实现

**组件状态扩展**:
```typescript
const [highlightLine, setHighlightLine] = useState<number | null>(null);
```

**scrollToLine 方法改进**:
```typescript
scrollToLine: (lineNumber: number) => {
  if (!textareaRef.current) return;

  // 1. 计算居中位置
  const lines = value.split('\n');
  const targetLine = Math.max(1, Math.min(lineNumber, lines.length));

  const lineHeight = 21; // 14px * 1.5
  const editorHeight = textareaRef.current.clientHeight;
  const targetLineTop = (targetLine - 1) * lineHeight;
  const scrollTop = Math.max(0, targetLineTop - editorHeight / 2 + lineHeight / 2);

  textareaRef.current.scrollTop = scrollTop;

  // 2. 触发高亮效果
  setHighlightLine(targetLine);

  // 3. 2 秒后清除高亮
  setTimeout(() => setHighlightLine(null), 2000);
}
```

**行号渲染改进**:
```typescript
{lineNumbers.map((num) => (
  <div
    key={num}
    className={num === highlightLine ? 'line-highlight' : ''}
    style={{ height: '21px' }}
  >
    {num}
  </div>
))}
```

**CSS 样式新增** (`App.css`):
```css
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

---

## 4. 修改文件清单

| 文件 | 修改内容 | 行数估算 |
|------|----------|----------|
| `frontend/src/AppSimple.tsx` | 添加 highlightLine 状态，修改 scrollToLine 和行号渲染 | ~20 行 |
| `frontend/src/App.css` | 新增 `.line-highlight` 样式和动画 | ~15 行 |

---

## 5. 测试计划

### 5.1 功能测试

| 测试场景 | 预期结果 |
|----------|----------|
| 点击跳转到第 1 行 | 第 1 行滚动到屏幕中央并高亮 |
| 点击跳转到中间行 | 目标行滚动到屏幕中央并高亮 |
| 点击跳转到最后一行 | 最后一行滚动到屏幕中央并高亮 |
| 连续点击多次 | 高亮正确切换到最新点击的行 |
| 高亮 2 秒后 | 高亮自动消失 |

### 5.2 边界测试

| 测试场景 | 预期结果 |
|----------|----------|
| 跳转行号 < 1 | 自动修正为第 1 行 |
| 跳转行号 > 最大行数 | 自动修正为最后一行 |
| 空内容跳转 | 不报错，无效果 |

### 5.3 视觉测试

- ✅ 高亮背景色清晰可见但不刺眼
- ✅ 闪烁动画流畅（3 次，每次 300ms）
- ✅ 高亮淡出自然

---

## 6. 实施计划

详细的实施计划将由 `writing-plans` 技能生成。

---

## 7. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 行高计算不准导致位置偏移 | 低 | 使用与 CSS 一致的常量 (14px * 1.5 = 21px) |
| 2 秒定时器未清理导致内存泄漏 | 低 | 使用 useEffect 清理定时器 |
| 动画性能问题 | 低 | 使用 CSS transform 和 opacity |

---

## 附录

### A. 动画时序图

```
0ms     ━━━ 点击按钮，触发高亮
        ━━━ 开始动画第 1 周期
150ms   ━━━ 第 1 次淡出 (opacity: 0.4)
300ms   ━━━ 第 1 次淡入 (opacity: 1)，开始第 2 周期
450ms   ━━━ 第 2 次淡出 (opacity: 0.4)
600ms   ━━━ 第 2 次淡入 (opacity: 1)，开始第 3 周期
750ms   ━━━ 第 3 次淡出 (opacity: 0.4)
900ms   ━━━ 第 3 次淡入 (opacity: 1)，动画结束
2000ms  ━━━ 高亮完全消失
```

### B. 颜色方案

| 元素 | 颜色 | 用途 |
|------|------|------|
| 高亮渐变起 | `rgba(255, 230, 0, 0.4)` | 左侧更明显的黄色 |
| 高亮渐变止 | `rgba(255, 230, 0, 0.15)` | 右侧较淡的黄色 |
| 行号背景 | `#2d2d2d` | 深灰色背景 |
| 行号文字 | `#858585` | 灰色文字 |
