<script setup>
import { computed } from "vue";

const props = defineProps({
  costData: { type: Object, default: null },
  loading: { type: Boolean, default: false },
});

function fmt(n) {
  if (n == null) return "—";
  return n.toLocaleString("ru-RU") + " ₽";
}

const profitClass = computed(() => {
  if (!props.costData) return "";
  return props.costData.is_profitable ? "profit" : "loss";
});

const marginPct = computed(() => {
  const d = props.costData;
  if (!d?.margin || !d?.sell_price || d.sell_price === 0) return null;
  return Math.round((d.margin / d.sell_price) * 100);
});
</script>

<template>
  <aside class="summary">
    <div class="summary-header">
      <span class="summary-title">Сводка</span>
      <span v-if="loading" class="loading-dot">●</span>
    </div>

    <p v-if="loading" class="loading-msg">Считаем стоимость…</p>

    <template v-if="!costData && !loading">
      <p class="empty">Выберите предмет чтобы увидеть расчёт</p>
    </template>

    <template v-else-if="costData">
      <!-- Итоговые цифры -->
      <div class="metrics">
        <div class="metric">
          <span class="metric-label">Купить</span>
          <span class="metric-value">{{ fmt(costData.total_buy_cost) }}</span>
        </div>
        <div class="metric">
          <span class="metric-label">Крафт</span>
          <span class="metric-value">{{ fmt(costData.total_craft_cost) }}</span>
        </div>
        <div class="metric" :class="profitClass">
          <span class="metric-label">Продажа</span>
          <span class="metric-value">{{ fmt(costData.sell_price) }}</span>
        </div>
        <div class="metric" :class="profitClass">
          <span class="metric-label">Маржа</span>
          <span class="metric-value">
            {{ fmt(costData.margin) }}
            <span v-if="marginPct != null" class="pct">({{ marginPct }}%)</span>
          </span>
        </div>
      </div>

      <!-- Вердикт -->
      <div class="verdict" :class="profitClass">
        <span class="verdict-icon">{{ costData.is_profitable ? "✓" : "✗" }}</span>
        <span class="verdict-text">{{ costData.profitable_reason }}</span>
      </div>

      <!-- Список компонентов -->
      <div v-if="costData.components_summary?.length" class="components">
        <div class="components-header">Нужно закупить</div>
        <div
          v-for="comp in costData.components_summary"
          :key="comp.item_id"
          class="comp-row"
        >
          <span class="comp-name">{{ comp.item_name || comp.item_id }}</span>
          <span class="comp-amount">{{ comp.amount }} шт</span>
          <span class="comp-price">{{ fmt(comp.total_price) }}</span>
        </div>
      </div>

      <!-- Энергия -->
      <div v-if="costData.energy_price_per_unit" class="energy">
        <span class="energy-label">Цена энергии</span>
        <span class="energy-value">{{ costData.energy_price_per_unit }} ₽/ед</span>
      </div>
    </template>
  </aside>
</template>

<style scoped>
.summary {
  width: 100%;
  background: transparent;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  padding: 0;
  font-size: 0.85rem;
}
.loading-msg {
  font-size: 0.8rem;
  color: #93c5fd;
  margin: 0;
}

.summary-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.summary-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #e5e7eb;
  font-family: "RodondoRUS", sans-serif;
}
.loading-dot {
  color: #3b82f6;
  animation: pulse 1s infinite;
}
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

.empty { color: #6b7280; font-size: 0.85rem; }

.metrics {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}
.metric {
  background: #0f172a;
  border: 1px solid #1f2937;
  border-radius: 0.5rem;
  padding: 0.4rem 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.metric.profit { border-color: rgba(34, 197, 94, 0.3); }
.metric.loss { border-color: rgba(239, 68, 68, 0.3); }
.metric-label { font-size: 0.72rem; color: #6b7280; }
.metric-value { font-size: 0.9rem; color: #e5e7eb; font-weight: 600; }
.pct { font-size: 0.75rem; color: #9ca3af; }

.verdict {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.4rem 0.6rem;
  border-radius: 0.5rem;
  font-size: 0.8rem;
}
.verdict.profit { background: rgba(34, 197, 94, 0.1); color: #4ade80; }
.verdict.loss { background: rgba(239, 68, 68, 0.1); color: #f87171; }
.verdict-icon { font-size: 1rem; }

.components { display: flex; flex-direction: column; gap: 0.3rem; }
.components-header {
  font-size: 0.75rem;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.2rem;
}
.comp-row {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 0.4rem;
  align-items: center;
  padding: 0.25rem 0;
  border-bottom: 1px solid #0f172a;
  font-size: 0.8rem;
}
.comp-name { color: #d1d5db; }
.comp-amount { color: #6b7280; font-size: 0.75rem; }
.comp-price { color: #e5e7eb; text-align: right; }

.energy {
  display: flex;
  justify-content: space-between;
  padding: 0.35rem 0.5rem;
  background: rgba(251, 191, 36, 0.08);
  border: 1px solid rgba(251, 191, 36, 0.2);
  border-radius: 0.4rem;
  font-size: 0.78rem;
}
.energy-label { color: #fbbf24; }
.energy-value { color: #fde68a; }
</style>