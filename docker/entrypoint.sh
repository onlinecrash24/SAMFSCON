#!/bin/sh
#
# SAMFSCON entrypoint.
#
# Generates the Kerberos and Samba client configuration from environment
# variables, prepares the tmpfs credential-cache directory and hands over to
# supervisor. Everything here must work as an unprivileged user, so nothing is
# written outside the directories owned by the samfscon account.

set -eu

SAMFSCON_SERVER_HOST="${SAMFSCON_SERVER_HOST:-}"
SAMFSCON_SERVER_MODE="${SAMFSCON_SERVER_MODE:-auto}"
SAMFSCON_REALM="${SAMFSCON_REALM:-}"
SAMFSCON_WORKGROUP="${SAMFSCON_WORKGROUP:-}"
SAMFSCON_CONF_DIR="${SAMFSCON_CONF_DIR:-/etc/samfscon}"
SAMFSCON_CCACHE_DIR="${SAMFSCON_CCACHE_DIR:-/dev/shm/samfscon-ccache}"
SAMFSCON_TLS_CERT="${SAMFSCON_TLS_CERT:-${SAMFSCON_CONF_DIR}/tls/server.crt}"
SAMFSCON_TLS_KEY="${SAMFSCON_TLS_KEY:-${SAMFSCON_CONF_DIR}/tls/server.key}"
SAMFSCON_SMB_MIN_PROTOCOL="${SAMFSCON_SMB_MIN_PROTOCOL:-SMB3}"

log() { printf '%s [entrypoint] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >&2; }

# A server is optional: administrators can point SAMFSCON at one when they sign
# in. Configuring one only sets the default the sign-in form offers.
if [ -n "${SAMFSCON_REALM}" ]; then
    SAMFSCON_REALM=$(printf '%s' "${SAMFSCON_REALM}" | tr '[:lower:]' '[:upper:]')
fi
if [ -z "${SAMFSCON_WORKGROUP}" ] && [ -n "${SAMFSCON_REALM}" ]; then
    SAMFSCON_WORKGROUP=$(printf '%s' "${SAMFSCON_REALM}" | cut -d. -f1)
fi
if [ -z "${SAMFSCON_SERVER_HOST}" ]; then
    log "no default server configured — the sign-in form will ask for an address"
fi
export SAMFSCON_REALM SAMFSCON_WORKGROUP

mkdir -p "${SAMFSCON_CONF_DIR}" "${SAMFSCON_CONF_DIR}/tls"

# --------------------------------------------------------------------------
# Credential cache directory (tmpfs — never survives a restart, by design)
#
# Only domain-member sessions use it. A standalone session has no ticket; its
# password lives in the application's memory and is gone with the process,
# which is the trade the README spells out.
# --------------------------------------------------------------------------
mkdir -p "${SAMFSCON_CCACHE_DIR}"
chmod 700 "${SAMFSCON_CCACHE_DIR}"
# Stale caches from a previous run of the same container are useless: the
# session store that referenced them is gone.
find "${SAMFSCON_CCACHE_DIR}" -mindepth 1 -maxdepth 1 -type f -delete 2>/dev/null || true

# --------------------------------------------------------------------------
# krb5.conf
#
# Written by the application, not here: it maintains one [realms] block per
# realm anyone signs in to, including the KDC addresses where they are
# configured. All this does is make sure the path is set and the file exists.
# --------------------------------------------------------------------------
KRB5_CONF="${SAMFSCON_CONF_DIR}/krb5.conf"
if [ ! -f "${KRB5_CONF}" ]; then
    {
        echo "# Managed by SAMFSCON — realms are added as administrators sign in."
        echo "[libdefaults]"
        echo "    dns_lookup_realm = false"
        echo "    dns_lookup_kdc = true"
        echo "    rdns = false"
        echo "    forwardable = true"
        echo "    renewable = true"
        echo "    ticket_lifetime = ${SAMFSCON_TICKET_LIFETIME:-10h}"
        echo "    renew_lifetime = ${SAMFSCON_RENEW_LIFETIME:-7d}"
        echo "    default_ccache_name = FILE:${SAMFSCON_CCACHE_DIR}/default"
    } > "${KRB5_CONF}"
fi
export KRB5_CONFIG="${KRB5_CONF}"

# --------------------------------------------------------------------------
# smb.conf — only what the client side needs.
#
# Deliberately without `security = ads`: this container manages standalone
# servers as well as domain members, and the mode is a property of the server
# being managed, not of the container. The application sets what each
# connection needs (see samfscon.auth.credentials); everything below is the
# floor that holds for both.
# --------------------------------------------------------------------------
SMB_CONF="${SAMFSCON_CONF_DIR}/smb.conf"
{
    echo "[global]"
    if [ -n "${SAMFSCON_REALM}" ]; then
        echo "    realm = ${SAMFSCON_REALM}"
    fi
    if [ -n "${SAMFSCON_WORKGROUP}" ]; then
        echo "    workgroup = ${SAMFSCON_WORKGROUP}"
    fi
    # Signing is required rather than negotiated, and SMB1 is off the table.
    # This console changes shares and permissions; doing that over an unsigned
    # connection is not a trade worth offering.
    echo "    client signing = mandatory"
    echo "    client min protocol = ${SAMFSCON_SMB_MIN_PROTOCOL}"
    echo "    client use spnego = yes"
    # Samba would otherwise generate its own krb5.conf and find the KDC for it
    # over DNS SRV, bypassing the one this container writes with the KDC
    # addresses that were configured. See auth/kerberos.kinit_loadparm.
    echo "    create krb5 conf = no"
    echo "    log level = ${SAMFSCON_SAMBA_LOG_LEVEL:-0}"
    echo "    private dir = /var/lib/samfscon"
    echo "    state directory = /var/lib/samfscon"
    echo "    cache directory = /var/cache/samfscon"
    echo "    lock directory = /var/cache/samfscon"
} > "${SMB_CONF}"
export SAMFSCON_SMB_CONF="${SMB_CONF}"

# --------------------------------------------------------------------------
# TLS material — self-signed fallback so a fresh container is usable at once.
# Production deployments mount a real certificate over /etc/samfscon/tls.
#
# A bind mount from the host does not inherit the image's ownership, so the
# configured directory may well not be writable by this unprivileged user. In
# that case we fall back to a directory we do own, rather than starting nginx
# without a certificate.
# --------------------------------------------------------------------------
if [ ! -f "${SAMFSCON_TLS_CERT}" ] || [ ! -f "${SAMFSCON_TLS_KEY}" ]; then
    tls_dir=$(dirname "${SAMFSCON_TLS_CERT}")
    if ! mkdir -p "${tls_dir}" 2>/dev/null || [ ! -w "${tls_dir}" ]; then
        log "WARNING: ${tls_dir} is not writable — using /var/lib/samfscon/tls instead."
        log "         Mount a certificate there, or make the directory writable for uid $(id -u)."
        mkdir -p /var/lib/samfscon/tls
        SAMFSCON_TLS_CERT=/var/lib/samfscon/tls/server.crt
        SAMFSCON_TLS_KEY=/var/lib/samfscon/tls/server.key
    fi

    if [ ! -f "${SAMFSCON_TLS_CERT}" ]; then
        log "no TLS certificate found, generating a self-signed one (replace it for production)"
        if ! openssl req -x509 -newkey rsa:2048 -nodes -days 825 \
            -subj "/CN=${SAMFSCON_PUBLIC_HOST:-samfscon.local}" \
            -addext "subjectAltName=DNS:${SAMFSCON_PUBLIC_HOST:-samfscon.local},DNS:localhost,IP:127.0.0.1" \
            -keyout "${SAMFSCON_TLS_KEY}" -out "${SAMFSCON_TLS_CERT}" 2>/tmp/openssl.err
        then
            log "FATAL: could not create a TLS certificate:"
            cat /tmp/openssl.err >&2
            exit 1
        fi
        chmod 600 "${SAMFSCON_TLS_KEY}"
    fi
fi
export SAMFSCON_TLS_CERT SAMFSCON_TLS_KEY

# --------------------------------------------------------------------------
# nginx configuration. Only the placeholders listed on the envsubst command
# line are substituted, so nginx's own $host/$request_uri survive untouched.
# --------------------------------------------------------------------------
if [ -f "${SAMFSCON_CONF_DIR}/nginx.conf.template" ]; then
    SAMFSCON_PUBLIC_HTTPS_PORT="${SAMFSCON_PUBLIC_HTTPS_PORT:-443}"
    export SAMFSCON_PUBLIC_HTTPS_PORT
    if [ "${SAMFSCON_PUBLIC_HTTPS_PORT}" = "443" ]; then
        REDIRECT_TARGET='https://$host$request_uri'
    else
        REDIRECT_TARGET="https://\$host:${SAMFSCON_PUBLIC_HTTPS_PORT}\$request_uri"
    fi
    export REDIRECT_TARGET
    envsubst '${REDIRECT_TARGET} ${SAMFSCON_TLS_CERT} ${SAMFSCON_TLS_KEY}' \
        < "${SAMFSCON_CONF_DIR}/nginx.conf.template" \
        > "${SAMFSCON_CONF_DIR}/nginx.conf"
fi

mkdir -p /run/samfscon

log "server=${SAMFSCON_SERVER_HOST:-<chosen at sign-in>} mode=${SAMFSCON_SERVER_MODE}"
# `net --version` prints the version but also complains about a missing
# subcommand, and the complaint goes to stdout — so redirecting stderr would
# discard nothing. Pick the version out instead of assuming where the noise
# lands.
samba_version=$(net --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+[^[:space:]]*' | head -n 1)
log "samba client ${samba_version:-unknown}, min protocol ${SAMFSCON_SMB_MIN_PROTOCOL}"

case "${1:-supervisor}" in
    supervisor)
        exec supervisord -c /etc/samfscon/supervisord.conf
        ;;
    api)
        # Single-process mode, useful for development against a mounted source tree.
        exec uvicorn samfscon.main:app --host 0.0.0.0 --port 8000
        ;;
    shell)
        exec /bin/sh
        ;;
    *)
        exec "$@"
        ;;
esac
