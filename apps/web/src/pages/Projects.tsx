import React, { useCallback, useEffect, useState } from 'react';
import { createNovel, createProject, getNovels, getProjects } from '../api/client';
import { useStudioStore } from '../store/useStudioStore';

const emptyForm = {
  name: '',
  description: '',
  target_platform: '番茄小说',
  target_audience: '18-35 岁网文读者',
  expected_word_count: 300000,
  protagonist_type: '',
  reference_style: '',
};

export default function Projects() {
  const selectProject = useStudioStore((s) => s.selectProject);
  const setError = useStudioStore((s) => s.setError);
  const [projects, setProjects] = useState<any[]>([]);
  const [novelCounts, setNovelCounts] = useState<Record<number, number>>({});
  const [form, setForm] = useState(emptyForm);
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(async () => {
    try {
      const rows = await getProjects();
      setProjects(rows);
      const counts: Record<number, number> = {};
      for (const project of rows) {
        counts[project.id] = (await getNovels(project.id)).length;
      }
      setNovelCounts(counts);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载项目失败');
    }
  }, [setError]);

  useEffect(() => {
    load();
  }, [load]);

  const submit = async () => {
    if (!form.name.trim()) {
      setError('项目名称不能为空');
      return;
    }
    setCreating(true);
    try {
      const project = await createProject({
        ...form,
        pleasure_points: ['成长升级', '强冲突', '章节钩子'],
        forbidden_tropes: ['无意义水文', '人物降智', '设定自相矛盾'],
      });
      await createNovel({
        project_id: project.id,
        title: form.name,
        genre: '玄幻',
        synopsis: form.description,
        target_word_count: form.expected_word_count,
      });
      setForm(emptyForm);
      setShowForm(false);
      await load();
      selectProject(project.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建项目失败');
    } finally {
      setCreating(false);
    }
  };

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Project Library</p>
          <h1>项目管理</h1>
          <p className="muted">每个项目代表一套长篇小说生产计划，可包含多本小说或不同版本。</p>
        </div>
        <button className="button primary" onClick={() => setShowForm(true)}>新建项目</button>
      </header>

      {showForm && (
        <div className="panel form-panel">
          <div className="panel-title">
            <h2>新建小说项目</h2>
            <button className="text-button" onClick={() => setShowForm(false)}>收起</button>
          </div>
          <div className="form-grid">
            <Field label="项目名称">
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="例如：星墟行者" />
            </Field>
            <Field label="目标平台">
              <select value={form.target_platform} onChange={(e) => setForm({ ...form, target_platform: e.target.value })}>
                <option>番茄小说</option>
                <option>起点中文网</option>
                <option>晋江文学城</option>
                <option>自定义平台</option>
              </select>
            </Field>
            <Field label="目标读者">
              <input value={form.target_audience} onChange={(e) => setForm({ ...form, target_audience: e.target.value })} />
            </Field>
            <Field label="预计字数">
              <input type="number" value={form.expected_word_count} onChange={(e) => setForm({ ...form, expected_word_count: Number(e.target.value) || 0 })} />
            </Field>
            <Field label="主角类型">
              <input value={form.protagonist_type} onChange={(e) => setForm({ ...form, protagonist_type: e.target.value })} placeholder="普通人逆袭、重生、天才流..." />
            </Field>
            <Field label="参考风格">
              <input value={form.reference_style} onChange={(e) => setForm({ ...form, reference_style: e.target.value })} placeholder="节奏、叙事口味或参考作者" />
            </Field>
            <Field label="简介" wide>
              <textarea rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </Field>
          </div>
          <div className="form-actions">
            <button className="button secondary" onClick={() => setShowForm(false)}>取消</button>
            <button className="button primary" onClick={submit} disabled={creating}>{creating ? '创建中...' : '创建并进入设定'}</button>
          </div>
        </div>
      )}

      {projects.length === 0 ? (
        <div className="empty-state">
          <h2>还没有项目</h2>
          <p>先创建一个项目，系统会自动生成一本同名小说，方便你马上进入设定和章节工作流。</p>
          <button className="button primary" onClick={() => setShowForm(true)}>创建第一个项目</button>
        </div>
      ) : (
        <div className="card-grid">
          {projects.map((project) => (
            <button key={project.id} className="project-card" onClick={() => selectProject(project.id)}>
              <div className="card-topline">
                <span className="badge">{project.target_platform || '未设平台'}</span>
                <span>{novelCounts[project.id] || 0} 本小说</span>
              </div>
              <h2>{project.name}</h2>
              <p>{project.description || '暂无简介。'}</p>
              <div className="card-meta">
                <span>{project.expected_word_count ? `${project.expected_word_count.toLocaleString()} 字` : '未设字数'}</span>
                <span>{new Date(project.created_at).toLocaleDateString('zh-CN')}</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </section>
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
