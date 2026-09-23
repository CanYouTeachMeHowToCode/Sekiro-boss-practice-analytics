import { describe, expect, it } from "vitest";
import { topKeys } from "./analytics";

describe("topKeys", () => {
  it("returns the single highest key", () => {
    expect(topKeys({ "1": 2, "2": 5, "3": 1 })).toEqual(["2"]);
  });

  it("returns every key tied for the highest count", () => {
    expect(topKeys({ "1": 3, "2": 1, "3": 3 })).toEqual(["1", "3"]);
  });

  it("returns nothing when there are no counts", () => {
    expect(topKeys({})).toEqual([]);
  });
});
