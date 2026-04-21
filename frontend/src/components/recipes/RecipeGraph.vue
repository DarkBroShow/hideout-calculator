<script setup>
import { ref, computed, toRef, watch, reactive } from "vue";
import { VueFlow, useVueFlow } from "@vue-flow/core";
import { Background } from "@vue-flow/background";
import { Controls } from "@vue-flow/controls";

import "@vue-flow/core/dist/style.css";
import "@vue-flow/core/dist/theme-default.css";
import "@vue-flow/controls/dist/style.css";

import { useRecipeTree } from "../../composables/useRecipeTree";
import { useRecipeCost } from "../../composables/useRecipeCost";
import FlowRecipeNode from "./FlowRecipeNode.vue";
import RecipeSummary from "./RecipeSummary.vue";

const props = defineProps({
  item: {
    type: Object,
    default: null,
  },
});

// Количество для расчёта
const craftAmount = ref(1);

// Загрузка стоимости
const { costData, loading: costLoading, error: costError, reload: reloadCost } =
  useRecipeCost(toRef(props, "item"), craftAmount);

// Обогащаем узлы данными о ценах из costData
function enrichNodeWithCost(nodeId, costTree) {
  if (!costTree) return {};
  // Рекурсивно ищем узел по item_id
  function find(node) {
    if (!node) return null;
    if (node.item_id === nodeId) return node;
    for (const child of node.components || []) {
      const found = find(child);
      if (found) return found;
    }
    return null;
  }
  return find(costTree) || {};
}


const { tree, loading, error } = useRecipeTree(toRef(props, "item"));

const nodes = ref([]);
const edges = ref([]);

const nodeTypes = {
  recipeNode: FlowRecipeNode,
};

// карта родитель -> массив дочерних id (для группового драга)
const treeMap = new Map(); // id -> { childrenIds: string[] }

// для каждого itemId храним индекс активного рецепта
const activeRecipeIndexByItem = ref({});

// для каждого itemId храним цену (когда посчитана)
const priceByItemId = ref({});

// ---- утилиты поиска узла в исходном дереве по itemId ----
function findTreeNodeByItemId(root, itemId) {
  if (!root) return null;
  const rootId = root.item?.id || root.itemId;
  if (rootId === itemId) return root;

  if (!root.recipes) return null;

  for (const recipe of root.recipes) {
    for (const ing of recipe.ingredients || []) {
      const childNode = ing.node;
      const childId = childNode?.item?.id || ing.itemId;
      if (!childNode || !childId) continue;
      const found = findTreeNodeByItemId(childNode, itemId);
      if (found) return found;
    }
  }

  return null;
}

// ---- построение графа с учётом активных рецептов ----
function buildGraphFromTree(root) {
  const resultNodes = [];
  const resultEdges = [];
  treeMap.clear();

  if (!root || !root.item) return { nodes: resultNodes, edges: resultEdges };

  const rootId = root.item.id || root.itemId || "root";

  const H_GAP = 260;
  const V_GAP = 380;

  function getActiveRecipe(node) {
    const recipes = node.recipes || [];
    if (!recipes.length) return null;
    const itemId = node.item?.id || node.itemId;
    const currentIndex = activeRecipeIndexByItem.value[itemId] ?? 0;
    return recipes[currentIndex] || recipes[0];
  }

  function getChildren(node) {
    const list = [];
    const recipe = getActiveRecipe(node);
    if (!recipe) return list;

    for (const ing of recipe.ingredients || []) {
      const childNode = ing.node;
      const childId = childNode?.item?.id || ing.itemId;
      if (!childId || !childNode) continue;

      list.push({
        id: childId,
        node: childNode,
        amount: ing.amount,
      });
    }

    return list;
  }

  function layout(node, id, depth, index, siblingsCount, parentX = 0) {
    let x;
    if (siblingsCount <= 1) {
      x = parentX;
    } else {
      const totalWidth = (siblingsCount - 1) * H_GAP;
      const startX = parentX - totalWidth / 2;
      x = startX + index * H_GAP;
    }

    const y = depth * V_GAP;

    const itemId = node.item?.id || id;
    const recipes = node.recipes || [];
    const recipesCount = recipes.length;
    const activeIdx = activeRecipeIndexByItem.value[itemId] ?? 0;
    const price = priceByItemId.value[itemId];
    const priceLabel =
      typeof price === "number"
        ? `${price.toLocaleString("ru-RU")} ₽`
        : "---";
    const costNode = enrichNodeWithCost(itemId, costData.value?.tree);
    // варианты для визуального выбора (иконка + имя)
    const recipeVariants = recipes.map((r, idx) => {
      const firstIng = (r.ingredients || [])[0];
      const vNode = firstIng?.node;
      const vItem = vNode?.item || null;

      return {
        index: idx,
        item: vItem
          ? {
              id: vItem.id,
              name_ru: vItem.name_ru,
              icon_path: vItem.icon_path,
            }
          : null,
      };
    });

    resultNodes.push({
      id,
      type: "recipeNode",
      position: { x, y },
      data: {
        item: node.item || { id },
        amountInput: 0,
        price,
        priceLabel,
        recipesCount,
        activeRecipeIndex: activeIdx,
        recipeVariants,
        buyPrice: costNode.auction_price,
        craftPrice: costNode.craft_cost,
        decision: costNode.decision,
      },
    });

    const children = getChildren(node);

    treeMap.set(id, {
      childrenIds: children.map((c) => c.id),
    });

    children.forEach((child, i) => {
      resultEdges.push({
        id: `${child.id}->${id}`,
        source: child.id,
        target: id,
        data: {
          amount: child.amount,
        },
      });

      layout(child.node, child.id, depth + 1, i, children.length, x);
    });
  }

  layout(root, rootId, 0, 0, 1, 0);

  return { nodes: resultNodes, edges: resultEdges };
}

// инициализация графа по дереву
watch(
  () => tree.value,
  (val) => {
    activeRecipeIndexByItem.value = {};
    priceByItemId.value = {};
    const { nodes: n, edges: e } = buildGraphFromTree(val);
    nodes.value = n;
    edges.value = e;
  },
  { immediate: true }
);

// переключение рецепта для конкретной ноды (через визуальный выбор)
function onSwitchRecipe(payload) {
  if (!tree.value) return;

  const { nodeId, recipeIndex } = payload;
  const node = nodes.value.find((n) => n.id === nodeId);
  if (!node) return;

  const itemId = node.data.item?.id || nodeId;

  const treeNode = findTreeNodeByItemId(tree.value, itemId);
  if (!treeNode || !treeNode.recipes || !treeNode.recipes.length) return;

  const recipes = treeNode.recipes;
  const idx = Math.min(Math.max(recipeIndex, 0), recipes.length - 1);
  activeRecipeIndexByItem.value[itemId] = idx;

  const { nodes: n, edges: e } = buildGraphFromTree(tree.value);
  nodes.value = n;
  edges.value = e;
}

// расчёт аукциона (пока заглушка с записью фиктивной цены)
function onCalcAuction(nodeId) {
  if (!tree.value) return;

  const node = nodes.value.find((n) => n.id === nodeId);
  if (!node) return;

  const itemId = node.data.item?.id || nodeId;

  const randomPrice = Math.round(Math.random() * 10000) + 100;
  priceByItemId.value = {
    ...priceByItemId.value,
    [itemId]: randomPrice,
  };

  const { nodes: n, edges: e } = buildGraphFromTree(tree.value);
  nodes.value = n;
  edges.value = e;
}

const hasTree = computed(() => !!tree.value);

// -------- групповой drag --------
const { onNodeDragStart, onNodeDrag, onNodeDragStop, updateNode } = useVueFlow();

const dragState = reactive({
  rootId: null,
  startPositions: new Map(),
});

function collectSubtreeIds(rootId) {
  const ids = [];
  const stack = [rootId];
  const visited = new Set();

  while (stack.length) {
    const id = stack.pop();
    if (visited.has(id)) continue;
    visited.add(id);
    ids.push(id);

    const children = treeMap.get(id)?.childrenIds || [];
    children.forEach((c) => stack.push(c));
  }

  return ids;
}

onNodeDragStart(({ node }) => {
  dragState.rootId = node.id;
  dragState.startPositions.clear();

  const subtreeIds = collectSubtreeIds(node.id);

  subtreeIds.forEach((id) => {
    const n = nodes.value.find((n) => n.id === id);
    if (!n) return;
    dragState.startPositions.set(id, { x: n.position.x, y: n.position.y });
  });
});

onNodeDrag(({ node }) => {
  if (!dragState.rootId) return;

  const rootStart = dragState.startPositions.get(dragState.rootId);
  if (!rootStart) return;

  const dx = node.position.x - rootStart.x;
  const dy = node.position.y - rootStart.y;

  dragState.startPositions.forEach((pos, id) => {
    if (id === dragState.rootId) return;
    updateNode(id, {
      position: {
        x: pos.x + dx,
        y: pos.y + dy,
      },
      positionAbsolute: undefined,
    });
  });
});

onNodeDragStop(() => {
  dragState.rootId = null;
  dragState.startPositions.clear();
});
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
      <div v-else-if="hasTree" class="graph-area">
        <div class="graph-wrapper">
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

            <template #node-recipeNode="ctx">
              <FlowRecipeNode
                v-bind="ctx"
                @switch-recipe="onSwitchRecipe"
                @calc-auction="onCalcAuction"
              />
            </template>
          </VueFlow>
        </div>
        <RecipeSummary :cost-data="costData" :loading="costLoading" />
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

.graph-area {
  display: flex;
  gap: 0;
  height: 60vh;
  border-radius: 0.75rem;
  border: 1px solid #1f2937;
  overflow: hidden;
}
.graph-wrapper {
  flex: 1;
  min-width: 0;
  height: 100%;
  border-radius: 0; /* убрать радиус т.к. теперь в контейнере */
  border: none;
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