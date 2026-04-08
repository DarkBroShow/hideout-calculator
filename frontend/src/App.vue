<!-- src/App.vue -->
<script setup>
import { ref, computed } from "vue";

const query = ref("");
const items = ref([]);
const loading = ref(false);
const error = ref("");

const selectedItem = ref(null);
const recipeTree = ref(null);
const treeLoading = ref(false);
const treeError = ref("");

async function search() {
  const q = query.value.trim();
  if (!q) {
    items.value = [];
    selectedItem.value = null;
    recipeTree.value = null;
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    const res = await fetch(`/api/items/search?q=${encodeURIComponent(q)}`);
    if (!res.ok) throw new Error("HTTP " + res.status);
    items.value = await res.json();
    selectedItem.value = null;
    recipeTree.value = null;
  } catch (e) {
    console.error(e);
    error.value = "Ошибка загрузки списка предметов";
  } finally {
    loading.value = false;
  }
}

async function loadTree(item) {
  selectedItem.value = item;
  recipeTree.value = null;
  treeError.value = "";
  treeLoading.value = true;
  try {
    const res = await fetch(`/api/recipes/${encodeURIComponent(item.id)}/tree`);
    if (!res.ok) throw new Error("HTTP " + res.status);
    recipeTree.value = await res.json();
  } catch (e) {
    console.error(e);
    treeError.value = "Ошибка загрузки дерева рецепта";
  } finally {
    treeLoading.value = false;
  }
}

const hasResults = computed(() => items.value && items.value.length > 0);
</script>

<template>
  <main class="page">
    <h1>Hideout Calculator — поиск предметов</h1>

    <form @submit.prevent="search" class="search">
      <input
        v-model="query"
        type="text"
        placeholder="Введите название предмета (например, Рыбное филе)"
      />
      <button type="submit">Искать</button>
    </form>

    <div v-if="loading">Загрузка...</div>
    <div v-else-if="error" class="error">{{ error }}</div>

    <div v-else>
      <ul v-if="hasResults" class="items">
        <li
          v-for="item in items"
          :key="item.id"
          :class="{ active: selectedItem && selectedItem.id === item.id }"
          @click="loadTree(item)"
        >
          <strong>{{ item.name_ru }}</strong>
          <span> ({{ item.id }})</span>
          <span v-if="item.category"> — {{ item.category }}</span>
        </li>
      </ul>

      <p v-else>Ничего не найдено. Попробуйте другой запрос.</p>

      <section v-if="selectedItem" class="tree">
        <h2>Крафт для: {{ selectedItem.name_ru }} ({{ selectedItem.id }})</h2>
        <div v-if="treeLoading">Загрузка дерева рецепта...</div>
        <div v-else-if="treeError" class="error">{{ treeError }}</div>
        <div v-else-if="recipeTree">
          <RecipeNode :node="recipeTree" />
        </div>
        <div v-else>
          <p>Рецептов не найдено.</p>
        </div>
      </section>
    </div>
  </main>
</template>

<script>
export default {
  components: {
    RecipeNode: {
      name: "RecipeNode",
      props: {
        node: {
          type: Object,
          required: true,
        },
      },
      template: `
        <div class="recipe-node">
          <div class="item-header">
            <strong>{{ node.item?.name_ru || node.item?.id || node.itemId }}</strong>
            <span v-if="node.item?.id && node.item?.id !== node.item?.name_ru">
              ({{ node.item.id }})
            </span>
          </div>

          <div v-if="node.recipes && node.recipes.length">
            <div
              v-for="recipe in node.recipes"
              :key="recipe.id"
              class="recipe-block"
            >
              <div class="recipe-meta">
                <span>Рецепт #{{ recipe.id }}</span>
                <span v-if="recipe.bench"> | Верстак: {{ recipe.bench }}</span>
                <span v-if="recipe.energy"> | Энергия: {{ recipe.energy }}</span>
                <span v-if="recipe.perk_id">
                  | Перк: {{ recipe.perk_id }} ({{ recipe.perk_level }})
                </span>
                <span> | Выход: {{ recipe.result_amount }}</span>
              </div>
              <ul class="ingredients">
                <li v-for="ing in recipe.ingredients" :key="ing.itemId">
                  <span>{{ ing.amount }} × </span>
                  <RecipeNode v-if="ing.node" :node="ing.node" />
                  <span v-else>{{ ing.itemId }}</span>
                </li>
              </ul>
            </div>
          </div>

          <div v-else class="no-recipes">
            Нет рецептов (базовый ресурс или ограничение глубины).
          </div>

          <div v-if="node.truncated" class="truncated">
            Дерево обрезано по глубине.
          </div>
          <div v-if="node.cycle" class="cycle">
            Обнаружен цикл в рецептах.
          </div>
        </div>
      `,
    },
  },
};
</script>

<style scoped>
.page {
  max-width: 960px;
  margin: 0 auto;
  padding: 2rem;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.search {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.search input {
  flex: 1;
  padding: 0.4rem 0.6rem;
}
.search button {
  padding: 0.4rem 0.8rem;
}
.error {
  color: #c00;
}
.items {
  list-style: none;
  padding: 0;
}
.items li {
  padding: 4px 0;
  border-bottom: 1px solid #eee;
  cursor: pointer;
}
.items li.active {
  background: #f0f6ff;
}
.tree {
  margin-top: 2rem;
}
.recipe-node {
  margin-left: 1rem;
  border-left: 2px solid #ddd;
  padding-left: 0.5rem;
}
.item-header {
  font-weight: 600;
  margin: 0.25rem 0;
}
.recipe-block {
  margin: 0.25rem 0 0.5rem;
}
.recipe-meta {
  font-size: 0.85rem;
  color: #555;
}
.ingredients {
  list-style: none;
  padding-left: 0.5rem;
}
.ingredients li {
  margin: 0.1rem 0;
}
.no-recipes,
.truncated,
.cycle {
  font-size: 0.85rem;
  color: #666;
}
.cycle {
  color: #a00;
}
</style>