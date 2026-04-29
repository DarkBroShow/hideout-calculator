<script setup>
import { computed, ref, onMounted, onBeforeUnmount, nextTick } from "vue";
import { Handle, Position } from "@vue-flow/core";
import { getCategoryLabel } from "../../utils/categoryLabels";
import { getRarityColor } from "../../utils/rarityColors";

const props = defineProps({
  id: { type: String, required: true },
  data: { type: Object, required: true },
});

const emit = defineEmits([
  "switch-recipe",
  "calc-auction",
  "remove-node",
  "override-decision",
]);

// Цвет рамки по редкости.
// Сначала пробуем прямой hex из поля color, затем fallback на getRarityColor.
const rarityBorderColor = computed(() => {
  const item = props.data.item;
  if (!item) return "#4b5563";
  if (item.color && /^#[0-9a-fA-F]{3,8}$/.test(item.color)) return item.color;
  return getRarityColor(item.rarity || item.rarity_code || item.color);
});

const categoryLabel = computed(() =>
  getCategoryLabel(props.data.item?.category)
);

// Если у ноды есть result_amount (крафт производит N штук) — показываем его.
// Иначе показываем amountInput (сколько штук нужно родителю).
const amountLabel = computed(() => {
  const ra = props.data.resultAmount;
  if (ra && ra > 1) return `${ra}×`;
  const ai = props.data.amountInput;
  if (ai && ai !== 1) return `${ai}×`;
  return "1×";
});

// Подпись под числом: "выход" когда показываем result_amount, "нужно" для ингредиентов
const amountSubLabel = computed(() => {
  const ra = props.data.resultAmount;
  if (ra && ra > 1) return "выход";
  return "нужно";
});

// Активное решение: override превалирует над расчётным
const effectiveDecision = computed(
  () => props.data.decisionOverride || props.data.decision
);

const decisionLabel = computed(() => {
  const d = effectiveDecision.value;
  if (d === "buy") return "Купить";
  if (d === "craft") return "Крафтить";
  return "?";
});

const isOverridden = computed(() => !!props.data.decisionOverride);

// Клик по badge-решению: если override установлен — сбрасываем, иначе ставим обратное
function onToggleDecision() {
  let next = null;
  if (isOverridden.value) {
    next = null; // сбросить к автоматическому
  } else {
    next = props.data.decision === "buy" ? "craft" : "buy";
  }
  emit("override-decision", { nodeId: props.id, override: next });
}

// ---- popup с вариантами рецепта ----
const showRecipes = ref(false);
const containerEl = ref(null);
const recipeBtnEl = ref(null);
const popupEl = ref(null);
const popupPos = ref({ top: 0, left: 0, width: 340 });

const hasVariants = computed(
  () => props.data.recipesCount && props.data.recipesCount > 1
);
const variants = computed(() => props.data.recipeVariants || []);
const activeIdx = computed(() => props.data.activeRecipeIndex ?? 0);

const POPUP_WIDTH = 340;
const POPUP_MARGIN = 8;

function updatePopupPosition() {
  const btn = recipeBtnEl.value;
  if (!btn) return;
  const rect = btn.getBoundingClientRect();
  const vw = window.innerWidth;
  let left = rect.right - POPUP_WIDTH;
  if (left < POPUP_MARGIN) left = POPUP_MARGIN;
  if (left + POPUP_WIDTH > vw - POPUP_MARGIN) {
    left = vw - POPUP_WIDTH - POPUP_MARGIN;
  }
  popupPos.value = { top: rect.bottom + 6, left, width: POPUP_WIDTH };
}

async function toggleRecipes() {
  if (!hasVariants.value) return;
  showRecipes.value = !showRecipes.value;
  if (showRecipes.value) {
    await nextTick();
    updatePopupPosition();
  }
}

function selectRecipe(idx) {
  emit("switch-recipe", { nodeId: props.id, recipeIndex: idx });
  showRecipes.value = false;
}

function iconUrl() {
  return props.data.item?.icon_path || null;
}

function onCalcAuction() {
  emit("calc-auction", props.id);
}

function onRemove() {
  emit("remove-node", props.id);
}

function onClickOutside(e) {
  if (!showRecipes.value) return;
  if (
    !containerEl.value?.contains(e.target) &&
    !popupEl.value?.contains(e.target)
  ) {
    showRecipes.value = false;
  }
}

function onKeydown(e) {
  if (e.key === "Escape" && showRecipes.value) showRecipes.value = false;
}

function onScrollOrResize() {
  if (showRecipes.value) updatePopupPosition();
}

onMounted(() => {
  document.addEventListener("mousedown", onClickOutside);
  document.addEventListener("keydown", onKeydown);
  window.addEventListener("scroll", onScrollOrResize, true);
  window.addEventListener("resize", onScrollOrResize);
});
onBeforeUnmount(() => {
  document.removeEventListener("mousedown", onClickOutside);
  document.removeEventListener("keydown", onKeydown);
  window.removeEventListener("scroll", onScrollOrResize, true);
  window.removeEventListener("resize", onScrollOrResize);
});
</script>

<template>
  <div
    class="node"
    :class="{ selected: data.selected }"
    :style="{ borderColor: rarityBorderColor }"
    ref="containerEl"
  >
    <!-- Кнопка удаления ноды из дерева -->
    <button
      type="button"
      class="remove-btn"
      title="Убрать из дерева"
      @click.stop="onRemove"
    >✕</button>

    <!-- ВЫХОД: сверху -->
    <Handle type="source" :position="Position.Top" class="handle handle-out" />

    <div class="icon-wrapper">
      <img v-if="iconUrl()" :src="iconUrl()" alt="" class="icon" loading="lazy" />
      <div v-else class="icon-placeholder">?</div>
    </div>

    <div class="info">
      <div class="name">{{ data.item?.name_ru || data.item?.id || "?" }}</div>
      <div class="meta">
        <span class="category">{{ categoryLabel }}</span>
      </div>
    </div>

    <div class="bottom-row">
      <div class="amount-block">
        <span class="amount-label">{{ amountSubLabel }}</span>
        <span class="amount-value">{{ amountLabel }}</span>
      </div>

      <div class="actions">
        <button
          ref="recipeBtnEl"
          type="button"
          class="btn primary"
          :class="{ disabled: !hasVariants }"
          @click.stop="toggleRecipes"
        >
          Рецепт
          <span v-if="hasVariants" class="badge">{{ data.recipesCount }}</span>
        </button>

        <div class="price-block">
          <div class="price-row">
            <span class="price-label">Купить</span>
            <span class="price-val">
              {{ data.buyPrice ? data.buyPrice.toLocaleString("ru-RU") + " ₽" : "..." }}
            </span>
          </div>
          <div class="price-row">
            <span class="price-label">Крафт</span>
            <span class="price-val craft">
              {{ data.craftPrice ? data.craftPrice.toLocaleString("ru-RU") + " ₽" : "—" }}
            </span>
          </div>
          <!-- Кликабельный badge решения. Клик — переключить override. -->
          <button
            type="button"
            class="decision-badge"
            :class="[effectiveDecision === 'buy' ? 'buy' : effectiveDecision === 'craft' ? 'craft' : 'unknown', { overridden: isOverridden }]"
            :title="isOverridden ? 'Сброс к авто' : 'Зафиксировать решение'"
            @click.stop="onToggleDecision"
          >
            {{ decisionLabel }}
            <span v-if="isOverridden" class="override-dot" title="Зафиксировано вручную">●</span>
          </button>
        </div>
      </div>
    </div>

    <!-- ВХОД: снизу -->
    <Handle type="target" :position="Position.Bottom" class="handle handle-in" />
  </div>

  <!-- Поп-ап с вариантами рецепта -->
  <Teleport to="body">
    <div
      v-if="showRecipes && hasVariants"
      ref="popupEl"
      class="variants-popup"
      :style="{
        top: popupPos.top + 'px',
        left: popupPos.left + 'px',
        width: popupPos.width + 'px',
      }"
      @mousedown.stop
    >
      <div class="variants-header">Варианты рецепта ({{ variants.length }})</div>
      <div class="variants-list">
        <button
          v-for="variant in variants"
          :key="variant.index"
          type="button"
          class="variant-card"
          :class="{ active: variant.index === activeIdx }"
          @click.stop="selectRecipe(variant.index)"
        >
          <div class="variant-icon-wrapper">
            <img
              v-if="variant.item?.icon_path"
              :src="variant.item.icon_path"
              alt=""
              class="variant-icon"
              loading="lazy"
            />
            <div v-else class="variant-icon-placeholder">?</div>
          </div>
          <div class="variant-info">
            <div class="variant-name">
              {{ variant.item?.name_ru || variant.item?.id || `Ветка #${variant.index + 1}` }}
            </div>
            <div v-if="variant.item?.id" class="variant-id">{{ variant.item.id }}</div>
          </div>
          <div v-if="variant.index === activeIdx" class="active-mark">✓</div>
        </button>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.node {
  position: relative;
  width: 210px;
  border-radius: 0.9rem;
  border: 2px solid #4b5563;
  background: #020617;
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.7);
  padding: 0.45rem 0.45rem 0.5rem;
  color: #e5e7eb;
  font-size: 0.9rem;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0.35rem;
  transition: box-shadow 0.15s;
}

/* Выделение синим — через box-shadow, не border (чтобы не конфликтовать с редкостью) */
.node.selected {
  box-shadow:
    0 0 0 2px #3b82f6,
    0 0 20px rgba(59, 130, 246, 0.35),
    0 10px 20px rgba(15, 23, 42, 0.7);
}

/* Кнопка удаления ноды */
.remove-btn {
  position: absolute;
  top: 0.3rem;
  right: 0.3rem;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: none;
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  font-size: 0.6rem;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  opacity: 0;
  transition: opacity 0.15s, background 0.15s;
  z-index: 2;
}
.node:hover .remove-btn { opacity: 1; }
.remove-btn:hover { background: rgba(239, 68, 68, 0.35); }

.icon-wrapper {
  width: 85%;
  aspect-ratio: 1 / 1;
  border-radius: 0.7rem;
  background: #020617;
  border: 1px solid #1f2937;
  overflow: hidden;
  margin: 0 auto;
}
.icon { width: 100%; height: 100%; object-fit: cover; }
.icon-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  color: #6b7280;
}

.info { text-align: center; }
.name {
  font-size: 1rem;
  font-weight: 700;
  word-wrap: break-word;
  white-space: normal;
}
.meta { font-size: 0.8rem; color: #9ca3af; }
.category { text-transform: none; }

.bottom-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.25rem;
}

.amount-block {
  min-width: 60px;
  max-width: 70px;
  padding: 0.2rem 0.3rem;
  border-radius: 0.7rem;
  background: #111827;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.05rem;
}
.amount-label { font-size: 0.7rem; color: #9ca3af; }
.amount-value { font-size: 1.2rem; font-weight: 700; }

.actions {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.25rem;
}

.price-block {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.price-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.72rem;
}
.price-label { color: #6b7280; }
.price-val { color: #e5e7eb; font-weight: 600; }
.price-val.craft { color: #60a5fa; }

.decision-badge {
  font-size: 0.68rem;
  text-align: center;
  padding: 0.1rem 0.4rem;
  border-radius: 0.3rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-top: 0.1rem;
  cursor: pointer;
  border: 1px solid transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  width: 100%;
  font-family: inherit;
  transition: filter 0.15s, border-color 0.15s;
}
.decision-badge:hover { filter: brightness(1.2); }
.decision-badge.buy { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.decision-badge.craft { background: rgba(59, 130, 246, 0.15); color: #60a5fa; }
.decision-badge.unknown { background: rgba(107, 114, 128, 0.15); color: #9ca3af; }
/* Рамка badge когда override зафиксирован */
.decision-badge.overridden { border-color: currentColor; }
.override-dot { font-size: 0.5rem; }

.btn {
  border-radius: 0.6rem;
  border: 1px solid transparent;
  padding: 0.22rem 0.55rem;
  font-size: 0.78rem;
  cursor: pointer;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}
.btn.primary {
  background: #1d4ed8;
  border-color: #1d4ed8;
  color: #f9fafb;
}
.btn.disabled { opacity: 0.6; cursor: default; }
.btn:hover:not(.disabled) { filter: brightness(1.05); }

.badge {
  background: rgba(255, 255, 255, 0.18);
  border-radius: 999px;
  padding: 0 0.35rem;
  font-size: 0.7rem;
  font-weight: 700;
}

.handle {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  width: 10px;
  height: 10px;
  border-radius: 999px;
  border: 2px solid #020617;
}
.handle-out { top: -7px; background: #22c55e; }
.handle-in { bottom: -7px; background: #3b82f6; }
</style>

<style>
.variants-popup {
  position: fixed;
  z-index: 9999;
  padding: 0.5rem;
  border-radius: 0.75rem;
  background: #020617;
  border: 1px solid #374151;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.7);
  max-height: 70vh;
  overflow-y: auto;
  color: #e5e7eb;
  font-family: inherit;
}
.variants-header {
  font-size: 0.78rem;
  color: #9ca3af;
  padding: 0.25rem 0.4rem 0.5rem;
  border-bottom: 1px solid #1f2937;
  margin-bottom: 0.4rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.variants-list { display: flex; flex-direction: column; gap: 0.25rem; }
.variant-card {
  display: grid;
  grid-template-columns: 40px 1fr auto;
  align-items: center;
  gap: 0.6rem;
  padding: 0.4rem 0.5rem;
  border-radius: 0.5rem;
  border: 1px solid #1f2937;
  background: #0b1120;
  color: #e5e7eb;
  cursor: pointer;
  text-align: left;
  font: inherit;
}
.variant-card:hover { border-color: #60a5fa; background: #111c33; }
.variant-card.active { border-color: #22c55e; background: rgba(34, 197, 94, 0.08); }
.variant-icon-wrapper {
  width: 40px;
  height: 40px;
  border-radius: 0.4rem;
  background: #020617;
  border: 1px solid #1f2937;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}
.variant-icon { width: 100%; height: 100%; object-fit: cover; }
.variant-icon-placeholder { font-size: 0.85rem; color: #6b7280; }
.variant-info { min-width: 0; }
.variant-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: #e5e7eb;
  white-space: normal;
  word-wrap: break-word;
}
.variant-id {
  font-size: 0.7rem;
  color: #6b7280;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.active-mark { color: #22c55e; font-weight: 700; font-size: 1rem; }
</style>
