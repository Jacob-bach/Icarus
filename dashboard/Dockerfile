FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json ./
RUN npm install

# Copy source code
COPY . .

# Build for production (optional, for dev mode we use vite dev server)
# RUN npm run build

# Development mode
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]
