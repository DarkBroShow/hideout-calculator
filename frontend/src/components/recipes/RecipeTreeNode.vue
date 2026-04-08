<script setup>
import { ref } from "vue";

const props = defineProps({
  node: {
    type: Object,
    required: true,
  },
});

const collapsed = ref(false);

function toggle() {
  collapsed.value = !collapsed.value;
}
</script>

<template>
  <div class="node">
    <div class="node-header">
      <button
        v-if="node.recipes && node.recipes.length"
        class="toggle"
        type="button"
        @click="toggle"
      >
        {{ collapsed ? "+" : "−" }}
      </button>
      <span class="item-name">
        {{ node.item?.name_ru || node.item?.id || node.itemId }}
      </span>
      <span v-if="node.item?.id" class="item-id">({{ node.item.id }})</span>
    </div>

    <div v-if="node.cycle" class="badge badge-cycle">Цикл в рецептах</div>
    <div v-if="node.truncated" class="badge badge-truncated">
      Дерево обрезано по глубине
    </div>

    <div
      v-if="node.recipes && node.recipes.length && !collapsed"
      class="recipes"
    >
      <div
        v-for="recipe in node.recipes"
        :key="recipe.id"
        class="recipe-block"
      >
        <div class="recipe-meta">
          <span>Рецепт #{{ recipe.id }}</span>
          <span v-if="recipe.bench"> · Верстак: {{ recipe.bench }}</span>
          <span v-if="recipe.energy"> · Энергия: {{ recipe.energy }}</span>
          <span v-if="recipe.perk_id">
            · Перк: {{ recipe.perk_id }} ({{ recipe.perk_level }})
          </span>
          <span> · Выход: {{ recipe.result_amount }}</span>
        </div>

        <ul class="ingredients">
          <li v-for="ing in recipe.ingredients" :key="ing.itemId">
            <span class="amount">{{ ing.amount }} × </span>
            <RecipeTreeNode
              v-if="ing.node"
              :node="ing.node"
              class="child"
            />
            <span v-else>{{ ing.itemId }}</span>
          </li>
        </ul>
      </div>
    </div>

    <div v-else-if="!node.recipes || !node.recipes.length" class="leaf-info">
      Базовый ресурс (рецепты не найдены).
    </div>
  </div>
</template>

<style scoped>
.node {
  margin-left: 0.75rem;
  border-left: 1px solid #1f2937;
  padding-left: 0.5rem;
  margin-top: 0.25rem;
}
.toggle {
  border: 1px solid #4b5563;
  background: #020617;
  color: #e5e7eb;
}
.item-id {
  color: #9ca3af;
}
.recipe-meta {
  font-size: 0.8rem;
  color: #9ca3af;
}
.leaf-info {
  font-size: 0.8rem;
  color: #6b7280;
}
.badge-cycle {
  background: rgba(239, 68, 68, 0.15);
  color: #fecaca;
}
.badge-truncated {
  background: rgba(56, 189, 248, 0.12);
  color: #bae6fd;
}
</style>