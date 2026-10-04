import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "./App";
import { ImportCenter } from "./Tools";
import { Api } from "./api";
import { writeDraft } from "./draft";
import { SessionContext, type Session } from "./session";
import type { ImportJob, Project } from "./types";
const project: Project = {
  id: "book",
  title: "作品",
  genre: "悬疑",
  mode: "serial",
  description: "",
  revision: 1,
  settings: {},
  created_at: "",
};
function state(api: unknown): Session {
  return {
    api: api as Api,
    project,
    branch: "main",
    providers: [],
    profiles: [],
    refresh: vi.fn(),
    report: vi.fn(),
    notice: vi.fn(),
    setRun: vi.fn(),
  };
}
describe("durable novel imports", () => {
  it("restores the latest branch import after leaving the page and resumes a persisted paused job", async () => {
    let job: ImportJob = {
      id: "import",
      status: "running",
      completed: 0,
      total: 2,
    };
    const api = {
      get: vi.fn().mockImplementation(() => Promise.resolve([job])),
      post: vi.fn().mockImplementation(() => {
        job = { ...job, status: "running" };
        return Promise.resolve(job);
      }),
    };
    const changed = vi.fn();
    const session = state(api);
    const view = (
      <SessionContext.Provider value={session}>
        <ImportCenter
          onRun={() => {}}
          onCommitted={() => {}}
          onImportJob={changed}
        />
      </SessionContext.Provider>
    );
    const first = render(view);
    expect(
      await screen.findByRole("button", { name: "暂停" }),
    ).toBeInTheDocument();
    first.unmount();
    job = { ...job, status: "paused", completed: 1 };
    render(view);
    const resume = await screen.findByRole("button", { name: "继续导入" });
    await waitFor(() => expect(resume).not.toBeDisabled());
    fireEvent.click(resume);
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/imports/import/resume"),
    );
    expect(api.get).toHaveBeenCalledWith(
      "/projects/book/imports?branch_id=main",
    );
    expect(changed).toHaveBeenCalledWith(
      expect.objectContaining({
        id: "import",
        status: "running",
        completed: 1,
      }),
    );
  });
  it("refreshes directory metadata for an already completed import without firing manuscript commit", async () => {
    const api = {
      get: vi
        .fn()
        .mockResolvedValue([
          { id: "import", status: "completed", completed: 2, total: 2 },
        ]),
    };
    const directory = vi.fn().mockResolvedValue(undefined);
    const commit = vi.fn();
    render(
      <SessionContext.Provider value={state(api)}>
        <ImportCenter
          onRun={() => {}}
          onCommitted={commit}
          onImportsChanged={directory}
        />
      </SessionContext.Provider>,
    );
    await waitFor(() => expect(directory).toHaveBeenCalledOnce());
    expect(commit).not.toHaveBeenCalled();
  });
  it("keeps watching an import after switching to writing, updates the directory when it finishes, and restores it on return", async () => {
    sessionStorage.setItem("easynovel.token", "session");
    localStorage.setItem("easynovel.project", "book");
    localStorage.setItem("easynovel.chapter", "chapter-1");
    writeDraft("chapter-1", {
      baseVersion: null,
      paragraphs: [
        { id: "author-paragraph", text: "作者未保存的正文", locked: false },
      ],
      savedAt: new Date().toISOString(),
    });
    history.replaceState(null, "", "/");
    let job: ImportJob | null = null;
    const baseChapters = [1, 2].map((number) => ({
      id: `chapter-${number}`,
      project_id: "book",
      branch_id: "main",
      title: `原章节${number}`,
      number,
      confirmed_version_id: null,
      draft_version_id: null,
      story_time: null,
      blocked: false,
      updated_at: "",
    }));
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async (input, init) => {
        const url = String(input);
        let data: unknown = [];
        if (url.endsWith("/health"))
          data = {
            version: "test",
            semantic_search: false,
            legacy_database_detected: false,
          };
        else if (url.endsWith("/projects"))
          data = [
            { ...project, revision: job?.status === "completed" ? 2 : 1 },
          ];
        else if (url.endsWith("/projects/book"))
          data = { ...project, revision: job?.status === "completed" ? 2 : 1 };
        else if (url.endsWith("/branches"))
          data = [{ id: "main", name: "主分支" }];
        else if (url.includes("/chapters?"))
          data = {
            items:
              job?.status === "completed"
                ? [
                    ...baseChapters,
                    ...[3, 4].map((number) => ({
                      ...baseChapters[0],
                      id: `chapter-${number}`,
                      number,
                      title: `导入章节${number}`,
                    })),
                  ]
                : baseChapters,
            total: job?.status === "completed" ? 4 : 2,
          };
        else if (url.endsWith("/chapters/chapter-1"))
          data = {
            ...baseChapters[0],
            draft: null,
            confirmed: null,
            project_revision: 1,
          };
        else if (
          url.endsWith("/chapters/chapter-1/versions") &&
          init?.method === "POST"
        )
          data = {
            id: "saved",
            ...JSON.parse(String(init.body)),
            status: "draft",
            created_at: "",
            chapter_id: "chapter-1",
          };
        else if (url.endsWith("/imports/preview"))
          data = {
            encoding: "UTF-8",
            warnings: [],
            chapters: [
              { title: "导入章节3", content: "第三章正文" },
              { title: "导入章节4", content: "第四章正文" },
            ],
          };
        else if (
          url.endsWith("/projects/book/imports") &&
          init?.method === "POST"
        ) {
          job = { id: "import", status: "running", completed: 0, total: 2 };
          data = job;
        } else if (url.includes("/imports?")) data = job ? [job] : [];
        else if (url.endsWith("/imports/import")) data = job;
        return new Response(JSON.stringify(data), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      });
    try {
      render(<App />);
      await screen.findByRole("button", {
        name: "导入与修复",
      });
      await waitFor(() =>
        expect(
          screen.getByRole("button", { name: "导入与修复" }),
        ).not.toBeDisabled(),
      );
      fireEvent.click(screen.getByRole("button", { name: "导入与修复" }));
      fireEvent.change(await screen.findByLabelText("选择作品文件"), {
        target: {
          files: [
            new File(["第三章正文"], "novel.txt", { type: "text/plain" }),
          ],
        },
      });
      const submit = await screen.findByRole("button", {
        name: "确认分章并导入正文",
      });
      await waitFor(() => expect(submit).not.toBeDisabled());
      fireEvent.click(submit);
      await screen.findByRole("button", { name: "暂停" });
      fireEvent.click(screen.getByRole("button", { name: "写作" }));
      expect(await screen.findByText("原章节1")).toBeInTheDocument();
      fireEvent.click(await screen.findByRole("button", { name: "恢复文本" }));
      const manuscript = screen.getByLabelText("章节正文");
      expect(manuscript).toHaveTextContent("作者未保存的正文");
      job = { id: "import", status: "completed", completed: 2, total: 2 };
      expect(
        await screen.findByText("导入章节4", {}, { timeout: 4000 }),
      ).toBeInTheDocument();
      expect(screen.getByText("4 章")).toBeInTheDocument();
      expect(screen.getByLabelText("章节正文")).toBe(manuscript);
      expect(manuscript).toHaveTextContent("作者未保存的正文");
      expect(
        fetchSpy.mock.calls.filter(([, init]) => init?.method === "POST"),
      ).toHaveLength(2);
      fireEvent.click(screen.getByRole("button", { name: "导入与修复" }));
      expect(await screen.findByText("2 / 2 章")).toBeInTheDocument();
      expect(screen.getByText("已完成")).toBeInTheDocument();
      expect(
        fetchSpy.mock.calls.filter(([, init]) => init?.method === "POST"),
      ).toHaveLength(3);
      expect(
        fetchSpy.mock.calls.some(
          ([url, init]) =>
            String(url).endsWith("/chapters/chapter-1/versions") &&
            JSON.parse(String(init?.body)).content === "作者未保存的正文",
        ),
      ).toBe(true);
    } finally {
      fetchSpy.mockRestore();
      history.replaceState(null, "", "/");
    }
  });
});
