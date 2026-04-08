FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY src ./src
COPY scripts ./scripts

ENV NODE_ENV=production

CMD ["sh", "-c", "node scripts/schema.js && node scripts/import-listing.js && node scripts/import-recipes.js && node scripts/import-items.js && npm start"]