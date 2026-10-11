FROM debian:bookworm-slim AS build

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git cmake g++ make gperf libssl-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Official Bot API 10.3; recursive update checks out the pinned TDLib submodule.
RUN git init /build/telegram-bot-api \
    && cd /build/telegram-bot-api \
    && git remote add origin https://github.com/tdlib/telegram-bot-api.git \
    && git fetch --depth 1 origin e3e9dd8e5b3d7ab8537cd5a10dc31d5ffa8f82d1 \
    && git checkout --detach FETCH_HEAD \
    && git submodule update --init --recursive --depth 1

RUN cmake -S /build/telegram-bot-api -B /build/output -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/opt/telegram-bot-api \
    && cmake --build /build/output --target install --parallel 2

FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates libssl3 zlib1g libstdc++6 bash iproute2 coreutils \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 kisara \
    && useradd --uid 10001 --gid 10001 --no-create-home kisara \
    && mkdir -p /var/lib/telegram-bot-api /opt/kisara \
    && chown 10001:10001 /var/lib/telegram-bot-api

COPY --from=build /opt/telegram-bot-api/bin/telegram-bot-api /usr/local/bin/telegram-bot-api
COPY --from=build /build/telegram-bot-api/LICENSE_1_0.txt /usr/share/doc/telegram-bot-api/LICENSE_1_0.txt
COPY --from=build /build/telegram-bot-api/td/LICENSE_1_0.txt /usr/share/doc/telegram-bot-api/TDLib-LICENSE_1_0.txt
COPY --from=build /build/telegram-bot-api/td/README.md /usr/share/doc/telegram-bot-api/TDLib-README.md
COPY deploy/telegram-bot-api-entrypoint.sh deploy/telegram-bot-api-probe.sh /opt/kisara/
RUN chmod 755 /opt/kisara/telegram-bot-api-*.sh

WORKDIR /var/lib/telegram-bot-api
USER 10001:10001
ENTRYPOINT ["/opt/kisara/telegram-bot-api-entrypoint.sh"]
