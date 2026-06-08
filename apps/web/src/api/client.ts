import {
  ChapterVersion,
  ModelCheckResult,
  ModelConfig,
} from './types';

const BASE = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const opts: RequestInit = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch(`${BASE}${path}`, opts);
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || res.statusText);
  }
  return res.json() as Promise<T>;
}

function query(params: Record<string, unknown>): string {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      qs.set(key, String(value));
    }
  });
  const text = qs.toString();
  return text ? `?${text}` : '';
}

export const getHealth = () => req<{ status: string; version: string }>('GET', '/health');

export const getProjects = () => req<any[]>('GET', '/api/v1/projects');
export const createProject = (data: any) => req<any>('POST', '/api/v1/projects', data);
export const updateProject = (id: number, data: any) => req<any>('PATCH', `/api/v1/projects/${id}`, data);

export const getNovels = (projectId?: number) => req<any[]>('GET', `/api/v1/novels${query({ project_id: projectId })}`);
export const createNovel = (data: any) => req<any>('POST', '/api/v1/novels', data);
export const updateNovel = (id: number, data: any) => req<any>('PATCH', `/api/v1/novels/${id}`, data);

export const getChapters = (novelId: number) => req<any[]>('GET', `/api/v1/chapters${query({ novel_id: novelId })}`);
export const createChapter = (data: any) => req<any>('POST', '/api/v1/chapters', data);
export const updateChapter = (id: number, data: any) => req<any>('PATCH', `/api/v1/chapters/${id}`, data);

export const getChapterVersions = (chapterId: number) =>
  req<ChapterVersion[]>('GET', `/api/v1/chapters/${chapterId}/versions`);
export const createChapterVersion = (chapterId: number, data: any) =>
  req<ChapterVersion>('POST', `/api/v1/chapters/${chapterId}/versions`, data);
export const updateChapterVersion = (chapterId: number, versionId: number, data: any) =>
  req<ChapterVersion>('PATCH', `/api/v1/chapters/${chapterId}/versions/${versionId}`, data);

export const getCharacters = (novelId: number) => req<any[]>('GET', `/api/v1/characters${query({ novel_id: novelId })}`);
export const createCharacter = (data: any) => req<any>('POST', '/api/v1/characters', data);
export const updateCharacter = (id: number, data: any) => req<any>('PATCH', `/api/v1/characters/${id}`, data);

export const getStyleGuides = (novelId: number) => req<any[]>('GET', `/api/v1/style-guides${query({ novel_id: novelId })}`);
export const createStyleGuide = (data: any) => req<any>('POST', '/api/v1/style-guides', data);
export const updateStyleGuide = (id: number, data: any) => req<any>('PATCH', `/api/v1/style-guides/${id}`, data);

export const getTimelineEvents = (novelId: number) => req<any[]>('GET', `/api/v1/timeline-events${query({ novel_id: novelId })}`);
export const createTimelineEvent = (data: any) => req<any>('POST', '/api/v1/timeline-events', data);
export const updateTimelineEvent = (id: number, data: any) => req<any>('PATCH', `/api/v1/timeline-events/${id}`, data);

export const getQualityReports = (chapterId: number) =>
  req<any[]>('GET', `/api/v1/quality-reports${query({ chapter_id: chapterId })}`);
export const getAgentRuns = (chapterId: number) =>
  req<any[]>('GET', `/api/v1/agent-runs${query({ chapter_id: chapterId })}`);

export const startWorkflow = (data: any) => req<any>('POST', '/api/v1/workflows/chapter', data);
export const getWorkflowStatus = (id: string) => req<any>('GET', `/api/v1/workflows/${id}/status`);
export const approveWorkflowStage = (id: string, data: any) =>
  req<any>('POST', `/api/v1/workflows/chapter/${id}/approve-stage`, data);

export const getWorldRules = (novelId: number) => req<any[]>('GET', `/api/v1/memory/world-rules${query({ novel_id: novelId })}`);
export const addWorldRule = (data: any) => req<any>('POST', '/api/v1/memory/world-rules', data);
export const getTimeline = (novelId: number) => req<any[]>('GET', `/api/v1/memory/timeline${query({ novel_id: novelId })}`);
export const getForeshadowings = (novelId: number) => req<any[]>('GET', `/api/v1/memory/foreshadowings${query({ novel_id: novelId })}`);
export const addForeshadowing = (data: any) => req<any>('POST', '/api/v1/memory/foreshadowings', data);
export const getStyleGuide = (novelId: number) => req<any>('GET', `/api/v1/memory/style-guide${query({ novel_id: novelId })}`);
export const getContextPack = (novelId: number, chapterId: number, goal?: string) =>
  req<any>('GET', `/api/v1/memory/context-pack${query({ novel_id: novelId, chapter_id: chapterId, chapter_goal: goal })}`);

export const getModelStatus = () => req<any>('GET', '/api/v1/models/status');
export const getModelConfig = () => req<ModelConfig>('GET', '/api/v1/models/config');
export const checkModelConfig = () => req<ModelCheckResult>('POST', '/api/v1/models/check');
export const getCostSummary = () => req<any>('GET', '/api/v1/models/cost-summary');

export async function exportNovel(novelId: number, format: 'txt' | 'markdown', chapterIds?: number[]): Promise<string> {
  const params = query({ format, chapter_ids: chapterIds?.join(',') });
  const res = await fetch(`${BASE}/api/v1/exports/novel/${novelId}${params}`, { method: 'POST' });
  if (!res.ok) throw new Error(await res.text());
  return res.text();
}
