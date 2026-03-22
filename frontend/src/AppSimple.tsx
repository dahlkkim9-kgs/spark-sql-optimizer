import React, { useState, useRef, useEffect, useImperativeHandle, forwardRef } from 'react';
import './App.css';
import { getFormatUrl, FORMATTER_VERSIONS, type FormatterVersion } from './config';

interface Issue {
  rule: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  message: string;
  line: number;
  suggestion: string;
}

interface AnalysisResult {
  file?: string;
  original_sql: string;
  optimized_sql: string;
  issues: Issue[];
  issue_count: number;
  high_priority: number;
  medium_priority: number;
  low_priority: number;
}

// 带行号的编辑器组件
interface LineNumberEditorRef {
  scrollToLine: (lineNumber: number) => void;
}

const LineNumberEditor = forwardRef<LineNumberEditorRef, { value: string; onChange: (val: string) => void; readOnly?: boolean }>(
  ({ value, onChange, readOnly = false }, ref) => {
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const linesRef = useRef<HTMLDivElement>(null);
    const editorContainerRef = useRef<HTMLDivElement>(null);
    const [lineCount, setLineCount] = useState(1);
    const [highlightLine, setHighlightLine] = useState<number | null>(null);
    const highlightTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
      const count = value.split('\n').length;
      setLineCount(count);
    }, [value]);

    // 清理高亮定时器
    useEffect(() => {
      return () => {
        if (highlightTimeoutRef.current) {
          clearTimeout(highlightTimeoutRef.current);
        }
      };
    }, []);

    const handleScroll = () => {
      if (textareaRef.current && linesRef.current) {
        linesRef.current.scrollTop = textareaRef.current.scrollTop;
      }
    };

    // 暴露scrollToLine方法给父组件
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

        // 将编辑器容器滚动到视口中央
        if (editorContainerRef.current) {
          editorContainerRef.current.scrollIntoView({
            behavior: 'smooth',
            block: 'center'
          });
        }

        // 触发高亮效果
        setHighlightLine(targetLine);

        // 3 秒后清除高亮（动画持续10次×0.3秒=3秒）
        highlightTimeoutRef.current = setTimeout(() => {
          setHighlightLine(null);
        }, 3000);
      }
    }));

    const lineNumbers = Array.from({ length: lineCount }, (_, i) => i + 1);

    return (
      <div ref={editorContainerRef} style={{ position: 'relative', display: 'flex', height: '100%' }}>
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
        {/* 文本编辑区 */}
        <div style={{ position: 'relative', flex: 1, height: '100%' }}>
          {/* 代码高亮覆盖层 */}
          {highlightLine !== null && (
            <div
              className="code-line-highlight"
              style={{
                position: 'absolute',
                left: '15px',
                right: '15px',
                top: `${(highlightLine - 1) * 21 + 15}px`,
                height: '21px',
                pointerEvents: 'none',
                zIndex: 10
              }}
            />
          )}
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onScroll={handleScroll}
            readOnly={readOnly}
            style={{
              width: '100%',
              height: '100%',
              minHeight: '200px',
              fontFamily: 'Consolas, Monaco, "Courier New", monospace',
              fontSize: '14px',
              lineHeight: '1.5',
              padding: '15px',
              border: 'none',
              resize: 'none',
              backgroundColor: '#1e1e1e',
              color: '#d4d4d4',
              outline: 'none',
              whiteSpace: 'pre',
              overflowWrap: 'normal',
              overflowX: 'auto',
              overflowY: 'auto'
            }}
            spellCheck={false}
        />
        </div>
      </div>
    );
  }
);

LineNumberEditor.displayName = 'LineNumberEditor';

function AppSimple() {
  const [sql, setSql] = useState(`-- 测试SQL: 粘贴你的Spark SQL到这里
SELECT * FROM users
CROSS JOIN orders
WHERE name LIKE '%john%'
  OR status = 'A'
  OR status = 'B';`);
  const [formattedSql, setFormattedSql] = useState<string>('');
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [fileName, setFileName] = useState<string>('');
  const [analysisCollapsed, setAnalysisCollapsed] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const editorRef = useRef<LineNumberEditorRef>(null);
  const [selectedFormatter, setSelectedFormatter] = useState<FormatterVersion>(FORMATTER_VERSIONS.V4);

  // 跳转到指定行
  const jumpToLine = (lineNumber: number) => {
    if (editorRef.current) {
      editorRef.current.scrollToLine(lineNumber);
      // 展开分析面板（如果折叠）
      setAnalysisCollapsed(false);
    }
  };

  const analyzeSQL = async () => {
    if (!sql.trim()) {
      alert('请先输入SQL语句');
      return;
    }

    setLoading(true);
    setResult(null);
    setAnalysisCollapsed(false);

    try {
      const response = await fetch('http://127.0.0.1:8888/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sql, filename: fileName || undefined })
      });
      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error('分析失败:', error);
      alert('分析失败，请确保后端服务已启动');
    } finally {
      setLoading(false);
    }
  };

  const formatSQL = async () => {
    if (!sql.trim()) {
      alert('请先输入SQL语句');
      return;
    }

    setLoading(true);
    setFormattedSql('');

    try {
      const formatUrl = getFormatUrl(selectedFormatter);
      const response = await fetch(formatUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sql: sql,
          options: { keyword_case: 'upper' }
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || '格式化失败');
      }

      setFormattedSql(data.formatted);
    } catch (error: any) {
      console.error('格式化异常:', error);
      alert(`格式化失败: ${error.message || '请确保后端服务已启动'}`);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    e.target.value = '';

    if (file.size > 10 * 1024 * 1024) {
      alert('文件太大，请上传小于10MB的文件');
      return;
    }

    setFileName(file.name);

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const content = event.target?.result as string;
        if (!content || content.length === 0) {
          alert('文件内容为空');
          return;
        }
        setSql(content);
        setResult(null);
        setFormattedSql('');
      } catch (error) {
        console.error('读取文件失败:', error);
        alert('读取文件失败');
      }
    };
    reader.onerror = () => {
      alert('读取文件时出错');
    };
    reader.readAsText(file);
  };

  const copyFormatted = () => {
    if (!formattedSql) {
      alert('请先格式化SQL');
      return;
    }
    navigator.clipboard.writeText(formattedSql);
    alert('已复制格式化结果');
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'HIGH': return '#ff4d4f';
      case 'MEDIUM': return '#ffad33';
      case 'LOW': return '#52c41a';
      default: return '#999';
    }
  };

  const getSeverityLabel = (severity: string) => {
    switch (severity) {
      case 'HIGH': return '高';
      case 'MEDIUM': return '中';
      case 'LOW': return '低';
      default: return '未知';
    }
  };

  // 获取指定行的内容
  const getLineContent = (lineNum: number) => {
    const lines = sql.split('\n');
    return lines[lineNum - 1] || '';
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>⚡ Spark SQL 优化工具</h1>
        <p className="subtitle">离线静态分析 · 智能优化建议</p>
      </header>

      <main className="app-main">
        {/* 上半部分：左右布局 */}
        <div className="main-editors">
          {/* 左侧：原始 SQL 编辑器 */}
          <div className="editor-section">
            <div className="section-header">
              <h2>📝 原始 SQL</h2>
              <div className="actions">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".sql,.txt"
                  onChange={handleFileUpload}
                  style={{ display: 'none' }}
                />
                <select
                  value={selectedFormatter}
                  onChange={(e) => setSelectedFormatter(e.target.value as FormatterVersion)}
                  className="formatter-select"
                  title="选择格式化器版本"
                >
                  <option value={FORMATTER_VERSIONS.V4}>V4 (正则)</option>
                  <option value={FORMATTER_VERSIONS.V5}>V5 (sqlglot)</option>
                </select>
                <button
                  className="btn btn-secondary"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={loading}
                >
                  📁 上传
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => { setSql(''); setFileName(''); setResult(null); setFormattedSql(''); }}
                  disabled={loading}
                >
                  清空
                </button>
                <button className="btn btn-secondary" onClick={formatSQL} disabled={loading || !sql.trim()}>
                  {loading ? '处理中...' : '✨ 格式化'}
                </button>
                <button className="btn btn-primary" onClick={analyzeSQL} disabled={loading || !sql.trim()}>
                  {loading ? '分析中...' : '📊 分析SQL'}
                </button>
              </div>
            </div>
            {fileName && (
              <div style={{ padding: '2px 5px', color: '#7f8c8d', fontSize: '11px' }}>
                📄 {fileName}
              </div>
            )}
            <div className="editor-container" style={{ height: 'calc(100vh - 165px)', minHeight: '500px' }}>
              <LineNumberEditor ref={editorRef} value={sql} onChange={setSql} />
            </div>
          </div>

          {/* 右侧：格式化结果预览 */}
          <div className="result-section">
            <div className="section-header">
              <h2>✨ 格式化结果</h2>
              <div className="actions">
                <button
                  className="btn btn-secondary"
                  onClick={copyFormatted}
                  disabled={!formattedSql}
                >
                  📋 复制结果
                </button>
              </div>
            </div>
            <div className="editor-container" style={{ height: 'calc(100vh - 165px)', minHeight: '600px', maxHeight: 'none' }}>
              <LineNumberEditor
                value={formattedSql || '-- 格式化结果将显示在这里\n-- 点击"✨ 格式化"按钮开始'}
                onChange={() => {}}
                readOnly={true}
              />
            </div>
          </div>
        </div>

        {/* 下部分析区域 */}
        <div className={`analysis-section ${analysisCollapsed ? 'collapsed' : ''}`}>
          <div className="analysis-header" onClick={() => setAnalysisCollapsed(!analysisCollapsed)}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '18px' }}>
                {analysisCollapsed ? '▶' : '▲'}
              </span>
              <h2>{analysisCollapsed ? '展开分析结果' : '分析结果面板'}</h2>
            </div>
            {result && (
              <div className="stats">
                <span className="stat high">🔴 {result.high_priority}</span>
                <span className="stat medium">🟡 {result.medium_priority}</span>
                <span className="stat low">🟢 {result.low_priority}</span>
              </div>
            )}
          </div>

          <div className="analysis-content">
            {!result ? (
              <div className="empty-state">
                <p>📊 点击"分析SQL"按钮开始分析</p>
                <p style={{ fontSize: '12px', color: '#95a5a6', marginTop: '10px' }}>
                  支持 CROSS JOIN 检测、隐式转换检测、子查询优化等
                </p>
              </div>
            ) : result.issues.length === 0 ? (
              <div className="empty-state">
                <p>🎉 未发现明显问题！SQL质量良好。</p>
              </div>
            ) : (
              result.issues.map((issue, index) => (
                <div key={index} className="issue-card" style={{ borderLeftColor: getSeverityColor(issue.severity) }}>
                  <div className="issue-header">
                    <span className="issue-severity" style={{ backgroundColor: getSeverityColor(issue.severity) }}>
                      {getSeverityLabel(issue.severity)}
                    </span>
                    <span className="issue-rule">{issue.rule}</span>
                    {issue.line > 0 && (
                      <button
                        className="issue-line"
                        onClick={() => jumpToLine(issue.line)}
                        title="点击跳转到该行"
                      >
                        🔗 第 {issue.line} 行
                      </button>
                    )}
                  </div>
                  <div className="issue-message">{issue.message}</div>
                  {issue.line > 0 && (
                    <div className="issue-code">
                      <div className="code-line">
                        <span className="line-number">{issue.line}:</span>
                        <span className="code-content">{getLineContent(issue.line).trim()}</span>
                      </div>
                    </div>
                  )}
                  {issue.suggestion && (
                    <div className="issue-suggestion">
                      <strong>💡 建议：</strong>{issue.suggestion}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </main>

      <footer className="app-footer">
        <p>基于MIT许可协议的开源组件构建 | 离线版本</p>
      </footer>
    </div>
  );
}

export default AppSimple;
