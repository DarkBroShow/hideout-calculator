<script setup>
const props = defineProps({
  tabs: {
    type: Array,
    default: () => [],
  },
  activeTab: {
    type: String,
    default: "",
  },
});
const emit = defineEmits(["update:active-tab"]);

function setTab(id) {
  emit("update:active-tab", id);
}
</script>

<template>
  <div class="shell">
    <div class="page">
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
        <slot name="main" />
      </main>
    </div>
  </div>
</template>

<style scoped>
.shell {
  min-height: 100vh;
  color: #e5e7eb;
  background:
    radial-gradient(circle at top, rgba(15, 23, 42, 0.98), rgba(0, 0, 0, 0.98)),
    url("/bg-hideout.jpg") center/cover no-repeat fixed;
}
.page {
  max-width: 1600px;
  margin: 0 auto;
  padding: 1.25rem 1.5rem;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 1.5rem;
  min-height: calc(100vh - 2.5rem); /* почти весь экран */
}

.sidebar {
  border-radius: 1rem;
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(30, 64, 175, 0.5);
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.6);
}
.sidebar-inner {
  display: flex;
  flex-direction: column;
  padding: 1rem;
  height: 100%;
}
.sidebar-header {
  margin-bottom: 0.75rem;
}
.sidebar-top {
  margin-bottom: 0.5rem;
}
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
  padding: 0.4rem 0.45rem;
  border-radius: 0.5rem;
  border: none;
  background: transparent;
  color: #9ca3af;
  font-size: 0.85rem;
  text-align: left;
  cursor: pointer;
  font-family: "RodondoRUS", sans-serif; /* здесь RodondoRUS */
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
.nav-item.active .nav-dot {
  background: #facc15;
}
.nav-label {
  flex: 1;
}
.sidebar-content {
  margin-top: 0.5rem;
  flex: 1;
  overflow-y: auto;
  padding-right: 0.25rem;
}
.main {
  border-radius: 1rem;
  background: radial-gradient(circle at top left, #020617, #020617 55%);
  border: 1px solid rgba(30, 64, 175, 0.6);
  box-shadow: 0 24px 50px rgba(15, 23, 42, 0.7);
  padding: 1.1rem 1.4rem;
  display: flex;
  flex-direction: column;
}

.main :deep(.main-section) {
  flex: 1;
  display: flex;
  flex-direction: column;
}

@media (max-width: 900px) {
  .page {
    grid-template-columns: 1fr;
  }
}
</style>