// 元件測試。src/lib 的資料層測試驗不到這些：排序有沒有真的換行順序、
// 篩選有沒有真的隱藏列、點一列有沒有真的發出事件、物件欄位在畫面上長什麼樣。

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import DataTable, { type DataTableColumn } from "../DataTable.vue";

const columns: DataTableColumn[] = [
  { key: "name", label: "name" },
  { key: "score", label: "score" },
  { key: "group", label: "group" },
];

const rows = [
  { name: "beta", score: 10, group: "b" },
  { name: "alpha", score: 2, group: "a" },
  { name: "gamma", score: 33, group: "a" },
];

function table(overrides: Record<string, unknown> = {}) {
  return mount(DataTable, {
    props: {
      columns,
      rows,
      rowKey: (row: Record<string, unknown>) => String(row.name),
      ...overrides,
    },
  });
}

function bodyText(wrapper: ReturnType<typeof table>): string[][] {
  return wrapper
    .findAll("tbody tr")
    .map((tr) => tr.findAll("td").map((td) => td.text()));
}

describe("DataTable 排序", () => {
  it("sorts numerically, not lexicographically", async () => {
    // 字串排序會把 10 排在 2 前面；這正是 toComparable 要避免的。
    const wrapper = table();

    await wrapper.findAll("th button")[1].trigger("click");

    expect(bodyText(wrapper).map((cells) => cells[1])).toEqual(["2", "10", "33"]);
  });

  it("toggles direction on a second click of the same column", async () => {
    const wrapper = table();
    const scoreHeader = wrapper.findAll("th button")[1];

    await scoreHeader.trigger("click");
    await scoreHeader.trigger("click");

    expect(bodyText(wrapper).map((cells) => cells[1])).toEqual(["33", "10", "2"]);
  });

  it("starts a new column ascending rather than keeping the previous direction", async () => {
    const wrapper = table();
    const headers = wrapper.findAll("th button");

    await headers[1].trigger("click");
    await headers[1].trigger("click");
    await headers[0].trigger("click");

    expect(bodyText(wrapper).map((cells) => cells[0])).toEqual(["alpha", "beta", "gamma"]);
  });
});

describe("DataTable 篩選", () => {
  it("hides rows that do not match", async () => {
    const wrapper = table();

    await wrapper.find("input.filter-input").setValue("alpha");

    expect(bodyText(wrapper)).toHaveLength(1);
    expect(bodyText(wrapper)[0][0]).toBe("alpha");
  });

  it("says so when nothing matches instead of showing an empty table", async () => {
    const wrapper = table();

    await wrapper.find("input.filter-input").setValue("找不到的東西");

    expect(bodyText(wrapper)).toHaveLength(0);
    expect(wrapper.text()).toContain("沒有符合篩選條件的資料列");
  });

  it("matches text nested inside an object column", async () => {
    const wrapper = table({
      rows: [{ name: "a", meta: { owner: "研究組" } }, { name: "b", meta: { owner: "平台組" } }],
      columns: [{ key: "name", label: "name" }, { key: "meta", label: "meta" }],
    });

    await wrapper.find("input.filter-input").setValue("研究組");

    expect(bodyText(wrapper)).toHaveLength(1);
  });
});

describe("DataTable 分組", () => {
  it("adds a group header row per distinct value, in current row order", async () => {
    // 分組跟著目前的排序走，不自己另外排一次——不然畫面上的順序會跟排序欄位對不上。
    const wrapper = table({ groupable: true });

    await wrapper.find("select").setValue("group");

    expect(wrapper.findAll("tr.group-row").map((tr) => tr.text())).toEqual(["b（1）", "a（2）"]);
  });

  it("reorders groups when the sort changes", async () => {
    const wrapper = table({ groupable: true });
    await wrapper.find("select").setValue("group");

    await wrapper.findAll("th button")[2].trigger("click");

    expect(wrapper.findAll("tr.group-row").map((tr) => tr.text())).toEqual(["a（2）", "b（1）"]);
  });

  it("labels rows whose group value is missing rather than dropping them", async () => {
    const wrapper = table({
      groupable: true,
      rows: [{ name: "a", group: "x" }, { name: "b" }],
    });

    await wrapper.find("select").setValue("group");

    expect(wrapper.findAll("tr.group-row").map((tr) => tr.text())).toContain("（空值）（1）");
  });
});

describe("DataTable 選取", () => {
  it("emits the clicked row", async () => {
    const wrapper = table();

    await wrapper.findAll("tbody tr")[0].trigger("click");

    expect(wrapper.emitted("select")?.[0][0]).toMatchObject({ name: "beta" });
  });

  it("emits on Enter so the table is usable from the keyboard", async () => {
    const wrapper = table();

    await wrapper.findAll("tbody tr")[1].trigger("keydown.enter");

    expect(wrapper.emitted("select")?.[0][0]).toMatchObject({ name: "alpha" });
  });

  it("marks the selected row", () => {
    const wrapper = table({ selectedKey: "alpha" });

    const selected = wrapper.findAll("tbody tr").filter((tr) => tr.classes("selected"));
    expect(selected).toHaveLength(1);
    expect(selected[0].text()).toContain("alpha");
  });
});

describe("DataTable 未知型別欄位", () => {
  it("renders an object column without producing [object Object]", () => {
    const wrapper = table({
      rows: [{ name: "a", payload: { retries: 3, note: "逾時" } }],
      columns: [{ key: "name", label: "name" }, { key: "payload", label: "payload" }],
    });

    expect(wrapper.text()).not.toContain("[object Object]");
    expect(wrapper.text()).toContain("{ retries, note }");
  });

  it("shows a placeholder for a missing value", () => {
    const wrapper = table({
      rows: [{ name: "a" }],
      columns: [{ key: "name", label: "name" }, { key: "missing", label: "missing" }],
    });

    expect(bodyText(wrapper)[0][1]).toBe("—");
  });

  it("offers an expand control for a value the cell cannot hold", async () => {
    const long = "字".repeat(400);
    const wrapper = table({
      rows: [{ name: "a", body: long }],
      columns: [{ key: "name", label: "name" }, { key: "body", label: "body" }],
    });

    const expand = wrapper.find("button.expand-button");
    expect(expand.exists()).toBe(true);

    await expand.trigger("click");

    expect(wrapper.emitted("expand")?.[0][0]).toEqual({ label: "body", content: long });
  });

  it("does not select the row when the expand control is used", async () => {
    const wrapper = table({
      rows: [{ name: "a", payload: { k: 1 } }],
      columns: [{ key: "name", label: "name" }, { key: "payload", label: "payload" }],
    });

    await wrapper.find("button.expand-button").trigger("click");

    expect(wrapper.emitted("select")).toBeUndefined();
  });

  it("keeps sorting a column that mixes types instead of throwing", async () => {
    const wrapper = table({
      rows: [{ name: "a", mixed: 5 }, { name: "b", mixed: { x: 1 } }, { name: "c", mixed: null }],
      columns: [{ key: "name", label: "name" }, { key: "mixed", label: "mixed" }],
    });

    await wrapper.findAll("th button")[1].trigger("click");

    expect(bodyText(wrapper)).toHaveLength(3);
  });

  it("lets a named slot override the default rendering", () => {
    const wrapper = mount(DataTable, {
      props: { columns, rows, rowKey: (row: Record<string, unknown>) => String(row.name) },
      slots: { score: "<span class='custom'>自訂</span>" },
    });

    expect(wrapper.find("span.custom").exists()).toBe(true);
  });
});
