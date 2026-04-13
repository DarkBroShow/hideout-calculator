# Frontend (Vue 3 + Vite)

## Структура
```
src/
├── api/ # HTTP клиенты
│ ├── http.js # обертка fetch
│ ├── items.js # /api/items/*
│ └── recipes.js # /api/recipes/*
├── components/
│ ├── layout/PageLayout.vue # общий layout + tabs
│ ├── search/ItemSearch.vue # поисковая строка
│ ├── recipes/RecipeGraph.vue # VueFlow граф
│ └── materials/MaterialEditor.vue
├── composables/
│ ├── useSearch.js # логика поиска
│ └── useRecipeTree.js # работа с деревом
└── utils/
├── categoryLabels.js # перевод категорий
└── rarityColors.js # цвета редкости
```

## Навигация
App.vue управляет 4 табами:
1. **recipes** — поиск + превью
2. **current-tree** — граф + редактор  
3. **profile** — заглушка
4. **hideout** — заглушка

## Библиотеки
- **VueFlow** (`@vue-flow/*`) — интерактивные графы рецептов
- **Vue 3** Composition API
- **Vite 8** — сборка + HMR