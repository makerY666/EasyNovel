import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  addForeshadowing,
  addWorldRule,
  createCharacter,
  createNovel,
  createStyleGuide,
  createTimelineEvent,
  exportNovel,
  getCharacters,
  getForeshadowings,
  getNovels,
  getProjects,
  getStyleGuides,
  getTimelineEvents,
  getWorldRules,
} from '../api/client';
import { useStudioStore } from '../store/useStudioStore';

type Tab = 'overview' | 'rules' | 'characters' | 'style' | 'timeline' | 'foreshadow' | 'export';

export default function NovelEditor() {
  const { activeProjectId, activeNovelId, selectNovel, setPage, setError } = useStudioStore();
  const [projects, setProjects] = useState<any[]>([]);
  const [novels, setNovels] = useState<any[]>([]);
  const [tab, setTab] = useState<Tab>('overview');
  const [rules, setRules] = useState<any[]>([]);
  const [characters, setCharacters] = useState<any[]>([]);
  const [styles, setStyles] = useState<any[]>([]);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [foreshadowings, setForeshadowings] = useState<any[]>([]);
  const [exportPreview, setExportPreview] = useState('');
  const [novelForm, setNovelForm] = useState({ title: '', genre: '玄幻', synopsis: '', target_word_count: 300000 });
  const [ruleForm, setRuleForm] = useState({ rule_id: '', content: '', priority: 'medium', category: 'world_setting' });
  const [characterForm, setCharacterForm] = useState({ name: '', role: 'protagonist', public_goal: '', hidden_desire: '', fear: '', voice_tone: '' });
  const [styleForm, setStyleForm] = useState({ name: '默认风格', narrative_pov: '第三人称有限视角', sentence_length_preference: 'medium', dialogue_density: 'medium', forbidden_words: '' });
  const [timelineForm, setTimelineForm] = useState({ chapter_id: 0, date_in_story: '第一天', location: '', events: '' });
  const [fsForm, setFsForm] = useState({ foreshadowing_id: '', introduced_at_chapter: 1, content: '', intended_payoff_chapter: 0 });

  const project = projects.find((item) => item.id === activeProjectId);
  const activeNovel = novels.find((item) => item.id === activeNovelId) || novels[0];
  const novelId = activeNovel?.id || 0;

  const loadProjectsAndNovels = useCallback(async () => {
    try {
      const projectRows = await getProjects();
      setProjects(projectRows);
      const projectId = activeProjectId || projectRows[0]?.id || 0;
      if (!projectId) return;
      const novelRows = await getNovels(projectId);
      setNovels(novelRows);
      if (!activeNovelId && novelRows[0]) {
        useStudioStore.setState({ activeNovelId: novelRows[0].id });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载设定库失败');
    }
  }, [activeProjectId, activeNovelId, setError]);

  const loadNovelAssets = useCallback(async () => {
    if (!novelId) return;
    try {
      const [ruleRows, characterRows, styleRows, timelineRows, fsRows] = await Promise.all([
        getWorldRules(novelId),
        getCharacters(novelId),
        getStyleGuides(novelId),
        getTimelineEvents(novelId),
        getForeshadowings(novelId),
      ]);
      setRules(ruleRows);
      setCharacters(characterRows);
      setStyles(styleRows);
      setTimeline(timelineRows);
      setForeshadowings(fsRows);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载小说资产失败');
    }
  }, [novelId, setError]);

  useEffect(() => {
    loadProjectsAndNovels();
  }, [loadProjectsAndNovels]);

  useEffect(() => {
    loadNovelAssets();
  }, [loadNovelAssets]);

  const tabs = useMemo(
    () => [
      ['overview', '概览'],
      ['rules', `世界观 ${rules.length}`],
      ['characters', `人物 ${characters.length}`],
      ['style', `风格 ${styles.length}`],
      ['timeline', `时间线 ${timeline.length}`],
      ['foreshadow', `伏笔 ${foreshadowings.length}`],
      ['export', '导出'],
    ] as [Tab, string][],
    [characters.length, foreshadowings.length, rules.length, styles.length, timeline.length],
  );

  if (!activeProjectId && projects.length === 0) {
    return (
      <section className="page">
        <div className="empty-state">
          <h2>先创建一个项目</h2>
          <p>设定库需要绑定到项目和小说。创建项目后，系统会自动生成默认小说。</p>
          <button className="button primary" onClick={() => setPage('projects')}>去创建项目</button>
        </div>
      </section>
    );
  }

  const createNovelFromForm = async () => {
    const projectId = activeProjectId || project?.id;
    if (!projectId || !novelForm.title.trim()) return;
    try {
      const novel = await createNovel({ ...novelForm, project_id: projectId });
      setNovelForm({ title: '', genre: '玄幻', synopsis: '', target_word_count: 300000 });
      setNovels(await getNovels(projectId));
      useStudioStore.setState({ activeNovelId: novel.id });
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建小说失败');
    }
  };

  const createRule = async () => {
    if (!novelId || !ruleForm.rule_id || !ruleForm.content) return;
    await addWorldRule({ ...ruleForm, novel_id: novelId });
    setRuleForm({ rule_id: '', content: '', priority: 'medium', category: 'world_setting' });
    setRules(await getWorldRules(novelId));
  };

  const createChar = async () => {
    if (!novelId || !characterForm.name) return;
    await createCharacter({
      novel_id: novelId,
      name: characterForm.name,
      role: characterForm.role,
      public_goal: characterForm.public_goal,
      hidden_desire: characterForm.hidden_desire,
      fear: characterForm.fear,
      voice_style: { tone: characterForm.voice_tone },
    });
    setCharacterForm({ name: '', role: 'protagonist', public_goal: '', hidden_desire: '', fear: '', voice_tone: '' });
    setCharacters(await getCharacters(novelId));
  };

  const createStyle = async () => {
    if (!novelId || !styleForm.name) return;
    await createStyleGuide({
      novel_id: novelId,
      name: styleForm.name,
      narrative_pov: styleForm.narrative_pov,
      sentence_length_preference: styleForm.sentence_length_preference,
      dialogue_density: styleForm.dialogue_density,
      forbidden_words: styleForm.forbidden_words.split(/[,\n，]/).map((s) => s.trim()).filter(Boolean),
      is_active: true,
    });
    setStyles(await getStyleGuides(novelId));
  };

  const createTimeline = async () => {
    if (!novelId || !timelineForm.location) return;
    await createTimelineEvent({
      novel_id: novelId,
      chapter_id: Number(timelineForm.chapter_id || 1),
      date_in_story: timelineForm.date_in_story,
      location: timelineForm.location,
      events: timelineForm.events.split(/\n/).map((s) => s.trim()).filter(Boolean),
    });
    setTimelineForm({ chapter_id: 0, date_in_story: '第一天', location: '', events: '' });
    setTimeline(await getTimelineEvents(novelId));
  };

  const createFs = async () => {
    if (!novelId || !fsForm.foreshadowing_id || !fsForm.content) return;
    await addForeshadowing({ ...fsForm, novel_id: novelId, intended_payoff_chapter: fsForm.intended_payoff_chapter || undefined });
    setFsForm({ foreshadowing_id: '', introduced_at_chapter: 1, content: '', intended_payoff_chapter: 0 });
    setForeshadowings(await getForeshadowings(novelId));
  };

  const previewExport = async (format: 'txt' | 'markdown') => {
    if (!novelId) return;
    setExportPreview(await exportNovel(novelId, format));
  };

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Story Bible</p>
          <h1>{activeNovel?.title || '小说设定库'}</h1>
          <p className="muted">{project?.name || '选择一个项目后开始维护设定。'}</p>
        </div>
        <div className="header-actions">
          <button className="button secondary" onClick={() => setPage('projects')}>项目列表</button>
          <button className="button primary" disabled={!novelId} onClick={() => novelId && selectNovel(novelId)}>进入章节工作台</button>
        </div>
      </header>

      <div className="panel">
        <div className="toolbar">
          <select value={novelId} onChange={(e) => useStudioStore.setState({ activeNovelId: Number(e.target.value) })}>
            {novels.map((novel) => <option key={novel.id} value={novel.id}>{novel.title}</option>)}
          </select>
          <input value={novelForm.title} onChange={(e) => setNovelForm({ ...novelForm, title: e.target.value })} placeholder="新小说标题" />
          <button className="button secondary" onClick={createNovelFromForm}>添加小说</button>
        </div>
      </div>

      <div className="tabs">
        {tabs.map(([id, label]) => (
          <button key={id} className={tab === id ? 'active' : ''} onClick={() => setTab(id)}>{label}</button>
        ))}
      </div>

      {tab === 'overview' && activeNovel && (
        <div className="two-column">
          <InfoPanel title="小说信息" items={[
            ['类型', activeNovel.genre || '未设置'],
            ['状态', activeNovel.status || 'planning'],
            ['目标字数', `${Number(activeNovel.target_word_count || 0).toLocaleString()} 字`],
            ['当前字数', `${Number(activeNovel.current_word_count || 0).toLocaleString()} 字`],
          ]} />
          <div className="panel">
            <h2>简介</h2>
            <p className="body-copy">{activeNovel.synopsis || '暂无简介。可以在项目阶段补充核心卖点，也可以在后续版本加入小说编辑表单。'}</p>
          </div>
        </div>
      )}

      {tab === 'rules' && (
        <AssetPanel title="世界观规则" empty="还没有硬设定。先写下不能被 AI 改坏的规则。">
          <div className="inline-form">
            <input value={ruleForm.rule_id} onChange={(e) => setRuleForm({ ...ruleForm, rule_id: e.target.value })} placeholder="rule_001" />
            <select value={ruleForm.priority} onChange={(e) => setRuleForm({ ...ruleForm, priority: e.target.value })}>
              <option>high</option><option>medium</option><option>low</option>
            </select>
            <input value={ruleForm.content} onChange={(e) => setRuleForm({ ...ruleForm, content: e.target.value })} placeholder="规则内容" />
            <button className="button primary" onClick={createRule}>添加</button>
          </div>
          <List rows={rules} titleKey="rule_id" bodyKey="content" metaKey="priority" />
        </AssetPanel>
      )}

      {tab === 'characters' && (
        <AssetPanel title="人物卡" empty="还没有人物。至少先建立主角、主要对手和关键关系人。">
          <div className="form-grid compact">
            <Field label="姓名"><input value={characterForm.name} onChange={(e) => setCharacterForm({ ...characterForm, name: e.target.value })} /></Field>
            <Field label="角色"><select value={characterForm.role} onChange={(e) => setCharacterForm({ ...characterForm, role: e.target.value })}><option>protagonist</option><option>antagonist</option><option>supporting</option><option>minor</option></select></Field>
            <Field label="公开目标"><input value={characterForm.public_goal} onChange={(e) => setCharacterForm({ ...characterForm, public_goal: e.target.value })} /></Field>
            <Field label="隐藏欲望"><input value={characterForm.hidden_desire} onChange={(e) => setCharacterForm({ ...characterForm, hidden_desire: e.target.value })} /></Field>
            <Field label="恐惧"><input value={characterForm.fear} onChange={(e) => setCharacterForm({ ...characterForm, fear: e.target.value })} /></Field>
            <Field label="口吻"><input value={characterForm.voice_tone} onChange={(e) => setCharacterForm({ ...characterForm, voice_tone: e.target.value })} /></Field>
          </div>
          <div className="form-actions"><button className="button primary" onClick={createChar}>添加人物</button></div>
          <List rows={characters} titleKey="name" bodyKey="public_goal" metaKey="role" />
        </AssetPanel>
      )}

      {tab === 'style' && (
        <AssetPanel title="风格指南" empty="还没有风格指南。创建一个后，章节生成会带入上下文。">
          <div className="form-grid compact">
            <Field label="名称"><input value={styleForm.name} onChange={(e) => setStyleForm({ ...styleForm, name: e.target.value })} /></Field>
            <Field label="叙事视角"><input value={styleForm.narrative_pov} onChange={(e) => setStyleForm({ ...styleForm, narrative_pov: e.target.value })} /></Field>
            <Field label="句长"><select value={styleForm.sentence_length_preference} onChange={(e) => setStyleForm({ ...styleForm, sentence_length_preference: e.target.value })}><option>short</option><option>medium</option><option>long</option></select></Field>
            <Field label="对话密度"><select value={styleForm.dialogue_density} onChange={(e) => setStyleForm({ ...styleForm, dialogue_density: e.target.value })}><option>low</option><option>medium</option><option>high</option></select></Field>
            <Field label="禁用词" wide><textarea rows={2} value={styleForm.forbidden_words} onChange={(e) => setStyleForm({ ...styleForm, forbidden_words: e.target.value })} placeholder="逗号或换行分隔" /></Field>
          </div>
          <div className="form-actions"><button className="button primary" onClick={createStyle}>保存为当前风格</button></div>
          <List rows={styles} titleKey="name" bodyKey="narrative_pov" metaKey="dialogue_density" />
        </AssetPanel>
      )}

      {tab === 'timeline' && (
        <AssetPanel title="时间线" empty="还没有时间线事件。定稿后也可以手动补充关键状态变化。">
          <div className="form-grid compact">
            <Field label="章节 ID"><input type="number" value={timelineForm.chapter_id || ''} onChange={(e) => setTimelineForm({ ...timelineForm, chapter_id: Number(e.target.value) || 0 })} /></Field>
            <Field label="故事时间"><input value={timelineForm.date_in_story} onChange={(e) => setTimelineForm({ ...timelineForm, date_in_story: e.target.value })} /></Field>
            <Field label="地点"><input value={timelineForm.location} onChange={(e) => setTimelineForm({ ...timelineForm, location: e.target.value })} /></Field>
            <Field label="事件" wide><textarea rows={2} value={timelineForm.events} onChange={(e) => setTimelineForm({ ...timelineForm, events: e.target.value })} /></Field>
          </div>
          <div className="form-actions"><button className="button primary" onClick={createTimeline}>添加时间线</button></div>
          <List rows={timeline} titleKey="date_in_story" bodyKey="location" metaKey="importance" />
        </AssetPanel>
      )}

      {tab === 'foreshadow' && (
        <AssetPanel title="伏笔账本" empty="还没有伏笔。记录计划回收点可以减少长篇断线。">
          <div className="form-grid compact">
            <Field label="伏笔 ID"><input value={fsForm.foreshadowing_id} onChange={(e) => setFsForm({ ...fsForm, foreshadowing_id: e.target.value })} /></Field>
            <Field label="引入章节"><input type="number" value={fsForm.introduced_at_chapter} onChange={(e) => setFsForm({ ...fsForm, introduced_at_chapter: Number(e.target.value) || 1 })} /></Field>
            <Field label="回收章节"><input type="number" value={fsForm.intended_payoff_chapter || ''} onChange={(e) => setFsForm({ ...fsForm, intended_payoff_chapter: Number(e.target.value) || 0 })} /></Field>
            <Field label="内容" wide><textarea rows={2} value={fsForm.content} onChange={(e) => setFsForm({ ...fsForm, content: e.target.value })} /></Field>
          </div>
          <div className="form-actions"><button className="button primary" onClick={createFs}>添加伏笔</button></div>
          <List rows={foreshadowings} titleKey="foreshadowing_id" bodyKey="content" metaKey="status" />
        </AssetPanel>
      )}

      {tab === 'export' && (
        <div className="panel">
          <div className="panel-title">
            <h2>导出小说</h2>
            <span className="badge">TXT / Markdown</span>
          </div>
          <div className="header-actions left">
            <button className="button secondary" disabled={!novelId} onClick={() => previewExport('txt')}>预览 TXT</button>
            <button className="button primary" disabled={!novelId} onClick={() => previewExport('markdown')}>预览 Markdown</button>
          </div>
          <textarea className="export-preview" readOnly value={exportPreview} placeholder="导出内容会显示在这里，可直接保存为 .txt 或 .md。" />
        </div>
      )}
    </section>
  );
}

function InfoPanel({ title, items }: { title: string; items: [string, string][] }) {
  return (
    <div className="panel">
      <h2>{title}</h2>
      <div className="status-list">
        {items.map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}
      </div>
    </div>
  );
}

function AssetPanel({ title, empty, children }: { title: string; empty: string; children: React.ReactNode }) {
  return (
    <div className="panel">
      <div className="panel-title"><h2>{title}</h2></div>
      {children}
      <p className="muted small">{empty}</p>
    </div>
  );
}

function List({ rows, titleKey, bodyKey, metaKey }: { rows: any[]; titleKey: string; bodyKey: string; metaKey?: string }) {
  if (rows.length === 0) return null;
  return (
    <div className="asset-list">
      {rows.map((row) => (
        <div key={row.id || row[titleKey]} className="asset-item">
          <div>
            <strong>{row[titleKey] || '未命名'}</strong>
            <p>{Array.isArray(row[bodyKey]) ? row[bodyKey].join(' / ') : row[bodyKey]}</p>
          </div>
          {metaKey && <span className="badge">{row[metaKey] || '-'}</span>}
        </div>
      ))}
    </div>
  );
}

function Field({ label, children, wide }: { label: string; children: React.ReactNode; wide?: boolean }) {
  return (
    <label className={`field ${wide ? 'wide' : ''}`}>
      <span>{label}</span>
      {children}
    </label>
  );
}
