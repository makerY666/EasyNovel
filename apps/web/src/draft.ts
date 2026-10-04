import type { Paragraph } from "./types";
export interface LocalDraft {
  baseVersion: string | null;
  paragraphs: Paragraph[];
  savedAt: string;
}
export const draftKey = (chapterId: string) => `easynovel.draft.${chapterId}`;
export function readDraft(chapterId: string): LocalDraft | null {
  try {
    const data = JSON.parse(
      localStorage.getItem(draftKey(chapterId)) ?? "null",
    );
    return data && Array.isArray(data.paragraphs) ? data : null;
  } catch {
    return null;
  }
}
export function writeDraft(chapterId: string, draft: LocalDraft) {
  localStorage.setItem(draftKey(chapterId), JSON.stringify(draft));
}
export function removeDraft(chapterId: string) {
  localStorage.removeItem(draftKey(chapterId));
}
export function protectedParagraphsPreserved(
  before: Paragraph[],
  after: Paragraph[],
) {
  return before
    .filter((p) => p.locked)
    .every((p) =>
      after.some(
        (candidate) => candidate.id === p.id && candidate.text === p.text,
      ),
    );
}
export function acceptedMemoryIndices(selected: Set<number>, count: number) {
  return Array.from(selected)
    .filter((i) => Number.isInteger(i) && i >= 0 && i < count)
    .sort((a, b) => a - b);
}
