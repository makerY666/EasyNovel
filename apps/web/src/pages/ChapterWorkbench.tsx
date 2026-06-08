import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  approveWorkflowStage,
  createChapter,
  createChapterVersion,
  getAgentRuns,
  getChapterVersions,
  getChapters,
  getContextPack,
  getNovels,
  getQualityReports,
  getWorkflowStatus,
  startWorkflow,
  updateChapterVersion,
} from '../api/client';
import { ChapterVersion } from '../api/types';
import { useStudioStore } from '../store/useStudioStore';

const STAGE_LABELS: Record<string, string> = {
  building_context: '构建上下文',
  planning_chapter: '规划章节卡',
  chapter_card_ready: '章节卡已生成',
  writing_draft: '生成初稿',
  draft_ready: '初稿完成',
  polishing_draft: '润色中',
  completed: '完成',
  failed: '失败',
};

const STAGE_PROGRESS: Record<string, number> = {
  building_context: 10,
  planning_chapter: 25,
  chapter_card_ready: 35,
  writing_draft: 55,
  draft_ready: 70,
  polishing_draft: 85,
  completed: 100,
  failed: 0,
};

export default function ChapterWorkbench() {
  const { activeNovelId, activeChapterId, activeChapterNumber, selectChapter, setPage, setError } = useStudioStore();
  const [novels, setNovels] = useState<any[]>([]);
  const [chapters, setChapters] = useState<any[]>([]);
  const [versions, setVersions] = useState<ChapterVersion[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState(0);
  const [content, setContent] = useState('');
  const [chapterGoal, setChapterGoal] = useState('');
  const [contextPack, setContextPack] = useState<any>(null);
  const [workflowId, setWorkflowId] = useState('');
  const [workflowState, setWorkflowState] = useState<any>(null);
  const [generating, setGenerating] = useState(false);
  const [qualityReports, setQualityReports] = useState<any[]>([]);
  const [agentRuns, setAgentRuns] = useState<any[]>([]);
  const pollingRef = useRef<number | undefined>(undefined);

  const activeNovel = novels.find((novel) => novel.id === activeNovelId);
  const activeChapter = chapters.find((chapter) => chapter.id === activeChapterId)
    || chapters.find((chapter) => chapter.chapter_number === activeChapterNumber);
  const activeVersion = versions.find((version) => version.id === selectedVersionId);

  const loadNovels = useCallback(async () => {
    try {
      const rows = await getNovels();
      setNovels(rows);
      if (!activeNovelId && rows[0]) useStudioStore.setState({ activeNovelId: rows[0].id });
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载小说失败');
    }
  }, [activeNovelId, setError]);

  const loadChapters = useCallback(async () => {
    if (!activeNovelId) return;
    try {
      const rows = await getChapters(activeNovelId);
      setChapters(rows);
      const chapter = rows.find((item) => item.id === activeChapterId) || rows[0];
      if (chapter && !activeChapterId) selectChapter(chapter.id, chapter.chapter_number);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载章节失败');
    }
  }, [activeChapterId, activeNovelId, selectChapter, setError]);

  const loadVersions = useCallback(async () => {
    const chapterId = activeChapter?.id;
    if (!chapterId) {
      setVersions([]);
      setContent('');
      return;
    }
    try {
      const rows = await getChapterVersions(chapterId);
      setVersions(rows);
      const current = rows.find((item) => item.id === activeChapter.current_version_id) || rows[rows.length - 1];
      if (current) {
        setSelectedVersionId(current.id);
        setContent(current.content);
      } else {
        setSelectedVersionId(0);
        setContent('');
      }
      setQualityReports(await getQualityReports(chapterId));
      setAgentRuns(await getAgentRuns(chapterId));
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载章节版本失败');
    }
  }, [activeChapter, setError]);

  useEffect(() => {
    loadNovels();
  }, [loadNovels]);

  useEffect(() => {
    loadChapters();
  }, [loadChapters]);

  useEffect(() => {
    loadVersions();
  }, [loadVersions]);

  useEffect(() => {
    const version = versions.find((item) => item.id === selectedVersionId);
    if (version) setContent(version.content);
  }, [selectedVersionId, versions]);

  useEffect(() => {
    if (!workflowId || !generating) return undefined;
    const poll = async () => {
      try {
        const state = await getWorkflowStatus(workflowId);
        setWorkflowState(state);
        if (state.draft_text && !state.polished_text) setContent(state.draft_text);
        if (state.polished_text) setContent(state.polished_text);
        if (state.status === 'completed' || state.current_stage === 'completed' || state.status === 'failed') {
          setGenerating(false);
          await loadChapters();
          await loadVersions();
          return;
        }
        pollingRef.current = window.setTimeout(poll, 1500);
      } catch (err) {
        setGenerating(false);
        setError(err instanceof Error ? err.message : '查询生成状态失败');
      }
    };
    poll();
    return () => {
      if (pollingRef.current) window.clearTimeout(pollingRef.current);
    };
  }, [generating, loadChapters, loadVersions, setError, workflowId]);

  const chapterButtons = useMemo(() => {
    const max = Math.max(10, ...chapters.map((chapter) => chapter.chapter_number + 2), activeChapterNumber + 2);
    return Array.from({ length: max }, (_, index) => index + 1);
  }, [activeChapterNumber, chapters]);

  const ensureChapter = async () => {
    if (!activeNovelId) throw new Error('请先选择小说');
    const existing = chapters.find((chapter) => chapter.chapter_number === activeChapterNumber);
    if (existing) return existing;
    const created = await createChapter({
      novel_id: activeNovelId,
      chapter_number: activeChapterNumber,
      title: `第 ${activeChapterNumber} 章`,
      target_word_count: 3000,
    });
    await loadChapters();
    selectChapter(created.id, created.chapter_number);
    return created;
  };

  const startGeneration = async () => {
    try {
      const chapter = await ensureChapter();
      setGenerating(true);
      setWorkflowState(null);
      setContent('');
      const wf = await startWorkflow({
        novel_id: activeNovelId,
        chapter_number: chapter.chapter_number,
        chapter_goal: chapterGoal || `推进第 ${chapter.chapter_number} 章的主要冲突，并留下明确章节钩子。`,
        polish_level: 'medium',
      });
      setWorkflowId(wf.workflow_id);
    } catch (err) {
      setGenerating(false);
      setError(err instanceof Error ? err.message : '启动生成失败');
    }
  };

  const saveManual = async (stage: 'manual' | 'final') => {
    try {
      const chapter = await ensureChapter();
      if (activeVersion && activeVersion.source === 'manual' && activeVersion.stage === stage) {
        const updated = await updateChapterVersion(chapter.id, activeVersion.id, { ...activeVersion, stage, content, source: 'manual' });
        setSelectedVersionId(updated.id);
      } else {
        const created = await createChapterVersion(chapter.id, { stage, content, source: 'manual' });
        setSelectedVersionId(created.id);
      }
      await loadChapters();
      await loadVersions();
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存版本失败');
    }
  };

  const approveFinal = async () => {
    if (!workflowId || !activeChapter?.id) {
      await saveManual('final');
      return;
    }
    try {
      await approveWorkflowStage(workflowId, {
        chapter_id: activeChapter.id,
        stage: 'final',
        content,
        mark_final: true,
      });
      await loadChapters();
      await loadVersions();
    } catch (err) {
      setError(err instanceof Error ? err.message : '定稿失败');
    }
  };

  const loadContext = async () => {
    try {
      const chapter = await ensureChapter();
      setContextPack(await getContextPack(activeNovelId, chapter.id, chapterGoal));
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载上下文失败');
    }
  };

  if (!activeNovelId && novels.length === 0) {
    return (
      <section className="page">
        <div className="empty-state">
          <h2>还没有可写作的小说</h2>
          <p>先在项目管理中创建项目和小说，再进入章节工作台。</p>
          <button className="button primary" onClick={() => setPage('projects')}>去创建项目</button>
        </div>
      </section>
    );
  }

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Chapter Workflow</p>
          <h1>{activeNovel?.title || '章节工作台'}</h1>
          <p className="muted">章节卡、初稿、润色、质量报告和人工定稿都会保存为版本。</p>
        </div>
        <div className="header-actions">
          <button className="button secondary" onClick={() => setPage('novel')}>返回设定库</button>
          <button className="button primary" onClick={startGeneration} disabled={generating || !activeNovelId}>
            {generating ? '生成中...' : '启动 AI 工作流'}
          </button>
        </div>
      </header>

      <div className="workbench-grid">
        <aside className="panel workbench-side">
          <h2>章节</h2>
          <div className="chapter-grid">
            {chapterButtons.map((num) => {
              const chapter = chapters.find((item) => item.chapter_number === num);
              const active = activeChapterNumber === num;
              return (
                <button
                  key={num}
                  className={active ? 'active' : ''}
                  onClick={() => {
                    if (chapter) selectChapter(chapter.id, chapter.chapter_number);
                    else useStudioStore.setState({ activeChapterNumber: num, activeChapterId: 0 });
                  }}
                >
                  {num}
                  {chapter?.status === 'final' && <span>F</span>}
                </button>
              );
            })}
          </div>

          <label className="field">
            <span>本章目标</span>
            <textarea rows={4} value={chapterGoal} onChange={(e) => setChapterGoal(e.target.value)} placeholder="这一章要完成什么剧情推进？" />
          </label>

          <div className="button-row">
            <button className="button secondary" onClick={loadContext}>上下文</button>
            <button className="button secondary" onClick={() => saveManual('manual')} disabled={!content.trim()}>保存</button>
            <button className="button primary" onClick={approveFinal} disabled={!content.trim()}>定稿</button>
          </div>

          {generating && (
            <div className="progress-box">
              <div className="progress-title">
                <span>{STAGE_LABELS[workflowState?.current_stage || 'building_context'] || '处理中'}</span>
                <strong>{STAGE_PROGRESS[workflowState?.current_stage || 'building_context'] || 0}%</strong>
              </div>
              <div className="progress"><span style={{ width: `${STAGE_PROGRESS[workflowState?.current_stage || 'building_context'] || 0}%` }} /></div>
            </div>
          )}

          {workflowState?.error && <div className="alert alert-error">{workflowState.error}</div>}
        </aside>

        <main className="panel editor-panel">
          <div className="panel-title">
            <div>
              <h2>{activeChapter?.title || `第 ${activeChapterNumber} 章`}</h2>
              <p className="muted small">{activeChapter?.status || 'planned'} · {content.length.toLocaleString()} 字符</p>
            </div>
            <select value={selectedVersionId} onChange={(e) => setSelectedVersionId(Number(e.target.value))}>
              <option value={0}>新内容</option>
              {versions.map((version) => (
                <option key={version.id} value={version.id}>
                  v{version.version_number} · {version.stage} · {version.word_count} 字
                </option>
              ))}
            </select>
          </div>
          <textarea
            className="novel-editor"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="在这里编辑 AI 初稿、润色稿或你的人工定稿。"
          />
        </main>

        <aside className="panel insight-panel">
          <h2>上下文与审校</h2>
          {contextPack ? (
            <div className="context-block">
              <h3>章节目标</h3>
              <p>{contextPack.chapter_goal || '未指定'}</p>
              <h3>世界观规则</h3>
              {(contextPack.world_rules || []).map((rule: any, index: number) => <p key={index}>- {rule.content}</p>)}
              <h3>未回收伏笔</h3>
              {(contextPack.open_foreshadowings || []).map((item: any, index: number) => <p key={index}>- {item.content}</p>)}
            </div>
          ) : (
            <p className="muted">点击“上下文”查看本章生成会读取的记忆包。</p>
          )}

          <h3>质量报告</h3>
          {qualityReports.length === 0 ? <p className="muted small">暂无质量报告。</p> : qualityReports.map((report) => (
            <div className="mini-card" key={report.id}>
              <strong>{Number(report.overall_score || 0).toFixed(1)}</strong>
              <span>{report.report_type}</span>
            </div>
          ))}

          <h3>Agent 运行</h3>
          {agentRuns.length === 0 ? <p className="muted small">暂无运行记录。</p> : agentRuns.map((run) => (
            <div className="mini-card" key={run.id}>
              <strong>{run.agent_name}</strong>
              <span>{run.status}</span>
            </div>
          ))}
        </aside>
      </div>
    </section>
  );
}
