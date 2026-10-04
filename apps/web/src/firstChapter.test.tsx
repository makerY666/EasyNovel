import { describe, it, expect, vi } from "vitest";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { Director, ModelBudget, RunReview } from "./Director";
import App from "./App";
import { ChapterWorkspace } from "./ChapterWorkspace";
import { bootstrap, Api } from "./api";
import { stageLabel } from "./runPresentation";
import { ReviewResults } from "./RunEvidence";
import { SessionContext, type Session } from "./session";
import type { Run, Provider } from "./types";
const provider: Provider = {
  id: "model",
  name: "连接",
  model: "creative",
  base_url: "http://localhost",
  has_key: true,
  context_limit: 16000,
  max_output: 2048,
  input_price: null,
  output_price: null,
};
const draftRun: Run = {
  id: "run",
  project_id: "book",
  chapter_id: "chapter",
  input_revision: 1,
  status: "awaiting_review",
  node: "review",
  request: { kind: "chapter", token_budget: 50000 },
  artifacts: { draft: "正文第一段。\n\n正文第二段。" },
  error: null,
  usage: { input_tokens: 300, output_tokens: 800, reserved_tokens: 0, cost: 0 },
  created_at: "",
};
function state(api: unknown): Session {
  return {
    api: api as Api,
    project: {
      id: "book",
      title: "新作",
      genre: "悬疑",
      mode: "serial",
      description: "",
      revision: 1,
      settings: {},
      created_at: "",
    },
    branch: "main",
    providers: [provider],
    profiles: [],
    refresh: vi.fn().mockResolvedValue(undefined),
    report: vi.fn(),
    notice: vi.fn(),
    setRun: vi.fn(),
  };
}
const pendingEvents = (_id: unknown, _after: unknown, signal: AbortSignal) =>
  new Promise<void>((resolve) =>
    signal.addEventListener("abort", () => resolve()),
  );
describe("first chapter authoring", () => {
  it("refreshes the history entry when a failed task resumes and completes without reloading the editor", async () => {
    let current = { ...draftRun, status: "failed", node: "architect" };
    let notify:
      | ((event: { seq: number; event: string; data: unknown }) => void)
      | undefined;
    const api = {
      get: vi
        .fn()
        .mockImplementation((path: string) =>
          Promise.resolve(
            path === "/projects/book/runs"
              ? [{ ...draftRun, status: "failed", node: "architect" }]
              : current,
          ),
        ),
      events: vi
        .fn()
        .mockImplementation((_id, _after, signal: AbortSignal, callback) => {
          notify = callback;
          return pendingEvents(_id, _after, signal);
        }),
    };
    const committed = vi.fn();
    render(
      <SessionContext.Provider value={state(api)}>
        <Director
          chapterId="chapter"
          runId="run"
          onRun={() => {}}
          onCommitted={committed}
        />
      </SessionContext.Provider>,
    );
    expect(
      await screen.findByRole("button", { name: /整理故事架构.*失败/ }),
    ).toBeInTheDocument();
    current = { ...draftRun, status: "awaiting_review", node: "review" };
    await act(async () => notify?.({ seq: 1, event: "status", data: {} }));
    expect(
      await screen.findByRole("button", { name: /等待审核正文.*待审核/ }),
    ).toBeInTheDocument();
    expect(committed).not.toHaveBeenCalled();
    current = { ...draftRun, status: "completed", node: "completed" };
    await act(async () => notify?.({ seq: 2, event: "status", data: {} }));
    expect(
      await screen.findByRole("button", { name: /正文已确认入库.*已完成/ }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /整理故事架构.*失败/ }),
    ).not.toBeInTheDocument();
    await waitFor(() => expect(committed).toHaveBeenCalledOnce());
  });
  it("shows a readable clean review result and summary instead of empty English issue fields", () => {
    render(
      <ReviewResults
        reviews={[{ issues: [], summary: "人物动机可信，事件衔接自然。" }]}
      />,
    );
    expect(screen.getByText("未发现需要修改的问题")).toBeInTheDocument();
    expect(screen.getByText("审稿摘要：")).toBeInTheDocument();
    expect(screen.getByText(/人物动机可信，事件衔接自然/)).toBeInTheDocument();
    expect(screen.queryByText("issues")).not.toBeInTheDocument();
    expect(screen.queryByText("summary")).not.toBeInTheDocument();
  });
  it("localizes review bases and severity while retaining verbatim quotes and evidence locations", () => {
    render(
      <ReviewResults
        reviews={[
          {
            issues: [
              {
                severity: "warning",
                basis: "future_risk",
                category: "continuity",
                quote: "critical",
                paragraph_id: "paragraph-uuid",
                evidence_ids: ["evidence-uuid"],
                description: "后续需要交代伤势恢复",
              },
            ],
            summary: "当前未出现已知矛盾",
          },
        ]}
      />,
    );
    expect(screen.getByText("审稿问题")).toBeInTheDocument();
    expect(screen.getByText("未来风险")).toBeInTheDocument();
    expect(screen.getByText("提醒")).toBeInTheDocument();
    expect(screen.getByText("原文引用")).toBeInTheDocument();
    expect(screen.getByText("critical")).toBeInTheDocument();
    expect(screen.getByText("paragraph-uuid")).toBeInTheDocument();
    expect(screen.getByText("evidence-uuid")).toBeInTheDocument();
  });
  it("labels candidate memory in Chinese and preserves expandable source evidence", async () => {
    const api = {
      get: vi.fn().mockResolvedValue({
        ...draftRun,
        artifacts: {
          ...draftRun.artifacts,
          memory_delta: [
            {
              kind: "event",
              title: "收到信",
              content: "林秋收到父亲的信",
              source_type: "text",
              source_version_id: "source-uuid",
              source_paragraph_id: "paragraph-uuid",
              data: { quote: "他拆开了信封。" },
            },
          ],
        },
      }),
      events: vi.fn().mockImplementation(pendingEvents),
    };
    render(
      <SessionContext.Provider value={state(api)}>
        <RunReview runId="run" onCommitted={() => {}} />
      </SessionContext.Provider>,
    );
    expect(
      await screen.findByText("事件与因果 · 正文证据"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByText("来源与原文证据"));
    expect(screen.getByText("来源版本")).toBeInTheDocument();
    expect(screen.getByText("source-uuid")).toBeInTheDocument();
    expect(screen.getByText("paragraph-uuid")).toBeInTheDocument();
    expect(screen.getByText("原文引用")).toBeInTheDocument();
    expect(screen.getByText("他拆开了信封。")).toBeInTheDocument();
    expect(screen.queryByText("quote")).not.toBeInTheDocument();
  });
  it("labels the bounded chapter length adjustment stage", () => {
    expect(stageLabel("length")).toBe("调整正文篇幅");
  });
  it.each(["awaiting_review", "completed", "stale"])(
    "starts a separate author revision from a %s task after saving and reads the latest project revision",
    async (status) => {
      const oldRun = {
        ...draftRun,
        status,
        artifacts: { ...draftRun.artifacts, version_id: "saved-candidate" },
      };
      const api = {
        get: vi
          .fn()
          .mockImplementation((path: string) =>
            Promise.resolve(
              path === "/projects/book" ? { revision: 3 } : oldRun,
            ),
          ),
        post: vi.fn().mockResolvedValue({ ...draftRun, id: "revision-run" }),
        events: vi.fn().mockImplementation(pendingEvents),
      };
      const session = state(api);
      const beforeCommit = vi.fn().mockResolvedValue(true);
      render(
        <SessionContext.Provider value={session}>
          <RunReview
            runId="run"
            onCommitted={() => {}}
            onBeforeCommit={beforeCommit}
          />
        </SessionContext.Provider>,
      );
      fireEvent.click(await screen.findByText("让 AI 按要求修改"));
      if (status === "stale")
        expect(
          screen.getByText(/新任务将重新读取当前前文/),
        ).toBeInTheDocument();
      fireEvent.change(screen.getByRole("textbox", { name: "修改要求" }), {
        target: { value: "  保留事件，增加试探站长的对话  " },
      });
      fireEvent.click(screen.getByRole("button", { name: "生成修改稿" }));
      await waitFor(() =>
        expect(api.post).toHaveBeenCalledWith("/runs/run/revise", {
          instruction: "保留事件，增加试探站长的对话",
          expected_revision: 3,
        }),
      );
      expect(beforeCommit).toHaveBeenCalledOnce();
      expect(session.setRun).toHaveBeenCalledWith("revision-run");
      expect(api.post).toHaveBeenCalledOnce();
      expect(screen.getByText(/正文第一段。/)).toBeInTheDocument();
    },
  );
  it("does not request author revision or switch tasks when saving fails", async () => {
    const api = {
      get: vi.fn().mockResolvedValue(draftRun),
      post: vi.fn(),
      events: vi.fn().mockImplementation(pendingEvents),
    };
    const session = state(api);
    const beforeCommit = vi.fn().mockResolvedValue(false);
    render(
      <SessionContext.Provider value={session}>
        <RunReview
          runId="run"
          onCommitted={() => {}}
          onBeforeCommit={beforeCommit}
        />
      </SessionContext.Provider>,
    );
    fireEvent.click(await screen.findByText("让 AI 按要求修改"));
    fireEvent.change(screen.getByRole("textbox", { name: "修改要求" }), {
      target: { value: "增加对话" },
    });
    fireEvent.click(screen.getByRole("button", { name: "生成修改稿" }));
    await waitFor(() => expect(beforeCommit).toHaveBeenCalledOnce());
    expect(api.post).not.toHaveBeenCalled();
    expect(api.get).not.toHaveBeenCalledWith("/projects/book");
    expect(session.setRun).not.toHaveBeenCalled();
    expect(screen.getByRole("textbox", { name: "修改要求" })).toHaveValue(
      "增加对话",
    );
  });
  it("explains how to configure a model before paid authoring is available", () => {
    render(
      <SessionContext.Provider value={{ ...state({}), providers: [] }}>
        <ModelBudget
          provider=""
          onProvider={() => {}}
          budget={50000}
          onBudget={() => {}}
        />
      </SessionContext.Provider>,
    );
    expect(
      screen.getByText("尚未配置模型，请到设置→模型连接添加服务"),
    ).toBeInTheDocument();
  });
  it("explains when length was adjusted and a style suggestion was rejected", async () => {
    const api = {
      get: vi.fn().mockResolvedValue({
        ...draftRun,
        artifacts: {
          ...draftRun.artifacts,
          length_adjustment: { before: 600, after: 1400 },
          style_rejected: "润色改变剧情，保留审稿后的正文",
        },
      }),
      events: vi.fn().mockImplementation(pendingEvents),
    };
    render(
      <SessionContext.Provider value={state(api)}>
        <RunReview runId="run" onCommitted={() => {}} />
      </SessionContext.Provider>,
    );
    expect(await screen.findByText("正文长度已调整")).toBeInTheDocument();
    expect(
      screen.getByText("文体修改未采用：润色改变剧情，保留审稿后的正文"),
    ).toBeInTheDocument();
  });
  it("reconnects when a launch session changes on the same page and leaves unrelated hashes alone", async () => {
    history.replaceState(null, "", "/");
    sessionStorage.setItem("easynovel.token", "first-session");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(
      async (input) =>
        new Response(
          JSON.stringify(
            String(input).endsWith("/health")
              ? {
                  version: "test",
                  semantic_search: false,
                  legacy_database_detected: false,
                }
              : [],
          ),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
    );
    try {
      render(<App />);
      await waitFor(() =>
        expect(fetchSpy).toHaveBeenCalledWith(
          "/api/v1/health",
          expect.objectContaining({ headers: expect.any(Headers) }),
        ),
      );
      history.replaceState(null, "", "/#session=second-session&view=write");
      fireEvent(window, new HashChangeEvent("hashchange"));
      await waitFor(() =>
        expect(
          fetchSpy.mock.calls.some(
            ([url, init]) =>
              String(url).endsWith("/health") &&
              new Headers(init?.headers).get("Authorization") ===
                "Bearer second-session",
          ),
        ).toBe(true),
      );
      expect(sessionStorage.getItem("easynovel.token")).toBe("second-session");
      expect(location.hash).toBe("#view=write");
      const count = fetchSpy.mock.calls.length;
      history.replaceState(null, "", "/#chapter/one");
      fireEvent(window, new HashChangeEvent("hashchange"));
      expect(location.hash).toBe("#chapter/one");
      expect(fetchSpy.mock.calls.length).toBe(count);
    } finally {
      fetchSpy.mockRestore();
      history.replaceState(null, "", "/");
    }
  });
  it("uses an explicit launch session for every initial request even when storage contains an expired token", async () => {
    sessionStorage.setItem("easynovel.token", "expired-session");
    localStorage.setItem("easynovel.project", "book");
    history.replaceState(null, "", "/#session=fresh-session");
    const project = state({}).project;
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async (input) => {
        const url = String(input);
        const data = url.endsWith("/health")
          ? {
              version: "test",
              semantic_search: false,
              legacy_database_detected: false,
            }
          : url.endsWith("/projects")
            ? [project]
            : url.endsWith("/projects/book")
              ? project
              : url.includes("/chapters?")
                ? { items: [], total: 0 }
                : [];
        return new Response(JSON.stringify(data), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      });
    try {
      render(<App />);
      expect(sessionStorage.getItem("easynovel.token")).toBe("fresh-session");
      expect(location.hash).toBe("");
      await waitFor(() =>
        expect(
          fetchSpy.mock.calls.some(([url]) =>
            String(url).includes("/chapters?"),
          ),
        ).toBe(true),
      );
      expect(
        fetchSpy.mock.calls.every(
          ([, init]) =>
            new Headers(init?.headers).get("Authorization") ===
            "Bearer fresh-session",
        ),
      ).toBe(true);
      expect(screen.queryByText(/401：/)).not.toBeInTheDocument();
    } finally {
      fetchSpy.mockRestore();
      history.replaceState(null, "", "/");
    }
  });
  it("updates old browser polling clients before hashchange is delivered", async () => {
    sessionStorage.setItem("easynovel.token", "expired-session");
    const oldClient = new Api({ base_url: "", token: "expired-session" });
    history.replaceState(null, "", "/#session=fresh-session");
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("[]", { status: 200 }));
    try {
      await oldClient.get("/health");
      expect(
        new Headers(fetchSpy.mock.calls[0][1]?.headers).get("Authorization"),
      ).toBe("Bearer fresh-session");
      expect(location.hash).toBe("#session=fresh-session");
      await bootstrap();
      expect(location.hash).toBe("");
      fetchSpy.mockResolvedValue(new Response("[]", { status: 200 }));
      await oldClient.get("/projects");
      expect(
        new Headers(fetchSpy.mock.calls[1][1]?.headers).get("Authorization"),
      ).toBe("Bearer fresh-session");
    } finally {
      fetchSpy.mockRestore();
      history.replaceState(null, "", "/");
    }
  });
  it("defaults to direct drafting, automatically selects a sole model, and explicitly enables automatic plan approval", async () => {
    const api = {
      get: vi.fn().mockResolvedValue([]),
      post: vi.fn().mockResolvedValue(draftRun),
    };
    const onRun = vi.fn();
    render(
      <SessionContext.Provider value={state(api)}>
        <Director
          chapterId="chapter"
          runId={null}
          onRun={onRun}
          onCommitted={() => {}}
        />
      </SessionContext.Provider>,
    );
    fireEvent.change(screen.getByRole("textbox", { name: "本章创作任务" }), {
      target: { value: "写第一章，人物在旧车站发现信件。" },
    });
    const submit = screen.getByRole("button", { name: "直接写正文" });
    await waitFor(() => expect(submit).not.toBeDisabled());
    fireEvent.click(submit);
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith(
        "/projects/book/runs",
        expect.objectContaining({
          chapter_id: "chapter",
          provider_id: "model",
          auto_approve_plan: true,
          candidate_count: 1,
          token_budget: 200000,
        }),
      ),
    );
    expect(onRun).toHaveBeenCalledWith("run");
  });
  it("preserves the author's custom task budget when changing chapter", async () => {
    const api = {
      get: vi.fn().mockResolvedValue([]),
      post: vi.fn().mockResolvedValue(draftRun),
    };
    const session = state(api);
    const view = (chapterId: string) => (
      <SessionContext.Provider value={session}>
        <Director
          chapterId={chapterId}
          runId={null}
          onRun={() => {}}
          onCommitted={() => {}}
        />
      </SessionContext.Provider>
    );
    const { rerender } = render(view("chapter"));
    fireEvent.change(
      screen.getByRole("spinbutton", { name: /^任务 Token 上限/ }),
      {
        target: { value: "137000" },
      },
    );
    rerender(view("next-chapter"));
    fireEvent.change(screen.getByRole("textbox", { name: "本章创作任务" }), {
      target: { value: "继续第二章" },
    });
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "直接写正文" }),
      ).not.toBeDisabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: "直接写正文" }));
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith(
        "/projects/book/runs",
        expect.objectContaining({
          token_budget: 137000,
          provider_id: "model",
          chapter_id: "next-chapter",
        }),
      ),
    );
  });
  it("never presents architecture or directive text stream as novel draft", async () => {
    const directive = {
      ...draftRun,
      chapter_id: null,
      request: { kind: "directive" },
      status: "completed",
      node: "directive_ready",
      artifacts: { directive: { title: "关系约束" } },
    };
    const api = {
      get: vi.fn().mockResolvedValue(directive),
      events: vi.fn().mockImplementation((_id, _after, signal, receive) => {
        receive({
          seq: 1,
          event: "text",
          data: { role: "planner", text: '{"kind":"directive"}' },
        });
        return pendingEvents(_id, _after, signal);
      }),
    };
    const s = state(api);
    const committed = vi.fn();
    render(
      <SessionContext.Provider value={s}>
        <RunReview runId="run" onCommitted={committed} />
      </SessionContext.Provider>,
    );
    await screen.findByText("关系约束");
    expect(screen.queryByText("正文候选")).not.toBeInTheDocument();
    expect(screen.getByText("模型流式技术日志（非正文）")).toBeInTheDocument();
    await waitFor(() =>
      expect(s.notice).toHaveBeenCalledWith(
        "创作指令已整理，请到故事资料核对候选约束",
      ),
    );
    expect(committed).not.toHaveBeenCalled();
  });
  it("shows intact per-call review logs and ignores replayed stream events", async () => {
    const api = {
      get: vi.fn().mockResolvedValue(draftRun),
      events: vi.fn().mockImplementation((_id, _after, signal, receive) => {
        const chunks = [
          { seq: 1, role: "editor", call_key: "editor:1", text: '{"sum' },
          { seq: 2, role: "continuity", call_key: "continuity:1", text: '{"summary":"无矛盾"}' },
          { seq: 3, role: "editor", call_key: "editor:1", text: 'mary":"动机合理"}' },
          { seq: 3, role: "editor", call_key: "editor:1", text: 'mary":"动机合理"}' },
          { seq: 4, role: "editor", call_key: "editor:2", text: '{"summary":"复核完成"}' },
        ];
        for (const { seq, ...data } of chunks) receive({ seq, event: "text", data });
        return pendingEvents(_id, _after, signal);
      }),
    };
    render(
      <SessionContext.Provider value={state(api)}>
        <RunReview runId="run" onCommitted={() => {}} />
      </SessionContext.Provider>,
    );
    await screen.findByText('{"summary":"动机合理"}', { exact: true });
    expect(screen.getByText('{"summary":"无矛盾"}', { exact: true })).toBeInTheDocument();
    expect(screen.getByText('{"summary":"复核完成"}', { exact: true })).toBeInTheDocument();
    expect(screen.getAllByText(/剧情与人物编辑 · 输出/)).toHaveLength(2);
    expect(screen.queryByText(/\[剧情与人物编辑\]/)).not.toBeInTheDocument();
  });
  it("warns authors when only part of the draft has valid extracted memory", async () => {
    const run = {
      ...draftRun,
      artifacts: {
        ...draftRun.artifacts,
        memory_delta: [],
        memory_warnings: [{ call_key: "memory:chunk:1", message: "记忆整理员输出校验失败", paragraph_ids: ["p2"] }],
      },
    };
    render(
      <SessionContext.Provider value={state({ get: vi.fn().mockResolvedValue(run), events: vi.fn().mockImplementation(pendingEvents) })}>
        <RunReview runId="run" onCommitted={() => {}} />
      </SessionContext.Provider>,
    );
    const warning = await screen.findByRole("alert");
    expect(warning).toHaveTextContent("部分正文的候选记忆未提取成功");
    expect(warning).toHaveTextContent("不能把空的记忆列表当作全文已核查");
    expect(warning).toHaveTextContent("涉及 1 段正文");
    expect(screen.getByText("正文第一段。", { exact: false })).toBeInTheDocument();
  });
  it("automatically previews actual novel draft without remounting or losing editor text", async () => {
    const { rerender } = render(
      <ChapterWorkspace run={null} projectId="book" chapterId="chapter">
        <textarea aria-label="已有手稿" defaultValue="尚未保存的文字" />
      </ChapterWorkspace>,
    );
    const original = screen.getByRole("textbox", { name: "已有手稿" });
    fireEvent.change(original, { target: { value: "作者正在写的新段落" } });
    rerender(
      <ChapterWorkspace run={draftRun} projectId="book" chapterId="chapter">
        <textarea aria-label="已有手稿" defaultValue="尚未保存的文字" />
      </ChapterWorkspace>,
    );
    await screen.findByRole("heading", { name: "正文候选预览" });
    expect(screen.getByText("正文第一段。")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "返回编辑器" }));
    expect(screen.getByRole("textbox", { name: "已有手稿" })).toBe(original);
    expect(original).toHaveValue("作者正在写的新段落");
  });
  it("keeps drafts from other chapters or books out of the active chapter", () => {
    render(
      <ChapterWorkspace
        run={{ ...draftRun, chapter_id: "other" }}
        projectId="book"
        chapterId="chapter"
      >
        <textarea aria-label="已有手稿" defaultValue="手稿" />
      </ChapterWorkspace>,
    );
    expect(
      screen.queryByRole("heading", { name: "正文候选预览" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "已有手稿" })).toBeVisible();
  });
  it("shows output truncation separately from total budget and raises both provider and role caps on resume", async () => {
    const paused: Run = {
      ...draftRun,
      status: "paused",
      node: "architect",
      error: "回答达到输出上限，结果未完整",
      artifacts: {
        output_limit_info: {
          role: "architect",
          maximum: 1024,
          provider_id: "model",
          provider_max_output: 2048,
          role_max_output: null,
          requested_output_limit: 1024,
          model: "creative",
          context_limit: 16000,
        },
      },
      request: {
        kind: "chapter",
        token_budget: 50000,
        provider_snapshots: { model: provider },
      },
    };
    const api = {
      get: vi.fn().mockResolvedValue(paused),
      post: vi.fn().mockResolvedValue({}),
      events: vi.fn().mockImplementation(pendingEvents),
    };
    render(
      <SessionContext.Provider value={state(api)}>
        <RunReview runId="run" onCommitted={() => {}} />
      </SessionContext.Provider>,
    );
    await screen.findByText("故事架构师：单次回答达到输出上限");
    fireEvent.click(screen.getByRole("button", { name: "调整额度并恢复" }));
    expect(
      screen.getByRole("spinbutton", { name: "任务总 Token 上限" }),
    ).toHaveValue(50000);
    expect(screen.getByRole("spinbutton", { name: "故事架构师" })).toHaveValue(
      4096,
    );
    expect(
      screen.getByRole("spinbutton", { name: /模型单次输出上限/ }),
    ).toHaveValue(4096);
    fireEvent.click(screen.getByRole("button", { name: "保存额度并恢复" }));
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/runs/run/resume", {
        token_budget: 50000,
        role_limits: { architect: 4096 },
        provider_output_limits: { model: 4096 },
      }),
    );
  });
  it("accepts launcher session token and immediately removes it from URL while preserving other hash parameters", async () => {
    history.replaceState(
      null,
      "",
      "/?project=book#session=" +
        encodeURIComponent("temporary-token") +
        "&view=write",
    );
    expect(await bootstrap()).toEqual({
      base_url: "",
      token: "temporary-token",
    });
    expect(sessionStorage.getItem("easynovel.token")).toBe("temporary-token");
    expect(location.hash).toBe("#view=write");
    expect(location.search).toBe("?project=book");
    history.replaceState(null, "", "/");
  });
  it("does not consume unrelated browser routes as a session parameter", async () => {
    history.replaceState(null, "", "/#chapter/one");
    expect(await bootstrap()).toBeNull();
    expect(location.hash).toBe("#chapter/one");
    history.replaceState(null, "", "/");
  });
  it("offers an explicit directive-only mode that never starts a chapter drafting run", async () => {
    const api = {
      get: vi.fn().mockResolvedValue([]),
      post: vi.fn().mockResolvedValue({
        ...draftRun,
        chapter_id: null,
        request: { kind: "directive" },
      }),
    };
    const beforeStart = vi.fn().mockResolvedValue(false);
    render(
      <SessionContext.Provider value={state(api)}>
        <Director
          chapterId="chapter"
          runId={null}
          onRun={() => {}}
          onCommitted={() => {}}
          onBeforeStart={beforeStart}
        />
      </SessionContext.Provider>,
    );
    fireEvent.keyDown(screen.getByRole("combobox", { name: "创作方式" }), {
      key: "Enter",
    });
    fireEvent.click(
      await screen.findByRole("option", { name: "整理创作指令" }),
    );
    fireEvent.change(
      screen.getByRole("textbox", { name: "自然语言创作指令" }),
      { target: { value: "本卷两人渐渐决裂" } },
    );
    fireEvent.click(screen.getByRole("button", { name: "整理创作指令" }));
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/projects/book/directives/parse", {
        text: "本卷两人渐渐决裂",
        provider_id: "model",
        token_budget: 200000,
      }),
    );
    expect(
      screen.getByText("仅整理候选约束卡，不生成小说正文。"),
    ).toBeInTheDocument();
    expect(beforeStart).not.toHaveBeenCalled();
  });
  it("leaves automatic plan approval disabled when the author chooses to review plans first", async () => {
    const api = {
      get: vi.fn().mockResolvedValue([]),
      post: vi.fn().mockResolvedValue(draftRun),
    };
    render(
      <SessionContext.Provider value={state(api)}>
        <Director
          chapterId="chapter"
          runId={null}
          onRun={() => {}}
          onCommitted={() => {}}
        />
      </SessionContext.Provider>,
    );
    fireEvent.keyDown(screen.getByRole("combobox", { name: "创作方式" }), {
      key: "Enter",
    });
    fireEvent.click(await screen.findByRole("option", { name: "先审核计划" }));
    fireEvent.change(screen.getByRole("textbox", { name: "本章创作任务" }), {
      target: { value: "规划火车站中的冲突" },
    });
    fireEvent.click(screen.getByRole("button", { name: "生成待审核计划" }));
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith(
        "/projects/book/runs",
        expect.objectContaining({
          auto_approve_plan: false,
          task: "规划火车站中的冲突",
        }),
      ),
    );
  });

  it("opening a previously completed run does not remount the current chapter editor", async () => {
    const api = {
      get: vi.fn().mockResolvedValue({
        ...draftRun,
        status: "completed",
        node: "completed",
        request: { ...draftRun.request, kind: "author_revision" },
      }),
      events: vi.fn().mockImplementation(pendingEvents),
    };
    const committed = vi.fn();
    render(
      <SessionContext.Provider value={state(api)}>
        <RunReview runId="run" onCommitted={committed} />
      </SessionContext.Provider>,
    );
    await screen.findByText(/正文第一段。/);
    expect(
      screen.getByText(/作者要求修订 · 正文已确认入库/),
    ).toBeInTheDocument();
    expect(committed).not.toHaveBeenCalled();
  });

  it("does not start a paid chapter task when saving the active manuscript fails", async () => {
    const api = {
      get: vi.fn().mockResolvedValue([]),
      post: vi.fn().mockResolvedValue(draftRun),
    };
    const beforeStart = vi.fn().mockResolvedValue(false);
    render(
      <SessionContext.Provider value={state(api)}>
        <Director
          chapterId="chapter"
          runId={null}
          onRun={() => {}}
          onCommitted={() => {}}
          onBeforeStart={beforeStart}
        />
      </SessionContext.Provider>,
    );
    fireEvent.change(screen.getByRole("textbox", { name: "本章创作任务" }), {
      target: { value: "继续第一章" },
    });
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "直接写正文" }),
      ).not.toBeDisabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: "直接写正文" }));
    await waitFor(() => expect(beforeStart).toHaveBeenCalledOnce());
    expect(api.post).not.toHaveBeenCalled();
    expect(screen.getByRole("textbox", { name: "本章创作任务" })).toHaveValue(
      "继续第一章",
    );
  });
  it("does not submit final approval when saving unsaved editor text fails", async () => {
    const api = {
      get: vi.fn().mockResolvedValue(draftRun),
      post: vi.fn().mockResolvedValue({}),
      events: vi.fn().mockImplementation(pendingEvents),
    };
    const beforeCommit = vi.fn().mockResolvedValue(false);
    render(
      <SessionContext.Provider value={state(api)}>
        <RunReview
          runId="run"
          onCommitted={() => {}}
          onBeforeCommit={beforeCommit}
        />
      </SessionContext.Provider>,
    );
    await screen.findByText(/正文第一段。/);
    fireEvent.click(
      screen.getByRole("button", { name: "确认审核与 0 条记忆" }),
    );
    await waitFor(() => expect(beforeCommit).toHaveBeenCalledOnce());
    expect(api.post).not.toHaveBeenCalled();
    expect(screen.getByText(/正文第一段。/)).toBeInTheDocument();
  });
});
