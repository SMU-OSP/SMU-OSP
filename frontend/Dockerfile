# Frontend image for LOCAL DEVELOPMENT / TESTING only.
# Runs the Vite dev server with HMR. Build context is ./frontend.
FROM node:20-slim

WORKDIR /app

# Install deps first for better layer caching.
COPY package.json package-lock.json ./
RUN npm ci

# App code (overridden by the bind mount in docker-compose for live reload).
COPY . .

EXPOSE 5173

# --host exposes the dev server outside the container.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
