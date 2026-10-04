import { useEffect, useRef, useState, type ReactNode } from "react";
import type { Run } from "./types";
import { previewableRun, stageLabel } from "./runPresentation";
export function ChapterWorkspace({
  run,
  projectId,
  chapterId,
  previewRequest = 0,
  children,
}: {
  run: Run | null;
  projectId: string;
  chapterId: string | null;
  previewRequest?: number;
  children: ReactNode;
}) {
  const [visible, setVisible] = useState<string | null>(null);
  const seen = useRef(new Set<string>());
  const matches = previewableRun(run, projectId, chapterId);
  useEffect(() => {
    if (
      previewableRun(run, projectId, chapterId) &&
      !seen.current.has(run.id)
    ) {
      seen.current.add(run.id);
      setVisible(run.id);
    }
  }, [run?.id, run?.artifacts.draft, projectId, chapterId]);
  useEffect(() => {
    if (previewRequest && previewableRun(run, projectId, chapterId))
      setVisible(run.id);
  }, [previewRequest]);
  const preview = matches && visible === run.id;
  return (
    <>
      <div hidden={preview} className="preserved-editor">
        {children}
      </div>
      {preview && (
        <section
          className="candidate-workspace"
          aria-labelledby="candidate-title"
        >
          <div className="page-title">
            <div>
              <small>
                {run.status === "completed"
                  ? "已确认入库"
                  : "尚未入库 · 作者确认前保留为候选"}
              </small>
              <h1 id="candidate-title">正文候选预览</h1>
            </div>
            <button onClick={() => setVisible(null)}>返回编辑器</button>
          </div>
          <p role="status" className="muted">
            {stageLabel(run.node)}。编辑器中的未保存文字保留；此预览为只读。
          </p>
          <div className="candidate-novel" aria-label="生成的正文候选">
            {run.artifacts.draft!.split(/\n\s*\n/).map((text, index) => (
              <p key={index}>{text}</p>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
