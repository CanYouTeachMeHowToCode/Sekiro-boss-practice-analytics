import { describe, expect, it } from "vitest";
import { makeTranslate } from "../i18n/language";
import { makeRecording } from "../api/testRecordings";
import {
  alternatives,
  formatClock,
  formatDuration,
  formatSize,
  isPending,
  percent,
  rejectReason,
  statusLabel,
  uploadErrorMessage,
} from "./recordings";

const en = makeTranslate("en");
const zh = makeTranslate("zh");

describe("recording helpers", () => {
  it("treats the statuses the worker has not finished with as pending", () => {
    expect(["uploaded", "checking", "queued", "processing"].every((s) => isPending(s as never))).toBe(true);
    expect(["rejected", "done", "failed"].some((s) => isPending(s as never))).toBe(false);
  });

  it("formats moments to the tenth of a second and lengths to the second", () => {
    expect(formatClock(283.758)).toBe("4:43.8");
    expect(formatClock(5)).toBe("0:05.0");
    expect(formatClock(59.96)).toBe("1:00.0");
    expect(formatDuration(307.4)).toBe("5:07");
    expect(formatDuration(59.6)).toBe("1:00");
  });

  it("formats file sizes", () => {
    expect(formatSize(1.5 * 1024 ** 3)).toBe("1.5 GB");
    expect(formatSize(350 * 1024 ** 2)).toBe("350 MB");
    expect(formatSize(100)).toBe("1 KB");
  });

  it("rounds progress down to a whole percent between 0 and 100", () => {
    expect(percent(0.379)).toBe(37);
    expect(percent(1.2)).toBe(100);
    expect(percent(-1)).toBe(0);
  });

  it("labels a status, with the progress while analysing", () => {
    expect(statusLabel(makeRecording({ status: "processing", progress: 0.42 }), en)).toBe("Analysing: 42%");
    expect(statusLabel(makeRecording({ status: "queued" }), zh)).toBe("等待分析");
  });

  it("explains known reject and upload error codes, and unknown ones generally", () => {
    expect(rejectReason("too_long", en)).toBe("It is longer than 10 minutes.");
    expect(rejectReason("not_castle_genichiro", en)).toBe("It does not meet the requirements on the upload page.");
    expect(rejectReason(null, zh)).toBe("不符合上传页面上的要求。");
    expect(uploadErrorMessage("too_large", en)).toBe("The file is larger than 2 GB.");
    expect(uploadErrorMessage("aborted", zh)).toBe("上传失败，请重试。");
  });

  it("joins alternatives the way each language does", () => {
    expect(alternatives(["A"], en)).toBe("A");
    expect(alternatives(["A", "B"], en)).toBe("A or B");
    expect(alternatives(["A", "B", "C"], en)).toBe("A, B or C");
    expect(alternatives(["甲", "乙", "丙"], zh)).toBe("甲、乙或丙");
  });
});
