# syntax=docker/dockerfile:1
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
# lockfileが無い前提なので install を使用
RUN npm install
COPY . .
RUN npm run build

FROM caddy:2-alpine
# /buff_sim1 配下で配信するため、dist を /srv/buff_sim1 に配置
COPY --from=build /app/dist /srv/buff_sim1
EXPOSE 80
CMD ["caddy", "file-server", "--root", "/srv", "--listen", ":80"]
