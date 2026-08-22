<script setup lang="ts">
import appIcon from "../assets/app-icon.svg";
</script>

<template>
  <nav class="nav-rail">
    <div class="brand"><img :src="appIcon" alt="" />實驗檢視器</div>
    <RouterLink to="/" class="nav-item">總覽</RouterLink>
    <RouterLink to="/experiments" class="nav-item">實驗</RouterLink>
    <RouterLink to="/records" class="nav-item">紀錄</RouterLink>
    <RouterLink to="/diagnostics" class="nav-item">診斷與關於</RouterLink>
  </nav>
</template>

<style scoped>
.nav-rail {
  width: 180px;
  flex-shrink: 0;
  border-right: 1px solid var(--color-border);
  background: var(--color-bg-alt);
  padding: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.brand {
  font-weight: 600;
  color: var(--color-heading);
  margin-bottom: var(--space-3);
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.brand img {
  width: 28px;
  height: 28px;
  flex: none;
}
.nav-item {
  color: var(--color-text);
  text-decoration: none;
  padding: 6px 8px;
  border-radius: var(--radius);
}
.nav-item:hover {
  background: rgba(38, 139, 210, 0.08);
}
.nav-item.router-link-active {
  background: rgba(38, 139, 210, 0.16);
  color: var(--color-heading);
  font-weight: 600;
}

@media (max-width: 720px) {
  .nav-rail {
    width: 100%;
    flex-direction: row;
    flex-wrap: wrap;
    border-right: none;
    border-bottom: 1px solid var(--color-border);
  }
  .brand {
    margin-bottom: 0;
    margin-right: var(--space-3);
  }
}
</style>
