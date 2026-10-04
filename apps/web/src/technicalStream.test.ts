import { describe, expect, it } from "vitest";
import { appendTechnicalOutput } from "./technicalStream";

describe("technical stream output", () => {
  it("concatenates fragments verbatim without injecting role labels", () => {
    const first = appendTechnicalOutput([], { role: "editor", call_key: "audit:1", text: '{"sum' });
    const result = appendTechnicalOutput(first, { role: "editor", call_key: "audit:1", text: 'mary":"通过"}' });
    expect(result).toEqual([{ key: "audit:1", role: "editor", text: '{"summary":"通过"}' }]);
    expect(first[0].text).toBe('{"sum');
  });
  it("isolates concurrent calls and later calls by the same reviewer", () => {
    let result = appendTechnicalOutput([], { role: "editor", call_key: "editor:1", text: "人物" });
    result = appendTechnicalOutput(result, { role: "continuity", call_key: "continuity:1", text: "时序" });
    result = appendTechnicalOutput(result, { role: "editor", call_key: "editor:1", text: "可信" });
    result = appendTechnicalOutput(result, { role: "editor", call_key: "editor:2", text: "复核" });
    expect(result.map((item) => item.text)).toEqual(["人物可信", "时序", "复核"]);
  });
  it("bounds total retained output without mutating earlier state", () => {
    const first = appendTechnicalOutput([], { role: "editor", call_key: "a", text: "123456" }, 8);
    const second = appendTechnicalOutput(first, { role: "writer", call_key: "b", text: "abcdef" }, 8);
    expect(second.map((item) => item.text)).toEqual(["56", "abcdef"]);
    const third = appendTechnicalOutput(second, { role: "writer", call_key: "b", text: "xyz" }, 8);
    expect(third.map((item) => item.text)).toEqual(["bcdefxyz"]);
    expect(first[0].text).toBe("123456");
  });
});
