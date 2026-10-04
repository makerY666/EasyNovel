import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import { SessionContext, type Session } from "./session";
import { Evidence, RunReview } from "./Director";
import { Records } from "./Records";
import { BackupCenter } from "./Tools";
import { NovelEditor, stableParagraphs } from "./NovelEditor";
import { writeDraft, readDraft, acceptedMemoryIndices } from "./draft";
import type { Run, Project } from "./types";
import { Api } from "./api";
const project: Project = {
  id: "p",
  title: "作品",
  genre: "",
  mode: "serial",
  description: "",
  revision: 7,
  settings: {},
  created_at: "",
};
function session(api: unknown): Session {
  return {
    api: api as Api,
    project,
    branch: "main",
    providers: [],
    profiles: [],
    refresh: vi.fn().mockResolvedValue(undefined),
    report: vi.fn(),
    notice: vi.fn(),
    setRun: vi.fn(),
  };
}
const run: Run = {
  id: "r",
  project_id: "p",
  chapter_id: "c",
  status: "awaiting_review",
  node: "review",
  input_revision: 7,
  artifacts: {
    draft: "这是正文候选",
    memory_delta: [
      { kind: "state", title: "位置变化", content: "人物抵达城内" },
      { kind: "knowledge", title: "得知秘密", content: "人物得知信件来源" },
    ],
  },
  error: null,
  usage: { input_tokens: 10, output_tokens: 20, reserved_tokens: 0, cost: 0 },
  created_at: "",
};
describe("author review and draft safety", () => {
  it("downloads a backup using its original zip filename", async () => {
    const api = {
      get: vi
        .fn()
        .mockResolvedValue([
          {
            id: "backup",
            name: "manual-20261003.zip",
            created_at: "2026-10-03T00:00:00Z",
          },
        ]),
      download: vi.fn().mockResolvedValue(undefined),
    };
    render(
      <SessionContext.Provider value={session(api)}>
        <BackupCenter />
      </SessionContext.Provider>,
    );
    const download = await screen.findByRole("button", { name: "下载" });
    await waitFor(() => expect(download).not.toBeDisabled());
    fireEvent.click(download);
    await waitFor(() =>
      expect(api.download).toHaveBeenCalledWith(
        "/backups/backup/download",
        "manual-20261003.zip",
      ),
    );
  });
  it("only submits selected memory indices, with revision and an idempotency key", async () => {
    const api = {
      get: vi.fn().mockResolvedValue(run),
      post: vi.fn().mockImplementation(() => {
        api.get.mockResolvedValue({ ...run, status: "completed" });
        return Promise.resolve({});
      }),
      events: vi
        .fn()
        .mockImplementation(
          (_id, _after, signal) =>
            new Promise<void>((resolve) =>
              signal.addEventListener("abort", () => resolve()),
            ),
        ),
    };
    const committed = vi.fn();
    render(
      <SessionContext.Provider value={session(api)}>
        <RunReview runId="r" onCommitted={committed} />
      </SessionContext.Provider>,
    );
    await screen.findByText("位置变化");
    fireEvent.click(screen.getByRole("checkbox", { name: "得知秘密" }));
    fireEvent.click(
      screen.getByRole("button", { name: "确认审核与 1 条记忆" }),
    );
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const [path, body] = api.post.mock.calls[0];
    expect(path).toBe("/runs/r/approve");
    expect(body.accepted_memory_indices).toEqual([1]);
    expect(body.expected_revision).toBe(7);
    expect(body.idempotency_key).toMatch(/^[0-9a-f-]{36}$/);
    await waitFor(() => expect(committed).toHaveBeenCalled());
  });
  it("preserves edited candidate and reports error if re-audit fails", async () => {
    const api = {
      get: vi.fn().mockResolvedValue(run),
      post: vi.fn().mockRejectedValue(new Error("离线")),
      events: vi
        .fn()
        .mockImplementation(
          (_id, _after, signal) =>
            new Promise<void>((resolve) =>
              signal.addEventListener("abort", () => resolve()),
            ),
        ),
    };
    const s = session(api);
    render(
      <SessionContext.Provider value={s}>
        <RunReview runId="r" onCommitted={() => {}} />
      </SessionContext.Provider>,
    );
    await screen.findByText("这是正文候选");
    fireEvent.click(screen.getByRole("button", { name: "编辑候选并重新审稿" }));
    fireEvent.change(screen.getByRole("textbox", { name: "编辑正文候选" }), {
      target: { value: "保留我的修改" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存并重新审稿" }));
    await waitFor(() => expect(s.report).toHaveBeenCalled());
    expect(screen.getByRole("textbox", { name: "编辑正文候选" })).toHaveValue(
      "保留我的修改",
    );
  });
  it("recovers local text after reload and saves stable paragraph IDs as a draft", async () => {
    const paragraphs = [
      { id: "stable-id", text: "恢复的作者文本", locked: true },
    ];
    writeDraft("c", {
      baseVersion: null,
      paragraphs,
      savedAt: "2026-10-02T10:00:00Z",
    });
    const api = {
      get: vi.fn().mockResolvedValue({
        id: "c",
        title: "开篇",
        number: 1,
        draft: null,
        confirmed: null,
        project_revision: 7,
      }),
      post: vi
        .fn()
        .mockResolvedValue({ id: "v", content: "恢复的作者文本", paragraphs }),
    };
    render(
      <SessionContext.Provider value={session(api)}>
        <NovelEditor
          chapterId="c"
          onSaved={() => {}}
          onImpact={() => {}}
          onRun={() => {}}
        />
      </SessionContext.Provider>,
    );
    await screen.findByText("恢复文本");
    fireEvent.click(screen.getByRole("button", { name: "恢复文本" }));
    fireEvent.click(screen.getByRole("button", { name: "保存草稿" }));
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    expect(api.post.mock.calls[0][0]).toBe("/chapters/c/versions");
    expect(api.post.mock.calls[0][1]).toMatchObject({
      content: "恢复的作者文本",
      paragraphs,
      expected_revision: 7,
      source: "manual",
    });
    await waitFor(() => expect(readDraft("c")).toBeNull());
  });
  it("rejects edits and deletion of locked paragraphs while allowing explicit unlock", () => {
    const editor = new Editor({
      extensions: [StarterKit, stableParagraphs],
      content: {
        type: "doc",
        content: [
          {
            type: "paragraph",
            attrs: { paragraphId: "keep", locked: true },
            content: [{ type: "text", text: "锁定文本" }],
          },
          {
            type: "paragraph",
            attrs: { paragraphId: "free", locked: false },
            content: [{ type: "text", text: "可编辑" }],
          },
        ],
      },
    });
    editor.commands.setTextSelection(2);
    editor.commands.insertContent("破坏");
    expect(editor.getText()).toContain("锁定文本");
    expect(editor.getText()).not.toContain("破坏");
    editor.commands.updateAttributes("paragraph", { locked: false });
    editor.commands.insertContent("修改");
    expect(editor.getText()).toContain("修改");
    editor.destroy();
  });
  it("keeps free GET search as default and only uses paid POST search after explicit budget choice", async () => {
    const result = { items: [], semantic_search: false };
    const api = {
      get: vi.fn().mockResolvedValue(result),
      post: vi.fn().mockRejectedValue(new Error("本分支还没有可用语义索引")),
    };
    const s = session(api);
    render(
      <SessionContext.Provider value={s}>
        <Evidence chapterId="c" />
      </SessionContext.Provider>,
    );
    fireEvent.change(
      screen.getByRole("textbox", { name: "检索人物、道具或情节" }),
      { target: { value: "玉佩" } },
    );
    fireEvent.click(screen.getByRole("button", { name: "查找证据" }));
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(
        "/projects/p/search?q=%E7%8E%89%E4%BD%A9&branch_id=main&limit=20",
      ),
    );
    expect(api.post).not.toHaveBeenCalled();
    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "使用语义检索（嵌入调用可能计费）",
      }),
    );
    fireEvent.change(
      screen.getByRole("spinbutton", { name: /查询嵌入 Token 上限/ }),
      { target: { value: "1500" } },
    );
    fireEvent.click(screen.getByRole("button", { name: "查找证据" }));
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/projects/p/search", {
        q: "玉佩",
        branch_id: "main",
        story_time: undefined,
        token_budget: 1500,
      }),
    );
    await waitFor(() => expect(s.report).toHaveBeenCalled());
    expect(api.get).toHaveBeenCalledTimes(1);
  });
  it("never includes invalid memory selections", () =>
    expect(acceptedMemoryIndices(new Set([2, -1, 5, 0, 1.5]), 3)).toEqual([
      0, 2,
    ]));
  it("asks explicitly before accepting a revision that changes the approved plot", async () => {
    const changed = {
      ...run,
      status: "awaiting_plan",
      artifacts: {
        plans: [{ title: "原计划", goal: "保持目标" }],
        proposed_revision: {
          change_reason: "核心事件改为失败",
          content: "变更后的正文",
        },
      },
    };
    const api = {
      get: vi.fn().mockResolvedValue(changed),
      post: vi.fn().mockResolvedValue({}),
      events: vi
        .fn()
        .mockImplementation(
          (_id, _after, signal) =>
            new Promise<void>((resolve) =>
              signal.addEventListener("abort", () => resolve()),
            ),
        ),
    };
    render(
      <SessionContext.Provider value={session(api)}>
        <RunReview runId="r" onCommitted={() => {}} />
      </SessionContext.Provider>,
    );
    await screen.findByText("核心事件改为失败");
    expect(
      screen.queryByRole("button", { name: "批准此计划并生成正文" }),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "接受剧情调整" }));
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/runs/r/approve-plan", {
        accept_change: true,
      }),
    );
  });
  it("resumes a paused task with explicit token and role output limits", async () => {
    const paused = {
      ...run,
      status: "paused",
      request: { token_budget: 200000 },
      usage: { ...run.usage, cost_known: false },
    };
    const api = {
      get: vi.fn().mockResolvedValue(paused),
      post: vi.fn().mockResolvedValue({}),
      events: vi
        .fn()
        .mockImplementation(
          (_id, _after, signal) =>
            new Promise<void>((resolve) =>
              signal.addEventListener("abort", () => resolve()),
            ),
        ),
    };
    render(
      <SessionContext.Provider value={session(api)}>
        <RunReview runId="r" onCommitted={() => {}} />
      </SessionContext.Provider>,
    );
    await screen.findByText("金额未知 · 仅统计 Token");
    fireEvent.click(screen.getByRole("button", { name: "调整额度并恢复" }));
    expect(
      screen.getByRole("spinbutton", { name: "任务总 Token 上限" }),
    ).toHaveValue(200000);
    fireEvent.change(
      screen.getByRole("spinbutton", { name: "任务总 Token 上限" }),
      { target: { value: "300000" } },
    );
    fireEvent.click(screen.getByText("角色输出上限（响应截断时调整）"));
    fireEvent.change(screen.getByRole("spinbutton", { name: "正文作者" }), {
      target: { value: "8192" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存额度并恢复" }));
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/runs/r/resume", {
        token_budget: 300000,
        role_limits: { writer: 8192 },
      }),
    );
  });
  it("requires acknowledgement of downstream effects before approving a canon replacement", async () => {
    const candidate = {
      id: "replacement",
      supersedes_id: "original",
      kind: "character",
      title: "人物目标修订",
      content: "人物决定离开",
      status: "candidate",
      source_type: "author",
      data: {},
      entity_ids: [],
      valid_from: 0,
      project_id: "p",
      branch_id: "main",
    };
    const impact = {
      id: "impact",
      source_record_id: "original",
      source_chapter_id: null,
      version_id: null,
      coverage: "结构化依赖",
      status: "preview",
      items: [
        {
          chapter_id: "future",
          number: 18,
          title: "寻找信件",
          kind: "direct",
          reason: "后续行动依赖原目标",
        },
      ],
    };
    const api = {
      get: vi
        .fn()
        .mockImplementation((path: string) =>
          Promise.resolve(
            path.includes("/records/replacement/impact") ? impact : [candidate],
          ),
        ),
      post: vi.fn().mockResolvedValue({}),
    };
    render(
      <SessionContext.Provider value={session(api)}>
        <Records />
      </SessionContext.Provider>,
    );
    await screen.findByText("人物目标修订");
    fireEvent.click(screen.getByRole("button", { name: "确认" }));
    await screen.findByText("后续行动依赖原目标");
    const submit = screen.getByRole("button", { name: "确认资料入库" });
    expect(submit).toBeDisabled();
    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "我已核查上述影响，接受更新资料并将受影响章节标记为待修复",
      }),
    );
    fireEvent.click(submit);
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/records/replacement/approve", {
        expected_revision: 7,
        impact_acknowledged: true,
      }),
    );
  });
});
