import { Inspect } from "./ui";

export const evidenceFields: Record<string, string> = {
  issues: "审稿问题",
  summary: "审稿摘要",
  quote: "原文引用",
  basis: "判断依据",
  category: "问题类别",
  paragraph_id: "正文段落",
  evidence_ids: "相关证据标识",
  triage_reason: "复核说明",
  dependencies: "依赖证据",
  entity_ids: "关联人物与实体",
  valid_from: "故事生效时间",
  valid_until: "故事截止时间",
  source_type: "证据类型",
  cause: "原因",
  result: "结果",
  participants: "参与者",
  attribute: "状态属性",
  value: "状态值",
};
export const evidenceValues: Record<string, Record<string, string>> = {
  severity: { critical: "关键问题", warning: "提醒", suggestion: "建议" },
  basis: {
    observed_conflict: "已发生的事实冲突",
    missing_cause: "缺少因果",
    future_risk: "未来风险",
    creative_detail: "创作细节",
    preference: "审美偏好",
  },
  category: {
    continuity: "连续性",
    chronology: "时序",
    character: "人物",
    causality: "因果",
    pacing: "节奏",
    plot: "剧情",
    logic: "逻辑",
    knowledge: "人物认知",
    meta_prose: "叙述边界",
    motivation: "人物动机",
    style: "文风",
  },
  source_type: {
    author: "作者声明",
    text: "正文证据",
    speech: "人物言论",
    inference: "模型推断",
  },
};

export function ReviewResults({ reviews }: { reviews: unknown[] }) {
  return (
    <div>
      {reviews.map((value, index) => {
        if (!value || typeof value !== "object" || Array.isArray(value))
          return (
            <Inspect
              key={index}
              value={value}
              fieldLabels={evidenceFields}
              valueLabels={evidenceValues}
            />
          );
        const review = value as Record<string, unknown>;
        if (!Array.isArray(review.issues))
          return (
            <Inspect
              key={index}
              value={review}
              fieldLabels={evidenceFields}
              valueLabels={evidenceValues}
            />
          );
        const other = Object.fromEntries(
          Object.entries(review).filter(
            ([key]) => !["issues", "summary"].includes(key),
          ),
        );
        return (
          <article key={index}>
            {review.issues.length === 0 ? (
              <p>未发现需要修改的问题</p>
            ) : (
              <Inspect
                value={{ issues: review.issues }}
                fieldLabels={evidenceFields}
                valueLabels={evidenceValues}
              />
            )}
            {typeof review.summary === "string" && review.summary && (
              <p>
                <strong>审稿摘要：</strong>
                {review.summary}
              </p>
            )}
            {Object.keys(other).length > 0 && (
              <Inspect
                value={other}
                fieldLabels={evidenceFields}
                valueLabels={evidenceValues}
              />
            )}
          </article>
        );
      })}
    </div>
  );
}
