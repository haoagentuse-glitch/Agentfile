<script setup lang="ts"></script>

<template>
  <nav class="nav-rail">
    <div class="brand">experiment-viewer</div>
    <RouterLink to="/" class="nav-item">Overview</RouterLink>
    <RouterLink to="/experiments" class="nav-item">Experiments</RouterLink>
    <RouterLink to="/records" class="nav-item">Records</RouterLink>
    <RouterLink to="/diagnostics" class="nav-item">Diagnostics / About</RouterLink>
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
