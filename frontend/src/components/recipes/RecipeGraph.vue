<script setup>
import { ref, computed, toRef, watch, reactive } from "vue";
import { VueFlow, useVueFlow, MarkerType } from "@vue-flow/core";
import { Background } from "@vue-flow/background";
import { Controls } from "@vue-flow/controls";
import dagre from "dagre";

import "@vue-flow/core/dist/style.css";
import "@vue-flow/core/dist/theme-default.css";
import "@vue-flow/controls/dist/style.css";

import { useRecipeTree } from "../../composables/useRecipeTree";
import { useRecipeCost } from "../../composables/useRecipeCost";
import FlowRecipeNode from "./FlowRecipeNode.vue";

const props = defineProps({
item: { type: Object, default: null },
});

const craftAmount = ref(1);

const { tree, loading, error } = useRecipeTree(toRef(props, "item"));

// Карта item_id -> recipe_id, выбранный пользователем.
// Передаётся в useRecipeCost, чтобы бэкенд считал по фиксированным рецептам.
const recipeChoicesByItem = ref({});

const { costData, loading: costLoading } = useRecipeCost(
  toRef(props, "item"),
  craftAmount,
  recipeChoicesByItem,
);

// Рекурсивно ищем NodeCost в дереве цен — по item_id.
// Используется для подмешивания цен в данные ноды при рендере.
function enrichNodeWithCost(itemId, costTree) {
  if (!costTree) return {};
  function find(node) {
    if (!node) return null;
    if (node.item_id === itemId) return node;
    for (const child of node.components || []) {
      const found = find(child);
      if (found) return found;
    }
    return null;
  }
  return find(costTree) || {};
}

const nodes = ref([]);
const edges = ref([]);

const nodeTypes = { recipeNode: FlowRecipeNode };

// nodeId -> массив дочерних nodeId (для группового drag)
const treeMap = new Map();
// nodeId -> { item_id, recipe_id выбранный } — нужно чтобы из ноды UI поднять выбор
const nodeMeta = new Map();

// Сохранённые пользовательские позиции.
// Ключ = nodeId. Сбрасывается только при загрузке нового дерева.
const userPositions = new Map();

const NODE_WIDTH = 210;
const NODE_HEIGHT = 280;
// Поиск исходной TreeNode по item_id — используется при смене рецепта.
function findTreeNodeByItemId(root, itemId) {
  if (!root) return null;
  const rootId = root.item?.id || root.itemId;
  if (rootId === itemId) return root;

  if (!root.recipes) return null;

  for (const recipe of root.recipes) {
    for (const ing of recipe.ingredients || []) {
      const childNode = ing.node;
      if (!childNode) continue;
      const found = findTreeNodeByItemId(childNode, itemId);
      if (found) return found;
    }
  }
  return null;
}

// Возвращает индекс активного рецепта по item_id (с учётом recipeChoicesByItem).
function getActiveRecipeIndex(node) {
  const itemId = node.item?.id || node.itemId;
  const recipes = node.recipes || [];
  if (!recipes.length) return -1;
  const chosenId = recipeChoicesByItem.value[itemId];
  if (chosenId != null) {
    const idx = recipes.findIndex((r) => r.id === chosenId);
    if (idx >= 0) return idx;
  }
  return 0;
}

// Строим НАСТОЯЩЕЕ дерево (без дедупликации).
// nodeId формируется из path, чтобы одно вхождение != другому.
function buildGraphFromTree(root) {
  const resultNodes = [];
  const resultEdges = [];
  treeMap.clear();
  nodeMeta.clear();

  if (!root || !root.item) return { nodes: resultNodes, edges: resultEdges };

  function makeNodeObj(node, nodeId, amountNeeded) {
    const itemId = node.item?.id || node.itemId;
    const recipes = node.recipes || [];
    const recipesCount = recipes.length;
    const activeIdx = Math.max(0, getActiveRecipeIndex(node));
    const costNode = enrichNodeWithCost(itemId, costData.value?.tree);

    const recipeVariants = recipes.map((r, idx) => {
      const firstIng = (r.ingredients || [])[0];
      const vItem = firstIng?.node?.item || null;

      return {
        index: idx,
        recipeId: r.id,
        item: vItem
          ? { id: vItem.id, name_ru: vItem.name_ru, icon_path: vItem.icon_path }
          : null,
      };
    });
    nodeMeta.set(nodeId, { itemId, recipes });

    return {
      id: nodeId,
      type: "recipeNode",
      position: { x: 0, y: 0 },
      data: {
        item: node.item || { id: itemId },
        amountInput: amountNeeded,
        recipesCount,
        activeRecipeIndex: activeIdx,
        recipeVariants,
        buyPrice: costNode.auction_price,
        craftPrice: costNode.craft_cost,
        decision: costNode.decision,
      },
    };
  }

  // DFS-обход с уникальным nodeId по path. dedup тут НЕ нужен —
  // дерево намеренно дублирует общие компоненты, иначе не структурировано.
  // amountNeeded — сколько штук этого предмета нужно для родителя
  // (для корня = 1, для ингредиента = ing.amount).
  function walk(node, nodeId, amountNeeded) {
    const obj = makeNodeObj(node, nodeId, amountNeeded);
    resultNodes.push(obj);

    const itemId = node.item?.id || node.itemId;
    const recipes = node.recipes || [];
    const activeIdx = getActiveRecipeIndex(node);
    const recipe = activeIdx >= 0 ? recipes[activeIdx] : null;
    const childIds = [];

    if (recipe) {
      const ingredients = recipe.ingredients || [];
      ingredients.forEach((ing, i) => {
        const childNode = ing.node;
        const childItemId = childNode?.item?.id || ing.itemId;
        if (!childItemId || !childNode) return;

        const childNodeId = `${nodeId}/${i}:${childItemId}`;
        childIds.push(childNodeId);

        // Цвет/толщина edge зависят от decision дочерней ноды:
        // craft = зелёный путь, buy = синий, no_data = серый.
        const childCost = enrichNodeWithCost(childItemId, costData.value?.tree);
        const decision = childCost.decision || "unknown";
        const stroke =
          decision === "craft" ? "#22c55e"
          : decision === "buy" ? "#3b82f6"
          : "#6b7280";
        resultEdges.push({
          id: `${childNodeId}->${nodeId}`,
          source: childNodeId,
          target: nodeId,
          type: "smoothstep",
          animated: false,
          markerEnd: { type: MarkerType.ArrowClosed, color: stroke, width: 18, height: 18 },
          style: { stroke, strokeWidth: 2.5 },
        });

        walk(childNode, childNodeId, ing.amount);
      });
    }

    treeMap.set(nodeId, { childrenIds: childIds });
  }

  const rootId = `0:${root.item.id || root.itemId || "root"}`;
  walk(root, rootId, 1);

  // ---- dagre layout (BT — снизу вверх, как в EMI) ----
  const g = new dagre.graphlib.Graph();
  g.setGraph({
    rankdir: "BT",
    nodesep: 50,
    ranksep: 110,
    marginx: 40,
    marginy: 40,
    ranker: "tight-tree",
  });
  g.setDefaultEdgeLabel(() => ({}));

  for (const n of resultNodes) {
    g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  }
  for (const e of resultEdges) {
    g.setEdge(e.source, e.target);
  }

  dagre.layout(g);

  for (const n of resultNodes) {
    const dn = g.node(n.id);
    if (dn) {
      n.position = { x: dn.x - NODE_WIDTH / 2, y: dn.y - NODE_HEIGHT / 2 };
    }
    const userPos = userPositions.get(n.id);
    if (userPos) n.position = { x: userPos.x, y: userPos.y };
  }

  return { nodes: resultNodes, edges: resultEdges };
}

// Полный сброс при смене дерева (новый предмет).
watch(
  () => tree.value,
  (val) => {
    recipeChoicesByItem.value = {};
    userPositions.clear();
    const { nodes: n, edges: e } = buildGraphFromTree(val);
    nodes.value = n;
    edges.value = e;
  },
  { immediate: true }
);

// Перерисовка при обновлении цен (без сброса позиций и выбора).
watch(
  () => costData.value,
  () => {
    if (!tree.value) return;
    const { nodes: n, edges: e } = buildGraphFromTree(tree.value);
    nodes.value = n;
    edges.value = e;
  }
);
function rebuildPreservingPositions() {
  const { nodes: n, edges: e } = buildGraphFromTree(tree.value);
  nodes.value = n;
  edges.value = e;
}

// Смена рецепта в UI: запоминаем recipe_id для item_id и перестраиваем граф.
// useRecipeCost увидит изменение recipeChoicesByItem и перезапросит цены.
function onSwitchRecipe(payload) {
  if (!tree.value) return;
  const { nodeId, recipeIndex } = payload;
  const meta = nodeMeta.get(nodeId);
  if (!meta) return;

  const recipes = meta.recipes || [];
  const idx = Math.min(Math.max(recipeIndex, 0), recipes.length - 1);
  const chosen = recipes[idx];
  if (!chosen) return;

  recipeChoicesByItem.value = {
    ...recipeChoicesByItem.value,
    [meta.itemId]: chosen.id,
  };

  rebuildPreservingPositions();
}

// Кнопка пересчёта аукциона: дёргаем reload бэкенда (force_refresh пока нет).
// Просто триггерим watch costData → перерисовка. Цена обновится из ответа бэка.
function onCalcAuction(_nodeId) {
  // no-op для текущей итерации — реальный refresh цен делает useRecipeCost.
}

const hasTree = computed(() => !!tree.value);

// -------- групповой drag --------
const { onNodeDragStart, onNodeDrag, onNodeDragStop, updateNode } = useVueFlow();

const dragState = reactive({
  rootId: null,
  startPositions: new Map(),
  moved: false,
});

const DRAG_THRESHOLD_PX = 2;

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
  dragState.moved = false;
  dragState.startPositions.clear();

  collectSubtreeIds(node.id).forEach((id) => {
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

  // защита от "клик двигает детей": реальный drag только при заметном смещении
  if (!dragState.moved && Math.abs(dx) < DRAG_THRESHOLD_PX && Math.abs(dy) < DRAG_THRESHOLD_PX) {
    return;
  }
  dragState.moved = true;

  dragState.startPositions.forEach((pos, id) => {
    if (id === dragState.rootId) return;
     updateNode(id, { position: { x: pos.x + dx, y: pos.y + dy } });
  });
});

onNodeDragStop(({ node }) => {
  if (!dragState.rootId) return;
  if (dragState.moved) {
    const rootStart = dragState.startPositions.get(dragState.rootId);
    const dx = node.position.x - rootStart.x;
    const dy = node.position.y - rootStart.y;

    dragState.startPositions.forEach((pos, id) => {
      const finalX = pos.x + dx;
      const finalY = pos.y + dy;
      userPositions.set(id, { x: finalX, y: finalY });

      const n = nodes.value.find((n) => n.id === id);
      if (n) n.position = { x: finalX, y: finalY };
    });
  }

  dragState.rootId = null;
  dragState.moved = false;
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
.placeholder { font-size: 0.95rem; color: #9ca3af; }
.item-header { margin-bottom: 0.75rem; }
.name { font-size: 1.05rem; font-weight: 700; color: #e5e7eb; }
.meta { font-size: 0.9rem; color: #9ca3af; display: flex; gap: 0.5rem; }
.id {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
    "Liberation Mono", "Courier New", monospace;
}
.category { text-transform: lowercase; }
.status { font-size: 0.95rem; color: #9ca3af; }
.error { font-size: 0.95rem; color: #fecaca; }

.graph-area {
  display: flex;
  gap: 0;
  height: calc(100vh - 240px);
  min-height: 480px;
  border-radius: 0.75rem;
  border: 1px solid #1f2937;
  overflow: hidden;
}
.graph-wrapper {
  flex: 1;
  min-width: 0;
  height: 100%;
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

:deep(.vue-flow__controls-button:hover) { background: #1f2937; }
:deep(.vue-flow__controls-button svg) { fill: #e5e7eb; }

:deep(.vue-flow__edge-text) { fill: #e5e7eb; font-size: 12px; font-weight: 700; }
:deep(.vue-flow__edge-textbg) { fill: #020617; }
:deep(.vue-flow__edge-path) { stroke-linecap: round; }
</style>