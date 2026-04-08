export function getRarityColor(rarity) {
  if (!rarity) return "#4b5563"; // серый по умолчанию
  const r = String(rarity).toUpperCase();

  if (r.includes("LEGEND")) return "#f97316"; // легендарный — оранжевый
  if (r.includes("EPIC") || r.includes("ELITE")) return "#a855f7"; // фиолетовый
  if (r.includes("RARE")) return "#3b82f6"; // синий
  if (r.includes("UNCOMMON")) return "#22c55e"; // зелёный
  if (r.includes("NEWBIE") || r.includes("COMMON")) return "#9ca3af"; // серый

  return "#4b5563";
}