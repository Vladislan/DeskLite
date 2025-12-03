# build
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build            # створить /app/dist

# serve
FROM nginx:1.27-alpine
WORKDIR /usr/share/nginx/html
COPY --from=build /app/dist ./
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
