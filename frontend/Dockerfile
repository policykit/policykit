FROM node:23

WORKDIR /app/
COPY yarn.lock package.json ./
RUN yarn install
VOLUME /app/node_modules
CMD ["yarn", "dev"]
