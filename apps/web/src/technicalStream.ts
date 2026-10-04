export type TechnicalOutput = {
  key: string;
  role: string;
  text: string;
};

// Keep each call's fragments together, even when reviewers stream concurrently.
export function appendTechnicalOutput(
  previous: TechnicalOutput[],
  data: unknown,
  limit = 64000,
): TechnicalOutput[] {
  const chunk =
    typeof data === "string"
      ? { text: data }
      : data && typeof data === "object"
        ? (data as Record<string, unknown>)
        : {};
  const text =
    typeof chunk.text === "string"
      ? chunk.text
      : typeof chunk.content === "string"
        ? chunk.content
        : "";
  if (!text) return previous;
  const role = typeof chunk.role === "string" ? chunk.role : "model";
  const key = typeof chunk.call_key === "string" ? chunk.call_key : role;
  const outputs = previous.map((item) => ({ ...item }));
  const current = outputs.find((item) => item.key === key);
  if (current) current.text += text;
  else outputs.push({ key, role, text });
  let excess = outputs.reduce((sum, item) => sum + item.text.length, 0) - limit;
  while (excess > 0 && outputs.length) {
    const first = outputs[0];
    const remove = Math.min(excess, first.text.length);
    first.text = first.text.slice(remove);
    excess -= remove;
    if (!first.text) outputs.shift();
  }
  return outputs;
}
