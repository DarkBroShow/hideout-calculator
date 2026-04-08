import { requestJson } from "./http";

export function searchItems(query) {
  const q = (query || "").trim();
  if (!q) return Promise.resolve([]);

  const url = `/api/items/search?q=${encodeURIComponent(q)}`;
  return requestJson(url);
}