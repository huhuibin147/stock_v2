<template>
  <div class="admin-layout">
    <aside class="sidebar">
      <div class="sidebar-title">后台管理</div>
      <nav class="sidebar-nav">
        <router-link to="/admin" class="nav-item" exact-active-class="active">
          <span class="nav-icon">📊</span> 系统概览
        </router-link>
        <router-link to="/admin/stocks" class="nav-item" active-class="active">
          <span class="nav-icon">📈</span> 股票管理
        </router-link>
        <router-link to="/admin/news" class="nav-item" active-class="active">
          <span class="nav-icon">📰</span> 资讯管理
        </router-link>
        <router-link to="/admin/concepts" class="nav-item" active-class="active">
          <span class="nav-icon">🏷️</span> 概念管理
        </router-link>
        <router-link to="/admin/supply-chain" class="nav-item" active-class="active">
          <span class="nav-icon">🔗</span> 供应链管理
        </router-link>
      </nav>
      <div class="sidebar-footer">
        <router-link to="/" class="nav-item back-link">
          <span class="nav-icon">←</span> 返回前台
        </router-link>
      </div>
    </aside>
    <main class="admin-main">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.admin-layout {
  display: flex;
  min-height: calc(100vh - 56px);
}
.sidebar {
  width: 200px;
  background: var(--bg);
  border-right: 1px solid var(--border-light);
  padding: 16px 0;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
.sidebar-title {
  padding: 0 16px 16px;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-light);
}
.sidebar-nav {
  flex: 1;
  padding: 8px 0;
}
.sidebar-footer {
  border-top: 1px solid var(--border-light);
  padding-top: 8px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  transition: all 0.15s;
}
.nav-item:hover {
  background: var(--bg-secondary);
  color: var(--text);
  text-decoration: none;
}
.nav-item.active {
  color: var(--primary);
  background: var(--primary-light);
  font-weight: 600;
}
.nav-icon { font-size: 15px; }
.back-link { color: var(--text-muted); }
.back-link:hover { color: var(--primary); }

.admin-main {
  flex: 1;
  padding: 24px;
  overflow-x: auto;
}
</style>
