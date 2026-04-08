<script setup>
import { computed, toRef, watch, ref } from "vue";
import { VueFlow } from "@vue-flow/core";
import { Background } from "@vue-flow/background";
import { Controls } from "@vue-flow/controls";

import "@vue-flow/core/dist/style.css";
import "@vue-flow/core/dist/theme-default.css";
import "@vue-flow/controls/dist/style.css";

import { useRecipeTree } from "../../composables/useRecipeTree";
import FlowRecipeNode from "./FlowRecipeNode.vue";

const props = defineProps({
  item: {
    type: Object,
    default: null,
  },
});

const { tree, loading, error } = useRecipeTree(toRef(props, "item"));

const nodes = ref([]);
const edges = ref([]);

const nodeTypes = {
  recipeNode: FlowRecipeNode,
};

function buildGraphFromTree(root) {
  const n = [];
  const e = [];
  const amountsByNode = {}; // nodeId -> суммарное количество "входа" (для отображения)

  if (!root || !root.item) return { nodes: n, edges: e };

  const rootId = root.item.id || root.itemId || "root";

  const queue = [{ node: root, id: rootId, depth: 0 }];
  const seen = new Set();

  while (queue.length) {
    const { node, id, depth } = queue.shift();
    if (seen.has(id)) continue;
    seen.add(id);

    // инициализация, если ещё не было
    if (!(id in amountsByNode)) {
      amountsByNode[id] = 0;
    }

    n.push({
      id,
      type: "recipeNode",
      position: { x: depth * 260, y: depth * 40 },
      data: {
        item: node.item || { id },
        amountInput: amountsByNode[id] || 0,
        price: null,
      },
    });

    if (node.recipes && node.recipes.length) {
      for (const recipe of node.recipes) {
        for (const ing of recipe.ingredients || []) {
          const childId = ing.node?.item?.id || ing.itemId;
          if (!childId) continue;

          // считаем, сколько этого ингредиента идёт в текущий узел
          if (!(childId in amountsByNode)) {
            amountsByNode[childId] = 0;
          }
          amountsByNode[childId] += ing.amount;

          e.push({
            id: `${childId}->${id}`,
            source: childId,
            target: id,
            data: {
              amount: ing.amount,
            },
          });

          queue.push({
            node: ing.node,
            id: childId,
            depth: depth + 1,
          });
        }
      }
    }
  }

  // обновляем data.amountInput в уже созданных нодах
  for (const node of n) {
    node.data.amountInput = amountsByNode[node.id] || 0;
  }

  return { nodes: n, edges: e };
}

watch(
  () => tree.value,
  (val) => {
    const { nodes: n, edges: e } = buildGraphFromTree(val);
    nodes.value = n;
    edges.value = e;
  },
  { immediate: true }
);

function onSwitchRecipe(nodeId) {
  // TODO: переключение рецептов для ноды (когда будет несколько рецептов на один item)
  console.log("switch recipe for", nodeId);
}

function onCalcAuction(nodeId) {
  // TODO: расчёт аукциона для всей ветки, не только выбранной ноды
  console.log("calc auction from", nodeId);
}

const hasTree = computed(() => !!tree.value);
</script>

<template>
  <section>
    <h2 class="title">Рецепт и дерево крафта</h2>

    <div v-if="!item" class="placeholder">
      Выберите предмет во вкладке «Рецепты», чтобы построить дерево.
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
      <div v-else-if="hasTree" class="graph-wrapper">
        <VueFlow
          v-model:nodes="nodes"
          v-model:edges="edges"
          :nodes-draggable="true"
          :nodes-connectable="false"
          :zoom-on-scroll="true"
          :pan-on-drag="true"
          :fit-view="true"
          :min-zoom="0.2"
          :max-zoom="2"
          :node-types="nodeTypes"
        >
          <Background variant="dots" :gap="24" :size="1" />
          <Controls />
          <MiniMap />

          <!-- слушаем события из кастомной ноды -->
          <template #node-recipeNode="ctx">
            <FlowRecipeNode
              v-bind="ctx"
              @switch-recipe="onSwitchRecipe"
              @calc-auction="onCalcAuction"
            />
          </template>
        </VueFlow>
      </div>
      <div v-else class="status">
        Рецепты для этого предмета не найдены.
      </div>
    </div>
  </section>
</template>

<style scoped>
.title {
  font-size: 1.3rem;
  font-weight: 400;
  margin-bottom: 1rem;
  font-family: "RodondoRUS", sans-serif;
}
.placeholder {
  font-size: 0.95rem;
  color: #9ca3af;
}
.item-header {
  margin-bottom: 0.75rem;
}
.name {
  font-size: 1.05rem;
  font-weight: 700;
  color: #e5e7eb;
}
.meta {
  font-size: 0.9rem;
  color: #9ca3af;
  display: flex;
  gap: 0.5rem;
}
.id {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
    "Liberation Mono", "Courier New", monospace;
}
.category {
  text-transform: lowercase;
}
.status {
  font-size: 0.95rem;
  color: #9ca3af;
}
.error {
  font-size: 0.95rem;
  color: #fecaca;
}
.graph-wrapper {
  height: 60vh; /* базово ~60% экрана */
  border-radius: 0.75rem;
  border: 1px solid #1f2937;
  background: radial-gradient(circle at top left, #020617, #020617 60%);
  overflow: hidden;
}

@media (min-height: 900px) {
  .graph-wrapper {
    height: 70vh;
  }
}

@media (max-height: 700px) {
  .graph-wrapper {
    height: 55vh;
  }
}

:deep(.vue-flow__controls) {
  background: rgba(15, 23, 42, 0.9);
  border-radius: 0.5rem;
  border: 1px solid #1f2937;
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.9);
}

:deep(.vue-flow__controls-button) {
  background: #020617;
  border-radius: 0.4rem;
  border: 1px solid #374151;
  color: #e5e7eb;
}

:deep(.vue-flow__controls-button:hover) {
  background: #1f2937;
}

:deep(.vue-flow__controls-button svg) {
  fill: #e5e7eb;
}

</style>