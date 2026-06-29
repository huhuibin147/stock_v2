import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import App from "./App.vue";
import "./styles/global.css";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: () => import("./views/Home.vue") },
    { path: "/stock/:code", component: () => import("./views/StockProfile.vue") },
    {
      path: "/admin",
      component: () => import("./views/admin/Layout.vue"),
      children: [
        { path: "", component: () => import("./views/admin/Dashboard.vue") },
        { path: "stocks", component: () => import("./views/admin/Stocks.vue") },
        { path: "news", component: () => import("./views/admin/News.vue") },
        { path: "concepts", component: () => import("./views/admin/Concepts.vue") },
      ],
    },
  ],
});

createApp(App).use(router).mount("#app");
