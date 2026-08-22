// 第二份 schema 的跨頁驗收：同一個 generic fixture 必須走過主要 UI seam。

import path from "node:path";
import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { describe, expect, it, vi } from "vitest";

vi.mock("../../lib/tauri-fs", () => import("../../lib/test-utils/fs-fixture"));
vi.mock("echarts/core", () => ({ use: vi.fn() }));
vi.mock("echarts/charts", () => ({ BarChart: {} }));
vi.mock("echarts/components", () => ({ GridComponent: {}, LegendComponent: {}, TooltipComponent: {} }));
vi.mock("echarts/renderers", () => ({ CanvasRenderer: {} }));
vi.mock("vue-echarts", () => ({ default: { name: "VChart", template: "<div class='v-chart' />" } }));

import OverviewView from "../OverviewView.vue";
import ExperimentsView from "../ExperimentsView.vue";
import ExperimentWorkspaceView from "../ExperimentWorkspaceView.vue";
import { loadProject } from "../../lib/project-loader";

const genericRoot = path.resolve(process.cwd(), "tests/fixtures/generic");

async function loadGenericIntoStore() {
  const snapshot = await loadProject(genericRoot);
  const store = await import("../../store/project");
  store.useProjectStore().snapshot.value = snapshot;
  return snapshot;
}

describe("generic manifest 的主要畫面", () => {
  it("renders Overview from the manifest adapter snapshot", async () => {
    await loadGenericIntoStore();

    const wrapper = mount(OverviewView);

    expect(wrapper.text()).toContain("2實驗數");
    expect(wrapper.text()).toContain("執行：done");
    expect(wrapper.text()).toContain("資料錯誤摘要");
  });

  it("lists generic experiments and routes through the public workspace route", async () => {
    await loadGenericIntoStore();
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: "/", component: { template: "<div />" } },
        { path: "/experiments/:id", name: "experiment-workspace", component: { template: "<div />" } },
      ],
    });
    await router.push("/");
    await router.isReady();
    const wrapper = mount(ExperimentsView, { global: { plugins: [router] } });

    expect(wrapper.text()).toContain("exp-a");
    expect(wrapper.text()).toContain("exp-b");
    await wrapper.findAll("tbody tr")[0].trigger("click");
    await flushPromises();

    expect(router.currentRoute.value.name).toBe("experiment-workspace");
    expect(router.currentRoute.value.params.id).toBe("exp-a");
  });

  it("opens the generic experiment workspace and its run records", async () => {
    await loadGenericIntoStore();
    const wrapper = mount(ExperimentWorkspaceView, { props: { id: "exp-a" } });

    expect(wrapper.text()).toContain("exp-a");
    expect(wrapper.text()).toContain("摘要");
    const runsTab = wrapper.findAll("nav.tabs button").find((button) => button.text() === "執行紀錄");
    expect(runsTab).toBeDefined();
    await runsTab!.trigger("click");

    expect(wrapper.text()).toContain("run-a1");
    expect(wrapper.text()).toContain("run-a2");
  });
});
