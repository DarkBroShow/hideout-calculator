# GitFlow (упрощенный)

## Ветки
| Ветка | Назначение |
|-------|------------|
| `main` | Рабочая версия |
| `develop` | Текущая разработка |
| `feature/название` | Новая фича |
| `fix/название` | Багфикс |
| `hotfix/критичный` | Срочный фикс продакшена |

## Процесс
```mermaid
graph TD
  A[develop] --> B[git checkout -b feature/search-ui]
  B --> C[разработка]
  C --> D[PR в develop]
  D --> E[тест + мерж]
  E --> F[git checkout develop<br>git pull]
  F --> G[готово к релизу]
  G --> H[git checkout main<br>git merge develop<br>git tag v0.2.0]
```

## Коммиты (Conventional Commits)
```
feat: add material editor
fix: recipe tree infinite loop
docs: update architecture diagram
refactor: split search composable
chore: bump vueflow version
```

## Релиз
```bash
git checkout develop
git checkout -b release/v0.2.0
# финальные фиксы
git checkout main
git merge release/v0.2.0
git tag v0.2.0
git push origin main --tags
```
