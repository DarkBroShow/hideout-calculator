import { ref, computed } from "vue";
import { searchItems } from "../api/items";

export function useSearch() {
  const query = ref("");
  const items = ref([]);
  const loading = ref(false);
  const error = ref("");

  const hasResults = computed(() => items.value && items.value.length > 0);

  async function search() {
    const q = query.value.trim();
    if (!q) {
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

  return {
    query,
    items,
    loading,
    error,
    hasResults,
    search,
  };
}