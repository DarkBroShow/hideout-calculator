import { ref, watch } from "vue";
import { fetchRecipeTree } from "../api/recipes";

export function useRecipeTree(selectedItemRef) {
  const tree = ref(null);
  const loading = ref(false);
  const error = ref("");

  async function loadTree(item) {
    if (!item) {
      tree.value = null;
      error.value = "";
      return;
    }
    loading.value = true;
    error.value = "";
    try {
      tree.value = await fetchRecipeTree(item.id);
    } catch (e) {
      console.error(e);
      error.value = "Ошибка загрузки дерева рецепта";
    } finally {
      loading.value = false;
    }
  }

  watch(
    selectedItemRef,
    (item) => {
      loadTree(item);
    },
    { immediate: true }
  );

  return {
    tree,
    loading,
    error,
    reload: () => loadTree(selectedItemRef.value),
  };
}