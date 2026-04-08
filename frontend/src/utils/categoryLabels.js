const CATEGORY_LABELS = {
  misc: "Другое",
  weapon: "Оружие",
  armor: "Броня",
  artifact: "Артефакт",
  component: "Компонент",
  barter: "Бартовский предмет",
  consumable: "Расходник",
};

export function getCategoryLabel(code) {
  if (!code) return "Без категории";
  const norm = String(code).toLowerCase();
  return CATEGORY_LABELS[norm] || code;
}