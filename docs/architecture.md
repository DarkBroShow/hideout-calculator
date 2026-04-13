# Архитектура

## Поток данных
```
game-data/stalcraft-database/
└── иконки (.png) + статичные данные для импорта в БД

backend/scripts/import-*.js
└── парсит данные → заполняет PostgreSQL

PostgreSQL (3 таблицы):
├── items (id, name_ru, category, rarity, icon_path)
├── recipes (id, result_item_id, result_amount, bench, energy...)
└── recipe_ingredients (recipe_id, ingredient_item_id, amount)

Express API (backend/src/index.js):
├── /api/health — Healthcheck
├── /api/items/search?q=... — поиск предметов
└── /api/recipes/:itemId/tree — дерево крафта (рекурсия до 6 уровней)

Frontend (Vue 3 + Vite):
├── src/api/*.js — HTTP запросы
├── composables/useSearch.js — логика поиска
├── composables/useRecipeTree.js — работа с деревом
└── компоненты: ItemSearch → RecipeGraph → MaterialEditor
```

## API Endpoints

| Метод | Endpoint | Описание | Пример |
|-------|----------|----------|--------|
| GET | `/api/health` | Healthcheck | `{"status": "ok"}` |
| GET | `/api/items/search?q=железо` | Поиск предметов | `[{id: "item_123", name_ru: "Железный лом"}]` |
| GET | `/api/recipes/item_123/tree` | Дерево крафта | `{item: {...}, recipes: [{ingredients: [...]}]}` |

## Docker сервисы
```
db (postgres:16-alpine)
↓ backend (hideout-backend)
↓ (CORS)
frontend (nginx + Vue build)
```