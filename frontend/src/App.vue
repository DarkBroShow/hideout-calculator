<script setup>
import PageLayout from "./components/layout/PageLayout.vue";
import ItemSearch from "./components/search/ItemSearch.vue";
import RecipeGraph from "./components/recipes/RecipeGraph.vue";
import MaterialEditor from "./components/materials/MaterialEditor.vue";
import { ref, computed } from "vue";

const selectedItem = ref(null);
const activeTab = ref("recipes"); // profile | hideout | recipes | current-tree

function handleItemSelected(item) {
  selectedItem.value = item;
  activeTab.value = "current-tree";
}

const tabs = [
  { id: "profile", label: "Профиль" },
  { id: "hideout", label: "Убежище" },
  { id: "recipes", label: "Рецепты" },
  { id: "current-tree", label: "Дерево крафта" },
];

const activeTabLabel = computed(
  () => tabs.find((t) => t.id === activeTab.value)?.label || ""
);
</script>

<template>
  <PageLayout
    :tabs="tabs"
    :active-tab="activeTab"
    @update:active-tab="(val) => (activeTab = val)"
  >
    <template #header>
      <div class="brand">
        <div class="logo">
          <span class="logo-mark">HC</span>
        </div>
        <div>
          <h1 class="title">Hideout Calculator</h1>
          <p class="subtitle">
            Инструмент для расчёта крафта и анализа ресурсов.
          </p>
        </div>
      </div>
    </template>

    <template #sidebar-top>
      <div class="project-badge">
        <span class="name">Hideout Calculator</span>
        <span class="tag">beta</span>
      </div>
      <div class="tab-caption">
        {{ activeTabLabel }}
      </div>
    </template>

    <!-- В ЛЕВОМ БЛОКЕ — только текст/описания, без поиска -->
    <template #sidebar-content>
      <div v-if="activeTab === 'recipes'" class="sidebar-info">
        <p>
          В этом режиме можно искать предметы и просматривать их рецепты
          в центральной области.
        </p>
        <p>
          Выберите предмет, чтобы открыть дерево крафта и перейти к редактированию.
        </p>
      </div>

      <div v-else-if="activeTab === 'profile'" class="sidebar-info">
        <p>Здесь появятся настройки профиля и авторизация.</p>
      </div>

      <div v-else-if="activeTab === 'hideout'" class="sidebar-info">
        <p>Здесь будет ввод уровней убежища и доступных модулей.</p>
      </div>

      <div v-else-if="activeTab === 'current-tree'" class="sidebar-info">
        <p>Здесь будут быстрые фильтры и сводки по текущему рецепту.</p>
      </div>
    </template>

    <!-- В ЦЕНТРЕ — поиск и дерево -->
    <template #main>
      <section v-if="activeTab === 'recipes'" class="main-section">
        <ItemSearch @select="handleItemSelected" />
      </section>

      <section v-else-if="activeTab === 'current-tree'" class="main-section">
        <RecipeGraph :item="selectedItem" />
        <MaterialEditor :item="selectedItem" />
      </section>

      <section v-else-if="activeTab === 'profile'" class="main-section">
        <h2 class="section-title">Профиль</h2>
        <p class="section-text">
          Здесь будет вход в профиль, привязка аккаунта и персональные настройки.
        </p>
      </section>

      <section v-else-if="activeTab === 'hideout'" class="main-section">
        <h2 class="section-title">Уровни убежища</h2>
        <p class="section-text">
          Здесь появится ввод уровней модулей убежища и доступных крафтов.
        </p>
      </section>
    </template>
  </PageLayout>
</template>

<style scoped>
.brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.logo {
  width: 40px;
  height: 40px;
  border-radius: 0.9rem;
  background: radial-gradient(circle at 30% 20%, #60a5fa, #1f2937);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.4);
}
.logo-mark {
  font-size: 0.9rem;
  font-weight: 700;
  color: #e5e7eb;
  font-family: "RodondoRUS", sans-serif;
}
.title {
  font-size: 1.6rem;
  font-weight: 400;
  color: #e5e7eb;
  font-family: "RodondoRUS", sans-serif;
}
.subtitle {
  margin-top: 0.15rem;
  color: #9ca3af;
  font-size: 0.85rem;
}
.project-badge {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.4rem 0.55rem;
  border-radius: 0.5rem;
  background: linear-gradient(to right, #111827, #020617);
  border: 1px solid #1f2933;
  margin-bottom: 0.5rem;
}
.project-badge .name {
  font-size: 0.9rem;
  color: #e5e7eb;
  font-weight: 400;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-family: "RodondoRUS", sans-serif;
}
.project-badge .tag {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0.1rem 0.3rem;
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.15);
  color: #bfdbfe;
}
.tab-caption {
  font-size: 0.8rem;
  color: #9ca3af;
  margin-bottom: 0.75rem;
}
.sidebar-info {
  font-size: 0.85rem;
  color: #9ca3af;
}
.sidebar-info p {
  margin: 0 0 0.4rem;
}
.main-section {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  font-size: 0.95rem;
}
.section-title {
  font-size: 1.15rem;
  font-weight: 500;
}
.section-text {
  font-size: 0.95rem;
  color: #9ca3af;
}
</style>