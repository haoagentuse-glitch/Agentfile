<script setup lang="ts">
// 單筆 run/claim/gate-entry/artifact 的詳情用右側 drawer，不開新頁面（資訊架構規則）。
// 開啟時把 focus 移進 drawer，關閉時還給原本觸發它的元素——不然鍵盤操作者會失焦回到
// document.body，找不到自己原本在哪。Esc 關閉；窄視窗下寬度退到接近全螢幕（見 theme 媒體查詢）。
import { nextTick, ref, watch } from "vue";

const props = defineProps<{ open: boolean; title: string }>();
const emit = defineEmits<{ close: [] }>();

const panelRef = ref<HTMLElement | null>(null);
let previouslyFocused: HTMLElement | null = null;

watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen) {
      previouslyFocused = document.activeElement as HTMLElement | null;
      await nextTick();
      panelRef.value?.focus();
    } else {
      previouslyFocused?.focus?.();
      previouslyFocused = null;
    }
  }
);

const focusableSelector = [
  "button:not([disabled])",
  "a[href]",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

function handleKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") {
    event.preventDefault();
    emit("close");
    return;
  }
  if (event.key !== "Tab" || !panelRef.value) return;

  const focusable = [...panelRef.value.querySelectorAll<HTMLElement>(focusableSelector)];
  if (focusable.length === 0) {
    event.preventDefault();
    panelRef.value.focus();
    return;
  }

  const first = focusable[0];
  const last = focusable.at(-1)!;
  const active = document.activeElement;
  if (event.shiftKey && (active === first || active === panelRef.value)) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && active === last) {
    event.preventDefault();
    first.focus();
  }
}
</script>

<template>
  <div v-if="open" class="drawer-backdrop" @click.self="emit('close')" @keydown="handleKeydown">
    <aside ref="panelRef" class="drawer" role="dialog" aria-modal="true" :aria-label="title" tabindex="-1">
      <header class="drawer-header">
        <strong>{{ title }}</strong>
        <button aria-label="關閉" @click="emit('close')">✕</button>
      </header>
      <div class="drawer-body">
        <slot />
      </div>
    </aside>
  </div>
</template>

<style scoped>
.drawer-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(7, 54, 66, 0.25);
  display: flex;
  justify-content: flex-end;
  z-index: 20;
}
.drawer {
  width: 420px;
  max-width: 90vw;
  background: var(--color-bg);
  border-left: 1px solid var(--color-border);
  height: 100%;
  overflow-y: auto;
  padding: var(--space-4);
}
.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--space-2);
}

@media (max-width: 560px) {
  .drawer {
    width: 100vw;
    max-width: 100vw;
  }
}
</style>
