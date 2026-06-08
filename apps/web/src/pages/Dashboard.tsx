import React, { useCallback, useEffect, useState } from 'react';
import { getChapters, getCostSummary, getModelConfig, getNovels, getProjects } from '../api/client';
import { ModelConfig } from '../api/types';
import { useStudioStore } from '../store/useStudioStore';

interface Stats {
  projects: number;
  novels: number;
  chapters: number;
  words: number;
}

export default function Dashboard() {
  const setPage = useStudioStore((s) => s.setPage);
  const setError = useStudioStore((s) => s.setError);
  const [stats, setStats] = useState<Stats>({ projects: 0, novels: 0, chapters: 0, words: 0 });
  const [model, setModel] = useState<ModelConfig | null>(null);
  const [cost, setCost] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const projects = await getProjects();
      let novelCount = 0;
      let chapterCount = 0;
      let wordCount = 0;
      for (const project of projects) {
        const novels = await getNovels(project.id);
        novelCount += novels.length;
        for (const novel of novels) {
          const chapters = await getChapters(novel.id);
          chapterCount += chapters.length;
          wordCount += Number(novel.current_word_count || 0);
        }
      }
      setStats({ projects: projects.length, novels: novelCount, chapters: chapterCount, words: wordCount });
      setModel(await getModelConfig());
      setCost(await getCostSummary());
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载仪表盘失败');
    } finally {
      setLoading(false);
    }
  }, [setError]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Local AI Novel Workflow</p>
          <h1>AI 小说工作台</h1>
          <p className="muted">从设定、人物、章节生成到审校导出，集中在一个本地工作流里。</p>
        </div>
        <div className="header-actions">
          <button className="button secondary" onClick={load} disabled={loading}>刷新</button>
          <button className="button primary" onClick={() => setPage('projects')}>新建项目</button>
        </div>
      </header>

      <div className="stats-grid">
        <Metric label="项目" value={stats.projects} />
        <Metric label="小说" value={stats.novels} />
        <Metric label="章节" value={stats.chapters} />
        <Metric label="总字数" value={`${(stats.words / 10000).toFixed(1)} 万`} />
      </div>

      <div className="two-column">
        <div className="panel">
          <div className="panel-title">
            <h2>工作流入口</h2>
            <span className="badge">推荐顺序</span>
          </div>
          <div className="step-list">
            <button onClick={() => setPage('projects')}>
              <strong>1. 创建项目</strong>
              <span>确定题材、平台、读者和爽点边界。</span>
            </button>
            <button onClick={() => setPage('novel')}>
              <strong>2. 建立设定库</strong>
              <span>维护世界观、人物、风格指南、时间线和伏笔。</span>
            </button>
            <button onClick={() => setPage('workbench')}>
              <strong>3. 生成章节</strong>
              <span>章节卡、初稿、润色、质量评分和人工定稿。</span>
            </button>
          </div>
        </div>

        <div className="panel">
          <div className="panel-title">
            <h2>运行状态</h2>
            <button className="text-button" onClick={() => setPage('models')}>查看模型设置</button>
          </div>
          <div className="status-list">
            <div>
              <span>模型 Provider</span>
              <strong>{model?.provider || '-'}</strong>
            </div>
            <div>
              <span>API Key</span>
              <strong className={model?.api_key_configured ? 'ok' : 'danger'}>
                {model?.api_key_configured ? '已配置' : '未配置'}
              </strong>
            </div>
            <div>
              <span>快速模型</span>
              <strong>{model?.flash_model || '-'}</strong>
            </div>
            <div>
              <span>累计调用</span>
              <strong>{cost?.calls_count ?? 0}</strong>
            </div>
            <div>
              <span>累计成本</span>
              <strong>${Number(cost?.total_cost_usd || 0).toFixed(4)}</strong>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="metric-card">
      <div className="metric-value">{value}</div>
      <div className="metric-label">{label}</div>
    </div>
  );
}
