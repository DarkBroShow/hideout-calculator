<script setup>
import { computed, toRef } from "vue";
import RecipeTreeNode from "./RecipeTreeNode.vue";
import { useRecipeTree } from "../../composables/useRecipeTree";

const props = defineProps({
  item: {
    type: Object,
    default: null,
  },
});

const { tree, loading, error } = useRecipeTree(toRef(props, "item"));

const hasTree = computed(() => !!tree.value);
</script>

<template>
  <section>
    <h2 class="title">Рецепт и дерево крафта</h2>

    <div v-if="!item" class="placeholder">
      Выберите предмет слева, чтобы посмотреть рецепты.
    </div>

    <div v-else>
      <div class="item-header">
        <div class="name">{{ item.name_ru }}</div>
        <div class="meta">
          <span class="id">{{ item.id }}</span>
          <span v-if="item.category" class="category">{{ item.category }}</span>
        </div>
      </div>

      <div v-if="loading" class="status">Загрузка дерева рецепта...</div>
      <div v-else-if="error" class="error">{{ error }}</div>
      <div v-else-if="hasTree">
        <RecipeTreeNode :node="tree" />
      </div>
      <div v-else class="status">
        Рецепты для этого предмета не найдены.
      </div>
    </div>
  </section>
</template>

<style scoped>
.title {
  font-size: 1.2rem;
  font-weight: 400;
  margin-bottom: 0.75rem;
  font-family: "RodondoRUS", sans-serif;
}
.placeholder {
  font-size: 0.95rem;
  color: #6b7280;
}
.item-header {
  margin-bottom: 0.5rem;
}
.name {
  font-size: 1.05rem;
  font-weight: 600;
  color: #e5e7eb;
}
.meta {
  font-size: 0.8rem;
  color: #9ca3af;
  display: flex;
  gap: 0.5rem;
}
.status {
  font-size: 0.9rem;
  color: #9ca3af;
}
.error {
  font-size: 0.9rem;
  color: #fecaca;
}
</style>