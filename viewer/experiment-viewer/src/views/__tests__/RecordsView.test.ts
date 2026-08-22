// Records 分頁的通用性驗收：第二份 schema 的 fixture 走同一個 loadProject(root)，
// 進同一組 Records 元件。新增欄位只改資料與 viewer.json，不改 Vue。

import path from "node:path";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

vi.mock("../../lib/tauri-fs", () => import("../../lib/test-utils/fs-fixture"));

import RecordsView from "../RecordsView.vue";
import type { ProjectSnapshot } from "../../lib/canonical";
import { loadProject } from "../../lib/project-loader";

// jsdom 環境的 import.meta.url 不是 file: URL，改用 vitest 的工作目錄（專案根）解析。
const fixturesDir = path.resolve(process.cwd(), "tests/fixtures");

// useProjectStore 是模組層的單例 ref；直接餵 snapshot，不繞路啟動整個 app。
async function mountWithSnapshot(snapshot: ProjectSnapshot) {
  const store = await import("../../store/project");
  store.useProjectStore().snapshot.value = snapshot;
  return mount(RecordsView);
}

async function genericSnapshot(): Promise<ProjectSnapshot> {
  return loadProject(path.join(fixturesDir, "generic"));
}

describe("RecordsView 與 manifest 專案", () => {
  it("loads the second schema through the same loadProject entry point", async () => {
    const snapshot = await genericSnapshot();

    expect(snapshot.adapterKind).toBe("manifest");
    expect(snapshot.genericCollections.map((c) => c.name)).toEqual(["notes"]);
  });

  it("builds columns from viewer.json rather than fixed field names", async () => {
    const wrapper = await mountWithSnapshot(await genericSnapshot());

    const headers = wrapper.findAll("th button").map((button) => button.text().replace(/[▲▼]\s*$/, "").trim());
    expect(headers).toContain("meta.title");
    expect(headers).toContain("body");
  });

  it("shows the metric catalog including metrics with no declared direction", async () => {
    const wrapper = await mountWithSnapshot(await genericSnapshot());

    // 沒有方向定義時忠實顯示「（未定義）」，不是空白讓人以為漏資料。
    expect(wrapper.text()).toContain("（未定義）");
    expect(wrapper.text()).toContain("higher_is_better");
  });

  it("opens a record drawer when a row is selected", async () => {
    const wrapper = await mountWithSnapshot(await genericSnapshot());

    const collectionTable = wrapper.findAllComponents({ name: "DataTable" }).at(-1)!;
    await collectionTable.findAll("tbody tr")[0].trigger("click");

    expect(wrapper.find("pre").exists()).toBe(true);
  });
});

describe("RecordsView 未知型別與缺值", () => {
  function snapshotWith(records: Array<Record<string, unknown>>, columns: string[]): ProjectSnapshot {
    return {
      projectRoot: "/p",
      recordsRoot: "/p/records/experiments",
      rootKind: "relative",
      adapterKind: "manifest",
      experiments: [],
      comparisons: [],
      metricDefinitions: [],
      artifacts: [],
      genericCollections: [{
        name: "things",
        columns,
        records: records.map((fields, index) => ({
          id: `r${index}`,
          sourcePath: `things/r${index}.json`,
          fields,
        })),
      }],
      diagnostics: [],
    };
  }

  it("renders an object field without producing [object Object]", async () => {
    const wrapper = await mountWithSnapshot(
      snapshotWith([{ payload: { retries: 3, note: "逾時" } }], ["payload"])
    );

    expect(wrapper.text()).not.toContain("[object Object]");
    expect(wrapper.text()).toContain("{ retries, note }");
  });

  it("renders an array field as a readable summary", async () => {
    const wrapper = await mountWithSnapshot(
      snapshotWith([{ tags: ["retrieval", "latency"] }], ["tags"])
    );

    expect(wrapper.text()).toContain("retrieval, latency");
  });

  it("shows a placeholder when the declared column is missing from a record", async () => {
    const wrapper = await mountWithSnapshot(snapshotWith([{ other: 1 }], ["missing.path"]));

    const cells = wrapper.findAll("tbody td").map((td) => td.text());
    expect(cells).toContain("—");
  });

  it("keeps a falsy value visible instead of treating it as missing", async () => {
    const wrapper = await mountWithSnapshot(snapshotWith([{ count: 0, ok: false }], ["count", "ok"]));

    const cells = wrapper.findAll("tbody td").map((td) => td.text());
    expect(cells).toContain("0");
    expect(cells).toContain("false");
  });

  it("opens a drawer with the full content of a truncated field", async () => {
    const long = "字".repeat(400);
    const wrapper = await mountWithSnapshot(snapshotWith([{ body: long }], ["body"]));

    await wrapper.find("button.expand-button").trigger("click");

    expect(wrapper.findAll("pre").some((pre) => pre.text() === long)).toBe(true);
  });

  it("falls back to id and source when viewer.json declares no columns", async () => {
    const wrapper = await mountWithSnapshot(snapshotWith([{ anything: 1 }], []));

    const headers = wrapper.findAll("th button").map((button) => button.text().replace(/[▲▼]\s*$/, "").trim());
    expect(headers).toEqual(expect.arrayContaining(["id", "source"]));
  });

  it("says so when there are no generic collections at all", async () => {
    const empty = snapshotWith([], []);
    empty.genericCollections = [];

    const wrapper = await mountWithSnapshot(empty);

    expect(wrapper.text()).toContain("沒有 viewer.json 定義的額外紀錄集合");
  });
});
