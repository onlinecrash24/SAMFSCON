# syntax=docker/dockerfile:1.7
#
# SAMFSCON — Samba FileServer Console
#
# Debian instead of Alpine on purpose: the runtime needs python3-samba, which
# exists only as a distribution package. There is no PyPI equivalent, and
# rebuilding the Samba python bindings by hand is not worth the trouble — they
# are what every protocol in this application is spoken through.

ARG DEBIAN_RELEASE=trixie
ARG NODE_VERSION=22

# ---------------------------------------------------------------------------
# Stage 1 — frontend bundle
# ---------------------------------------------------------------------------
FROM node:${NODE_VERSION}-slim AS frontend

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# Copied file by file rather than `COPY frontend/ ./`: that form would drop the
# host's node_modules on top of the ones just installed, and a Windows-built
# tsc shim cannot run here. The .dockerignore covers this too — this makes the
# build correct even without it.
COPY frontend/index.html frontend/tsconfig.json frontend/vite.config.ts ./
COPY frontend/src ./src
COPY frontend/public ./public

RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2 — runtime
# ---------------------------------------------------------------------------
FROM debian:${DEBIAN_RELEASE}-slim AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# python3-samba carries the SMB and DCE/RPC bindings this application is built
# on. samba-common-bin gives us `net` and `testparm` for cross-checking a
# result against the server from a shell, smbclient the same for shares, and
# krb5-user gives klist/kinit for the domain-member diagnostics.
#
# Deliberately NOT installed: the `samba` package itself. That is the server,
# and this container is a client — installing it would drag smbd, nmbd and the
# provisioning stack in for nothing.
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        python3-venv \
        python3-pip \
        python3-samba \
        smbclient \
        samba-common-bin \
        libsmbclient \
        krb5-user \
        ca-certificates \
        nginx \
        supervisor \
        tini \
        curl \
        openssl \
        gettext-base \
    && rm -rf /var/lib/apt/lists/*

# --system-site-packages keeps the distribution's samba bindings visible inside
# the venv; without it every `import samba` fails.
RUN python3 -m venv --system-site-packages /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /opt/samfscon

COPY backend/pyproject.toml ./
COPY backend/samfscon ./samfscon
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

COPY --from=frontend /build/dist /srv/samfscon/www
COPY docker/nginx.conf.template /etc/samfscon/nginx.conf.template
COPY docker/supervisord.conf /etc/samfscon/supervisord.conf
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Non-root. The ccache directory lives on tmpfs and is created by the
# entrypoint, since /dev/shm is mounted fresh on every start.
# The tls/servers directories must exist in the image and belong to samfscon:
# docker seeds a named volume from the image directory, permissions included.
# Without them, a volume mounted at /etc/samfscon/tls arrives owned by root and
# the entrypoint cannot write the fallback certificate.
RUN groupadd --gid 1000 samfscon \
    && useradd --uid 1000 --gid 1000 --home-dir /var/lib/samfscon --create-home samfscon \
    && mkdir -p /var/lib/samfscon/tls /var/log/samfscon /var/cache/samfscon \
                /etc/samfscon/tls /etc/samfscon/servers \
                /var/lib/nginx /var/log/nginx /run/samfscon \
    && chown -R samfscon:samfscon /var/lib/samfscon /var/log/samfscon /var/cache/samfscon \
                              /etc/samfscon /var/lib/nginx /var/log/nginx /run/samfscon \
                              /srv/samfscon

USER samfscon

# Ports above 1024 so nginx can bind without extra capabilities.
EXPOSE 8080 8443

# The endpoint answers in about two milliseconds. Five seconds still ran out on
# a host bringing thirty containers up at once — what timed out was starting
# the process that asks, not the answer. A tighter limit measures the machine's
# load rather than this application's health.
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8080/api/v1/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]
CMD ["supervisor"]

# ---------------------------------------------------------------------------
# Stage 3 — test image
#
# Adds the test suite and pytest on top of the runtime image, so the tests run
# against exactly the image that ships rather than against a separately
# installed set of dependencies. Selected with SAMFSCON_TARGET=test, which
# docker-compose.yml passes through as the build target.
# ---------------------------------------------------------------------------
FROM runtime AS test

USER root
COPY backend/tests /opt/samfscon/tests
RUN pip install --no-cache-dir "pytest>=8.2" "pytest-asyncio>=0.23" "httpx>=0.27" \
    && chown -R samfscon:samfscon /opt/samfscon
USER samfscon
