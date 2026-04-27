<script setup>
import PageLayout from "./components/layout/PageLayout.vue";
import ItemSearch from "./components/search/ItemSearch.vue";
import RecipeGraph from "./components/recipes/RecipeGraph.vue";
import MaterialEditor from "./components/materials/MaterialEditor.vue";
import RecipeSummary from "./components/recipes/RecipeSummary.vue";
import { useRecipeCost } from "./composables/useRecipeCost";
import { ref, computed } from "vue";
import logoUrl from "./assets/icons/logo_main.png";

const selectedItem = ref(null);
const activeTab = ref("current-tree");
const craftAmount = ref(1);

const { costData, loading: costLoading } = useRecipeCost(selectedItem, craftAmount);

function handleItemSelected(item) {
  selectedItem.value = item;
  activeTab.value = "current-tree";
}

const tabs = [
  { id: "profile", label: "Профиль" },
  { id: "hideout", label: "Убежище" },
  { id: "directory", label: "Справочник" },
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
       <img :src="logoUrl" alt="logo" class="logo-img" />
        <h1 class="title">Калькулятор убежки</h1>
      </div>
    </template>

    <template #sidebar-top>
      <div class="project-badge">
        <span class="name">Hideout Calculator</span>
        <span class="tag">alpha</span>
      </div>
      <div class="tab-caption">
        {{ activeTabLabel }}
      </div>
    </template>

    <template #sidebar-content>
      <div v-if="activeTab === 'directory'" class="sidebar-info">
        <p>
           Здесь появится поиск рецептов по предметам. Введите название
          для просмотра дерева ингредиентов.
        </p>
      </div>

      <div v-else-if="activeTab === 'profile'" class="sidebar-info">
        <p>Здесь появятся настройки профиля и авторизация.</p>
      </div>

      <div v-else-if="activeTab === 'hideout'" class="sidebar-info">
        <p>Здесь будет ввод уровней убежища и доступных модулей.</p>
      </div>

      <div v-else-if="activeTab === 'current-tree'" class="sidebar-info">
         <RecipeSummary :cost-data="costData" :loading="costLoading" />
      </div>
    </template>

   <template #main>
      <section v-if="activeTab === 'directory'" class="main-section">
        <h2 class="section-title">Справочник</h2>
        <p class="section-text">
          Здесь появится поиск рецептов по предметам. Введите название
          для просмотра дерева ингредиентов.
        </p>
      </section>

      <section v-else-if="activeTab === 'current-tree'" class="main-section">
        <ItemSearch @select="handleItemSelected" />
        <RecipeGraph :item="selectedItem" />
        <div class="materials-fold">
          <MaterialEditor :item="selectedItem" />
        </div>
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
  gap: 0.65rem;
}
.logo-img {
  width: 44px;
  height: 44px;
  object-fit: contain;
  border-radius: 0.5rem;
  flex-shrink: 0;
}
.title {
  font-size: 1.25rem;
  font-weight: 400;
  color: #e5e7eb;
  font-family: "RodondoRUS", sans-serif;
  line-height: 1.1;
  margin: 0;
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
  font-size: 0.85rem;
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
  padding: 0.1rem 0.35rem;
  border-radius: 999px;
  background: rgba(220, 38, 38, 0.18);
  color: #fca5a5;
  font-weight: 700;
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
.sidebar-info p { margin: 0 0 0.4rem; }
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
.materials-fold {
  margin-top: 4rem;
  padding-top: 1.5rem;
  border-top: 1px dashed rgba(148, 163, 184, 0.25);
}
</style>