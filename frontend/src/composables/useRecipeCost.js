import { ref, watch } from "vue";
import { fetchRecipeCost } from "../api/recipes";

export function useRecipeCost(selectedItemRef, amountRef, choicesRef = null) {
  const costData = ref(null);
  const loading = ref(false);
  const error = ref("");

  async function load(item, amount, choices) {
    if (!item) { costData.value = null; return; }
    loading.value = true;
    error.value = "";
    try {
      costData.value = await fetchRecipeCost(item.id, amount || 1, {
        recipeChoices: choices || null,
      });
    } catch (e) {
      error.value = "Ошибка загрузки стоимости рецепта";
      console.error(e);
    } finally {
      loading.value = false;
    }
  }
 // deep-watch на choicesRef чтобы реагировать на смену рецепта внутри объекта
  watch(
    [selectedItemRef, amountRef, choicesRef ?? ref(null)],
    ([item, amount, choices]) => load(item, amount, choices),
    { immediate: true, deep: true }
  );

  return {
    costData,
    loading,
    error,
    reload: () => load(selectedItemRef.value, amountRef.value, choicesRef?.value),
  };
}