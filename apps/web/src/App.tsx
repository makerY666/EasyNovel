import { useEffect, useRef, useState } from "react";
import {
  BookOpen,
  PenLine,
  LibraryBig,
  FolderInput,
  Settings2,
  Archive,
  PanelRightClose,
  Plus,
  RefreshCw,
} from "lucide-react";
import {
  Api,
  ApiError,
  bootstrap,
  bootstrapBrowser,
  type BackendConfig,
} from "./api";
import { SessionContext, query } from "./session";
import { Badge, Choice, Empty, Field, Modal, State, TabPanel } from "./ui";
import type {
  Branch,
  Chapter,
  ImportJob,
  Profile,
  Project,
  Provider,
  Run,
} from "./types";
import { NovelEditor } from "./NovelEditor";
import { ChapterWorkspace } from "./ChapterWorkspace";
import { stageLabel } from "./runPresentation";
import { Director, Evidence } from "./Director";
import { Records } from "./Records";
import { Settings } from "./Settings";
import { BackupCenter, Tools } from "./Tools";
import { ImportMonitor } from "./ImportMonitor";
export default function App() {
  const [api, setApi] = useState<Api | null>(() => {
    const config = bootstrapBrowser();
    return config ? new Api(config) : null;
  });
  const [booting, setBooting] = useState(true);
  const [token, setToken] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState(
    localStorage.getItem("easynovel.project") ?? "",
  );
  const [project, setProject] = useState<Project | null>(null);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [chapterId, setChapterId] = useState<string | null>(
    localStorage.getItem("easynovel.chapter"),
  );
  const [branch, setBranch] = useState("main");
  const [branches, setBranches] = useState<Branch[]>([]);
  const [view, setView] = useState("projects");
  const [createProject, setCreateProject] = useState(false);
  const [createChapter, setCreateChapter] = useState(false);
  const [createBranch, setCreateBranch] = useState(false);
  const [backup, setBackup] = useState(false);
  const [busy, setBusy] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [previewRequest, setPreviewRequest] = useState(0);
  const [side, setSide] = useState("director");
  const [sideVisible, setSideVisible] = useState(() =>
    localStorage.getItem("easynovel.evidence.visible") !== null
      ? localStorage.getItem("easynovel.evidence.visible") === "true"
      : window.innerWidth >= 1400,
  );
  const [reload, setReload] = useState(0);
  const [impactVersion, setImpactVersion] = useState<string | null>(null);
  const [importJobs, setImportJobs] = useState<ImportJob[]>([]);
  const [importSignal, setImportSignal] = useState(0);
  const sideManual = useRef(
    localStorage.getItem("easynovel.evidence.visible") !== null,
  );
  const [health, setHealth] = useState<{
    version: string;
    semantic_search: boolean;
    legacy_database_detected: boolean;
  } | null>(null);
  useEffect(() => {
    const resized = () => {
      if (!sideManual.current) setSideVisible(window.innerWidth >= 1400);
    };
    window.addEventListener("resize", resized);
    return () => window.removeEventListener("resize", resized);
  }, []);
  const report = (e: unknown) =>
    setError(
      e instanceof ApiError && e.status === 401
        ? "401：本地服务会话已失效，请重新连接。"
        : e instanceof ApiError && e.status === 409
          ? `${e.message}。作品版本已变化；候选与本地文本保留，请刷新后核对。`
          : e instanceof Error
            ? e.message
            : String(e),
    );
  const execute = async (work: () => Promise<void>) => {
    setBusy(true);
    setError("");
    try {
      await work();
    } catch (e) {
      report(e);
    } finally {
      setBusy(false);
    }
  };
  const notice = (s: string) => {
    setMessage(s);
  };
  useEffect(() => {
    let alive = true;
    const connectSession = () => {
      const config = bootstrapBrowser();
      if (config) {
        setError("");
        setApi(new Api(config));
        setBooting(false);
        return;
      }
      void bootstrap()
        .then((config) => {
          if (alive && config) {
            setError("");
            setApi(new Api(config));
          }
        })
        .catch((error) => {
          if (alive) report(error);
        })
        .finally(() => {
          if (alive) setBooting(false);
        });
    };
    const onHashChange = () => {
      if (new URLSearchParams(window.location.hash.slice(1)).has("session"))
        connectSession();
    };
    if (!api) connectSession();
    else setBooting(false);
    window.addEventListener("hashchange", onHashChange);
    return () => {
      alive = false;
      window.removeEventListener("hashchange", onHashChange);
    };
  }, []);
  const refresh = async () => {
    if (!api) return;
    const [ps, pv, pf] = await Promise.all([
      api.get<Project[]>("/projects"),
      api.get<Provider[]>("/providers"),
      api.get<Profile[]>("/profiles"),
    ]);
    setProjects(ps);
    setProviders(pv);
    setProfiles(pf);
    if (projectId) {
      const current = ps.find((p) => p.id === projectId);
      setProject(current ?? null);
    } else if (ps.length) {
      setProjectId(ps[0].id);
      setProject(ps[0]);
    }
  };
  useEffect(() => {
    if (api)
      void execute(async () => {
        setHealth(await api.get("/health"));
        await refresh();
      });
  }, [api]);
  useEffect(() => {
    if (api && projectId) {
      localStorage.setItem("easynovel.project", projectId);
      void execute(async () => {
        setProject(await api.get(`/projects/${projectId}`));
        setBranches(await api.get(`/projects/${projectId}/branches`));
      });
    }
  }, [api, projectId]);
  const loadChapters = async () => {
    if (!api || !projectId) return;
    const result = await api.get<{ items: Chapter[]; total: number }>(
      `/projects/${projectId}/chapters?${query({ branch_id: branch, offset, limit: 100 })}`,
    );
    setChapters(result.items);
    setTotal(result.total);
  };
  useEffect(() => {
    if (api && projectId) void execute(loadChapters);
  }, [api, projectId, branch, offset, reload]);
  useEffect(() => {
    if (!api || !runId) {
      setRun(null);
      return;
    }
    setRun(null);
    let alive = true;
    const fetchRun = () =>
      api
        .get<Run>(`/runs/${runId}`)
        .then((r) => {
          if (alive) setRun(r);
        })
        .catch(report);
    void fetchRun();
    const timer = setInterval(() => void fetchRun(), 3000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [api, runId]);
  const guard = () =>
    new Promise<boolean>((resolve) => {
      if (view === "write" && chapterId)
        window.dispatchEvent(
          new CustomEvent("easynovel-before-switch", { detail: { resolve } }),
        );
      else resolve(true);
    });
  const navigate = async (next: string) => {
    if (await guard()) {
      if (next === "write" && projectId) {
        try {
          await Promise.all([loadChapters(), refresh()]);
          setImportSignal((value) => value + 1);
        } catch (error) {
          report(error);
          return;
        }
      }
      setView(next);
      setError("");
      if (
        view === "tools" &&
        next !== "tools" &&
        importJobs.some((job) =>
          ["queued", "running", "paused"].includes(job.status),
        )
      )
        notice(
          "导入任务已保存，后台导入仍可继续；返回导入页可查看、暂停或恢复。",
        );
    }
  };
  const selectChapter = async (id: string) => {
    if (id !== chapterId && !(await guard())) return;
    if (id !== chapterId) setRunId(null);
    setChapterId(id);
    localStorage.setItem("easynovel.chapter", id);
    setView("write");
    setImpactVersion(null);
  };
  const committed = () => {
    setReload((n) => n + 1);
    void refresh();
  };
  const importsChanged = async () => {
    await Promise.all([loadChapters(), refresh()]);
  };
  const connect = async (config: BackendConfig) => {
    setConnecting(true);
    try {
      const next = new Api(config);
      await next.get("/health");
      sessionStorage.setItem("easynovel.token", config.token);
      setApi(next);
      setError("");
    } catch (e) {
      report(e);
    } finally {
      setConnecting(false);
    }
  };
  if (booting)
    return (
      <div className="startup">
        <BookOpen size={32} />
        <h1>EasyNovel</h1>
        <p>连接本地小说工作站…</p>
      </div>
    );
  if (!api)
    return (
      <div className="startup">
        <BookOpen size={36} />
        <h1>EasyNovel</h1>
        <p>本地小说工作站</p>
        <form
          className="connect-form"
          onSubmit={(e) => {
            e.preventDefault();
            void connect({ base_url: "", token });
          }}
        >
          <Field
            label="开发服务会话令牌"
            hint="双击“启动.cmd”可自动打开并连接工作站。手动令牌仅用于自行启动开发服务；桌面安装版自动连接。"
          >
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              autoComplete="off"
              required
            />
          </Field>
          <button className="primary" disabled={connecting}>
            {connecting ? "正在连接…" : "连接本地服务"}
          </button>
        </form>
        {error && (
          <p role="alert" className="error-inline">
            {error}
          </p>
        )}
      </div>
    );
  const nav = [
    ["projects", "作品", BookOpen],
    ["write", "写作", PenLine],
    ["records", "故事资料", LibraryBig],
    ["tools", "导入与修复", FolderInput],
    ["settings", "设置", Settings2],
  ] as const;
  const shell = (
    <>
      {project && (
        <ImportMonitor
          api={api}
          projectId={project.id}
          branch={branch}
          signal={importSignal}
          onChanged={importsChanged}
          onJobs={setImportJobs}
          onError={report}
        />
      )}
      <aside className="main-rail">
        <div className="brand" title="EasyNovel">
          EN
        </div>
        {nav.map(([id, label, Icon]) => (
          <button
            key={id}
            onClick={() => void navigate(id)}
            disabled={!project && id !== "projects"}
            className={view === id ? "active" : ""}
            aria-current={view === id ? "page" : undefined}
          >
            <Icon size={20} />
            <span>{label}</span>
          </button>
        ))}
        <div className="rail-spacer" />
        <button onClick={() => setBackup(true)} disabled={!project}>
          <Archive size={20} />
          <span>备份导出</span>
        </button>
      </aside>
      <div className="application">
        <header className="topbar">
          <span className="app-title">
            EasyNovel <small>小说工作站</small>
          </span>
          <select
            aria-label="当前作品"
            value={projectId}
            onChange={(e) =>
              void execute(async () => {
                if (!(await guard())) return;
                setProjectId(e.target.value);
                setChapterId(null);
                setBranch("main");
                setOffset(0);
                setRunId(null);
                setView("projects");
              })
            }
          >
            <option value="">选择作品</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title}
              </option>
            ))}
          </select>
          <button onClick={() => setCreateProject(true)}>
            <Plus size={14} />
            新建作品
          </button>
          <div className="topbar-space" />
          {project && (
            <span className="muted">
              {project.mode === "serial" ? "长篇网文" : "精品长篇"} · 修订{" "}
              {project.revision}
            </span>
          )}
          <button
            className="icon-button"
            disabled={busy}
            onClick={() =>
              void execute(async () => {
                await refresh();
                await loadChapters();
              })
            }
            aria-label="刷新"
          >
            <RefreshCw size={16} />
          </button>
        </header>
        {error && (
          <div className="error-banner" role="alert">
            <span>{error}</span>
            <button onClick={() => setError("")}>关闭</button>
            {error.includes("401") || error.includes("令牌") ? (
              <button
                onClick={() => {
                  sessionStorage.removeItem("easynovel.token");
                  setApi(null);
                }}
              >
                重新连接
              </button>
            ) : null}
          </div>
        )}
        {message && (
          <div className="message-banner" role="status">
            <span>{message}</span>
            <button onClick={() => setMessage("")}>关闭</button>
          </div>
        )}
        <main className={`main-content ${view === "write" ? "writing" : ""}`}>
          {view === "projects" && (
            <div className="page">
              <div className="page-title">
                <div>
                  <small>作品与创作入口</small>
                  <h1>{project?.title ?? "开始一部作品"}</h1>
                </div>
                <button
                  className="primary"
                  onClick={() => setCreateProject(true)}
                >
                  新建作品
                </button>
              </div>
              {project ? (
                <>
                  <p className="description">
                    {project.description ||
                      "在设置中补充作品的主题、读者与创作方向。"}
                  </p>
                  <div className="project-actions">
                    <button
                      onClick={() => {
                        if (chapters[0])
                          void selectChapter(chapterId ?? chapters[0].id);
                        else setCreateChapter(true);
                      }}
                    >
                      <PenLine size={20} />
                      进入写作
                    </button>
                    <button onClick={() => setView("records")}>
                      <LibraryBig size={20} />
                      整理故事资料
                    </button>
                    <button onClick={() => setView("tools")}>
                      <FolderInput size={20} />
                      导入已有作品
                    </button>
                    <button onClick={() => setView("settings")}>
                      <Settings2 size={20} />
                      配置模型与预算
                    </button>
                  </div>
                  <section className="tool-section">
                    <h2>创作顺序</h2>
                    <ol className="steps">
                      <li>建立人物、世界规则与主线目标。</li>
                      <li>创建章节，下达任务，直接写正文或先审核场景计划。</li>
                      <li>查看正文、审稿意见与候选记忆。</li>
                      <li>确认入库，再继续下一章。</li>
                    </ol>
                  </section>
                  {health?.legacy_database_detected && (
                    <section className="tool-section">
                      <h3>发现旧版数据库</h3>
                      <p>迁移前生成备份，旧记忆作为待核查资料保留。</p>
                      <button
                        disabled={busy}
                        onClick={() =>
                          void execute(async () => {
                            const result = await api.post<{ count: number }>(
                              "/legacy/import",
                            );
                            await refresh();
                            notice(`旧版数据导入完成：${result.count} 条`);
                          })
                        }
                      >
                        备份并导入旧数据
                      </button>
                    </section>
                  )}
                </>
              ) : (
                <Empty>
                  新建作品，或者创建作品后导入 TXT / Markdown 长篇。
                </Empty>
              )}
            </div>
          )}
          {project && view === "write" && (
            <>
              <aside className="chapter-nav">
                <div className="chapter-nav-head">
                  <h2>作品目录</h2>
                  <button
                    aria-label="添加章节"
                    className="icon-button"
                    onClick={() => setCreateChapter(true)}
                  >
                    <Plus size={17} />
                  </button>
                </div>
                <Field label="故事分支">
                  <select
                    value={branch}
                    onChange={(e) =>
                      void execute(async () => {
                        if (!(await guard())) return;
                        setBranch(e.target.value);
                        setChapterId(null);
                        setOffset(0);
                      })
                    }
                  >
                    <option value="main">主线</option>
                    {branches
                      .filter((b) => b.id !== "main")
                      .map((b) => (
                        <option key={b.id} value={b.id}>
                          {b.name}
                        </option>
                      ))}
                  </select>
                </Field>
                <button
                  className="link-button"
                  onClick={() => setCreateBranch(true)}
                >
                  创建备选分支
                </button>
                <div className="chapter-list">
                  {chapters.length === 0 ? (
                    <Empty>添加章节开始写作。</Empty>
                  ) : (
                    chapters.map((c) => (
                      <button
                        className={chapterId === c.id ? "active" : ""}
                        key={c.id}
                        onClick={() => void selectChapter(c.id)}
                      >
                        <span className="chapter-number">{c.number}</span>
                        <span>
                          {c.title}
                          <small>
                            {c.blocked
                              ? "等待影响修复"
                              : c.confirmed_version_id &&
                                  c.confirmed_version_id === c.draft_version_id
                                ? "已确认"
                                : c.draft_version_id
                                  ? "有草稿"
                                  : c.confirmed_version_id
                                    ? "已确认"
                                    : "尚未写作"}
                          </small>
                        </span>
                      </button>
                    ))
                  )}
                </div>
                <div className="pagination">
                  <button
                    disabled={offset === 0}
                    onClick={() => setOffset(Math.max(0, offset - 100))}
                  >
                    上一页
                  </button>
                  <span>{total} 章</span>
                  <button
                    disabled={offset + 100 >= total}
                    onClick={() => setOffset(offset + 100)}
                  >
                    下一页
                  </button>
                </div>
              </aside>
              <div className="writing-center">
                <div className="mobile-chapters">
                  <select
                    aria-label="选择章节"
                    value={chapterId ?? ""}
                    onChange={(e) => void selectChapter(e.target.value)}
                  >
                    <option value="">选择章节</option>
                    {chapters.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.number}. {c.title}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() => setCreateChapter(true)}
                    aria-label="新建章节"
                  >
                    <Plus size={16} />
                  </button>
                  <button
                    disabled={offset === 0}
                    onClick={() => setOffset(Math.max(0, offset - 100))}
                  >
                    前页
                  </button>
                  <button
                    disabled={offset + 100 >= total}
                    onClick={() => setOffset(offset + 100)}
                  >
                    后页
                  </button>
                </div>
                <div className="writing-entry">
                  <button
                    onClick={() => {
                      setSide("director");
                      setSideVisible(true);
                    }}
                  >
                    AI 写作 · 打开作者导演
                  </button>
                  <small>输入任务即可直接写正文；已有手稿保留。</small>
                </div>
                <ChapterWorkspace
                  run={run}
                  projectId={project.id}
                  chapterId={chapterId}
                  previewRequest={previewRequest}
                >
                  {chapterId ? (
                    <NovelEditor
                      key={`${chapterId}-${reload}`}
                      chapterId={chapterId}
                      onSaved={() => void loadChapters()}
                      onImpact={(version) => {
                        setImpactVersion(version);
                        void navigate("tools");
                      }}
                      onRun={(id) => {
                        setRunId(id);
                        setSide("director");
                        setSideVisible(true);
                      }}
                    />
                  ) : (
                    <Empty>从目录选择章节，或添加新章节。</Empty>
                  )}
                </ChapterWorkspace>
              </div>
              <button
                className="evidence-toggle icon-button"
                aria-label={sideVisible ? "收起证据轨道" : "展开证据轨道"}
                onClick={() => {
                  sideManual.current = true;
                  setSideVisible((v) => {
                    localStorage.setItem(
                      "easynovel.evidence.visible",
                      String(!v),
                    );
                    return !v;
                  });
                }}
              >
                <PanelRightClose size={18} />
              </button>
              {sideVisible && (
                <aside className="evidence-rail">
                  <TabPanel
                    value={side}
                    onChange={setSide}
                    tabs={[
                      {
                        id: "director",
                        label: "作者导演",
                        content: (
                          <Director
                            chapterId={chapterId}
                            runId={runId}
                            onRun={setRunId}
                            onCommitted={committed}
                            onBeforeStart={guard}
                            onBeforeCommit={guard}
                            onViewDraft={(candidate) => {
                              if (
                                candidate.project_id !== project.id ||
                                candidate.chapter_id !== chapterId
                              ) {
                                notice(
                                  "该正文属于另一章节，请先切换到对应章节",
                                );
                                return;
                              }
                              setRun(candidate);
                              setPreviewRequest((n) => n + 1);
                            }}
                          />
                        ),
                      },
                      {
                        id: "evidence",
                        label: "证据轨道",
                        content: <Evidence chapterId={chapterId} />,
                      },
                    ]}
                  />
                </aside>
              )}
            </>
          )}
          {project && view === "records" && <Records />}
          {project && view === "tools" && (
            <Tools
              chapterId={chapterId}
              versionId={impactVersion}
              onRun={setRunId}
              onCommitted={committed}
              onImportsChanged={importsChanged}
              onImportJob={() => setImportSignal((value) => value + 1)}
            />
          )}
          {project && view === "settings" && <Settings key={project.id} />}
        </main>
        <footer className="run-status" aria-live="polite">
          <span className="status-dot" />
          <span>{run ? stageLabel(run.node) : "本地工作站已连接"}</span>
          {run && (
            <>
              <State value={run.status} />
              <span>
                输入 {run.usage?.input_tokens ?? 0} · 输出{" "}
                {run.usage?.output_tokens ?? 0}
              </span>
              <button
                onClick={() => {
                  setView("write");
                  setSide("director");
                  setSideVisible(true);
                }}
              >
                查看任务
              </button>
            </>
          )}
          <div className="topbar-space" />
          <span className="muted">
            {health?.semantic_search ? "语义索引已配置" : "全文与结构化检索"} ·
            v{health?.version ?? "—"}
          </span>
        </footer>
      </div>
      <Modal
        open={createProject}
        onOpenChange={setCreateProject}
        title="新建作品"
      >
        <NewProject
          busy={busy}
          onSubmit={(data) =>
            void execute(async () => {
              if (!(await guard())) return;
              const created = await api.post<Project>("/projects", data);
              setProjectId(created.id);
              setProject(created);
              setChapterId(null);
              setBranch("main");
              setCreateProject(false);
              setView("projects");
              await refresh();
            })
          }
        />
      </Modal>
      {project && (
        <>
          <Modal
            open={createChapter}
            onOpenChange={setCreateChapter}
            title="添加章节"
          >
            <NewChapter
              busy={busy}
              onSubmit={(data) =>
                void execute(async () => {
                  if (!(await guard())) return;
                  const c = await api.post<Chapter>(
                    `/projects/${project.id}/chapters`,
                    { ...data, branch_id: branch },
                  );
                  setCreateChapter(false);
                  await refresh();
                  await loadChapters();
                  await selectChapter(c.id);
                })
              }
            />
          </Modal>
          <Modal
            open={createBranch}
            onOpenChange={setCreateBranch}
            title="创建备选故事分支"
          >
            <NewBranch
              busy={busy}
              onSubmit={(name) =>
                void execute(async () => {
                  const b = await api.post<Branch>(
                    `/projects/${project.id}/branches`,
                    { name, source_branch_id: branch },
                  );
                  setBranches(
                    await api.get(`/projects/${project.id}/branches`),
                  );
                  setCreateBranch(false);
                  notice(`备选分支「${b.name}」已创建，请从目录切换`);
                })
              }
            />
          </Modal>
          <Modal open={backup} onOpenChange={setBackup} title="备份与导出">
            <BackupCenter />
          </Modal>
        </>
      )}
    </>
  );
  return project ? (
    <SessionContext.Provider
      value={{
        api,
        project,
        branch,
        providers,
        profiles,
        refresh,
        report,
        notice,
        setRun: setRunId,
      }}
    >
      {shell}
    </SessionContext.Provider>
  ) : (
    shell
  );
}
function NewProject({
  busy,
  onSubmit,
}: {
  busy: boolean;
  onSubmit: (data: unknown) => void;
}) {
  const [title, setTitle] = useState("");
  const [genre, setGenre] = useState("");
  const [mode, setMode] = useState("serial");
  const [description, setDescription] = useState("");
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({ title, genre, mode, description });
      }}
    >
      <Field label="作品名称">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          autoFocus
        />
      </Field>
      <Field label="题材">
        <input value={genre} onChange={(e) => setGenre(e.target.value)} />
      </Field>
      <Field label="创作模式">
        <Choice
          value={mode}
          onChange={setMode}
          label="创作模式"
          options={[
            { value: "serial", label: "长篇网文 · 持续期待与阶段兑现" },
            { value: "literary", label: "精品长篇 · 主题、结构与语言" },
          ]}
        />
      </Field>
      <Field label="主题、读者与创作方向">
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={4}
        />
      </Field>
      <button className="primary" disabled={busy || !title.trim()}>
        创建作品
      </button>
    </form>
  );
}
function NewChapter({
  busy,
  onSubmit,
}: {
  busy: boolean;
  onSubmit: (data: Record<string, unknown>) => void;
}) {
  const [title, setTitle] = useState("");
  const [number, setNumber] = useState("");
  const [time, setTime] = useState("");
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({
          title,
          number: number ? +number : undefined,
          story_time: time ? +time : undefined,
        });
      }}
    >
      <Field label="章节标题">
        <input
          required
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          autoFocus
        />
      </Field>
      <Field label="章序（留空自动接续）">
        <input
          type="number"
          min={1}
          value={number}
          onChange={(e) => setNumber(e.target.value)}
        />
      </Field>
      <Field label="故事发生时间（用于倒叙与认知过滤）">
        <input
          type="number"
          value={time}
          onChange={(e) => setTime(e.target.value)}
        />
      </Field>
      <button className="primary" disabled={busy}>
        添加章节
      </button>
    </form>
  );
}
function NewBranch({
  busy,
  onSubmit,
}: {
  busy: boolean;
  onSubmit: (name: string) => void;
}) {
  const [name, setName] = useState("");
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(name);
      }}
    >
      <p>
        从当前分支建立独立的备选故事方向。采用另一分支正文后仍需重新审核记忆。
      </p>
      <Field label="分支名称">
        <input
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          autoFocus
        />
      </Field>
      <button className="primary" disabled={busy}>
        创建备选分支
      </button>
    </form>
  );
}
