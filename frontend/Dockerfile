FROM node:20-alpine

WORKDIR /app

# Copy package descriptors first to benefit from layer caching
COPY package.json ./

RUN npm install

# Copy frontend source files
COPY . .

EXPOSE 3000

# Start Vite dev server binding port 3000
CMD ["npm", "run", "dev"]
