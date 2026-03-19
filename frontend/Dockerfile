FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --registry=https://registry.npmmirror.com

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
