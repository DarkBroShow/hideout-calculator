<script setup>
import { useSearch } from "../../composables/useSearch";
import { getCategoryLabel } from "../../utils/categoryLabels";

const emit = defineEmits(["select"]);
const { query, items, loading, error, hasResults } = useSearch();

function handleSelect(item) {
  emit("select", item);
}

function iconUrl(item) {
  if (!item?.icon_path) return null;
  return item.icon_path;
}
</script>

<template>
  <section>
    <h2 class="title">Поиск предметов</h2>

    <div class="search">
      <input
        v-model="query"
        type="text"
        placeholder="Введите название (например, Рыбное филе)"
        :class="{ loading }"
        autocomplete="off"
        spellcheck="false"
      />
      <span v-if="loading" class="spinner" aria-hidden="true" />
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <ul v-else-if="hasResults" class="items">
      <li v-for="item in items" :key="item.id" @click="handleSelect(item)">
        <div class="icon-wrapper">
          <img
            v-if="iconUrl(item)"
            :src="iconUrl(item)"
            alt=""
            class="icon"
            loading="lazy"
            referrerpolicy="no-referrer"
          />
          <div v-else class="icon-placeholder">?</div>
        </div>
        <div class="info">
          <div class="name">{{ item.name_ru }}</div>
          <div class="meta">
            <span class="category">{{ getCategoryLabel(item.category) }}</span>
          </div>
        </div>
      </li>
    </ul>

    <p v-else-if="query.length >= 2 && !loading" class="empty">
      Ничего не найдено. Попробуйте другой запрос.
    </p>
  </section>
</template>

<style scoped>
.title {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 1rem;
  font-family: "RodondoRUS", sans-serif;
}

.search {
  position: relative;
  margin-bottom: 1rem;
}
.search input {
  width: 100%;
  padding: 0.55rem 2.2rem 0.55rem 0.8rem;
  border-radius: 0.5rem;
  border: 1px solid #4b5563;
  background: #020617;
  color: #e5e7eb;
  font-size: 0.95rem;
  box-sizing: border-box;
  transition: border-color 0.15s;
}
.search input:focus {
  outline: none;
  border-color: #2563eb;
}
.search input::placeholder {
  color: #6b7280;
}
.spinner {
  position: absolute;
  right: 0.65rem;
  top: 50%;
  transform: translateY(-50%);
  width: 14px;
  height: 14px;
  border: 2px solid #374151;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: translateY(-50%) rotate(360deg); } }

.error { color: #fecaca; font-size: 0.9rem; }

.items {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 520px;
  overflow-y: auto;
}
.items li {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.35rem;
  border-bottom: 1px solid #111827;
  cursor: pointer;
}
.items li:hover { background: rgba(37, 99, 235, 0.15); }

.icon-wrapper {
  width: 40px;
  height: 40px;
  border-radius: 0.5rem;
  background: #020617;
  border: 1px solid #1f2937;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  flex-shrink: 0;
}
.icon { width: 100%; height: 100%; object-fit: cover; }
.icon-placeholder { font-size: 0.8rem; color: #6b7280; }

.info { flex: 1; min-width: 0; }
.name { font-size: 1rem; font-weight: 600; color: #e5e7eb; }
.meta { font-size: 0.9rem; color: #9ca3af; }
.category { text-transform: none; }

.empty { font-size: 0.95rem; color: #6b7280; }
</style>
