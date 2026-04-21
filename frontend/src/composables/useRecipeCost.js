import { ref, watch } from "vue";
import { fetchRecipeCost } from "../api/recipes";

export function useRecipeCost(selectedItemRef, amountRef) {
  const costData = ref(null);
  const loading = ref(false);
  const error = ref("");

  async function load(item, amount) {
    if (!item) { costData.value = null; return; }
    loading.value = true;
    error.value = "";
    try {
      costData.value = await fetchRecipeCost(item.id, amount || 1);
    } catch (e) {
      error.value = "Ошибка загрузки стоимости рецепта";
      console.error(e);
    } finally {
      loading.value = false;
    }
  }

  watch(
    [selectedItemRef, amountRef],
    ([item, amount]) => load(item, amount),
    { immediate: true }
  );

  return { costData, loading, error, reload: () => load(selectedItemRef.value, amountRef.value) };
}