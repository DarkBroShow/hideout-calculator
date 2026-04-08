<!-- frontend/src/components/search/ItemSearch.vue -->
<script setup>
import { useSearch } from "../../composables/useSearch";
import { getCategoryLabel } from "../../utils/categoryLabels";

const emit = defineEmits(["select"]);
const { query, items, loading, error, hasResults, search } = useSearch();

function handleSelect(item) {
  emit("select", item);
}

function iconUrl(item) {
  if (!item?.icon_path) return null;
  // backend монтирует stalcraft-database в /icons,
  // так что иконки доступны по относительному пути
  return item.icon_path; // например: /icons/misc/dqg5.png
}
</script>

<template>
  <section>
    <h2 class="title">Поиск предметов</h2>

    <form @submit.prevent="search" class="search">
      <input
        v-model="query"
        type="text"
        placeholder="Введите название (например, Рыбное филе)"
      />
      <button type="submit" :disabled="loading">
        {{ loading ? "Поиск..." : "Искать" }}
      </button>
    </form>

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
            <span class="category">
              {{ getCategoryLabel(item.category) }}
            </span>
          </div>
        </div>
      </li>
    </ul>

    <p v-else class="empty">Ничего не найдено. Попробуйте другой запрос.</p>
  </section>
</template>

<style scoped>
.title {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 1rem;
}

.search {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.search input {
  flex: 1;
  padding: 0.55rem 0.8rem;
  border-radius: 0.5rem;
  border: 1px solid #4b5563;
  background: #020617;
  color: #e5e7eb;
  font-size: 0.95rem;
}

.search input::placeholder {
  color: #6b7280;
}

.search button {
  padding: 0.55rem 1rem;
  border-radius: 0.5rem;
  border: none;
  background: #2563eb;
  color: #ffffff;
  font-weight: 600;
  font-size: 0.95rem;
  cursor: pointer;
}

.search button:disabled {
  opacity: 0.7;
  cursor: default;
}

.error {
  color: #fecaca;
  font-size: 0.9rem;
}

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

.items li:hover {
  background: rgba(37, 99, 235, 0.15);
}

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
}

.icon {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.icon-placeholder {
  font-size: 0.8rem;
  color: #6b7280;
}

.info {
  flex: 1;
}

.name {
  font-size: 1rem;
  font-weight: 600;
  color: #e5e7eb;
}

.meta {
  font-size: 0.9rem;
  color: #9ca3af;
}

.category {
  text-transform: none;
}

.empty {
  font-size: 0.95rem;
  color: #6b7280;
}
</style>