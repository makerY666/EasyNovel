import type { Run } from "./types";
export const roleLabels: Record<string, string> = {
  architect: "故事架构师",
  planner: "章节与场景规划师",
  writer: "正文作者",
  continuity: "连续性审计员",
  editor: "剧情与人物编辑",
  stylist: "文体编辑",
  memory: "记忆整理员",
};
export function stageLabel(node: string) {
  return (
    (
      {
        context: "准备上下文",
        architect: "整理故事架构",
        architecture: "整理故事架构",
        planner: "规划章节与场景",
        plan: "规划章节与场景",
        approve_plan: "等待审核计划",
        writer: "生成正文",
        draft: "生成正文",
        audit: "审核正文",
        revise: "修订正文",
        length: "调整正文篇幅",
        author_revision: "按作者要求修订正文",
        polish: "调整文体",
        stylist: "调整文体",
        memory: "整理候选记忆",
        review: "等待审核正文",
        commit: "确认正文入库",
        completed: "正文已确认入库",
        directive: "整理创作指令",
        directive_ready: "创作指令已整理",
        import_memory: "提取导入记忆",
        import_complete: "导入记忆提取完成",
        repair: "生成修复候选",
        repair_candidates_ready: "修复候选已生成",
        cancelled: "任务已取消",
      } as Record<string, string>
    )[node] ??
    roleLabels[node] ??
    node
  );
}
export function completionMessage(run: Run) {
  const kind = run.request?.kind;
  if (kind === "directive" || run.artifacts.directive)
    return "创作指令已整理，请到故事资料核对候选约束";
  if (kind === "import" || run.artifacts.analyzed_chapters)
    return "候选记忆已提取，请到故事资料核查";
  if (kind === "repair" || run.artifacts.repair_versions)
    return "修复候选已生成，请逐章核查";
  if (
    run.artifacts.draft &&
    (kind === "chapter" ||
      kind === "rewrite" ||
      kind === "author_revision" ||
      !kind)
  )
    return "正文已确认入库";
  return "当前阶段已结束，请查看运行记录";
}
export function suggestedOutputLimit(
  info: NonNullable<Run["artifacts"]["output_limit_info"]>,
) {
  return Math.max(
    128,
    Math.min(
      100000,
      Math.max(128, info.context_limit - 256),
      Math.max(
        info.maximum * 2,
        (info.role_max_output ?? 0) * 2,
        info.provider_max_output * 2,
      ),
    ),
  );
}
export function previewableRun(
  run: Run | null,
  projectId: string,
  chapterId: string | null,
): run is Run {
  return (
    !!run &&
    run.project_id === projectId &&
    run.chapter_id === chapterId &&
    !!run.artifacts.draft
  );
}
