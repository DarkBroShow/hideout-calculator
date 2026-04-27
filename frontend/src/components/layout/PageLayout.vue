<script setup>
const props = defineProps({
  tabs: { type: Array, default: () => [] },
  activeTab: { type: String, default: "" },
});
const emit = defineEmits(["update:active-tab"]);

function setTab(id) {
  emit("update:active-tab", id);
}
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="sidebar-inner">
        <div class="sidebar-header">
          <slot name="header" />
        </div>

        <div class="sidebar-top">
          <slot name="sidebar-top" />
        </div>

        <nav v-if="tabs.length" class="nav">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            type="button"
            class="nav-item"
            :class="{ active: tab.id === activeTab }"
            @click="setTab(tab.id)"
          >
            <span class="nav-dot" />
            <span class="nav-label">{{ tab.label }}</span>
          </button>
        </nav>

        <div class="sidebar-content">
          <slot name="sidebar-content" />
        </div>
      </div>
    </aside>

    <main class="main">
      <div class="main-inner">
        <slot name="main" />
      </div>
    </main>
  </div>
</template>

<style scoped>
.shell {
  min-height: 100vh;
  color: #e5e7eb;
  background:
    radial-gradient(circle at top, rgba(15, 23, 42, 0.98), rgba(0, 0, 0, 0.98)),
    url("/bg-hideout.jpg") center/cover no-repeat fixed;
  display: flex;
  align-items: stretch;
}

.sidebar {
  width: 280px;
  flex: 0 0 280px;
  position: sticky;
  top: 0;
  height: 100vh;
  background: rgba(8, 13, 25, 0.97);
  border-right: 1px solid rgba(30, 64, 175, 0.55);
  box-shadow: 4px 0 20px rgba(0, 0, 0, 0.5);
  z-index: 5;
}
.sidebar-inner {
  display: flex;
  flex-direction: column;
  padding: 1rem 0.9rem;
  height: 100%;
  box-sizing: border-box;
}
.sidebar-header { margin-bottom: 0.75rem; }
.sidebar-top { margin-bottom: 0.5rem; }
.nav {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 0.75rem;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.45rem 0.55rem;
  border-radius: 0.5rem;
  border: none;
  background: transparent;
  color: #9ca3af;
  font-size: 0.9rem;
  text-align: left;
  cursor: pointer;
  font-family: "RodondoRUS", sans-serif;
}
.nav-item:hover {
  background: rgba(31, 41, 55, 0.85);
  color: #e5e7eb;
}
.nav-item.active {
  background: linear-gradient(to right, #1d4ed8, #0ea5e9);
  color: #f9fafb;
}
.nav-dot {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.7);
}
.nav-item.active .nav-dot { background: #facc15; }
.nav-label { flex: 1; }
.sidebar-content {
  margin-top: 0.5rem;
  flex: 1;
  overflow-y: auto;
  padding-right: 0.25rem;
}
.main {
  flex: 1;
  min-width: 0;
  padding: 1.1rem 1.4rem 1.4rem;
}
.main-inner {
  max-width: 1500px;
  margin: 0 auto;
}

.main :deep(.main-section) {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

@media (max-width: 900px) {
  .shell { flex-direction: column; }
  .sidebar {
    position: static;
    width: 100%;
    flex: 0 0 auto;
    height: auto;
    border-right: none;
    border-bottom: 1px solid rgba(30, 64, 175, 0.55);
  }
}
</style>