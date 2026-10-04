import { useEffect, useRef, useState } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { Extension } from "@tiptap/core";
import { Plugin } from "@tiptap/pm/state";
import { Lock, Unlock, Save, History, Check, Undo2 } from "lucide-react";
import { useAction, useSession } from "./session";
import { Empty, Modal, State, Tick, Field } from "./ui";
import type { ChapterDetail, Paragraph, Version } from "./types";
import {
  readDraft,
  removeDraft,
  writeDraft,
  protectedParagraphsPreserved,
} from "./draft";
import { ParagraphDiff } from "./ParagraphDiff";
const paragraphsOf = (doc: import("@tiptap/pm/model").Node): Paragraph[] => {
  const output: Paragraph[] = [];
  doc.forEach((node) => {
    if (node.type.name === "paragraph")
      output.push({
        id: String(node.attrs.paragraphId),
        text: node.textContent,
        locked: !!node.attrs.locked,
      });
  });
  return output;
};
export const stableParagraphs = Extension.create({
  name: "stableParagraphs",
  addGlobalAttributes() {
    return [
      {
        types: ["paragraph"],
        attributes: {
          paragraphId: {
            default: null,
            parseHTML: (e) => e.getAttribute("data-paragraph-id"),
            renderHTML: (a) => ({ "data-paragraph-id": a.paragraphId }),
          },
          locked: {
            default: false,
            parseHTML: (e) => e.getAttribute("data-locked") === "true",
            renderHTML: (a) =>
              a.locked
                ? { "data-locked": "true", contenteditable: "false" }
                : { "data-locked": "false" },
          },
        },
      },
    ];
  },
  addProseMirrorPlugins() {
    return [
      new Plugin({
        filterTransaction: (tr) =>
          tr.getMeta("trustedLoad") ||
          !tr.docChanged ||
          protectedParagraphsPreserved(
            paragraphsOf(tr.before),
            paragraphsOf(tr.doc),
          ),
        appendTransaction: (_trs, _old, state) => {
          const tr = state.tr;
          const ids = new Set<string>();
          state.doc.descendants((node, pos) => {
            if (node.type.name === "paragraph") {
              const id = node.attrs.paragraphId as string | null;
              if (!id || ids.has(id)) {
                const next = crypto.randomUUID();
                tr.setNodeMarkup(pos, undefined, {
                  ...node.attrs,
                  paragraphId: next,
                });
                ids.add(next);
              } else ids.add(id);
            }
          });
          return tr.docChanged ? tr : null;
        },
      }),
    ];
  },
});
const contentOf = (paragraphs: Paragraph[]) => ({
  type: "doc",
  content: (paragraphs.length
    ? paragraphs
    : [{ id: crypto.randomUUID(), text: "", locked: false }]
  ).map((p) => ({
    type: "paragraph",
    attrs: { paragraphId: p.id, locked: p.locked },
    content: p.text ? [{ type: "text", text: p.text }] : [],
  })),
});
export function NovelEditor({
  chapterId,
  onSaved,
  onImpact,
  onRun,
}: {
  chapterId: string;
  onSaved: () => void;
  onImpact: (version: string) => void;
  onRun: (id: string) => void;
}) {
  const { api, project, refresh, notice, providers } = useSession();
  const { busy, act } = useAction();
  const [detail, setDetail] = useState<ChapterDetail | null>(null);
  const [dirty, setDirty] = useState(false);
  const [saveStatus, setSaveStatus] = useState("");
  const [recover, setRecover] = useState<ReturnType<typeof readDraft>>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [history, setHistory] = useState(false);
  const [commit, setCommit] = useState(false);
  const [preview, setPreview] = useState<Version | null>(null);
  const [externalVersion, setExternalVersion] = useState("");
  const [rewriteOpen, setRewriteOpen] = useState(false);
  const [rewriteText, setRewriteText] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [provider, setProvider] = useState("");
  const [budget, setBudget] = useState(20000);
  const [override, setOverride] = useState("");
  const detailRef = useRef(detail);
  detailRef.current = detail;
  const changedRef = useRef(false);
  const revisionRef = useRef(project.revision);
  revisionRef.current = project.revision;
  const initialized = useRef(false);
  const saveRef = useRef<() => Promise<boolean>>(async () => false);
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: false,
        blockquote: false,
        codeBlock: false,
        bulletList: false,
        orderedList: false,
        listItem: false,
        horizontalRule: false,
        code: false,
        bold: false,
        italic: false,
        strike: false,
      }),
      stableParagraphs,
    ],
    content: contentOf([]),
    editorProps: {
      attributes: { "aria-label": "章节正文", class: "novel-text" },
    },
    onUpdate: ({ editor }) => {
      if (!initialized.current) return;
      const paragraphs = paragraphsOf(editor.state.doc);
      changedRef.current = true;
      setDirty(true);
      setSaveStatus("未保存");
      try {
        writeDraft(chapterId, {
          baseVersion:
            detailRef.current?.draft?.id ??
            detailRef.current?.confirmed?.id ??
            null,
          paragraphs,
          savedAt: new Date().toISOString(),
        });
      } catch {
        setSaveStatus("浏览器恢复空间不足，请立即保存草稿");
      }
    },
  });
  const load = async () => {
    const next = await api.get<ChapterDetail>(`/chapters/${chapterId}`);
    initialized.current = false;
    setDetail(next);
    editor
      ?.chain()
      .setMeta("trustedLoad", true)
      .setContent(
        contentOf(
          next.draft?.paragraphs?.length
            ? next.draft.paragraphs
            : next.confirmed?.paragraphs?.length
              ? next.confirmed.paragraphs
              : (next.draft?.content ?? next.confirmed?.content ?? "")
                  .split(/\n\s*\n|\n/)
                  .map((text) => ({
                    id: crypto.randomUUID(),
                    text,
                    locked: false,
                  })),
        ),
        { emitUpdate: false },
      )
      .run();
    setDirty(false);
    changedRef.current = false;
    setSaveStatus("已载入");
    setRecover(readDraft(chapterId));
    initialized.current = true;
  };
  useEffect(() => {
    if (editor) void act(load);
  }, [chapterId, editor]);
  const save = async () => {
    if (!editor || !detailRef.current) return false;
    const current = paragraphsOf(editor.state.doc);
    const signature = JSON.stringify(current);
    const version = await api.post<Version>(`/chapters/${chapterId}/versions`, {
      content: current.map((p) => p.text).join("\n\n"),
      paragraphs: current,
      expected_revision: revisionRef.current,
      source: "manual",
      parent_id: detailRef.current.draft?.id ?? detailRef.current.confirmed?.id,
    });
    detailRef.current = {
      ...detailRef.current!,
      draft: version,
      draft_version_id: version.id,
    };
    setDetail(detailRef.current);
    if (JSON.stringify(paragraphsOf(editor.state.doc)) === signature) {
      changedRef.current = false;
      setDirty(false);
      removeDraft(chapterId);
      setSaveStatus("草稿已保存");
    }
    onSaved();
    return true;
  };
  saveRef.current = save;
  useEffect(() => {
    const timer = setInterval(() => {
      if (changedRef.current && !busy) void act(() => saveRef.current());
    }, 15000);
    return () => clearInterval(timer);
  }, [chapterId, busy]);
  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
        event.preventDefault();
        void act(() => saveRef.current());
      }
    };
    const leave = (event: BeforeUnloadEvent) => {
      if (changedRef.current) {
        event.preventDefault();
        event.returnValue = "";
      }
    };
    window.addEventListener("keydown", key);
    window.addEventListener("beforeunload", leave);
    return () => {
      window.removeEventListener("keydown", key);
      window.removeEventListener("beforeunload", leave);
    };
  }, []);
  useEffect(() => {
    const guard = (event: Event) => {
      const detail = (event as CustomEvent<{ resolve: (ok: boolean) => void }>)
        .detail;
      if (!changedRef.current) {
        detail.resolve(true);
        return;
      }
      void act(() => saveRef.current()).then((ok) =>
        detail.resolve(ok === true),
      );
    };
    window.addEventListener("easynovel-before-switch", guard);
    return () => window.removeEventListener("easynovel-before-switch", guard);
  }, [chapterId]);
  const restore = () => {
    if (!recover || !editor) return;
    editor
      .chain()
      .setMeta("trustedLoad", true)
      .setContent(contentOf(recover.paragraphs), { emitUpdate: true })
      .run();
    setRecover(null);
    notice("已恢复本地文本。保存前请核对服务端版本。");
  };
  if (!detail || !editor) return <Empty>正在读取章节…</Empty>;
  const paragraphs = paragraphsOf(editor.state.doc);
  return (
    <div className="editor-workspace">
      <header className="editor-heading">
        <div>
          <small>
            第 {detail.number} 章 {detail.blocked && "· 后续创作等待影响修复"}
          </small>
          <h1>{detail.title}</h1>
        </div>
        <span className="muted">
          {paragraphs.reduce((n, p) => n + p.text.length, 0)} 字
        </span>
      </header>
      {recover && (
        <div className="notice recovery">
          发现本地恢复稿（{new Date(recover.savedAt).toLocaleString()}）
          {recover.baseVersion !==
            (detail.draft?.id ?? detail.confirmed?.id ?? null) && (
            <strong>；服务端版本已变化，请先查看历史。</strong>
          )}
          <button onClick={restore}>恢复文本</button>
          <button
            onClick={() => {
              removeDraft(chapterId);
              setRecover(null);
            }}
          >
            放弃恢复稿
          </button>
        </div>
      )}
      <div className="editor-toolbar">
        <button disabled={busy} onClick={() => void act(save)}>
          <Save size={15} />
          保存草稿
        </button>
        <button
          disabled={busy}
          onClick={() =>
            void act(async () => {
              if (dirty) await save();
              setCommit(true);
            })
          }
        >
          <Check size={15} />
          确认入库
        </button>
        <button
          onClick={() => {
            const locked = editor.getAttributes("paragraph").locked;
            editor
              .chain()
              .focus()
              .updateAttributes("paragraph", { locked: !locked })
              .run();
            if (!dirty) {
              changedRef.current = true;
              setDirty(true);
              writeDraft(chapterId, {
                baseVersion: detail.draft?.id ?? detail.confirmed?.id ?? null,
                paragraphs: paragraphsOf(editor.state.doc),
                savedAt: new Date().toISOString(),
              });
            }
          }}
        >
          <Lock size={15} />
          切换段落锁定
        </button>
        <button
          disabled={busy}
          onClick={() =>
            void act(async () => {
              setVersions(await api.get(`/chapters/${chapterId}/versions`));
              setHistory(true);
            })
          }
        >
          <History size={15} />
          历史
        </button>
        <button onClick={() => setRewriteOpen(true)}>局部修改</button>
        <span aria-live="polite" className="muted">
          {saveStatus}
        </span>
      </div>
      <EditorContent editor={editor} />
      <div className="editor-note">
        锁定段落保留原文。自动保存间隔 15 秒；Ctrl+S
        立即保存。草稿需确认入库后才进入故事证据。
      </div>
      <Modal open={commit} onOpenChange={setCommit} title="确认正文入库">
        <p>将本章草稿确认为正式正文。草稿保存与正文确认分别处理。</p>
        {detail.confirmed && (
          <p className="notice">本章已有正式正文，修改前文需要先分析影响。</p>
        )}
        <Field label="有意安排说明（可选）">
          <textarea
            value={override}
            onChange={(e) => setOverride(e.target.value)}
          />
        </Field>
        <div className="actions">
          <button
            onClick={() => {
              setCommit(false);
              if (detail.draft) onImpact(detail.draft.id);
            }}
            disabled={!detail.draft}
          >
            分析影响
          </button>
          <button
            className="primary"
            disabled={busy || !detail.draft}
            onClick={() =>
              void act(async () => {
                await api.post(`/chapters/${chapterId}/commit`, {
                  version_id: detail.draft!.id,
                  expected_revision: project.revision,
                  idempotency_key: crypto.randomUUID(),
                  override_reason: override || undefined,
                });
                setCommit(false);
                await refresh();
                await load();
                notice("正文已确认入库");
              })
            }
          >
            确认本章正文
          </button>
        </div>
      </Modal>
      <Modal open={history} onOpenChange={setHistory} title="版本历史与采用">
        <div className="version-list">
          {versions.length === 0 ? (
            <Empty>尚无保存版本。</Empty>
          ) : (
            versions.map((v) => (
              <button
                className="version-row"
                key={v.id}
                onClick={() => setPreview(v)}
              >
                <span>
                  {new Date(v.created_at).toLocaleString()} · {v.source}
                </span>
                <State value={v.status} />
                <small>{v.id.slice(0, 8)}</small>
              </button>
            ))
          )}
        </div>
        {preview && (
          <>
            <h3>所选版本</h3>
            <p className="provenance">版本标识：{preview.id}</p>
            <ParagraphDiff before={detail.confirmed} after={preview} />
            <div className="actions">
              <button
                disabled={busy}
                onClick={() =>
                  void act(async () => {
                    await api.post(`/chapters/${chapterId}/adopt`, {
                      source_version_id: preview.id,
                      expected_revision: project.revision,
                    });
                    setHistory(false);
                    await refresh();
                    await load();
                    notice("已采用为候选草稿，请审核后确认");
                  })
                }
              >
                <Undo2 size={14} />
                采用整章为候选
              </button>
            </div>
          </>
        )}
        <details>
          <summary>从其他故事分支采用整章</summary>
          <p className="muted">
            在另一分支的同章历史中复制完整版本标识。采用后创建候选草稿，仍需审核事实和记忆。
          </p>
          <Field label="其他分支的正文版本标识">
            <input
              value={externalVersion}
              onChange={(e) => setExternalVersion(e.target.value)}
            />
          </Field>
          <button
            disabled={busy || !externalVersion.trim()}
            onClick={() =>
              void act(async () => {
                await api.post(`/chapters/${chapterId}/adopt`, {
                  source_version_id: externalVersion.trim(),
                  expected_revision: project.revision,
                });
                setHistory(false);
                await refresh();
                await load();
                notice("另一分支正文已采用为候选，请重新审核记忆");
              })
            }
          >
            采用另一分支整章
          </button>
        </details>
      </Modal>
      <Modal open={rewriteOpen} onOpenChange={setRewriteOpen} title="局部修改">
        <p>选择需要修改的段落。锁定段落不能参与修改。</p>
        <div className="paragraph-picker">
          {paragraphs.map((p, i) => (
            <Tick
              key={p.id}
              checked={selected.has(p.id)}
              onChange={(checked) => {
                const next = new Set(selected);
                checked ? next.add(p.id) : next.delete(p.id);
                setSelected(next);
              }}
              label={
                <span>
                  {p.locked ? <Lock size={12} /> : <Unlock size={12} />} {i + 1}
                  . {p.text.slice(0, 80) || "空段落"}
                </span>
              }
            />
          ))}
        </div>
        <Field label="修改要求">
          <textarea
            value={rewriteText}
            onChange={(e) => setRewriteText(e.target.value)}
            placeholder="例如：事件不变，压缩描写并增强对话中的试探"
          />
        </Field>
        <Field label="模型">
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
          >
            <option value="">选择模型</option>
            {providers.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} / {p.model}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Token 上限">
          <input
            type="number"
            min={1}
            value={budget}
            onChange={(e) => setBudget(+e.target.value)}
          />
        </Field>
        <button
          className="primary"
          disabled={
            busy ||
            !provider ||
            !rewriteText.trim() ||
            !selected.size ||
            paragraphs.some((p) => p.locked && selected.has(p.id))
          }
          onClick={() =>
            void act(async () => {
              await save();
              const run = await api.post<{ id: string }>(
                `/chapters/${chapterId}/rewrite`,
                {
                  version_id: detailRef.current!.draft!.id,
                  paragraph_ids: [...selected],
                  instruction: rewriteText,
                  provider_id: provider,
                  token_budget: budget,
                  expected_revision: project.revision,
                },
              );
              setRewriteOpen(false);
              onRun(run.id);
            })
          }
        >
          生成并审核局部修改
        </button>
      </Modal>
    </div>
  );
}
