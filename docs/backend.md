# Backend (hideout-backend)

## Входная точка
`backend/src/index.js` — Express сервер + PostgreSQL + статика иконок

## Структура таблиц
```sql
items: id, name_ru, category, rarity, icon_path
recipes: id, result_item_id, result_amount, bench, energy, perk_id, perk_level  
recipe_ingredients: recipe_id, ingredient_item_id, amount
```

## Импорт данных
```bash
# В контейнере backend
npm run import:items    # заполняет items
npm run import:recipes  # заполняет recipes + recipe_ingredients
```

Скрипты читают `game-data/stalcraft-database/` и парсят в PostgreSQL.

## Особенности
- Рекурсивная функция `buildRecipeTree()` строит дерево до 6 уровней
- Защита от циклов через `visited Set`
- Статические иконки: `/icons/*.png`
- CORS включен для frontend