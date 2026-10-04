export interface Project {
  id: string;
  title: string;
  genre: string;
  mode: "serial" | "literary";
  description: string;
  revision: number;
  settings: Record<string, unknown>;
  created_at: string;
}
export interface Paragraph {
  id: string;
  text: string;
  locked: boolean;
}
export interface Version {
  id: string;
  chapter_id: string;
  content: string;
  paragraphs: Paragraph[];
  status: string;
  source: string;
  parent_id: string | null;
  created_at: string;
}
export interface Chapter {
  id: string;
  project_id: string;
  branch_id: string;
  number: number;
  title: string;
  story_time: number | null;
  confirmed_version_id: string | null;
  draft_version_id: string | null;
  blocked: boolean;
  updated_at: string;
}
export interface ChapterDetail extends Chapter {
  draft: Version | null;
  confirmed: Version | null;
  project_revision: number;
}
export type RecordKind =
  | "rule"
  | "character"
  | "state"
  | "knowledge"
  | "relationship"
  | "event"
  | "foreshadow"
  | "plan"
  | "directive"
  | "summary";
export interface RecordInput {
  kind: RecordKind;
  title: string;
  content: string;
  entity_ids?: string[];
  valid_from?: number | null;
  valid_until?: number | null;
  source_version_id?: string | null;
  source_paragraph_id?: string | null;
  source_type?: "author" | "text" | "speech" | "inference";
  status?: string;
  data?: Record<string, unknown>;
  dependencies?: string[];
  branch_id?: string;
}
export interface StoryRecord extends RecordInput {
  id: string;
  project_id: string;
  branch_id: string;
  status: string;
  created_at: string;
  supersedes_id?: string | null;
}
export interface SearchItem {
  id: string;
  kind: string;
  title: string;
  content: string;
  source_version_id: string | null;
  source_paragraph_id: string | null;
  reason: string;
  score: number;
}
export interface ContextPack {
  revision: number;
  constraints: unknown[];
  evidence: unknown[];
  character_knowledge: unknown[];
  plans: unknown[];
  token_estimate: number;
  warnings: string[];
  semantic_search: boolean;
}
export interface Provider {
  id: string;
  name: string;
  base_url: string;
  model: string;
  has_key: boolean;
  context_limit: number;
  max_output: number;
  input_price: number | null;
  output_price: number | null;
  embedding_model?: string;
  extra_body?: Record<string, unknown>;
}
export interface Role {
  provider_id?: string;
  prompt?: string;
  temperature?: number;
  max_output?: number;
}
export interface Profile {
  id: string;
  name: string;
  roles: Record<string, Role>;
  max_revisions: number;
  review_dimensions: string[];
}
export interface Run {
  id: string;
  project_id: string;
  chapter_id: string | null;
  request?: {
    token_budget?: number;
    money_budget?: number;
    kind?: string;
    auto_approve_plan?: boolean;
    profile_snapshot?: { roles?: Record<string, Role> };
    provider_snapshots?: Record<string, Provider>;
  };
  status: string;
  node: string;
  input_revision: number;
  artifacts: {
    length_adjustment?: unknown;
    style_rejected?: string;
    output_limit_info?: {
      role: string;
      maximum: number;
      provider_id: string;
      provider_max_output: number;
      role_max_output: number | null;
      requested_output_limit: number | null;
      model: string;
      context_limit: number;
    };
    proposed_revision?: { content: string; change_reason: string };
    directive?: unknown;
    analyzed_chapters?: string[];
    total?: number;
    architecture?: string;
    plan?: unknown;
    plans?: unknown[];
    draft?: string;
    reviews?: unknown[];
    memory_delta?: RecordInput[];
    memory_warnings?: { call_key: string; message: string; paragraph_ids: string[] }[];
    version_id?: string;
    context?: ContextPack;
    repair_versions?: unknown[];
  };
  error: string | null;
  usage: {
    input_tokens: number;
    output_tokens: number;
    reserved_tokens: number;
    cost: number;
    cost_known?: boolean;
  };
  created_at: string;
}
export interface Branch {
  id: string;
  name: string;
}
export interface ImportJob {
  id: string;
  status: string;
  total: number;
  completed: number;
  error?: string;
}
export interface Impact {
  id: string;
  source_record_id?: string | null;
  source_chapter_id: string | null;
  version_id: string | null;
  items: {
    chapter_id: string;
    number: number;
    title: string;
    reason: string;
    kind: "direct" | "inferred";
  }[];
  coverage: unknown;
  status: string;
}
export interface Backup {
  id: string;
  name: string;
  created_at: string;
}
