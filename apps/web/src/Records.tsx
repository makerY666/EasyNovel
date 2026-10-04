import { useEffect, useState } from "react";
import { useAction, useSession, query } from "./session";
import { Choice, Empty, Field, Inspect, Modal, State, Tick } from "./ui";
import type { Impact, RecordInput, RecordKind, StoryRecord } from "./types";
export const kinds: { value: RecordKind; label: string }[] = [
  { value: "character", label: "人物" },
  { value: "rule", label: "世界规则" },
  { value: "state", label: "动态状态" },
  { value: "knowledge", label: "人物认知" },
  { value: "relationship", label: "人物关系" },
  { value: "event", label: "事件与因果" },
  { value: "foreshadow", label: "伏笔与承诺" },
  { value: "plan", label: "分层计划" },
  { value: "directive", label: "导演指令" },
  { value: "summary", label: "来源摘要" },
];
const sourceLabels = {
  author: "作者声明",
  text: "正文事实",
  speech: "人物言论",
  inference: "模型推断",
};
const extraFields: Record<
  RecordKind,
  { key: string; label: string; type?: "number" | "lines" }[]
> = {
  character: [
    { key: "aliases", label: "别名（逗号分隔）", type: "lines" },
    { key: "goal", label: "长期目标" },
    { key: "fear", label: "恐惧" },
    { key: "voice", label: "口吻与语言习惯" },
  ],
  rule: [
    { key: "conditions", label: "适用条件" },
    { key: "exceptions", label: "例外" },
  ],
  state: [
    { key: "character_id", label: "人物标识" },
    { key: "attribute", label: "状态属性" },
    { key: "value", label: "状态值" },
  ],
  knowledge: [
    { key: "character_id", label: "人物标识" },
    { key: "belief", label: "相信或知道的内容" },
    { key: "acquisition", label: "如何得知" },
  ],
  relationship: [
    { key: "from_character_id", label: "关系发起方" },
    { key: "to_character_id", label: "关系对象" },
    { key: "attitude", label: "看待对方的态度" },
    { key: "cause", label: "变化原因" },
  ],
  event: [
    { key: "location", label: "地点" },
    { key: "participants", label: "参与者（逗号分隔）", type: "lines" },
    { key: "cause", label: "原因" },
    { key: "result", label: "结果" },
  ],
  foreshadow: [
    { key: "introduced_chapter", label: "埋设章节", type: "number" },
    { key: "payoff_start", label: "计划回收起章", type: "number" },
    { key: "payoff_end", label: "计划回收止章", type: "number" },
    { key: "conditions", label: "回收条件" },
    { key: "payoff_evidence", label: "兑现证据（已回收时必填）" },
  ],
  plan: [
    { key: "scope_id", label: "范围标识" },
    { key: "pov", label: "视角" },
    { key: "location", label: "地点" },
    { key: "goal", label: "场景目标" },
    { key: "obstacle", label: "阻力" },
    { key: "turn", label: "转折" },
    { key: "cost", label: "代价" },
    { key: "state_changes", label: "状态变化" },
  ],
  directive: [
    { key: "scope_id", label: "范围标识" },
    {
      key: "locked_paragraph_ids",
      label: "锁定段落标识（逗号分隔）",
      type: "lines",
    },
  ],
  summary: [
    { key: "level", label: "摘要层级" },
    { key: "source_version_ids", label: "来源版本（逗号分隔）", type: "lines" },
  ],
};
export function Records() {
  const { api, project, branch, refresh, notice } = useSession();
  const { busy, act } = useAction();
  const [kind, setKind] = useState<RecordKind>("character");
  const [records, setRecords] = useState<StoryRecord[]>([]);
  const [status, setStatus] = useState("");
  const [entity, setEntity] = useState("");
  const [time, setTime] = useState("");
  const [editing, setEditing] = useState<StoryRecord | null>(null);
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [retire, setRetire] = useState<StoryRecord | null>(null);
  const [reason, setReason] = useState("");
  const [approving, setApproving] = useState<StoryRecord | null>(null);
  const [recordImpact, setRecordImpact] = useState<Impact | null>(null);
  const [ack, setAck] = useState(false);
  const load = async () => {
    setRecords(
      await api.get(
        `/projects/${project.id}/records?${query({ kind, branch_id: branch, status, entity, story_time: time })}`,
      ),
    );
  };
  useEffect(() => {
    void act(load);
  }, [project.id, branch, kind, status]);
  return (
    <div className="page">
      <div className="page-title">
        <div>
          <small>故事圣经 · 所有资料均保留来源</small>
          <h1>故事资料</h1>
        </div>
        <button
          className="primary"
          onClick={() => {
            setEditing(null);
            setOpen(true);
          }}
        >
          添加{kinds.find((k) => k.value === kind)?.label}
        </button>
      </div>
      <div className="record-categories">
        {kinds.map((k) => (
          <button
            key={k.value}
            aria-pressed={kind === k.value}
            className={kind === k.value ? "active" : ""}
            onClick={() => {
              setKind(k.value);
              setSelected(new Set());
            }}
          >
            {k.label}
          </button>
        ))}
      </div>
      <form
        className="filter-row"
        onSubmit={(e) => {
          e.preventDefault();
          void act(load);
        }}
      >
        <Field label="状态">
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">全部</option>
            <option value="confirmed">已确认</option>
            <option value="candidate">候选</option>
            <option value="disputed">有争议</option>
            <option value="superseded">已替代</option>
          </select>
        </Field>
        <Field label="实体名称或标识">
          <input value={entity} onChange={(e) => setEntity(e.target.value)} />
        </Field>
        <Field label="场景发生时间">
          <input
            type="number"
            value={time}
            onChange={(e) => setTime(e.target.value)}
          />
        </Field>
        <button disabled={busy}>筛选</button>
      </form>
      {selected.size > 0 && (
        <div className="actions">
          <span>已选 {selected.size} 条候选</span>
          <button
            disabled={busy}
            onClick={() =>
              void act(async () => {
                for (const id of selected) {
                  const current = await api.get<{ revision: number }>(
                    `/projects/${project.id}`,
                  );
                  await api.post(`/records/${id}/approve`, {
                    expected_revision: current.revision,
                  });
                }
                setSelected(new Set());
                await refresh();
                await load();
                notice("所选候选资料已确认");
              })
            }
          >
            批量确认入库
          </button>
        </div>
      )}
      <div className="record-list">
        {records.length === 0 ? (
          <Empty>
            此类别还没有资料。添加作者设定，或在导入中心提取待核查记忆。
          </Empty>
        ) : (
          records.map((r) => (
            <article className="record" key={r.id}>
              <div className="row">
                {r.status === "candidate" && !r.supersedes_id && (
                  <Tick
                    checked={selected.has(r.id)}
                    onChange={(v) => {
                      const next = new Set(selected);
                      v ? next.add(r.id) : next.delete(r.id);
                      setSelected(next);
                    }}
                    label="选择"
                  />
                )}
                <h3>{r.title}</h3>
                <State value={r.status} />
              </div>
              <p>{r.content}</p>
              <div className="provenance">
                <span>{sourceLabels[r.source_type ?? "author"]}</span>
                <span>
                  故事时间：{r.valid_from ?? "不限"} → {r.valid_until ?? "不限"}
                </span>
                <span>实体：{r.entity_ids?.join("、") || "未关联"}</span>
                {r.source_version_id && (
                  <span>
                    正文证据 {r.source_version_id} /{" "}
                    {r.source_paragraph_id ?? "整章"}
                  </span>
                )}
              </div>
              {r.data && (
                <details>
                  <summary>查看结构化资料</summary>
                  <Inspect value={r.data} />
                </details>
              )}
              <div className="actions">
                <button
                  onClick={() => {
                    setEditing(r);
                    setOpen(true);
                  }}
                >
                  编辑为新版本
                </button>
                {r.status === "candidate" && (
                  <button
                    disabled={busy}
                    onClick={() =>
                      void act(async () => {
                        setRecordImpact(
                          r.supersedes_id
                            ? await api.get<Impact>(`/records/${r.id}/impact`)
                            : null,
                        );
                        setAck(false);
                        setApproving(r);
                      })
                    }
                  >
                    确认
                  </button>
                )}
                <button
                  disabled={busy}
                  onClick={() =>
                    void act(async () => {
                      setRecordImpact(
                        await api.get<Impact>(`/records/${r.id}/impact`),
                      );
                      setAck(false);
                      setRetire(r);
                      setReason("");
                    })
                  }
                >
                  撤回
                </button>
              </div>
            </article>
          ))
        )}
      </div>
      <Modal
        open={open}
        onOpenChange={setOpen}
        title={editing ? "替换资料版本" : "添加故事资料"}
      >
        <RecordForm
          kind={kind}
          existing={editing}
          onDone={async () => {
            setOpen(false);
            await refresh();
            await load();
          }}
        />
      </Modal>
      <Modal
        open={!!retire}
        onOpenChange={(v) => !v && setRetire(null)}
        title="撤回资料"
      >
        <p>将撤回「{retire?.title}」，保留历史和来源。</p>
        <RecordImpact impact={recordImpact} ack={ack} setAck={setAck} />
        <Field label="撤回原因">
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </Field>
        <button
          disabled={
            busy || !reason.trim() || (!!recordImpact?.items.length && !ack)
          }
          onClick={() =>
            void act(async () => {
              await api.post(`/records/${retire!.id}/retire`, {
                expected_revision: project.revision,
                reason,
                impact_acknowledged: ack,
              });
              setRetire(null);
              await refresh();
              await load();
            })
          }
        >
          确认撤回
        </button>
      </Modal>
      <Modal
        open={!!approving}
        onOpenChange={(v) => !v && setApproving(null)}
        title="确认故事资料"
      >
        <p>
          确认「{approving?.title}」为正式故事记忆。替换资料会保留旧版及其证据。
        </p>
        <RecordImpact impact={recordImpact} ack={ack} setAck={setAck} />
        <button
          className="primary"
          disabled={busy || (!!recordImpact?.items.length && !ack)}
          onClick={() =>
            void act(async () => {
              await api.post(`/records/${approving!.id}/approve`, {
                expected_revision: project.revision,
                impact_acknowledged: ack,
              });
              setApproving(null);
              await refresh();
              await load();
            })
          }
        >
          确认资料入库
        </button>
      </Modal>
    </div>
  );
}
function RecordForm({
  kind,
  existing,
  onDone,
}: {
  kind: RecordKind;
  existing: StoryRecord | null;
  onDone: () => Promise<void>;
}) {
  const { api, project, branch } = useSession();
  const { act, busy } = useAction();
  const [draft, setDraft] = useState<RecordInput>(
    existing
      ? { ...existing, status: "candidate" }
      : {
          kind,
          title: "",
          content: "",
          source_type: "author",
          status: "candidate",
          data: {},
        },
  );
  const update = (key: string, value: unknown) =>
    setDraft((p) => ({ ...p, [key]: value }));
  const data = (key: string, value: unknown) =>
    setDraft((p) => ({ ...p, data: { ...p.data, [key]: value } }));
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        void act(async () => {
          const input = { ...draft, branch_id: branch };
          if (existing)
            await api.patch(`/records/${existing.id}`, {
              ...input,
              expected_revision: project.revision,
            });
          else await api.post(`/projects/${project.id}/records`, input);
          await onDone();
        });
      }}
    >
      <div className="form-grid">
        <Field label="标题">
          <input
            required
            value={draft.title}
            onChange={(e) => update("title", e.target.value)}
          />
        </Field>
        <Field label="资料状态">
          <Choice
            label="资料状态"
            value={draft.status ?? "candidate"}
            onChange={(v) => update("status", v)}
            options={[
              { value: "candidate", label: "候选，稍后确认" },
              { value: "confirmed", label: "作者确认" },
            ]}
          />
        </Field>
      </div>
      <Field label="内容">
        <textarea
          required
          rows={4}
          value={draft.content}
          onChange={(e) => update("content", e.target.value)}
        />
      </Field>
      <div className="form-grid">
        <Field label="来源类型">
          <Choice
            label="来源类型"
            value={draft.source_type ?? "author"}
            onChange={(v) => update("source_type", v)}
            options={Object.entries(sourceLabels).map(([value, label]) => ({
              value,
              label,
            }))}
          />
        </Field>
        <Field label="相关实体（逗号分隔）">
          <input
            value={draft.entity_ids?.join(",") ?? ""}
            onChange={(e) =>
              update(
                "entity_ids",
                e.target.value
                  .split(/[,，]/)
                  .map((s) => s.trim())
                  .filter(Boolean),
              )
            }
          />
        </Field>
        <Field label="生效故事时间">
          <input
            type="number"
            value={draft.valid_from ?? ""}
            onChange={(e) =>
              update("valid_from", e.target.value === "" ? 0 : +e.target.value)
            }
          />
        </Field>
        <Field label="结束故事时间">
          <input
            type="number"
            value={draft.valid_until ?? ""}
            onChange={(e) =>
              update(
                "valid_until",
                e.target.value === "" ? null : +e.target.value,
              )
            }
          />
        </Field>
        <Field label="来源正文版本">
          <input
            value={draft.source_version_id ?? ""}
            onChange={(e) =>
              update("source_version_id", e.target.value || null)
            }
          />
        </Field>
        <Field label="来源段落">
          <input
            value={draft.source_paragraph_id ?? ""}
            onChange={(e) =>
              update("source_paragraph_id", e.target.value || null)
            }
          />
        </Field>
      </div>
      {kind === "plan" && (
        <Field label="计划层级">
          <Choice
            label="计划层级"
            value={String(draft.data?.level ?? "chapter")}
            onChange={(v) => data("level", v)}
            options={[
              ["book", "全书"],
              ["volume", "卷"],
              ["arc", "故事弧"],
              ["chapter", "章"],
              ["scene", "场景"],
            ].map(([value, label]) => ({ value, label }))}
          />
        </Field>
      )}
      {kind === "directive" && (
        <>
          <Field label="指令作用范围">
            <Choice
              label="指令作用范围"
              value={String(draft.data?.scope ?? "book")}
              onChange={(v) => data("scope", v)}
              options={[
                ["book", "全书"],
                ["volume", "卷"],
                ["arc", "故事弧"],
                ["chapter", "章"],
                ["scene", "场景"],
                ["paragraph", "段落"],
              ].map(([value, label]) => ({ value, label }))}
            />
          </Field>
          <Tick
            checked={!!draft.data?.hard}
            onChange={(v) => data("hard", v)}
            label="硬约束（必须满足）"
          />
        </>
      )}
      {kind === "foreshadow" && (
        <Field label="回收状态">
          <Choice
            label="回收状态"
            value={String(draft.data?.status ?? "open")}
            onChange={(v) => data("status", v)}
            options={[
              { value: "open", label: "待回收" },
              { value: "resolved", label: "已兑现" },
              { value: "abandoned", label: "作者放弃" },
            ]}
          />
        </Field>
      )}
      <div className="form-grid">
        {extraFields[kind].map((f) => (
          <Field key={f.key} label={f.label}>
            <input
              type={f.type === "number" ? "number" : "text"}
              value={
                Array.isArray(draft.data?.[f.key])
                  ? (draft.data![f.key] as unknown[]).join(",")
                  : String(draft.data?.[f.key] ?? "")
              }
              onChange={(e) =>
                data(
                  f.key,
                  f.type === "number"
                    ? e.target.value === ""
                      ? null
                      : +e.target.value
                    : f.type === "lines"
                      ? e.target.value
                          .split(/[,，]/)
                          .map((v) => v.trim())
                          .filter(Boolean)
                      : e.target.value,
                )
              }
            />
          </Field>
        ))}
      </div>
      <Field label="依赖的资料标识（逗号分隔）">
        <input
          value={draft.dependencies?.join(",") ?? ""}
          onChange={(e) =>
            update(
              "dependencies",
              e.target.value.split(/[,，]/).filter(Boolean),
            )
          }
        />
      </Field>
      <button className="primary" disabled={busy}>
        保存资料{existing ? "新版本" : ""}
      </button>
    </form>
  );
}

function RecordImpact({
  impact,
  ack,
  setAck,
}: {
  impact: Impact | null;
  ack: boolean;
  setAck: (v: boolean) => void;
}) {
  if (!impact) return null;
  return (
    <section>
      <h3>修改故事资料的后续影响</h3>
      <Inspect value={impact.coverage} />
      {impact.items.length === 0 ? (
        <p className="muted">未发现结构化依赖。仍需作者核查情节含义。</p>
      ) : (
        <>
          {impact.items.map((item) => (
            <article key={item.chapter_id} className="record">
              <strong>
                第 {item.number} 章 · {item.title} ·{" "}
                {item.kind === "direct" ? "直接影响" : "推测影响"}
              </strong>
              <p>{item.reason}</p>
            </article>
          ))}
          <Tick
            checked={ack}
            onChange={setAck}
            label="我已核查上述影响，接受更新资料并将受影响章节标记为待修复"
          />
        </>
      )}
    </section>
  );
}
