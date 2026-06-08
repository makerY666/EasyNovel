// API Types for AI Novel Studio

export interface Project {
  id: number;
  name: string;
  description?: string;
  target_platform?: string;
  target_audience?: string;
  expected_word_count?: number;
  protagonist_type?: string;
  pleasure_points?: string[];
  forbidden_tropes?: string[];
  reference_style?: string;
  created_at: string;
  updated_at: string;
}

export interface Novel {
  id: number;
  project_id: number;
  title: string;
  subtitle?: string;
  synopsis?: string;
  genre?: string;
  sub_genre?: string;
  target_word_count?: number;
  current_word_count: number;
  status: string;
  style_guide?: string;
  taboo_words?: string[];
  created_at: string;
  updated_at: string;
}

export interface Chapter {
  id: number;
  novel_id: number;
  chapter_number: number;
  title?: string;
  summary?: string;
  target_word_count?: number;
  current_word_count: number;
  status: string;
  chapter_card?: ChapterCard;
  current_version_id?: number;
  pov?: string;
  time_in_story?: string;
  location?: string;
  created_at: string;
  updated_at: string;
}

export interface ChapterVersion {
  id: number;
  chapter_id: number;
  novel_id: number;
  version_number: number;
  stage: 'draft' | 'polished' | 'manual' | 'final' | string;
  content: string;
  word_count: number;
  source: 'ai' | 'manual' | 'import' | string;
  workflow_id?: string;
  version_metadata?: Record<string, unknown>;
  created_at: string;
}

export interface ChapterCard {
  chapter_number: number;
  title: string;
  pov?: string;
  chapter_goal: string;
  opening_hook: string;
  main_conflict: string;
  turning_point?: string;
  emotional_shift?: string;
  new_information?: string[];
  foreshadowing?: string[];
  ending_hook?: string;
  must_not_violate?: string[];
}

export interface Character {
  id: number;
  novel_id: number;
  name: string;
  role?: string;
  public_goal?: string;
  hidden_desire?: string;
  fear?: string;
  relationship_to_protagonist?: string;
  current_knowledge?: string[];
  secrets?: string[];
  voice_style?: {
    sentence_length?: string;
    tone?: string;
    taboo_words?: string[];
  };
  physical_description?: string;
  personality_traits?: string[];
  background_story?: string;
  skills?: string[];
  weaknesses?: string[];
  created_at: string;
  updated_at: string;
}

export interface WorldRule {
  id: number;
  novel_id: number;
  rule_id: string;
  content: string;
  priority?: string;
  category?: string;
  is_active: boolean;
  created_by?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface TimelineEvent {
  id: number;
  chapter_id: number;
  novel_id: number;
  date_in_story: string;
  location: string;
  events?: string[];
  state_changes?: string[];
  duration?: string;
  weather?: string;
  importance?: string;
  created_at: string;
  updated_at: string;
}

export interface Foreshadowing {
  id: number;
  novel_id: number;
  foreshadowing_id: string;
  introduced_at_chapter: number;
  content: string;
  intended_payoff_chapter?: number;
  intended_payoff_content?: string;
  status: string;
  related_characters?: string[];
  importance?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface StyleGuide {
  id: number;
  novel_id: number;
  name: string;
  description?: string;
  narrative_pov?: string;
  sentence_length_preference?: string;
  dialogue_density?: string;
  description_intensity?: string;
  rhythm_preference?: string;
  forbidden_words?: string[];
  forbidden_phrases?: string[];
  preferred_sentence_patterns?: string[];
  character_voice_guidelines?: Record<string, string>;
  platform_specific_rules?: Record<string, string>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface QualityReport {
  id: number;
  chapter_id: number;
  novel_id: number;
  report_type: string;
  overall_score?: number;
  plot_progression?: number;
  conflict_strength?: number;
  character_consistency?: number;
  style_naturalness?: number;
  dialogue_quality?: number;
  hook_strength?: number;
  continuity_safety?: number;
  cliche_density?: number;
  main_problems?: string[];
  revision_plan?: string[];
  strengths?: string[];
  weaknesses?: string[];
  recommendations?: string[];
  is_passing: boolean;
  blocking_issues?: string[];
  evaluator_agent?: string;
  evaluator_version?: string;
  created_at: string;
}

export interface WorkflowStatus {
  workflow_id: string;
  status: string;
  current_stage: string;
  chapter_id?: number;
  chapter_number?: number;
  chapter_card?: ChapterCard;
  draft_text?: string;
  polished_text?: string;
  style_changes?: string[];
  quality_score?: Record<string, number>;
  error?: string;
}

export interface ModelConfig {
  provider: string;
  base_url: string;
  flash_model: string;
  pro_model: string;
  timeout_seconds: number;
  api_key_configured: boolean;
}

export interface ModelCheckResult {
  ok: boolean;
  message?: string;
  provider?: string;
  flash_model?: string;
  pro_model?: string;
}

export interface ModelStatus {
  [key: string]: {
    status: string;
    latency?: number;
    cost_per_token?: number;
  };
}

export interface CostSummary {
  total_cost_usd: number;
  calls_count: number;
  by_model?: Record<string, number>;
  by_task?: Record<string, number>;
}
