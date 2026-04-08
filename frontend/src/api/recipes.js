import { requestJson } from "./http";

export function fetchRecipeTree(itemId) {
  if (!itemId) return Promise.resolve(null);
  const url = `/api/recipes/${encodeURIComponent(itemId)}/tree`;
  return requestJson(url);
}