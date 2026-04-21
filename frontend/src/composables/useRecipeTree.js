import { ref, watch } from "vue";
import { fetchRecipeTree } from "../api/recipes";

// Адаптирует новый формат бекенда к формату который ожидает RecipeGraph
function adaptNode(node) {
  if (!node) return null;
  return {
    item: node.item || { id: node.item_id },
    itemId: node.item_id,
    recipes: (node.recipes || []).map(recipe => ({
      id: recipe.recipe_id,
      bench: recipe.bench,
      energy: recipe.energy,
      result_amount: recipe.result_amount,
      required_perk_id: recipe.required_perk_id,
      category_ru: recipe.category_ru,
      ingredients: (recipe.ingredients || []).map(ing => ({
        itemId: ing.item_id,
        amount: ing.amount,
        node: adaptNode(ing.node),
      })),
    })),
  };
}

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
      const raw = await fetchRecipeTree(item.id);
      tree.value = adaptNode(raw);
    } catch (e) {
      console.error(e);
      error.value = "Ошибка загрузки дерева рецепта";
    } finally {
      loading.value = false;
    }
  }

  watch(selectedItemRef, loadTree, { immediate: true });

  return { tree, loading, error, reload: () => loadTree(selectedItemRef.value) };
}