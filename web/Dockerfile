FROM node:22-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

ENV NEXT_PUBLIC_API_URL=/api
ENV NEXT_PUBLIC_USE_MOCKS=0

RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]