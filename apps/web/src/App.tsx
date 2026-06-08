import React from 'react';
import ChapterWorkbench from './pages/ChapterWorkbench';
import Dashboard from './pages/Dashboard';
import ModelSettings from './pages/ModelSettings';
import NovelEditor from './pages/NovelEditor';
import Projects from './pages/Projects';
import { PageKey, useStudioStore } from './store/useStudioStore';

const NAV: { id: PageKey; label: string; icon: string }[] = [
  { id: 'dashboard', label: '仪表盘', icon: 'D' },
  { id: 'projects', label: '项目', icon: 'P' },
  { id: 'novel', label: '设定库', icon: 'N' },
  { id: 'workbench', label: '章节工作台', icon: 'W' },
  { id: 'models', label: '模型设置', icon: 'M' },
];

export default function App() {
  const { page, setPage, error, clearError } = useStudioStore();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">AI</div>
          <div>
            <strong>EasyNovel</strong>
            <span>本地小说工作流</span>
          </div>
        </div>
        <nav className="nav-list">
          {NAV.map((item) => (
            <button
              key={item.id}
              className={`nav-button ${page === item.id ? 'active' : ''}`}
              onClick={() => setPage(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span>v0.3.0</span>
          <span>SQLite + OpenAI-compatible</span>
        </div>
      </aside>

      <main className="workspace">
        {error && (
          <div className="alert alert-error">
            <span>{error}</span>
            <button className="icon-button" onClick={clearError}>x</button>
          </div>
        )}
        {page === 'dashboard' && <Dashboard />}
        {page === 'projects' && <Projects />}
        {page === 'novel' && <NovelEditor />}
        {page === 'workbench' && <ChapterWorkbench />}
        {page === 'models' && <ModelSettings />}
      </main>
    </div>
  );
}
