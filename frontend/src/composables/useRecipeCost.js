import { ref, watch } from "vue";
import { fetchRecipeCost } from "../api/recipes";

export function useRecipeCost(
  selectedItemRef,
  amountRef,
  choicesRef = null,
  overridesRef = null,
) {
  const costData = ref(null);
  const loading = ref(false);
  const error = ref("");

  async function load(item, amount, choices, overrides) {
    if (!item) { costData.value = null; return; }
    loading.value = true;
    error.value = "";
    try {
      costData.value = await fetchRecipeCost(item.id, amount || 1, {
        recipeChoices: choices || null,
        decisionOverrides: overrides || null,
      });
    } catch (e) {
      error.value = "Ошибка загрузки стоимости рецепта";
      console.error(e);
    } finally {
      loading.value = false;
    }
  }

  watch(
    [selectedItemRef, amountRef, choicesRef ?? ref(null), overridesRef ?? ref(null)],
    ([item, amount, choices, overrides]) => load(item, amount, choices, overrides),
    { immediate: true, deep: true }
  );

  return {
    costData,
    loading,
    error,
    reload: () =>
      load(
        selectedItemRef.value,
        amountRef.value,
        choicesRef?.value,
        overridesRef?.value,
      ),
  };
}
