import type { Paragraph, Version } from "./types";
const getParagraphs = (v: Version): Paragraph[] =>
  v.paragraphs?.length
    ? v.paragraphs
    : v.content
        .split(/\n\s*\n/)
        .map((text, i) => ({ id: `line-${i}`, text, locked: false }));
export function ParagraphDiff({
  before,
  after,
}: {
  before: Version | null;
  after: Version;
}) {
  if (!before) return <pre className="text-preview">{after.content}</pre>;
  const old = getParagraphs(before);
  const next = getParagraphs(after);
  const oldById = new Map(old.map((p) => [p.id, p]));
  const newById = new Map(next.map((p) => [p.id, p]));
  const deleted = old.filter((p) => !newById.has(p.id));
  return (
    <div className="paragraph-diff">
      <p className="muted">
        比较正式正文 {before.id.slice(0, 8)} → 所选版本 {after.id.slice(0, 8)}
        ；按稳定段落标识对照。
      </p>
      {deleted.map((p) => (
        <div key={p.id} className="diff-deleted">
          <small>删除</small>
          <p>{p.text}</p>
        </div>
      ))}
      {next.map((p) => {
        const previous = oldById.get(p.id);
        const changed = previous && previous.text !== p.text;
        return (
          <div
            className={
              !previous ? "diff-added" : changed ? "diff-changed" : "diff-same"
            }
            key={p.id}
          >
            <small>
              {!previous ? "新增" : changed ? "修改" : "未变"}
              {p.locked ? " · 锁定" : ""}
            </small>
            {changed && <p className="old-text">{previous.text}</p>}
            <p>{p.text}</p>
          </div>
        );
      })}
    </div>
  );
}
