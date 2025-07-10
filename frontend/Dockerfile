FROM node:23

RUN corepack enable

WORKDIR /app/frontend
COPY yarn.lock package.json .yarnrc.yml ./
RUN --mount=type=cache,target=/root/.yarn YARN_CACHE_FOLDER=/root/.yarn yarn install
VOLUME /app/frontend/node_modules
CMD ["yarn", "dev"]
