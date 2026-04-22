import { requestJson } from "./http";

export function fetchRecipeTree(itemId) {
  if (!itemId) return Promise.resolve(null);
  return requestJson(`/api/recipes/tree/${encodeURIComponent(itemId)}`);
}

export function fetchRecipeCost(itemId, amount = 1, opts = {}) {
  if (!itemId) return Promise.resolve(null);
  const { forceRefresh = false, recipeChoices = null } = opts;
  const params = new URLSearchParams({
    item_id: itemId,
    amount,
    ...(forceRefresh ? { force_refresh: "true" } : {}),
  });
  // recipeChoices: { item_id: recipe_id } — фиксированные пользователем рецепты
  if (recipeChoices && Object.keys(recipeChoices).length) {
    params.set("recipe_choices", JSON.stringify(recipeChoices));
  }  
  return requestJson(`/api/recipes/cost?${params}`);
}

export function fetchItemPrice(itemId, forceRefresh = false) {
  const params = forceRefresh ? "?force_refresh=true" : "";
  return requestJson(`/api/recipes/price/${encodeURIComponent(itemId)}${params}`);
}