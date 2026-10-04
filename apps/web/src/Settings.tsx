import { useState } from "react";
import { useSession, useAction } from "./session";
import { Choice, Empty, Field, Inspect, Modal, TabPanel } from "./ui";
import type { Profile, Provider, Role } from "./types";
const roles = [
  ["architect", "故事架构师"],
  ["planner", "章节与场景规划师"],
  ["writer", "正文作者"],
  ["continuity", "连续性审计员"],
  ["editor", "剧情与人物编辑"],
  ["stylist", "文体编辑"],
  ["memory", "记忆整理员"],
];
export function Settings() {
  const { api, project, providers, profiles, refresh, notice } = useSession();
  const { act, busy } = useAction();
  const [tab, setTab] = useState("models");
  const [editProvider, setEditProvider] = useState<Provider | null>(null);
  const [providerOpen, setProviderOpen] = useState(false);
  const [editProfile, setEditProfile] = useState<Profile | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [test, setTest] = useState<unknown>(null);
  const [remove, setRemove] = useState<Provider | null>(null);
  const [title, setTitle] = useState(project.title);
  const [description, setDescription] = useState(project.description);
  const [tokenBudget, setTokenBudget] = useState(
    Number(project.settings.token_budget ?? 50000),
  );
  const [moneyBudget, setMoneyBudget] = useState(
    String(project.settings.money_budget ?? ""),
  );
  const [chapterTokens, setChapterTokens] = useState(
    String(project.settings.chapter_token_budget ?? ""),
  );
  const [chapterMoney, setChapterMoney] = useState(
    String(project.settings.chapter_money_budget ?? ""),
  );
  const [rolling, setRolling] = useState(
    Number(project.settings.near_chapters ?? 5),
  );
  const [arc, setArc] = useState(Number(project.settings.arc_chapters ?? 20));
  return (
    <div className="page">
      <div className="page-title">
        <div>
          <small>模型与创作参数</small>
          <h1>设置</h1>
        </div>
      </div>
      <TabPanel
        value={tab}
        onChange={setTab}
        tabs={[
          {
            id: "models",
            label: "模型连接",
            content: (
              <>
                <div className="actions">
                  <button
                    className="primary"
                    onClick={() => {
                      setEditProvider(null);
                      setProviderOpen(true);
                    }}
                  >
                    添加模型服务
                  </button>
                </div>
                {providers.length === 0 ? (
                  <Empty>
                    添加 OpenAI-compatible 模型服务，密钥保存在系统凭据库。
                  </Empty>
                ) : (
                  providers.map((p) => (
                    <article key={p.id} className="record">
                      <h3>{p.name}</h3>
                      <p>
                        {p.model} · {p.base_url}
                      </p>
                      <p className="muted">
                        密钥{p.has_key ? "已保存" : "未设置"} · 上下文{" "}
                        {p.context_limit} · 输出 {p.max_output} · 输入/输出价格{" "}
                        {p.input_price ?? "未知"} / {p.output_price ?? "未知"}{" "}
                        每百万 tokens
                      </p>
                      <div className="actions">
                        <button
                          onClick={() => {
                            setEditProvider(p);
                            setProviderOpen(true);
                          }}
                        >
                          编辑
                        </button>
                        <button
                          disabled={busy}
                          onClick={() =>
                            void act(async () =>
                              setTest(
                                await api.post(`/providers/${p.id}/test`),
                              ),
                            )
                          }
                        >
                          实际连接测试
                        </button>
                        <button onClick={() => setRemove(p)}>删除</button>
                      </div>
                    </article>
                  ))
                )}
                {test && (
                  <section className="tool-section">
                    <h3>连接测试结果</h3>
                    <Inspect value={test} />
                  </section>
                )}
              </>
            ),
          },
          {
            id: "profiles",
            label: "智能体与审稿",
            content: (
              <>
                <div className="actions">
                  <button
                    className="primary"
                    onClick={() => {
                      setEditProfile(null);
                      setProfileOpen(true);
                    }}
                  >
                    添加工作流模板
                  </button>
                </div>
                {profiles.length === 0 ? (
                  <Empty>
                    默认流程可直接使用。建立模板后可分别配置每个智能体的模型、提示词与参数。
                  </Empty>
                ) : (
                  profiles.map((p) => (
                    <article className="record" key={p.id}>
                      <h3>{p.name}</h3>
                      <p>
                        最多修订 {p.max_revisions} 轮 ·{" "}
                        {p.review_dimensions?.join("、") ||
                          "使用作品类型默认审稿标准"}
                      </p>
                      <p className="muted">
                        已配置角色：
                        {Object.keys(p.roles ?? {})
                          .map((r) => roles.find(([id]) => id === r)?.[1] ?? r)
                          .join("、")}
                      </p>
                      <button
                        onClick={() => {
                          setEditProfile(p);
                          setProfileOpen(true);
                        }}
                      >
                        编辑模板
                      </button>
                    </article>
                  ))
                )}
              </>
            ),
          },
          {
            id: "project",
            label: "作品与预算",
            content: (
              <form
                className="tool-content"
                onSubmit={(e) => {
                  e.preventDefault();
                  void act(async () => {
                    await api.patch(`/projects/${project.id}`, {
                      expected_revision: project.revision,
                      title,
                      description,
                      settings: {
                        ...project.settings,
                        token_budget: tokenBudget,
                        money_budget: moneyBudget ? +moneyBudget : null,
                        chapter_token_budget: chapterTokens
                          ? +chapterTokens
                          : null,
                        chapter_money_budget: chapterMoney
                          ? +chapterMoney
                          : null,
                        near_chapters: rolling,
                        arc_chapters: arc,
                      },
                    });
                    await refresh();
                    notice("作品配置已保存");
                  });
                }}
              >
                <Field label="作品标题">
                  <input
                    required
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                  />
                </Field>
                <Field label="作品说明">
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                  />
                </Field>
                <Field label="默认任务 Token 上限">
                  <input
                    type="number"
                    min={1}
                    value={tokenBudget}
                    onChange={(e) => setTokenBudget(+e.target.value)}
                  />
                </Field>
                <Field
                  label="默认任务金额上限（可选）"
                  hint="模型价格未知时，金额预算不可可靠执行；token 上限仍有效"
                >
                  <input
                    type="number"
                    step="0.01"
                    min={0}
                    value={moneyBudget}
                    onChange={(e) => setMoneyBudget(e.target.value)}
                  />
                </Field>
                <div className="form-grid">
                  <Field
                    label="每章累计 Token 上限"
                    hint="累计计算同章全部创作任务；留空不限"
                  >
                    <input
                      type="number"
                      min={1}
                      value={chapterTokens}
                      onChange={(e) => setChapterTokens(e.target.value)}
                    />
                  </Field>
                  <Field
                    label="每章累计金额上限"
                    hint="价格已知时累计计算；留空不限"
                  >
                    <input
                      type="number"
                      min={0.01}
                      step="0.01"
                      value={chapterMoney}
                      onChange={(e) => setChapterMoney(e.target.value)}
                    />
                  </Field>
                </div>
                <div className="form-grid">
                  <Field label="近期细化章数">
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={rolling}
                      onChange={(e) => setRolling(+e.target.value)}
                    />
                  </Field>
                  <Field label="故事弧规划章数">
                    <input
                      type="number"
                      min={1}
                      max={500}
                      value={arc}
                      onChange={(e) => setArc(+e.target.value)}
                    />
                  </Field>
                </div>
                <button className="primary" disabled={busy}>
                  保存配置
                </button>
              </form>
            ),
          },
        ]}
      />
      <Modal
        open={providerOpen}
        onOpenChange={setProviderOpen}
        title={editProvider ? "编辑模型连接" : "添加模型连接"}
      >
        <ProviderForm
          existing={editProvider}
          onDone={async () => {
            setProviderOpen(false);
            await refresh();
          }}
        />
      </Modal>
      <Modal
        open={profileOpen}
        onOpenChange={setProfileOpen}
        title={editProfile ? "编辑工作流模板" : "添加工作流模板"}
      >
        <ProfileForm
          existing={editProfile}
          onDone={async () => {
            setProfileOpen(false);
            await refresh();
          }}
        />
      </Modal>
      <Modal
        open={!!remove}
        onOpenChange={(v) => !v && setRemove(null)}
        title="删除模型连接"
      >
        <p>
          删除「{remove?.name}」及其保存的密钥。使用此服务的智能体配置需要调整。
        </p>
        <button
          className="danger-button"
          disabled={busy}
          onClick={() =>
            void act(async () => {
              await api.delete(`/providers/${remove!.id}`);
              setRemove(null);
              await refresh();
            })
          }
        >
          删除连接
        </button>
      </Modal>
    </div>
  );
}
function ProviderForm({
  existing,
  onDone,
}: {
  existing: Provider | null;
  onDone: () => Promise<void>;
}) {
  const { api } = useSession();
  const { act, busy } = useAction();
  const [name, setName] = useState(existing?.name ?? "");
  const [url, setUrl] = useState(existing?.base_url ?? "");
  const [model, setModel] = useState(existing?.model ?? "");
  const [key, setKey] = useState("");
  const [context, setContext] = useState(existing?.context_limit ?? 32000);
  const [output, setOutput] = useState(existing?.max_output ?? 4096);
  const [inputPrice, setInputPrice] = useState(
    String(existing?.input_price ?? ""),
  );
  const [outputPrice, setOutputPrice] = useState(
    String(existing?.output_price ?? ""),
  );
  const [embedding, setEmbedding] = useState(existing?.embedding_model ?? "");
  const [extraBody, setExtraBody] = useState(
    JSON.stringify(existing?.extra_body ?? {}, null, 2),
  );
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        void act(async () => {
          const payload = {
            name,
            base_url: url,
            model,
            ...(key ? { api_key: key } : {}),
            context_limit: context,
            max_output: output,
            input_price: inputPrice ? +inputPrice : null,
            output_price: outputPrice ? +outputPrice : null,
            embedding_model: embedding || null,
            extra_body: JSON.parse(extraBody),
          };
          if (existing) await api.patch(`/providers/${existing.id}`, payload);
          else await api.post("/providers", payload);
          setKey("");
          await onDone();
        });
      }}
    >
      <Field label="连接名称">
        <input
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </Field>
      <Field label="API 基础地址">
        <input
          type="url"
          required
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://…/v1"
        />
      </Field>
      <Field label="模型名称">
        <input
          required
          value={model}
          onChange={(e) => setModel(e.target.value)}
        />
      </Field>
      <Field
        label="API 密钥"
        hint={
          existing?.has_key
            ? "已有密钥。留空保持；输入新密钥替换。"
            : "密钥不会在响应或日志中展示。"
        }
      >
        <input
          type="password"
          autoComplete="new-password"
          value={key}
          onChange={(e) => setKey(e.target.value)}
        />
      </Field>
      <div className="form-grid">
        <Field label="上下文容量">
          <input
            type="number"
            min={1024}
            value={context}
            onChange={(e) => setContext(+e.target.value)}
          />
        </Field>
        <Field label="单次最大输出">
          <input
            type="number"
            min={1}
            value={output}
            onChange={(e) => setOutput(+e.target.value)}
          />
        </Field>
        <Field label="输入价格 / 百万 tokens">
          <input
            type="number"
            min={0}
            step="any"
            value={inputPrice}
            onChange={(e) => setInputPrice(e.target.value)}
          />
        </Field>
        <Field label="输出价格 / 百万 tokens">
          <input
            type="number"
            min={0}
            step="any"
            value={outputPrice}
            onChange={(e) => setOutputPrice(e.target.value)}
          />
        </Field>
      </div>
      <Field label="嵌入模型名称（可选）">
        <input
          value={embedding}
          onChange={(e) => setEmbedding(e.target.value)}
        />
      </Field>
      <Field
        label="供应商扩展参数（JSON 对象）"
        hint={
          '例如：{"thinking":{"type":"disabled"}}。不接受模型、密钥、messages 等基础请求覆盖。'
        }
      >
        <textarea
          rows={5}
          value={extraBody}
          onChange={(e) => setExtraBody(e.target.value)}
          spellCheck={false}
        />
      </Field>
      <button className="primary" disabled={busy}>
        保存连接
      </button>
    </form>
  );
}
function ProfileForm({
  existing,
  onDone,
}: {
  existing: Profile | null;
  onDone: () => Promise<void>;
}) {
  const { api, providers } = useSession();
  const { act, busy } = useAction();
  const [name, setName] = useState(existing?.name ?? "");
  const [config, setConfig] = useState<Record<string, Role>>(
    existing?.roles ?? {},
  );
  const [rounds, setRounds] = useState(existing?.max_revisions ?? 2);
  const [dimensions, setDimensions] = useState(
    existing?.review_dimensions?.join("\n") ?? "",
  );
  const role = (id: string, patch: Partial<Role>) =>
    setConfig((p) => ({ ...p, [id]: { ...p[id], ...patch } }));
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        void act(async () => {
          const payload = {
            name,
            roles: config,
            max_revisions: rounds,
            review_dimensions: dimensions
              .split("\n")
              .map((s) => s.trim())
              .filter(Boolean),
          };
          if (existing) await api.patch(`/profiles/${existing.id}`, payload);
          else await api.post("/profiles", payload);
          await onDone();
        });
      }}
    >
      <Field label="模板名称">
        <input
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </Field>
      <Field label="自动修改最多轮数">
        <input
          type="number"
          min={0}
          max={2}
          value={rounds}
          onChange={(e) => setRounds(+e.target.value)}
        />
      </Field>
      <Field label="审稿维度（每行一项）">
        <textarea
          value={dimensions}
          onChange={(e) => setDimensions(e.target.value)}
          placeholder="人物动机与代价\n前文伏笔与时序\n信息揭示和阅读期待"
        />
      </Field>
      {roles.map(([id, label]) => (
        <details key={id}>
          <summary>{label}</summary>
          <Field label="角色模型">
            <select
              value={config[id]?.provider_id ?? ""}
              onChange={(e) =>
                role(id, { provider_id: e.target.value || undefined })
              }
            >
              <option value="">使用任务默认模型</option>
              {providers.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} / {p.model}
                </option>
              ))}
            </select>
          </Field>
          <Field label="角色提示词">
            <textarea
              rows={3}
              value={config[id]?.prompt ?? ""}
              onChange={(e) => role(id, { prompt: e.target.value })}
            />
          </Field>
          <div className="form-grid">
            <Field label="温度">
              <input
                type="number"
                min={0}
                max={2}
                step="0.1"
                value={config[id]?.temperature ?? ""}
                onChange={(e) =>
                  role(id, {
                    temperature: e.target.value ? +e.target.value : undefined,
                  })
                }
              />
            </Field>
            <Field label="最大输出">
              <input
                type="number"
                min={1}
                value={config[id]?.max_output ?? ""}
                onChange={(e) =>
                  role(id, {
                    max_output: e.target.value ? +e.target.value : undefined,
                  })
                }
              />
            </Field>
          </div>
        </details>
      ))}
      <button className="primary" disabled={busy}>
        保存模板
      </button>
    </form>
  );
}
