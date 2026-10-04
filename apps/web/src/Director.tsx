import { useEffect, useRef, useState } from "react";
import { useSession, useAction, query } from "./session";
import {
  Badge,
  Choice,
  Empty,
  Field,
  Inspect,
  Modal,
  State,
  TabPanel,
  Tick,
} from "./ui";
import type { ContextPack, Project, Run, SearchItem } from "./types";
import { acceptedMemoryIndices } from "./draft";
import { appendTechnicalOutput, type TechnicalOutput } from "./technicalStream";
import { kinds } from "./Records";
import { evidenceFields, evidenceValues, ReviewResults } from "./RunEvidence";
import {
  completionMessage,
  roleLabels,
  stageLabel,
  suggestedOutputLimit,
} from "./runPresentation";
export function ModelBudget({
  provider,
  onProvider,
  budget,
  onBudget,
  profile,
  onProfile,
}: {
  provider: string;
  onProvider: (id: string) => void;
  budget: number;
  onBudget: (n: number) => void;
  profile?: string;
  onProfile?: (id: string) => void;
}) {
  const { providers, profiles } = useSession();
  useEffect(() => {
    if (!provider && providers.length === 1) onProvider(providers[0].id);
  }, [provider, providers]);
  return (
    <>
      {providers.length === 0 && (
        <p className="notice" role="status">
          尚未配置模型，请到设置→模型连接添加服务
        </p>
      )}
      <Field label="模型">
        <Choice
          label="模型"
          value={provider}
          onChange={onProvider}
          options={providers.map((p) => ({
            value: p.id,
            label: `${p.name} · ${p.model}`,
          }))}
        />
      </Field>
      <Field
        label="任务 Token 上限"
        hint="多轮规划、写作与审稿合计；单次输出上限另设，金额以服务商为准"
      >
        <input
          type="number"
          required
          min={1}
          value={budget}
          onChange={(e) => onBudget(+e.target.value)}
        />
      </Field>
      {onProfile && (
        <Field label="工作流模板">
          <select
            value={profile ?? ""}
            onChange={(e) => onProfile(e.target.value)}
          >
            <option value="">默认质量模板</option>
            {profiles.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </Field>
      )}
    </>
  );
}
export function Director({
  chapterId,
  runId,
  onRun,
  onCommitted,
  onViewDraft,
  onBeforeStart,
  onBeforeCommit,
}: {
  chapterId: string | null;
  runId: string | null;
  onRun: (id: string) => void;
  onCommitted: () => void;
  onViewDraft?: (run: Run) => void;
  onBeforeStart?: () => Promise<boolean>;
  onBeforeCommit?: () => Promise<boolean>;
}) {
  const { api, project, notice } = useSession();
  const { busy, act } = useAction();
  const [task, setTask] = useState("");
  const [provider, setProvider] = useState("");
  const [profile, setProfile] = useState("");
  const [budget, setBudget] = useState(200000);
  const [money, setMoney] = useState("");
  const [pov, setPov] = useState("");
  const [entities, setEntities] = useState("");
  const [time, setTime] = useState("");
  const [count, setCount] = useState("1");
  const [runs, setRuns] = useState<Run[]>([]);
  const [mode, setMode] = useState("direct");
  const load = async () =>
    setRuns(await api.get(`/projects/${project.id}/runs`));
  useEffect(() => {
    void act(load);
  }, [project.id, runId]);
  useEffect(() => {
    setTask("");
    setTime("");
  }, [chapterId]);
  const parse = mode === "directive";
  const modeHint = parse
    ? "仅整理候选约束卡，不生成小说正文。"
    : mode === "direct"
      ? "自动完成规划、写作和审稿；正文由你确认入库。"
      : "先查看并批准章节计划，然后生成正文、审稿与候选记忆。";
  return (
    <div className="director">
      <h2>作者导演</h2>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void act(async () => {
            if (!parse && onBeforeStart && !(await onBeforeStart())) return;
            const result = parse
              ? await api.post<Run>(
                  `/projects/${project.id}/directives/parse`,
                  { text: task, provider_id: provider, token_budget: budget },
                )
              : await api.post<Run>(`/projects/${project.id}/runs`, {
                  chapter_id: chapterId,
                  task,
                  provider_id: provider,
                  token_budget: budget,
                  money_budget: money ? +money : undefined,
                  profile_id: profile || undefined,
                  pov: pov || undefined,
                  entities: entities
                    .split(/[,，]/)
                    .map((s) => s.trim())
                    .filter(Boolean),
                  story_time: time ? +time : undefined,
                  candidate_count: mode === "direct" ? 1 : +count,
                  auto_approve_plan: mode === "direct",
                });
            onRun(result.id);
            await load();
            notice(
              parse
                ? "正在整理创作指令；完成后请核对候选约束"
                : mode === "direct"
                  ? "开始生成正文；系统将依次完成规划、写作和审稿"
                  : "开始规划；章节计划准备好后由你审核",
            );
          });
        }}
      >
        <Field label="创作方式">
          <Choice
            label="创作方式"
            value={mode}
            onChange={setMode}
            options={[
              { value: "direct", label: "直接写正文" },
              { value: "plan", label: "先审核计划" },
              { value: "directive", label: "整理创作指令" },
            ]}
          />
        </Field>
        <p className="muted" role="status">
          {modeHint}
        </p>
        <Field label={parse ? "自然语言创作指令" : "本章创作任务"}>
          <textarea
            required
            rows={5}
            value={task}
            onChange={(e) => setTask(e.target.value)}
            placeholder={
              parse
                ? "例如：让两人在本卷逐渐决裂，但本卷结束前不要公开背叛。"
                : "例如：写第一章。林秋收到失踪父亲寄来的信，在雨夜赶到旧车站，发现信封中的钥匙能打开站长室。突出他的犹豫、试探与第一次选择。"
            }
          />
        </Field>
        <ModelBudget
          provider={provider}
          onProvider={setProvider}
          budget={budget}
          onBudget={setBudget}
          profile={profile}
          onProfile={setProfile}
        />
        {!parse && (
          <details>
            <summary>场景与预算细节</summary>
            <Field label="视角人物">
              <input value={pov} onChange={(e) => setPov(e.target.value)} />
            </Field>
            <Field label="关联人物与实体（逗号分隔）">
              <input
                value={entities}
                onChange={(e) => setEntities(e.target.value)}
              />
            </Field>
            <Field label="故事发生时间">
              <input
                type="number"
                value={time}
                onChange={(e) => setTime(e.target.value)}
              />
            </Field>
            <Field label="金额上限（供应商计价单位）">
              <input
                type="number"
                min={0.01}
                step="0.01"
                value={money}
                onChange={(e) => setMoney(e.target.value)}
              />
            </Field>
            {mode === "plan" && (
              <Field label="规划方案">
                <Choice
                  label="规划方案"
                  value={count}
                  onChange={setCount}
                  options={[
                    { value: "1", label: "一个方案" },
                    { value: "3", label: "三个候选方案" },
                  ]}
                />
              </Field>
            )}
          </details>
        )}
        <button
          className="primary"
          disabled={
            busy ||
            !provider ||
            !task.trim() ||
            budget <= 0 ||
            (!parse && !chapterId)
          }
        >
          {parse
            ? "整理创作指令"
            : mode === "direct"
              ? "直接写正文"
              : "生成待审核计划"}
        </button>
        {!chapterId && !parse && <p className="muted">先选择或新建章节。</p>}
      </form>
      {runId && (
        <RunReview
          runId={runId}
          onCommitted={onCommitted}
          onViewDraft={onViewDraft}
          onBeforeCommit={onBeforeCommit}
          onRunUpdated={(updated) =>
            setRuns((history) =>
              history.map((item) => (item.id === updated.id ? updated : item)),
            )
          }
        />
      )}
      <h3>运行历史</h3>
      {runs.length === 0 ? (
        <Empty>尚未发起创作任务。</Empty>
      ) : (
        <div className="run-history">
          {runs.map((r) => (
            <button
              className="version-row"
              key={r.id}
              onClick={() => onRun(r.id)}
            >
              <span>
                {new Date(r.created_at).toLocaleString()} · {stageLabel(r.node)}
              </span>
              <State value={r.status} />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
export function RunReview({
  runId,
  onCommitted,
  onViewDraft,
  onBeforeCommit,
  onRunUpdated,
}: {
  runId: string;
  onCommitted: () => void;
  onViewDraft?: (run: Run) => void;
  onBeforeCommit?: () => Promise<boolean>;
  onRunUpdated?: (run: Run) => void;
}) {
  const {
    api,
    project,
    providers,
    refresh,
    report,
    notice,
    setRun: selectRun,
  } = useSession();
  const { busy, act } = useAction();
  const [run, setRun] = useState<Run | null>(null);
  const currentRunId = useRef(runId);
  currentRunId.current = runId;
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [planIndex, setPlanIndex] = useState(0);
  const [override, setOverride] = useState("");
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [revisionInstruction, setRevisionInstruction] = useState("");
  const [stream, setStream] = useState<TechnicalOutput[]>([]);
  const [streamState, setStreamState] = useState("连接事件流");
  const sequence = useRef(0);
  const [key, setKey] = useState(() => crypto.randomUUID());
  const completedNotified = useRef(false);
  const observedPending = useRef(false);
  const reviewNotified = useRef(false);
  const [providerLimits, setProviderLimits] = useState<Record<string, string>>(
    {},
  );
  const [resumeOpen, setResumeOpen] = useState(false);
  const [resumeTokens, setResumeTokens] = useState(100000);
  const [resumeMoney, setResumeMoney] = useState("");
  const [roleLimits, setRoleLimits] = useState<Record<string, string>>({});
  const load = async () => {
    const next = await api.get<Run>(`/runs/${runId}`);
    if (currentRunId.current === runId) {
      setRun(next);
      onRunUpdated?.(next);
    }
    return next;
  };
  useEffect(() => {
    let alive = true;
    let loading = false;
    sequence.current = 0;
    completedNotified.current = false;
    observedPending.current = false;
    reviewNotified.current = false;
    setSelected(new Set());
    setRevisionInstruction("");
    setEditing(false);
    setStream([]);
    setKey(crypto.randomUUID());
    setRun(null);
    const controller = new AbortController();
    let reconnect: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      if (!alive || loading) return;
      loading = true;
      try {
        await load();
      } catch (e) {
        if (alive) report(e);
      } finally {
        loading = false;
      }
    };
    void poll();
    const timer = setInterval(() => void poll(), 3000);
    const connect = async () => {
      try {
        await api.events(
          runId,
          sequence.current,
          controller.signal,
          (event) => {
            if (!alive) return;
            if (event.seq && event.seq <= sequence.current) return;
            sequence.current = Math.max(sequence.current, event.seq ?? 0);
            setStreamState("事件流已连接");
            if (
              event.event === "text" ||
              event.event === "token" ||
              event.event === "text_chunk" ||
              event.event === "chunk"
            ) {
              setStream((s) => appendTechnicalOutput(s, event.data));
            } else void poll();
          },
        );
      } catch {
        if (alive) setStreamState("事件流重连中；运行状态继续刷新");
      }
      if (alive) reconnect = setTimeout(() => void connect(), 3000);
    };
    void connect();
    return () => {
      alive = false;
      controller.abort();
      clearInterval(timer);
      if (reconnect) clearTimeout(reconnect);
    };
  }, [runId]);
  useEffect(() => {
    if (run && run.status !== "completed") observedPending.current = true;
    if (run?.status === "completed" && !completedNotified.current) {
      completedNotified.current = true;
      void refresh()
        .then(() => {
          if (
            observedPending.current &&
            run.artifacts.draft &&
            (!run.request?.kind ||
              ["chapter", "rewrite", "author_revision"].includes(
                run.request.kind,
              ))
          )
            onCommitted();
          notice(completionMessage(run));
        })
        .catch(report);
    }
  }, [run?.status]);
  useEffect(() => {
    if (
      run?.status === "awaiting_review" &&
      run.artifacts.draft &&
      !reviewNotified.current
    ) {
      reviewNotified.current = true;
      notice("正文已生成，请查看正文并确认入库");
    }
  }, [run?.status, run?.artifacts.draft]);
  if (!run) return <Empty>正在读取任务…</Empty>;
  const outputInfo = run.artifacts.output_limit_info;
  const runProviders = Object.values(run.request?.provider_snapshots ?? {});
  const configuredProviders = runProviders.length ? runProviders : providers;
  const invalidLimits =
    Object.values(roleLimits).some(
      (value) =>
        value && (!Number.isInteger(+value) || +value < 128 || +value > 100000),
    ) ||
    Object.entries(providerLimits).some(([id, value]) => {
      const current = configuredProviders.find((p) => p.id === id);
      const context =
        current?.context_limit ??
        (outputInfo?.provider_id === id ? outputInfo.context_limit : 100256);
      return (
        value &&
        (!Number.isInteger(+value) ||
          +value < 128 ||
          +value > Math.min(100000, context - 256))
      );
    });
  const active = [
    "queued",
    "running",
    "awaiting_plan",
    "awaiting_review",
  ].includes(run.status);
  const plans =
    run.artifacts.plans ?? (run.artifacts.plan ? [run.artifacts.plan] : []);
  const memory = run.artifacts.memory_delta ?? [];
  return (
    <section className="run-review">
      <div className="row">
        <h3>当前任务</h3>
        <State value={run.status} />
      </div>
      <small>
        {run.id} ·{" "}
        {run.request?.kind === "author_revision" && "作者要求修订 · "}
        {stageLabel(run.node)}
      </small>
      <div className="usage">
        <span>输入 {run.usage?.input_tokens ?? 0}</span>
        <span>输出 {run.usage?.output_tokens ?? 0}</span>
        <span>预留 {run.usage?.reserved_tokens ?? 0}</span>
        <span>
          {run.usage?.cost_known
            ? `估算费用 ${run.usage.cost}`
            : "金额未知 · 仅统计 Token"}
        </span>
      </div>
      <div className="actions">
        {active && (
          <button
            disabled={busy}
            onClick={() =>
              void act(async () => {
                await api.post(`/runs/${runId}/pause`);
                await load();
              })
            }
          >
            暂停
          </button>
        )}
        {["paused", "failed"].includes(run.status) && (
          <button
            disabled={busy}
            onClick={() => {
              setResumeTokens(
                run.request?.token_budget ??
                  Math.max(
                    100000,
                    (run.usage?.input_tokens ?? 0) +
                      (run.usage?.output_tokens ?? 0) +
                      50000,
                  ),
              );
              setRoleLimits({});
              setProviderLimits({});
              if (run.artifacts.output_limit_info) {
                const info = run.artifacts.output_limit_info;
                const target = suggestedOutputLimit(info);
                setRoleLimits({ [info.role]: String(target) });
                setProviderLimits({ [info.provider_id]: String(target) });
              }
              setResumeOpen(true);
            }}
          >
            调整额度并恢复
          </button>
        )}
        {!["completed", "cancelled"].includes(run.status) && (
          <button
            disabled={busy}
            onClick={() =>
              void act(async () => {
                await api.post(`/runs/${runId}/cancel`);
                await load();
              })
            }
          >
            取消
          </button>
        )}
      </div>
      {run.error && (
        <p role="alert" className="error-inline">
          {run.error}
        </p>
      )}
      <small className="muted">
        {streamState} · 输入修订 {run.input_revision}
      </small>
      {!!run.artifacts.directive && (
        <details open>
          <summary>解析后的候选指令</summary>
          <Inspect value={run.artifacts.directive} />
          <p>请到故事资料的导演指令中编辑、确认。</p>
        </details>
      )}
      {run.artifacts.analyzed_chapters && (
        <p>
          已分析 {run.artifacts.analyzed_chapters.length} /{" "}
          {run.artifacts.total ?? "—"} 章；候选记忆请到故事资料中核查。
        </p>
      )}
      {run.artifacts.architecture && (
        <details>
          <summary>故事架构建议</summary>
          <p>{run.artifacts.architecture}</p>
        </details>
      )}
      {run.artifacts.context && (
        <details>
          <summary>本次上下文与证据</summary>
          <ContextView pack={run.artifacts.context} />
        </details>
      )}
      {run.status === "awaiting_plan" && run.artifacts.proposed_revision && (
        <section className="notice">
          <h3>修改将改变核心事件或人物结果</h3>
          <p>{run.artifacts.proposed_revision.change_reason}</p>
          <pre className="text-preview">
            {run.artifacts.proposed_revision.content}
          </pre>
          <div className="actions">
            <button
              className="primary"
              disabled={busy}
              onClick={() =>
                void act(async () => {
                  await api.post(`/runs/${runId}/approve-plan`, {
                    accept_change: true,
                  });
                  await load();
                })
              }
            >
              接受剧情调整
            </button>
            <button
              disabled={busy}
              onClick={() =>
                void act(async () => {
                  await api.post(`/runs/${runId}/approve-plan`, {
                    accept_change: false,
                  });
                  await load();
                })
              }
            >
              保留原剧情继续审核
            </button>
          </div>
        </section>
      )}
      {plans.length > 0 && (
        <details open={run.status === "awaiting_plan"}>
          <summary>章节与场景计划</summary>
          {plans.length > 1 && (
            <div className="actions">
              {plans.map((_, i) => (
                <button
                  key={i}
                  aria-pressed={planIndex === i}
                  onClick={() => setPlanIndex(i)}
                >
                  方案 {i + 1}
                </button>
              ))}
            </div>
          )}
          <Inspect value={plans[planIndex]} />
          {run.status === "awaiting_plan" &&
            !run.artifacts.proposed_revision && (
              <button
                className="primary"
                disabled={busy}
                onClick={() =>
                  void act(async () => {
                    await api.post(`/runs/${runId}/approve-plan`, {
                      plan_index: planIndex,
                    });
                    await load();
                  })
                }
              >
                批准此计划并生成正文
              </button>
            )}
        </details>
      )}
      {stream.length > 0 && (
        <details>
          <summary>模型流式技术日志（非正文）</summary>
          <p>按模型调用拼接输出，并行审稿分开展示。仅保留最近 64000 字符。</p>
          {stream.map((output, index) => (
            <div key={output.key}>
              <strong>{roleLabels[output.role] ?? "模型输出"} · 输出 {index + 1}</strong>
              <pre className="text-preview">{output.text}</pre>
            </div>
          ))}
        </details>
      )}
      {outputInfo && (
        <div className="notice">
          <strong>
            {roleLabels[outputInfo.role] ?? outputInfo.role}
            ：单次回答达到输出上限
          </strong>
          <p>
            本次上限 {outputInfo.maximum} Tokens；模型上限{" "}
            {outputInfo.provider_max_output}，角色上限{" "}
            {outputInfo.role_max_output ?? "未单独设置"}，阶段请求上限{" "}
            {outputInfo.requested_output_limit ?? "未单独设置"}
            。请调整单次输出上限后恢复；任务总额度单独控制全部调用。
          </p>
        </div>
      )}
      {!!run.artifacts.draft && (
        <details open>
          <summary>正文候选</summary>
          {onViewDraft && (
            <button onClick={() => onViewDraft(run)}>查看正文</button>
          )}
          {editing ? (
            <>
              <textarea
                className="draft-edit"
                aria-label="编辑正文候选"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
              />
              <div className="actions">
                <button
                  disabled={busy}
                  onClick={() =>
                    void act(async () => {
                      await api.post(`/runs/${runId}/edit`, { draft });
                      setEditing(false);
                      await load();
                    })
                  }
                >
                  保存并重新审稿
                </button>
                <button onClick={() => setEditing(false)}>放弃编辑</button>
              </div>
            </>
          ) : (
            <>
              <pre className="text-preview">{run.artifacts.draft}</pre>
              {run.status === "awaiting_review" && (
                <button
                  onClick={() => {
                    setDraft(run.artifacts.draft ?? "");
                    setEditing(true);
                  }}
                >
                  编辑候选并重新审稿
                </button>
              )}
            </>
          )}
        </details>
      )}
      {!!run.artifacts.memory_warnings?.length && (
        <div className="notice" role="alert">
          <strong>部分正文的候选记忆未提取成功</strong>
          <p>正文和其他有效候选已保留。以下区域没有自动建立记忆，请核查后补充；不能把空的记忆列表当作全文已核查。</p>
          {run.artifacts.memory_warnings.map((warning) => (
            <p key={warning.call_key}>{warning.message}（涉及 {warning.paragraph_ids.length} 段正文）</p>
          ))}
        </div>
      )}
      {!!run.artifacts.length_adjustment && (
        <details>
          <summary>正文长度已调整</summary>
          <Inspect value={run.artifacts.length_adjustment} />
        </details>
      )}
      {run.artifacts.style_rejected && (
        <p className="notice">文体修改未采用：{run.artifacts.style_rejected}</p>
      )}
      {!!run.artifacts.draft &&
        (["awaiting_review", "completed"].includes(run.status) ||
          (run.status === "stale" && !!run.artifacts.version_id)) && (
          <details>
            <summary>让 AI 按要求修改</summary>
            <p className="muted">
              沿用原任务的模型与预算配置。费用计入新任务以及章节、作品累计上限；原候选保留，修改稿重新审稿并由你确认，不自动入库。待审核的原任务将取消。
            </p>
            {run.status === "stale" && (
              <p className="notice">
                原任务依据已过期。新任务将重新读取当前前文，并根据最新作品修订生成修改稿；当前章节稿件已变化时会拒绝启动，原候选仍保留。
              </p>
            )}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void act(async () => {
                  if (onBeforeCommit && !(await onBeforeCommit())) return;
                  const latest = await api.get<Project>(
                    `/projects/${project.id}`,
                  );
                  const revised = await api.post<Run>(`/runs/${runId}/revise`, {
                    instruction: revisionInstruction.trim(),
                    expected_revision: latest.revision,
                  });
                  selectRun(revised.id);
                  notice("修改任务已创建；原稿保留，修改稿需再次审核确认");
                });
              }}
            >
              <Field label="修改要求">
                <textarea
                  required
                  rows={5}
                  value={revisionInstruction}
                  onChange={(e) => setRevisionInstruction(e.target.value)}
                  placeholder="例如：保留旧车站发现信件的事件，增加林秋试探站长的对话，让结尾的选择更有代价。"
                />
              </Field>
              <button
                className="primary"
                disabled={busy || editing || !revisionInstruction.trim()}
              >
                生成修改稿
              </button>
              {editing && (
                <p className="muted">先保存或放弃候选编辑，再提出改稿要求。</p>
              )}
            </form>
          </details>
        )}
      {!!run.artifacts.reviews?.length && (
        <details open>
          <summary>审稿意见（{run.artifacts.reviews.length}）</summary>
          <ReviewResults reviews={run.artifacts.reviews} />
        </details>
      )}
      {run.artifacts.repair_versions && (
        <details open>
          <summary>修复候选版本</summary>
          <Inspect value={run.artifacts.repair_versions} />
          <p>请在受影响章节中逐章核对版本，再确认正文。</p>
        </details>
      )}
      {memory.length > 0 && (
        <details open>
          <summary>候选记忆（仅提交勾选项）</summary>
          {memory.map((m, i) => (
            <div className="memory-item" key={i}>
              <Tick
                checked={selected.has(i)}
                onChange={(v) => {
                  const next = new Set(selected);
                  v ? next.add(i) : next.delete(i);
                  setSelected(next);
                }}
                label={<strong>{m.title}</strong>}
              />
              <p>{m.content}</p>
              <small>
                {kinds.find((kind) => kind.value === m.kind)?.label ?? m.kind} ·{" "}
                {m.source_type
                  ? (evidenceValues.source_type[m.source_type] ?? m.source_type)
                  : "证据类型待核查"}
              </small>
              <details>
                <summary>来源与原文证据</summary>
                <Inspect
                  value={{
                    ...m.data,
                    source_version_id: m.source_version_id ?? "本次正文",
                    source_paragraph_id: m.source_paragraph_id ?? "整章",
                  }}
                  fieldLabels={evidenceFields}
                  valueLabels={evidenceValues}
                />
              </details>
            </div>
          ))}
        </details>
      )}
      {run.status === "awaiting_review" && (
        <div className="approval">
          <Field label="有意安排或审稿例外说明（可选）">
            <textarea
              value={override}
              onChange={(e) => setOverride(e.target.value)}
            />
          </Field>
          {run.input_revision !== project.revision && (
            <p className="notice">
              作品修订已变化，提交可能被拒绝。候选正文仍会保留。
            </p>
          )}
          <button
            disabled={busy || editing}
            className="primary"
            onClick={() =>
              void act(async () => {
                if (onBeforeCommit && !(await onBeforeCommit())) return;
                await api.post(`/runs/${runId}/approve`, {
                  accepted_memory_indices: acceptedMemoryIndices(
                    selected,
                    memory.length,
                  ),
                  override_reason: override || undefined,
                  idempotency_key: key,
                  expected_revision: project.revision,
                });
                await load();
                notice(
                  `审核请求已发送；选择了 ${selected.size} 条记忆，正在确认入库`,
                );
              })
            }
          >
            确认审核与 {selected.size} 条记忆
          </button>
        </div>
      )}
      <Modal
        open={resumeOpen}
        onOpenChange={setResumeOpen}
        title="调整预算与单次输出上限"
      >
        <p>
          已保存成果保留。任务总额度控制全部调用消耗；角色和模型输出上限控制一次回答的长度。输出截断时请提高单次输出上限。
        </p>
        <Field label="任务总 Token 上限">
          <input
            type="number"
            min={100}
            value={resumeTokens}
            onChange={(e) => setResumeTokens(+e.target.value)}
          />
        </Field>
        <Field label="任务金额上限（留空保持）">
          <input
            type="number"
            min={0.01}
            step="0.01"
            value={resumeMoney}
            onChange={(e) => setResumeMoney(e.target.value)}
          />
        </Field>
        <details open={!!outputInfo}>
          <summary>角色输出上限（响应截断时调整）</summary>
          {[
            ["architect", "故事架构师"],
            ["planner", "规划师"],
            ["writer", "正文作者"],
            ["continuity", "连续性审计"],
            ["editor", "剧情编辑"],
            ["stylist", "文体编辑"],
            ["memory", "记忆整理"],
          ].map(([id, label]) => (
            <Field key={id} label={label}>
              <small>
                当前：
                {outputInfo?.role === id
                  ? (outputInfo.role_max_output ?? "使用模型配置")
                  : (run.request?.profile_snapshot?.roles?.[id]?.max_output ??
                    "使用模型配置")}
              </small>
              <input
                type="number"
                min={128}
                max={100000}
                aria-label={label}
                value={roleLimits[id] ?? ""}
                onChange={(e) =>
                  setRoleLimits((p) => ({ ...p, [id]: e.target.value }))
                }
              />
            </Field>
          ))}
        </details>
        <details open={!!outputInfo}>
          <summary>模型输出上限（当前任务快照）</summary>
          {configuredProviders.map((provider) => (
            <Field
              key={provider.id}
              label={`模型单次输出上限 · ${provider.name} / ${provider.model}`}
            >
              <small>
                当前：
                {outputInfo?.provider_id === provider.id
                  ? outputInfo.provider_max_output
                  : provider.max_output}{" "}
                Tokens；上下文容量 {provider.context_limit}
              </small>
              <input
                type="number"
                min={128}
                max={Math.max(
                  128,
                  Math.min(100000, provider.context_limit - 256),
                )}
                value={providerLimits[provider.id] ?? ""}
                onChange={(e) =>
                  setProviderLimits((p) => ({
                    ...p,
                    [provider.id]: e.target.value,
                  }))
                }
              />
            </Field>
          ))}
          {outputInfo &&
            !configuredProviders.some(
              (p) => p.id === outputInfo.provider_id,
            ) && (
              <Field label={`模型单次输出上限 · ${outputInfo.model}`}>
                <small>
                  当前：{outputInfo.provider_max_output} Tokens；上下文容量{" "}
                  {outputInfo.context_limit}
                </small>
                <input
                  type="number"
                  min={128}
                  max={Math.max(
                    128,
                    Math.min(100000, outputInfo.context_limit - 256),
                  )}
                  value={providerLimits[outputInfo.provider_id] ?? ""}
                  onChange={(e) =>
                    setProviderLimits((p) => ({
                      ...p,
                      [outputInfo.provider_id]: e.target.value,
                    }))
                  }
                />
              </Field>
            )}
        </details>
        {invalidLimits && (
          <p className="error-inline" role="alert">
            单次输出上限必须是至少128的整数，并小于模型上下文容量。
          </p>
        )}
        <button
          className="primary"
          disabled={busy || resumeTokens < 100 || !!invalidLimits}
          onClick={() =>
            void act(async () => {
              await api.post(`/runs/${runId}/resume`, {
                token_budget: resumeTokens,
                ...(resumeMoney ? { money_budget: +resumeMoney } : {}),
                ...(Object.values(providerLimits).some(Boolean)
                  ? {
                      provider_output_limits: Object.fromEntries(
                        Object.entries(providerLimits)
                          .filter(([, value]) => value)
                          .map(([id, value]) => [id, +value]),
                      ),
                    }
                  : {}),
                role_limits: Object.fromEntries(
                  Object.entries(roleLimits)
                    .filter(([, value]) => value)
                    .map(([id, value]) => [id, +value]),
                ),
              });
              setResumeOpen(false);
              await load();
            })
          }
        >
          保存额度并恢复
        </button>
      </Modal>
    </section>
  );
}
export function Evidence({ chapterId }: { chapterId: string | null }) {
  const { api, project, branch } = useSession();
  const { busy, act } = useAction();
  const [tab, setTab] = useState("search");
  const [q, setQ] = useState("");
  const [items, setItems] = useState<SearchItem[]>([]);
  const [semantic, setSemantic] = useState(false);
  const [useSemantic, setUseSemantic] = useState(false);
  const [queryBudget, setQueryBudget] = useState(2000);
  const [lastHybrid, setLastHybrid] = useState(false);
  const [searched, setSearched] = useState(false);
  const [task, setTask] = useState("");
  const [time, setTime] = useState("");
  const [limit, setLimit] = useState(8000);
  const [pack, setPack] = useState<ContextPack | null>(null);
  return (
    <TabPanel
      value={tab}
      onChange={setTab}
      tabs={[
        {
          id: "search",
          label: "证据检索",
          content: (
            <>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void act(async () => {
                    const data = useSemantic
                      ? await api.post<{
                          items: SearchItem[];
                          semantic_search: boolean;
                        }>(`/projects/${project.id}/search`, {
                          q,
                          branch_id: branch,
                          story_time: time ? +time : undefined,
                          token_budget: queryBudget,
                        })
                      : await api.get<{
                          items: SearchItem[];
                          semantic_search: boolean;
                        }>(
                          `/projects/${project.id}/search?${query({ q, branch_id: branch, story_time: time, limit: 20 })}`,
                        );
                    setItems(data.items);
                    setSemantic(data.semantic_search);
                    setLastHybrid(useSemantic);
                    setSearched(true);
                  });
                }}
              >
                <Field label="检索人物、道具或情节">
                  <input
                    value={q}
                    onChange={(e) => setQ(e.target.value)}
                    required
                  />
                </Field>
                <Field label="故事时间（过滤未来信息）">
                  <input
                    type="number"
                    value={time}
                    onChange={(e) => setTime(e.target.value)}
                  />
                </Field>
                <Tick
                  checked={useSemantic}
                  onChange={setUseSemantic}
                  label="使用语义检索（嵌入调用可能计费）"
                />
                {useSemantic && (
                  <Field
                    label="查询嵌入 Token 上限"
                    hint="需要本分支已建立语义索引；未建立时展示错误，保留原查询结果。"
                  >
                    <input
                      type="number"
                      required
                      min={1}
                      value={queryBudget}
                      onChange={(e) => setQueryBudget(+e.target.value)}
                    />
                  </Field>
                )}
                <button disabled={busy || (useSemantic && queryBudget <= 0)}>
                  查找证据
                </button>
              </form>
              <p className="muted">
                {lastHybrid && semantic
                  ? "本次使用全文、结构化与语义混合检索"
                  : semantic
                    ? "全文与结构化检索；语义索引已配置"
                    : "使用结构化和全文检索；语义索引未启用"}
              </p>
              {searched && items.length === 0 ? (
                <Empty>没有找到证据，尝试实体名或别名。</Empty>
              ) : (
                items.map((item) => (
                  <article className="evidence" key={item.id}>
                    <strong>{item.title}</strong>
                    <Badge>{item.kind}</Badge>
                    <p>{item.content}</p>
                    <small>{item.reason}</small>
                    <small>
                      来源 {item.source_version_id ?? "作者设定"} /{" "}
                      {item.source_paragraph_id ?? "整章"}
                    </small>
                  </article>
                ))
              )}
            </>
          ),
        },
        {
          id: "context",
          label: "上下文",
          content: (
            <>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void act(async () =>
                    setPack(
                      await api.post(`/projects/${project.id}/context`, {
                        chapter_id: chapterId,
                        task,
                        story_time: time ? +time : undefined,
                        token_limit: limit,
                      }),
                    ),
                  );
                }}
              >
                <Field label="本章任务">
                  <textarea
                    value={task}
                    onChange={(e) => setTask(e.target.value)}
                    required
                  />
                </Field>
                <Field label="上下文 Token 容量">
                  <input
                    type="number"
                    min={1}
                    value={limit}
                    onChange={(e) => setLimit(+e.target.value)}
                  />
                </Field>
                <Field label="故事时间">
                  <input
                    type="number"
                    value={time}
                    onChange={(e) => setTime(e.target.value)}
                  />
                </Field>
                <button disabled={busy || !chapterId}>构建上下文预览</button>
              </form>
              {pack && <ContextView pack={pack} />}
            </>
          ),
        },
      ]}
    />
  );
}
export function ContextView({ pack }: { pack: ContextPack }) {
  return (
    <div className="context-view">
      <p>
        修订 {pack.revision} · 估算 {pack.token_estimate} tokens ·{" "}
        {pack.semantic_search ? "语义检索启用" : "语义检索未启用"}
      </p>
      {pack.warnings?.map((w, i) => (
        <p className="notice" key={i}>
          {w}
        </p>
      ))}
      {[
        ["必须满足的约束", pack.constraints],
        ["前文证据", pack.evidence],
        ["人物认知", pack.character_knowledge],
        ["未来计划", pack.plans],
      ].map(([title, items]) => (
        <details key={String(title)} open>
          <summary>{String(title)}</summary>
          <Inspect value={items} />
        </details>
      ))}
    </div>
  );
}
