import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import App from "./App.vue";
import "./styles/global.css";

const base = import.meta.env.BASE_URL || "/";
const router = createRouter({
  history: createWebHistory(base),
  routes: [
    { path: "/", component: () => import("./views/Home.vue") },
    { path: "/stocks", component: () => import("./views/StockList.vue") },
    { path: "/stock/:code", component: () => import("./views/StockProfile.vue") },
    { path: "/news", component: () => import("./views/NewsList.vue") },
    { path: "/news/:id", component: () => import("./views/NewsDetail.vue") },
    { path: "/xueqiu", component: () => import("./views/XueqiuRanking.vue") },
    { path: "/quant", component: () => import("./views/QuantRecommend.vue") },
    { path: "/chains", component: () => import("./views/ChainList.vue") },
    { path: "/supply-chain", component: () => import("./views/SupplyChainList.vue") },
    { path: "/supply-chain/:id", component: () => import("./views/SupplyChainDetail.vue") },
    {
      path: "/admin",
      component: () => import("./views/admin/Layout.vue"),
      children: [
        { path: "", component: () => import("./views/admin/Dashboard.vue") },
        { path: "stocks", component: () => import("./views/admin/Stocks.vue") },
        { path: "news", component: () => import("./views/admin/News.vue") },
        { path: "concepts", component: () => import("./views/admin/Concepts.vue") },
        { path: "supply-chain", component: () => import("./views/admin/SupplyChain.vue") },
      ],
    },
  ],
});

createApp(App).use(router).mount("#app");
