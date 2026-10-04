import { useEffect, useRef, useState } from "react";
import { useSession, useAction, query } from "./session";
import { Empty, Field, Inspect, Modal, State, TabPanel, Tick } from "./ui";
import { ModelBudget, RunReview } from "./Director";
import type { Backup, Chapter, Impact, ImportJob, Run, Version } from "./types";
export function Tools({
  chapterId,
  versionId,
  onRun,
  onCommitted,
  onImportsChanged,
  onImportJob,
}: {
  chapterId: string | null;
  versionId: string | null;
  onRun: (id: string) => void;
  onCommitted: () => void;
  onImportsChanged?: () => Promise<void> | void;
  onImportJob?: (job: ImportJob) => void;
}) {
  const [tab, setTab] = useState(versionId ? "impact" : "import");
  useEffect(() => {
    if (versionId) setTab("impact");
  }, [versionId]);
  return (
    <div className="page">
      <div className="page-title">
        <div>
          <small>既有作品与历史修改</small>
          <h1>导入与修复</h1>
        </div>
      </div>
      <TabPanel
        value={tab}
        onChange={setTab}
        tabs={[
          {
            id: "import",
            label: "导入长篇",
            content: (
              <ImportCenter
                onRun={onRun}
                onCommitted={onCommitted}
                onImportsChanged={onImportsChanged}
                onImportJob={onImportJob}
              />
            ),
          },
          {
            id: "impact",
            label: "影响与修复",
            content: (
              <ImpactCenter
                chapterId={chapterId}
                versionId={versionId}
                onRun={onRun}
                onCommitted={onCommitted}
              />
            ),
          },
          { id: "index", label: "语义索引", content: <IndexCenter /> },
        ]}
      />
    </div>
  );
}
export function ImportCenter({
  onRun,
  onCommitted,
  onImportsChanged,
  onImportJob,
}: {
  onRun: (id: string) => void;
  onCommitted: () => void;
  onImportsChanged?: () => Promise<void> | void;
  onImportJob?: (job: ImportJob) => void;
}) {
  const { api, project, branch, notice } = useSession();
  const { act, busy } = useAction();
  const [preview, setPreview] = useState<{
    encoding: string;
    chapters: { title: string; content: string }[];
    warnings: string[];
  } | null>(null);
  const [job, setJob] = useState<ImportJob | null>(null);
  const [jobs, setJobs] = useState<ImportJob[]>([]);
  const completed = useRef(new Set<string>());
  const [provider, setProvider] = useState("");
  const [profile, setProfile] = useState("");
  const [budget, setBudget] = useState(100000);
  const [ids, setIds] = useState("");
  const [run, setRun] = useState<string | null>(null);
  const [chapterIndex, setChapterIndex] = useState(0);
  const [splitLine, setSplitLine] = useState(1);
  useEffect(() => {
    let alive = true;
    setJob(null);
    setPreview(null);
    completed.current.clear();
    void act(async () => {
      const history = await api.get<ImportJob[]>(
        `/projects/${project.id}/imports?${query({ branch_id: branch })}`,
      );
      if (alive) {
        setJobs(history);
        setJob(history[0] ?? null);
      }
    });
    return () => {
      alive = false;
    };
  }, [api, project.id, branch]);
  useEffect(() => {
    if (job)
      setJobs((history) =>
        history.map((item) => (item.id === job.id ? job : item)),
      );
  }, [job]);
  useEffect(() => {
    if (job?.status !== "completed" || completed.current.has(job.id)) return;
    completed.current.add(job.id);
    void act(async () => {
      await onImportsChanged?.();
      notice(
        onImportsChanged
          ? "正文导入完成，章节目录已更新；候选记忆仍需核查"
          : "正文导入完成，候选记忆仍需核查",
      );
    });
  }, [job?.id, job?.status]);
  useEffect(() => {
    if (!job || !["queued", "running", "paused"].includes(job.status)) return;
    let alive = true;
    let polling = false;
    const timer = setInterval(() => {
      if (polling) return;
      polling = true;
      void act(async () => {
        try {
          const latest = await api.get<ImportJob>(`/imports/${job.id}`);
          if (alive) setJob(latest);
        } finally {
          polling = false;
        }
      });
    }, 2000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [api, project.id, branch, job?.id, job?.status]);
  const change = (field: "title" | "content", value: string) =>
    setPreview((p) =>
      p
        ? {
            ...p,
            chapters: p.chapters.map((c, i) =>
              i === chapterIndex ? { ...c, [field]: value } : c,
            ),
          }
        : p,
    );
  return (
    <div className="tool-content">
      <p>
        TXT / Markdown
        由本地后端检测编码与分章。导入正文后，模型提取的记忆仍需作者核查。
      </p>
      <Field label="选择作品文件">
        <input
          type="file"
          accept=".txt,.md,.markdown"
          disabled={busy}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file)
              void act(async () => {
                const body = new FormData();
                body.append("file", file);
                setPreview(
                  await api.request("/imports/preview", {
                    method: "POST",
                    body,
                  }),
                );
                setChapterIndex(0);
              });
          }}
        />
      </Field>
      {preview && (
        <>
          <p>
            编码 {preview.encoding} · {preview.chapters.length} 章
          </p>
          {preview.warnings.map((w, i) => (
            <p key={i} className="notice">
              {w}
            </p>
          ))}
          <div className="import-preview">
            <div className="import-boundaries">
              {preview.chapters.map((c, i) => (
                <button
                  key={i}
                  onClick={() => setChapterIndex(i)}
                  className={i === chapterIndex ? "active" : ""}
                >
                  {i + 1}. {c.title}
                </button>
              ))}
            </div>
            <div>
              {preview.chapters[chapterIndex] && (
                <>
                  <Field label="章节标题">
                    <input
                      value={preview.chapters[chapterIndex].title}
                      onChange={(e) => change("title", e.target.value)}
                    />
                  </Field>
                  <Field label="章节内容 / 分章边界">
                    <textarea
                      className="import-content"
                      value={preview.chapters[chapterIndex].content}
                      onChange={(e) => change("content", e.target.value)}
                    />
                  </Field>
                  <div className="actions">
                    <input
                      className="small-input"
                      type="number"
                      min={1}
                      aria-label="拆分起始行"
                      value={splitLine}
                      onChange={(e) => setSplitLine(+e.target.value)}
                    />
                    <button
                      onClick={() => {
                        const chapter = preview.chapters[chapterIndex];
                        const lines = chapter.content.split("\n");
                        if (splitLine <= 0 || splitLine >= lines.length) return;
                        const chapters = [...preview.chapters];
                        chapters.splice(
                          chapterIndex,
                          1,
                          {
                            title: chapter.title,
                            content: lines.slice(0, splitLine).join("\n"),
                          },
                          {
                            title: `${chapter.title}（续）`,
                            content: lines.slice(splitLine).join("\n"),
                          },
                        );
                        setPreview({ ...preview, chapters });
                      }}
                    >
                      在此行后拆分
                    </button>
                    <button
                      disabled={chapterIndex === 0}
                      onClick={() => {
                        const chapters = [...preview.chapters];
                        chapters[chapterIndex - 1] = {
                          ...chapters[chapterIndex - 1],
                          content:
                            chapters[chapterIndex - 1].content +
                            "\n\n" +
                            chapters[chapterIndex].content,
                        };
                        chapters.splice(chapterIndex, 1);
                        setPreview({ ...preview, chapters });
                        setChapterIndex(chapterIndex - 1);
                      }}
                    >
                      并入前章
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
          <button
            className="primary"
            disabled={
              busy ||
              !preview.chapters.length ||
              (!!job && ["running", "queued"].includes(job.status))
            }
            onClick={() =>
              void act(async () => {
                const created = await api.post<ImportJob>(
                  `/projects/${project.id}/imports`,
                  {
                    chapters: preview.chapters,
                    branch_id: branch,
                  },
                );
                setJob(created);
                setJobs((history) => [
                  created,
                  ...history.filter((item) => item.id !== created.id),
                ]);
                onImportJob?.(created);
                notice(
                  "导入任务已保存并在后台进行；可离开页面，返回后查看或暂停任务",
                );
              })
            }
          >
            确认分章并导入正文
          </button>
        </>
      )}
      {jobs.length > 1 && (
        <Field label="导入任务历史">
          <select
            value={job?.id ?? ""}
            onChange={(event) =>
              setJob(
                jobs.find((item) => item.id === event.target.value) ?? null,
              )
            }
          >
            {jobs.map((item) => (
              <option key={item.id} value={item.id}>
                {item.id} · {item.completed}/{item.total} 章
              </option>
            ))}
          </select>
        </Field>
      )}
      {job && (
        <section className="tool-section">
          <div className="row">
            <h3>导入任务</h3>
            <State value={job.status} />
          </div>
          <p>
            {job.completed} / {job.total} 章
          </p>
          {["queued", "running", "paused"].includes(job.status) && (
            <p className="muted">
              任务已保存，可离开本页；返回导入页可继续查看、暂停或恢复。
            </p>
          )}
          {job.error && <p role="alert">{job.error}</p>}
          <div className="actions">
            {["running", "queued"].includes(job.status) && (
              <button
                disabled={busy}
                onClick={() =>
                  void act(async () => {
                    const changed = await api.post<ImportJob>(
                      `/imports/${job.id}/pause`,
                    );
                    setJob(changed);
                    onImportJob?.(changed);
                  })
                }
              >
                暂停
              </button>
            )}
            {job.status === "paused" && (
              <button
                disabled={busy}
                onClick={() =>
                  void act(async () => {
                    const changed = await api.post<ImportJob>(
                      `/imports/${job.id}/resume`,
                    );
                    setJob(changed);
                    onImportJob?.(changed);
                  })
                }
              >
                继续导入
              </button>
            )}
            <button
              onClick={() =>
                void act(async () => {
                  await onImportsChanged?.();
                })
              }
            >
              刷新章节目录
            </button>
          </div>
        </section>
      )}
      <section className="tool-section">
        <h2>提取候选记忆</h2>
        <p>
          模型从已导入正文建立人物、规则、时间线与伏笔候选；不自动推定回收意图。
        </p>
        <Field label="优先分析的章节标识（逗号分隔；留空分析全部）">
          <input value={ids} onChange={(e) => setIds(e.target.value)} />
        </Field>
        <ModelBudget
          provider={provider}
          onProvider={setProvider}
          budget={budget}
          onBudget={setBudget}
          profile={profile}
          onProfile={setProfile}
        />
        <button
          className="primary"
          disabled={busy || !provider || budget <= 0}
          onClick={() =>
            void act(async () => {
              const result = await api.post<Run>(
                `/projects/${project.id}/imports/analyze`,
                {
                  chapter_ids: ids.trim()
                    ? ids.split(/[,，]/).map((s) => s.trim())
                    : undefined,
                  provider_id: provider,
                  token_budget: budget,
                  profile_id: profile || undefined,
                },
              );
              setRun(result.id);
              onRun(result.id);
            })
          }
        >
          开始提取与核查
        </button>
        {run && <RunReview runId={run} onCommitted={onCommitted} />}
      </section>
    </div>
  );
}
function ImpactCenter({
  chapterId,
  versionId,
  onRun,
  onCommitted,
}: {
  chapterId: string | null;
  versionId: string | null;
  onRun: (id: string) => void;
  onCommitted: () => void;
}) {
  const { api, project, branch, refresh, notice } = useSession();
  const { busy, act } = useAction();
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [chapter, setChapter] = useState(chapterId ?? "");
  const [versions, setVersions] = useState<Version[]>([]);
  const [version, setVersion] = useState(versionId ?? "");
  const [impact, setImpact] = useState<Impact | null>(null);
  const [knownImpacts, setKnownImpacts] = useState<Impact[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [reason, setReason] = useState("");
  const [provider, setProvider] = useState("");
  const [budget, setBudget] = useState(50000);
  const [run, setRun] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const loadImpacts = async () =>
    setKnownImpacts(await api.get(`/projects/${project.id}/impact`));
  useEffect(() => {
    void act(loadImpacts);
  }, [project.id, project.revision]);
  useEffect(() => {
    void act(async () => {
      const result = await api.get<{ items: Chapter[]; total: number }>(
        `/projects/${project.id}/chapters?${query({ branch_id: branch, offset, limit: 100 })}`,
      );
      setChapters(result.items);
      setTotal(result.total);
    });
  }, [project.id, branch, offset]);
  useEffect(() => {
    if (chapter)
      void act(async () => {
        setVersions(await api.get(`/chapters/${chapter}/versions`));
      });
  }, [chapter]);
  useEffect(() => {
    if (chapterId) setChapter(chapterId);
    if (versionId) setVersion(versionId);
  }, [chapterId, versionId]);
  return (
    <div className="tool-content">
      <p>先分析候选正文对后续的影响。直接依赖和推测影响分别展示；原稿保留。</p>
      <Field label="已有影响分析（重启后仍可处理）">
        <select
          value={impact?.id ?? ""}
          onChange={(e) => {
            setImpact(
              knownImpacts.find((i) => i.id === e.target.value) ?? null,
            );
            setSelected(new Set());
          }}
        >
          <option value="">选择已保存的影响分析</option>
          {knownImpacts.map((i) => (
            <option key={i.id} value={i.id}>
              {i.source_record_id ? "资料修改" : "正文修改"} · {i.status} ·{" "}
              {i.items.length} 章 · {i.id.slice(0, 8)}
            </option>
          ))}
        </select>
      </Field>
      <div className="form-grid">
        <Field label="修改的章节">
          <select
            value={chapter}
            onChange={(e) => {
              setChapter(e.target.value);
              setVersion("");
              setImpact(null);
            }}
          >
            <option value="">选择章节</option>
            {chapters.map((c) => (
              <option key={c.id} value={c.id}>
                {c.number}. {c.title}
                {c.blocked ? "（等待修复）" : ""}
              </option>
            ))}
          </select>
        </Field>
        <Field label="候选版本">
          <select value={version} onChange={(e) => setVersion(e.target.value)}>
            <option value="">选择版本</option>
            {versions.map((v) => (
              <option key={v.id} value={v.id}>
                {new Date(v.created_at).toLocaleString()} · {v.status} ·{" "}
                {v.id.slice(0, 8)}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <div className="actions">
        <button
          disabled={offset === 0}
          onClick={() => setOffset(Math.max(0, offset - 100))}
        >
          前 100 章
        </button>
        <span>
          {offset + 1}—{Math.min(total, offset + 100)} / {total}
        </span>
        <button
          disabled={offset + 100 >= total}
          onClick={() => setOffset(offset + 100)}
        >
          后 100 章
        </button>
        <button
          className="primary"
          disabled={busy || !chapter || !version}
          onClick={() =>
            void act(async () => {
              setImpact(
                await api.post(`/chapters/${chapter}/impact`, {
                  version_id: version,
                  expected_revision: project.revision,
                }),
              );
              setSelected(new Set());
              await refresh();
              await loadImpacts();
            })
          }
        >
          分析修改影响
        </button>
      </div>
      {impact && (
        <section className="tool-section">
          <div className="row">
            <h2>受影响范围</h2>
            <State value={impact.status} />
          </div>
          <Inspect value={impact.coverage} />
          {impact.items.length === 0 ? (
            <Empty>
              未发现结构化依赖。请继续核对无法自动判断的文学层面影响。
            </Empty>
          ) : (
            impact.items.map((item) => (
              <article className="record" key={item.chapter_id}>
                <Tick
                  checked={selected.has(item.chapter_id)}
                  onChange={(v) => {
                    const next = new Set(selected);
                    v
                      ? next.add(item.chapter_id)
                      : next.delete(item.chapter_id);
                    setSelected(next);
                  }}
                  label={
                    <strong>
                      第 {item.number} 章 · {item.title} ·{" "}
                      {item.kind === "direct" ? "直接影响" : "推测影响"}
                    </strong>
                  }
                />
                <p>{item.reason}</p>
              </article>
            ))
          )}
          <Field label="人工核查说明">
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </Field>
          <button
            disabled={busy || !reason.trim() || !selected.size}
            onClick={() =>
              void act(async () => {
                await api.post(`/impact/${impact.id}/resolve`, {
                  expected_revision: project.revision,
                  chapter_ids: [...selected],
                  reason,
                });
                await refresh();
                notice("所选影响已记录人工核查结果");
                onCommitted();
              })
            }
          >
            记录所选章节已核查
          </button>
          <h3>为所选章节生成修复候选</h3>
          <ModelBudget
            provider={provider}
            onProvider={setProvider}
            budget={budget}
            onBudget={setBudget}
          />
          <button
            className="primary"
            disabled={busy || !provider || !selected.size || budget <= 0}
            onClick={() =>
              void act(async () => {
                const result = await api.post<Run>(
                  `/impact/${impact.id}/repairs`,
                  {
                    chapter_ids: [...selected],
                    provider_id: provider,
                    token_budget: budget,
                  },
                );
                setRun(result.id);
                onRun(result.id);
              })
            }
          >
            生成修复候选并审核
          </button>
          {run && <RunReview runId={run} onCommitted={onCommitted} />}
        </section>
      )}
    </div>
  );
}
function IndexCenter() {
  const { api, project, branch, providers, notice } = useSession();
  const { act, busy } = useAction();
  const [provider, setProvider] = useState("");
  const [budget, setBudget] = useState(100000);
  const [job, setJob] = useState<{
    id: string;
    status: string;
    completed?: number;
    total?: number;
    error?: string;
  } | null>(null);
  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.status)) return;
    const timer = setInterval(
      () => void act(async () => setJob(await api.get(`/index/${job.id}`))),
      3000,
    );
    return () => clearInterval(timer);
  }, [job?.id, job?.status]);
  return (
    <div className="tool-content">
      <h2>语义索引</h2>
      <p>
        需要配置嵌入模型。更换模型会建立独立索引；结构化证据与全文检索持续可用。
      </p>
      <Field label="嵌入服务">
        <select value={provider} onChange={(e) => setProvider(e.target.value)}>
          <option value="">选择已配置嵌入模型的服务</option>
          {providers
            .filter((p) => p.embedding_model)
            .map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} / {p.embedding_model}
              </option>
            ))}
        </select>
      </Field>
      <button
        disabled={busy || !provider || budget <= 0}
        onClick={() =>
          void act(async () => {
            setJob(
              await api.post(`/projects/${project.id}/index`, {
                provider_id: provider,
                token_budget: budget,
                branch_id: branch,
              }),
            );
            notice("索引任务已创建");
          })
        }
      >
        重建语义索引
      </button>
      <Field label="索引 Token 上限">
        <input
          type="number"
          min={1}
          value={budget}
          onChange={(e) => setBudget(+e.target.value)}
        />
      </Field>
      {job && (
        <div>
          <State value={job.status} />
          <p>
            {job.completed ?? 0} / {job.total ?? "待计算"}
          </p>
          {job.error && <p role="alert">{job.error}</p>}
        </div>
      )}
    </div>
  );
}
export function BackupCenter() {
  const { api, project, branch, refresh, notice } = useSession();
  const { act, busy } = useAction();
  const [backups, setBackups] = useState<Backup[]>([]);
  const [restore, setRestore] = useState<Backup | null>(null);
  const [confirmation, setConfirmation] = useState("");
  const load = async () => setBackups(await api.get("/backups"));
  useEffect(() => {
    void act(load);
  }, []);
  return (
    <div className="tool-content">
      <h2>备份与导出</h2>
      <p>项目备份包含本地作品、记忆与版本历史。导出只包含已确认章节。</p>
      <div className="actions">
        <button
          disabled={busy}
          onClick={() =>
            void act(async () => {
              await api.post("/backups", { automatic: false });
              await load();
              notice("完整项目备份已创建");
            })
          }
        >
          创建完整备份
        </button>
        <button
          disabled={busy}
          onClick={() =>
            void act(() =>
              api.download(
                `/projects/${project.id}/export?${query({ format: "txt", branch_id: branch })}`,
                `${project.title}.txt`,
              ),
            )
          }
        >
          导出 TXT
        </button>
        <button
          disabled={busy}
          onClick={() =>
            void act(() =>
              api.download(
                `/projects/${project.id}/export?${query({ format: "md", branch_id: branch })}`,
                `${project.title}.md`,
              ),
            )
          }
        >
          导出 Markdown
        </button>
      </div>
      {backups.length === 0 ? (
        <Empty>尚无备份。创建完整备份后可以下载与恢复。</Empty>
      ) : (
        backups.map((b) => (
          <div className="version-row" key={b.id}>
            <span>
              {b.name} · {new Date(b.created_at).toLocaleString()}
            </span>
            <div className="actions">
              <button
                disabled={busy}
                onClick={() =>
                  void act(() =>
                    api.download(`/backups/${b.id}/download`, b.name),
                  )
                }
              >
                下载
              </button>
              <button
                onClick={() => {
                  setRestore(b);
                  setConfirmation("");
                }}
              >
                恢复
              </button>
            </div>
          </div>
        ))
      )}
      <Modal
        open={!!restore}
        onOpenChange={(v) => !v && setRestore(null)}
        title="恢复完整备份"
      >
        <p>
          将从「{restore?.name}
          」恢复整个本地数据库，覆盖当前工作数据。恢复前后端会创建备份；API
          密钥不会从备份恢复。
        </p>
        <Field label="输入 RESTORE 确认恢复">
          <input
            value={confirmation}
            onChange={(e) => setConfirmation(e.target.value)}
          />
        </Field>
        <button
          className="danger-button"
          disabled={busy || confirmation !== "RESTORE"}
          onClick={() =>
            void act(async () => {
              await api.post(`/backups/${restore!.id}/restore`, {
                confirmation,
              });
              setRestore(null);
              await refresh();
              await load();
              notice("备份恢复完成，请重新选择作品");
            })
          }
        >
          恢复数据库
        </button>
      </Modal>
    </div>
  );
}
