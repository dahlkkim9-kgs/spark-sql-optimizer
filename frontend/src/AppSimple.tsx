import React, { useState, useRef, useEffect } from 'react';
import './App.css';

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

interface FormatResult {
  original_sql: string;
  formatted_sql: string;
}

// 带行号的编辑器组件
function LineNumberEditor({ value, onChange, readOnly = false }: { value: string; onChange: (val: string) => void; readOnly?: boolean }) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const linesRef = useRef<HTMLDivElement>(null);
  const [lineCount, setLineCount] = useState(1);

  useEffect(() => {
    const count = value.split('\n').length;
    setLineCount(count);
  }, [value]);

  const handleScroll = () => {
    if (textareaRef.current && linesRef.current) {
      linesRef.current.scrollTop = textareaRef.current.scrollTop;
    }
  };

  const lineNumbers = Array.from({ length: lineCount }, (_, i) => i + 1);

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
          <div key={num} style={{ height: '21px' }}>{num}</div>
        ))}
      </div>
      {/* 文本编辑区 */}
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onScroll={handleScroll}
        readOnly={readOnly}
        style={{
          flex: 1,
          height: '100%',
          minHeight: '400px',
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
          overflowX: 'auto'
        }}
        spellCheck={false}
      />
    </div>
  );
}

function AppSimple() {
  const [sql, setSql] = useState(`-- 测试SQL: 粘贴你的Spark SQL到这里
SELECT * FROM users
CROSS JOIN orders
WHERE name LIKE '%john%'
  OR status = 'A'
  OR status = 'B';`);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [fileName, setFileName] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const analyzeSQL = async () => {
    setLoading(true);
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
    console.log('开始格式化SQL...');
    setLoading(true);
    try {
      console.log('发送格式化请求到:', 'http://localhost:5000/api/format');
      const response = await fetch('http://localhost:5000/api/format', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sql,
          options: {
            keyword_case: 'upper',
            semicolon_newline: true
          }
        })
      });
      console.log('收到响应，状态码:', response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('格式化响应错误:', errorText);
        alert(`格式化失败: ${response.status} - ${errorText}`);
        return;
      }

      const data = await response.json();
      console.log('格式化响应:', data);

      if (!data.success) {
        throw new Error(data.error || '格式化失败');
      }

      console.log('格式化成功，结果:', data.formatted);
      console.log('换行符数量:', (data.formatted.match(/\n/g) || []).length);
      console.log('前50个字符:', JSON.stringify(data.formatted.substring(0, 50)));
      console.log('实际字符串长度:', data.formatted.length);
      setSql(data.formatted);
      console.log('SQL已更新');
    } catch (error) {
      console.error('格式化异常:', error);
      alert(`格式化失败: ${(error as Error).message}\n请确保后端服务已启动 (http://localhost:5000)`);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setFileName(file.name);
      const reader = new FileReader();
      reader.onload = (event) => {
        const content = event.target?.result as string;
        setSql(content);
      };
      reader.readAsText(file);
    }
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
        <div className="editor-section">
          <div className="section-header">
            <h2>SQL编辑器</h2>
            <div className="actions">
              <input
                ref={fileInputRef}
                type="file"
                accept=".sql,.txt"
                onChange={handleFileUpload}
                style={{ display: 'none' }}
              />
              <button
                className="btn btn-secondary"
                onClick={() => fileInputRef.current?.click()}
              >
                📁 上传文件
              </button>
              <button className="btn btn-secondary" onClick={() => { setSql(''); setFileName(''); }}>
                清空
              </button>
              <button className="btn btn-secondary" onClick={formatSQL} disabled={loading}>
                {loading ? '处理中...' : '✨ 格式化'}
              </button>
              <button className="btn btn-primary" onClick={analyzeSQL} disabled={loading}>
                {loading ? '分析中...' : '分析SQL'}
              </button>
            </div>
          </div>
          {fileName && (
            <div style={{ padding: '5px 15px', color: '#7f8c8d', fontSize: '12px' }}>
              📄 {fileName}
            </div>
          )}
          <div className="editor-container" style={{ height: '400px' }}>
            <LineNumberEditor value={sql} onChange={setSql} />
          </div>
        </div>

        {result && (
          <div className="result-section">
            <div className="section-header">
              <h2>分析结果</h2>
              <div className="stats">
                <span className="stat high">高: {result.high_priority}</span>
                <span className="stat medium">中: {result.medium_priority}</span>
                <span className="stat low">低: {result.low_priority}</span>
              </div>
            </div>

            <div className="issues-list">
              {result.issues.length === 0 ? (
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
                        <span className="issue-line">第 {issue.line} 行</span>
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
                        <strong>建议：</strong>{issue.suggestion}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>

            {result.optimized_sql && result.optimized_sql !== result.original_sql && (
              <div className="optimized-section">
                <h3>优化后的SQL</h3>
                <div className="editor-container" style={{ height: '200px' }}>
                  <LineNumberEditor value={result.optimized_sql} onChange={() => {}} readOnly={true} />
                </div>
                <button
                  className="btn btn-secondary"
                  onClick={() => {
                    navigator.clipboard.writeText(result.optimized_sql);
                    alert('已复制到剪贴板');
                  }}
                >
                  复制优化后的SQL
                </button>
              </div>
            )}
          </div>
        )}
      </main>

      <footer className="app-footer">
        <p>基于MIT许可协议的开源组件构建 | 离线版本</p>
      </footer>
    </div>
  );
}

export default AppSimple;
