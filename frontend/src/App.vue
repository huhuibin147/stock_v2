<template>
  <div class="app">
    <header class="app-header">
      <div class="header-inner">
        <router-link to="/" class="logo">
          <span class="logo-icon">📈</span>
          <span class="logo-text">Stock V2</span>
          <span class="logo-sub">A股资讯分析系统</span>
        </router-link>
        <nav class="nav">
          <router-link to="/" class="nav-link">首页</router-link>
          <router-link to="/admin" class="nav-link">管理后台</router-link>
        </nav>
      </div>
    </header>
    <main class="app-main">
      <router-view />
    </main>
    <footer class="app-footer">
      <div class="footer-inner">
        <span>Stock V2 · A股资讯分析系统</span>
        <span class="footer-note">数据仅供参考，不构成投资建议</span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.app-header {
  background: #fff;
  border-bottom: 1px solid var(--border-light);
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(8px);
  background: rgba(255,255,255,0.95);
}
.header-inner {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 24px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: var(--text);
}
.logo-icon { font-size: 20px; }
.logo-text { font-size: 18px; font-weight: 800; color: var(--primary); }
.logo-sub { font-size: 12px; color: var(--text-muted); margin-left: 4px; }
.nav { display: flex; gap: 20px; }
.nav-link {
  font-size: 14px;
  color: var(--text-secondary);
  text-decoration: none;
  padding: 4px 0;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}
.nav-link:hover,
.nav-link.router-link-active {
  color: var(--primary);
  border-bottom-color: var(--primary);
  text-decoration: none;
}
.app-main {
  flex: 1;
}
.app-footer {
  border-top: 1px solid var(--border-light);
  background: #fff;
  padding: 16px 0;
}
.footer-inner {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-muted);
}
.footer-note { color: var(--text-muted); }
</style>
