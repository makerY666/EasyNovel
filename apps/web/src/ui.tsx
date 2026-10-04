import * as Dialog from "@radix-ui/react-dialog";
import * as Select from "@radix-ui/react-select";
import * as Checkbox from "@radix-ui/react-checkbox";
import * as Tabs from "@radix-ui/react-tabs";
import { Check, ChevronDown, X } from "lucide-react";
import { useRef, type ReactNode } from "react";
export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}
export function Choice({
  value,
  onChange,
  options,
  label,
}: {
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  label: string;
}) {
  return (
    <Select.Root value={value} onValueChange={onChange}>
      <Select.Trigger className="select" aria-label={label}>
        <Select.Value placeholder={`选择${label}`} />
        <Select.Icon>
          <ChevronDown size={14} />
        </Select.Icon>
      </Select.Trigger>
      <Select.Portal>
        <Select.Content className="select-menu" position="popper">
          <Select.Viewport>
            {options
              .filter((o) => o.value)
              .map((o) => (
                <Select.Item
                  key={o.value}
                  value={o.value}
                  className="select-option"
                >
                  <Select.ItemText>{o.label}</Select.ItemText>
                  <Select.ItemIndicator>
                    <Check size={14} />
                  </Select.ItemIndicator>
                </Select.Item>
              ))}
          </Select.Viewport>
        </Select.Content>
      </Select.Portal>
    </Select.Root>
  );
}
export function Tick({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  label: ReactNode;
}) {
  return (
    <label className="tick">
      <Checkbox.Root
        checked={checked}
        onCheckedChange={(v) => onChange(v === true)}
        className="checkbox"
      >
        <Checkbox.Indicator>
          <Check size={12} />
        </Checkbox.Indicator>
      </Checkbox.Root>
      <span>{label}</span>
    </label>
  );
}
export function Modal({
  open,
  onOpenChange,
  title,
  children,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  title: string;
  children: ReactNode;
}) {
  const previous = useRef<HTMLElement | null>(null);
  const wasOpen = useRef(false);
  if (open && !wasOpen.current)
    previous.current = document.activeElement as HTMLElement;
  wasOpen.current = open;
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="overlay" />
        <Dialog.Content
          onCloseAutoFocus={(event) => {
            event.preventDefault();
            previous.current?.focus();
          }}
          className="dialog"
          aria-describedby={undefined}
        >
          <div className="dialog-title">
            <Dialog.Title>{title}</Dialog.Title>
            <Dialog.Close aria-label="关闭" className="icon-button">
              <X size={18} />
            </Dialog.Close>
          </div>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
export function TabPanel({
  tabs,
  value,
  onChange,
}: {
  tabs: { id: string; label: string; content: ReactNode }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <Tabs.Root value={value} onValueChange={onChange} className="tabs">
      <Tabs.List className="tab-list">
        {tabs.map((t) => (
          <Tabs.Trigger className="tab" key={t.id} value={t.id}>
            {t.label}
          </Tabs.Trigger>
        ))}
      </Tabs.List>
      {tabs.map((t) => (
        <Tabs.Content key={t.id} value={t.id} className="tab-content">
          {t.content}
        </Tabs.Content>
      ))}
    </Tabs.Root>
  );
}
export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>;
}
export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
export const states: Record<string, string> = {
  candidate: "候选",
  confirmed: "已确认",
  superseded: "已替代",
  disputed: "有争议",
  retired: "已撤回",
  queued: "排队",
  running: "运行中",
  awaiting_plan: "等待审核计划",
  awaiting_review: "等待审核正文",
  paused: "已暂停",
  cancelled: "已取消",
  failed: "失败",
  stale: "输入已过期",
  completed: "已完成",
  draft: "草稿",
  open: "待回收",
  resolved: "已处理",
  abandoned: "已放弃",
};
export function State({ value }: { value: string }) {
  return (
    <Badge
      tone={
        ["failed", "stale", "disputed"].includes(value)
          ? "danger"
          : ["confirmed", "completed", "resolved"].includes(value)
            ? "success"
            : value.startsWith("awaiting") || value === "candidate"
              ? "warning"
              : "neutral"
      }
    >
      {states[value] ?? value}
    </Badge>
  );
}
export function Inspect({
  value,
  fieldLabels,
  valueLabels,
}: {
  value: unknown;
  fieldLabels?: Record<string, string>;
  valueLabels?: Record<string, Record<string, string>>;
}) {
  if (value === null || value === undefined) return null;
  if (typeof value !== "object") return <span>{String(value)}</span>;
  if (Array.isArray(value))
    return (
      <div className="inspection">
        {value.map((v, i) => (
          <div key={i}>
            <Inspect
              value={v}
              fieldLabels={fieldLabels}
              valueLabels={valueLabels}
            />
          </div>
        ))}
      </div>
    );
  return (
    <dl className="inspection">
      {Object.entries(value).map(([k, v]) => (
        <div key={k}>
          <dt>{fieldLabels?.[k] ?? labels[k] ?? k}</dt>
          <dd>
            {typeof v === "string" && valueLabels?.[k]?.[v] ? (
              valueLabels[k][v]
            ) : (
              <Inspect
                value={v}
                fieldLabels={fieldLabels}
                valueLabels={valueLabels}
              />
            )}
          </dd>
        </div>
      ))}
    </dl>
  );
}
const labels: Record<string, string> = {
  title: "标题",
  content: "内容",
  goal: "目标",
  obstacle: "阻力",
  turn: "转折",
  cost: "代价",
  pov: "视角",
  location: "地点",
  story_time: "故事时间",
  state_changes: "状态变化",
  scenes: "场景",
  constraints: "约束",
  evidence: "证据",
  reason: "原因",
  source_version_id: "来源版本",
  source_paragraph_id: "来源段落",
  severity: "严重性",
  issue: "问题",
  suggestion: "建议",
  description: "说明",
  kind: "类别",
  character_id: "人物",
  belief: "认知",
  acquisition: "获知方式",
  summary: "摘要",
  message: "说明",
  expected_changes: "预期变化",
  promises: "叙事承诺",
};
