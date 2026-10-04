# Workstation specification
Every screen must read as the same product if placed side by side.

## Navigation and views
Five top-level navigation groups: 作品, 写作, 故事资料, 导入与修复, 设置. Footer holds backup/export. Main workspace has chapter navigation (240px), central editor (flexible, min 420px), evidence/director pane (320px), bottom persistent run status. Under 1200px evidence becomes a Radix tab panel; under 900px chapter navigation collapses. No 3-column card grids.

## Primary flows
Create project (title, genre, mode, description) -> add chapter -> edit with Tiptap -> save draft -> confirm memory/正文 -> version history.
AI flow: provider and token budget -> task -> run plan -> approve plan -> review draft/issues/memory -> select accepted memory -> confirm. A run can pause/resume/cancel. Expose tokens and current node; retain artifacts if error.
Story records: category tabs -> list with provenance -> create/edit candidate or author-confirmed assertion -> filter evidence, temporal and entity fields. Category fields follow API contract; avoid raw JSON as the only editing mechanism.
Import: choose TXT/MD -> decode server preview -> editable boundaries -> confirm import -> memory extraction run with chosen model/budget -> batch candidate approval.
Repair: select chapter candidate -> analyze -> direct/inferred affected chapters -> create repair run for selected chapters -> accept versions after audit. Blocked successors visible.
Settings: provider URL/name/model/key; models per role, pricing, context/output limits; profile prompt and review dimensions; budget fields. Secrets never redisplayed.

## Components and states
Use Radix Dialog/Tabs/Select/Checkbox primitives, styled with locked tokens. Buttons semantic native elements. Error banner role=alert, task announcements aria-live=polite. Empty views tell the next action; never insert fake novel content. Network unavailable keeps unsaved text, displays retry. Disable duplicate submits. Form fields all have labels. Confirmation dialogs show content/change scope, restore focus on dismiss, Escape closes. Native downloads for backups/exports. Tiptap must persist stable paragraph IDs and locked paragraphs; local draft recovery on crash.
Chapter list paginated (100); current selection in URL/localStorage. Do not fetch full corpus. Save keyboard Ctrl+S. Focus outlines 2px accent. Pending dirty chapter switch saves draft or offers stay. Version stale errors preserve candidate and tell user to reload. SSE stream consumed using fetch auth header, reconnect by event sequence. Backend polls fallback acceptable.

## Handoff
Target: react-vite-tailwind-engineer. Implement under apps/web only. Use Radix primitives, Tiptap, Lucide; implement exactly this spec, theme tokens, do not redesign/reimplement Radix components. Backend contract in docs/API_CONTRACT.md. Acceptance: npm build and typecheck, functional empty/new/import/record/save/run-review/settings/version/backup flows, no mock data or false success. Add meaningful interaction tests for draft safety and review submissions.
