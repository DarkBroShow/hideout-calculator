# Поток данных

## Поиск предмета
```
ItemSearch.vue → ввод текста

useSearch.js → api/items.js → /api/items/search?q=...

Backend → PostgreSQL WHERE name_ru ILIKE '%q%'

Ответ → список предметов в dropdown
↓

Клик по предмету → activeTab = "current-tree"
```
## Построение дерева крафта
```
RecipeGraph.vue → api/recipes.js → /api/recipes/:itemId/tree

Backend → buildRecipeTree(itemId, depth=0, maxDepth=6)

Рекурсия: item → recipes → ingredients → buildRecipeTree()

Защита: visited Set (циклы), maxDepth=6 (бесконечность)

Ответ → дерево JSON → VueFlow nodes/edges
```

## Редактирование материалов
```
MaterialEditor.vue ← selectedItem (из App.vue)
↓ редактирование количества
→ обновляет RecipeGraph (emit/prop)
```

## Состояние приложения
```
App.vue (корень):
├── selectedItem: ref(null) # текущий предмет
├── activeTab: ref("recipes") # вкладка
└── tabs: [] # навигация
```