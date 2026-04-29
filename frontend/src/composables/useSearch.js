import { ref, computed, watch } from "vue";
import { searchItems } from "../api/items";

// Минимальная длина запроса для авто-поиска
const MIN_QUERY_LEN = 2;
// Задержка дебаунса в мс
const DEBOUNCE_MS = 300;

export function useSearch() {
  const query = ref("");
  const items = ref([]);
  const loading = ref(false);
  const error = ref("");

  const hasResults = computed(() => items.value && items.value.length > 0);

  let debounceTimer = null;

  async function search() {
    const q = query.value.trim();
    if (!q || q.length < MIN_QUERY_LEN) {
      items.value = [];
      error.value = "";
      return;
    }
    loading.value = true;
    error.value = "";
    try {
      items.value = await searchItems(q);
    } catch (e) {
      console.error(e);
      error.value = "Ошибка загрузки списка предметов";
    } finally {
      loading.value = false;
    }
  }

  // Авто-поиск с дебаунсом при каждом изменении query
  watch(query, (val) => {
    clearTimeout(debounceTimer);
    if (!val.trim() || val.trim().length < MIN_QUERY_LEN) {
      items.value = [];
      error.value = "";
      return;
    }
    debounceTimer = setTimeout(search, DEBOUNCE_MS);
  });

  return {
    query,
    items,
    loading,
    error,
    hasResults,
    search,
  };
}
