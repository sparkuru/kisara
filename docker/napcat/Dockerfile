ARG NAPCAT_BUILDER_IMAGE=node:22.22.0-bookworm
ARG NAPCAT_RUNTIME_IMAGE=mlikiowa/napcat-docker:latest

FROM ${NAPCAT_BUILDER_IMAGE} AS build

ARG NAPCAT_VERSION
ENV NAPCAT_VERSION=${NAPCAT_VERSION}

RUN npm install --global pnpm@9.15.9
WORKDIR /build
COPY repo/ ./

RUN pnpm install --frozen-lockfile \
    && pnpm run build:webui \
    && pnpm run build:shell \
    && pnpm run build:plugin-builtin

WORKDIR /build/packages/napcat-shell/dist
RUN npm pkg delete devDependencies \
    && npm install --omit=dev \
    && rm -f package-lock.json \
    && python3 -m zipfile -c /tmp/NapCat.Shell.zip *

FROM ${NAPCAT_RUNTIME_IMAGE}

ARG NAPCAT_VERSION
ARG NAPCAT_REVISION
ARG NAPCAT_SOURCE_STATE
LABEL org.opencontainers.image.source="https://github.com/XingYunStar/NapCatQQ" \
      org.opencontainers.image.version="${NAPCAT_VERSION}" \
      org.opencontainers.image.revision="${NAPCAT_REVISION}" \
      io.kisara.napcat.source-state="${NAPCAT_SOURCE_STATE}"

COPY --from=build /tmp/NapCat.Shell.zip /app/NapCat.Shell.zip
COPY --from=build /build/LICENSE /usr/share/doc/napcat/LICENSE
