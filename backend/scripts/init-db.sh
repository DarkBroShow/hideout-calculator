#!/usr/bin/env sh
set -e

echo "Running DB schema & imports..."

node scripts/schema.js
node scripts/import-listing.js
node scripts/import-recipes.js
node scripts/import-items.js

echo "DB init done"