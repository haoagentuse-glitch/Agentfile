// Hash history：桌面 app 沒有伺服器端路由可設定，也不需要為了幾個分頁引入額外框架，
// 只用 vue-router 換左側 nav／experiment workspace 的網址列可分享／可上一頁。

import { createRouter, createWebHashHistory } from "vue-router";
import OverviewView from "./views/OverviewView.vue";
import ExperimentsView from "./views/ExperimentsView.vue";
import RecordsView from "./views/RecordsView.vue";
import DiagnosticsView from "./views/DiagnosticsView.vue";

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: "/", name: "overview", component: OverviewView },
    { path: "/experiments", name: "experiments", component: ExperimentsView },
    {
      path: "/experiments/:id",
      name: "experiment-workspace",
      component: () => import("./views/ExperimentWorkspaceView.vue"),
      props: true,
    },
    { path: "/records", name: "records", component: RecordsView },
    { path: "/diagnostics", name: "diagnostics", component: DiagnosticsView },
  ],
});
