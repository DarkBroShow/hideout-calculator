<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from "vue";
import { Handle, Position } from "@vue-flow/core";
import { getCategoryLabel } from "../../utils/categoryLabels";
import { getRarityColor } from "../../utils/rarityColors";

const props = defineProps({
  id: {
    type: String,
    required: true,
  },
  data: {
    type: Object,
    required: true,
  },
});

const emit = defineEmits(["switch-recipe", "calc-auction"]);

const borderColor = computed(() =>
  getRarityColor(props.data.item?.rarity || props.data.item?.rarity_code)
);

const categoryLabel = computed(() =>
  getCategoryLabel(props.data.item?.category)
);

const amountLabel = computed(
  () =>
    props.data.amountInput && props.data.amountInput !== 1
      ? `${props.data.amountInput}×`
      : "1×"
);

const priceLabel = computed(() => props.data.priceLabel ?? "---");

// локальное состояние меню
const showRecipes = ref(false);
const containerEl = ref(null);

const hasVariants = computed(
  () => props.data.recipesCount && props.data.recipesCount > 1
);
const variants = computed(() => props.data.recipeVariants || []);
const activeIdx = computed(() => props.data.activeRecipeIndex ?? 0);

function toggleRecipes() {
  if (!hasVariants.value) return;
  showRecipes.value = !showRecipes.value;
}

function selectRecipe(idx) {
  emit("switch-recipe", { nodeId: props.id, recipeIndex: idx });
  showRecipes.value = false;
}

function iconUrl() {
  const path = props.data.item?.icon_path;
  if (!path) return null;
  return path;
}

function onCalcAuction() {
  emit("calc-auction", props.id);
}

function onClickOutside(e) {
  if (!showRecipes.value) return;
  const el = containerEl.value;
  if (!el) return;
  if (!el.contains(e.target)) {
    showRecipes.value = false;
  }
}

onMounted(() => {
  document.addEventListener("mousedown", onClickOutside);
});
onBeforeUnmount(() => {
  document.removeEventListener("mousedown", onClickOutside);
});
</script>

<template>
  <div class="node" :style="{ borderColor }" ref="containerEl">
    <!-- ВЫХОД: сверху -->
    <Handle
      type="source"
      :position="Position.Top"
      class="handle handle-out"
    />

    <div class="icon-wrapper">
      <img
        v-if="iconUrl()"
        :src="iconUrl()"
        alt=""
        class="icon"
        loading="lazy"
      />
      <div v-else class="icon-placeholder">?</div>
    </div>

    <div class="info">
      <div class="name">
        {{ data.item?.name_ru || data.item?.id || "?" }}
      </div>
      <div class="meta">
        <span class="category">{{ categoryLabel }}</span>
      </div>
    </div>

    <div class="bottom-row">
      <div class="amount-block">
        <span class="amount-label">Кол-во</span>
        <span class="amount-value">{{ amountLabel }}</span>
      </div>

      <div class="actions">
        <!-- кнопка открытия меню вариантов -->
        <button
          type="button"
          class="btn primary"
          :class="{ disabled: !hasVariants }"
          @click.stop="toggleRecipes"
        >
          Рецепт
        </button>

        <!-- кнопка с ценой -->
        <div class="price-block">
    <div class="price-row">
      <span class="price-label">Купить</span>
      <span class="price-val">{{ data.buyPrice ? data.buyPrice.toLocaleString('ru-RU') + ' ₽' : '...' }}</span>
    </div>
    <div class="price-row">
      <span class="price-label">Крафт</span>
      <span class="price-val craft">{{ data.craftPrice ? data.craftPrice.toLocaleString('ru-RU') + ' ₽' : '—' }}</span>
    </div>
    <div
      class="decision-badge"
      :class="data.decision === 'buy' ? 'buy' : data.decision === 'craft' ? 'craft' : 'unknown'"
    >
      {{ data.decision === 'buy' ? 'Купить' : data.decision === 'craft' ? 'Крафтить' : '?' }}
    </div>
  </div>
      </div>
    </div>

    <!-- визуальное меню вариантов рецепта -->
    <div v-if="showRecipes && hasVariants" class="variants-popup">
      <div class="variants-grid">
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
          <div class="variant-name">
            {{ variant.item?.name_ru || variant.item?.id || `Ветка #${variant.index + 1}` }}
          </div>
        </button>
      </div>
    </div>

    <!-- ВХОД: снизу -->
    <Handle
      type="target"
      :position="Position.Bottom"
      class="handle handle-in"
    />
  </div>
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
}

/* иконка предмета */
.icon-wrapper {
  width: 85%;
  aspect-ratio: 1 / 1;
  border-radius: 0.7rem;
  background: #020617;
  border: 1px solid #1f2937;
  overflow: hidden;
  margin: 0 auto;
}
.icon {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.icon-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  color: #6b7280;
}

/* имя по центру */
.info {
  text-align: center;
}
.name {
  font-size: 1rem;
  font-weight: 700;
  word-wrap: break-word;
  white-space: normal;
}
.meta {
  font-size: 0.8rem;
  color: #9ca3af;
}
.category {
  text-transform: none;
}

/* низ: количество и кнопки */
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
.amount-label {
  font-size: 0.7rem;
  color: #9ca3af;
}
.amount-value {
  font-size: 1.2rem;
  font-weight: 700;
}

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
  padding: 0.1rem 0.3rem;
  border-radius: 0.3rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-top: 0.1rem;
}
.decision-badge.buy { background: rgba(34,197,94,0.15); color: #4ade80; }
.decision-badge.craft { background: rgba(59,130,246,0.15); color: #60a5fa; }
.decision-badge.unknown { background: rgba(107,114,128,0.15); color: #9ca3af; }

.btn {
  border-radius: 0.6rem;
  border: 1px solid transparent;
  padding: 0.22rem 0.55rem;
  font-size: 0.78rem;
  cursor: pointer;
  white-space: nowrap;
}
.btn.primary {
  background: #1d4ed8;
  border-color: #1d4ed8;
  color: #f9fafb;
}
.btn.secondary {
  background: #111827;
  border-color: #374151;
  color: #e5e7eb;
}
.btn.disabled {
  opacity: 0.6;
  cursor: default;
}
.btn:hover:not(.disabled) {
  filter: brightness(1.05);
}

/* попап с вариантами */
.variants-popup {
  position: absolute;
  right: -4px;
  top: 100%;
  margin-top: 0.25rem;
  padding: 0.35rem;
  border-radius: 0.75rem;
  background: #020617;
  border: 1px solid #374151;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.95);
  z-index: 40;
  max-width: 260px;
}

.variants-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
  gap: 0.35rem;
}

.variant-card {
  border-radius: 0.6rem;
  border: 1px solid #374151;
  background: #020617;
  padding: 0.25rem 0.2rem 0.3rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
  cursor: pointer;
  min-width: 0;
}
.variant-card:hover {
  border-color: #60a5fa;
  background: #0b1120;
}
.variant-card.active {
  border-color: #22c55e;
  box-shadow: 0 0 0 1px rgba(34, 197, 94, 0.7);
}

.variant-icon-wrapper {
  width: 36px;
  height: 36px;
  border-radius: 0.4rem;
  background: #020617;
  border: 1px solid #1f2937;
  overflow: hidden;
}
.variant-icon {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.variant-icon-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  color: #6b7280;
}
.variant-name {
  font-size: 0.7rem;
  text-align: center;
  color: #e5e7eb;
  word-wrap: break-word;
  white-space: normal;
}

/* точки соединений */
.handle {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  width: 10px;
  height: 10px;
  border-radius: 999px;
  border: 2px solid #020617;
}
.handle-out {
  top: -7px;
  background: #22c55e;
}
.handle-in {
  bottom: -7px;
  background: #3b82f6;
}
</style>