"""Runtime configuration.

Everything is driven by SAMFSCON_* environment variables; the entrypoint derives
the Samba client configuration from the same values before the application
starts.

No file server is required here. Administrators point SAMFSCON at a server when
they sign in; configuring one only sets the default the sign-in form pre-fills.
"""

from __future__ import annotations

import functools
import json
import logging
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

logger = logging.getLogger(__name__)

# How a file server authenticates the people managing it. Not a preference but
# a property of the server: a standalone server has no KDC to issue tickets, and
# a domain member should not be talked to with NTLM when Kerberos is there.
MODE_AD_MEMBER = "ad_member"
MODE_STANDALONE = "standalone"
MODE_AUTO = "auto"


class ServerProfile(BaseModel):
    """A pre-configured file server, offered in the sign-in form.

    Loaded from the JSON file named by SAMFSCON_SERVERS_FILE::

        [
          {
            "id": "fs1",
            "label": "File server, main office",
            "host": "fs1.example.lan",
            "mode": "ad_member",
            "realm": "EXAMPLE.LAN"
          },
          {
            "id": "nas",
            "label": "Backup NAS",
            "host": "192.168.1.50",
            "mode": "standalone",
            "workgroup": "WORKGROUP"
          }
        ]

    Only ``id`` and ``host`` are required. ``mode`` defaults to ``auto``, which
    asks the server itself — see :mod:`samfscon.srv.discovery`.
    """

    id: str
    label: str | None = None
    host: str = ""
    mode: str = MODE_AUTO
    realm: str | None = None
    workgroup: str | None = None

    @field_validator("realm", mode="after")
    @classmethod
    def _upper_realm(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else None

    @field_validator("workgroup", mode="after")
    @classmethod
    def _upper_workgroup(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else None

    @field_validator("mode", mode="after")
    @classmethod
    def _known_mode(cls, value: str) -> str:
        mode = value.strip().lower() or MODE_AUTO
        if mode not in (MODE_AUTO, MODE_AD_MEMBER, MODE_STANDALONE):
            raise ValueError(f"mode must be one of auto, {MODE_AD_MEMBER}, {MODE_STANDALONE}")
        return mode


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SAMFSCON_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Default server (optional) ----------------------------------------
    # Empty is fine: the sign-in form then asks for a server address.
    server_host: str = Field(default="", description="Default file server, e.g. fs1.example.lan")
    server_mode: str = Field(
        default=MODE_AUTO,
        description=f"{MODE_AD_MEMBER}, {MODE_STANDALONE}, or auto to ask the server",
    )
    realm: str = Field(
        default="", description="Kerberos realm of the default server, e.g. EXAMPLE.LAN"
    )
    workgroup: str = Field(
        default="", description="NetBIOS domain of a standalone default server"
    )
    # NoDecode is essential: without it pydantic-settings tries to json.loads
    # the environment value before any validator runs, and a plain "kdc1,kdc2"
    # blows up at startup.
    kdc_hosts: Annotated[list[str], NoDecode] = Field(
        default_factory=list,
        description="Explicit KDC list for the realm; empty means DNS SRV discovery",
    )
    servers_file: Path | None = Field(
        default=None, description="JSON file with pre-configured server profiles"
    )
    allow_custom_servers: bool = Field(
        default=True,
        description="Whether administrators may type an arbitrary server address",
    )

    # --- SMB --------------------------------------------------------------
    # Signing is required rather than negotiated, and SMB3 is the floor. Both
    # are client-side decisions SAMFSCON gets to make: it manages the server's
    # shares and permissions, and doing that over an unsigned SMB1 connection
    # is not a trade worth offering. A server too old for either is one this
    # console refuses rather than accommodates.
    smb_min_protocol: str = Field(default="SMB3", description="Lowest SMB dialect to accept")
    smb_encrypt: bool = Field(
        default=False,
        description="Require SMB3 encryption on top of signing; needs a server that offers it",
    )
    smb_timeout_seconds: int = 30

    # --- Sessions ---------------------------------------------------------
    ccache_dir: Path = Path("/dev/shm/samfscon-ccache")
    session_idle_minutes: int = 60
    login_max_attempts: int = 5
    login_lockout_minutes: int = 5
    cookie_name: str = "samfscon_session"
    cookie_secure: bool = True

    # A standalone server has no Kerberos, so its sessions hold the password in
    # memory for as long as they live (see samfscon.auth.credentials). That is a
    # real trade, and an installation that does not want to make it can refuse
    # standalone sign-ins outright rather than rely on nobody trying.
    allow_standalone: bool = Field(
        default=True,
        description="Whether standalone (non-Kerberos) servers may be managed at all",
    )

    # --- Samba ------------------------------------------------------------
    smb_conf: Path = Path("/etc/samfscon/smb.conf")
    krb5_config: Path = Path("/etc/samfscon/krb5.conf")
    samba_log_level: int = 0

    # --- Runtime ----------------------------------------------------------
    log_level: str = "INFO"
    audit_file: Path = Path("/var/log/samfscon/audit.jsonl")
    worker_threads: int = 8
    operation_timeout_seconds: int = 120
    dev_mode: bool = False

    @field_validator("realm", mode="after")
    @classmethod
    def _upper_realm(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("workgroup", "smb_min_protocol", mode="after")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("server_mode", mode="after")
    @classmethod
    def _known_mode(cls, value: str) -> str:
        mode = value.strip().lower() or MODE_AUTO
        if mode not in (MODE_AUTO, MODE_AD_MEMBER, MODE_STANDALONE):
            logger.error("SAMFSCON_SERVER_MODE=%r is not a known mode; using auto", value)
            return MODE_AUTO
        return mode

    @field_validator("servers_file", mode="before")
    @classmethod
    def _empty_path_is_none(cls, value: object) -> object:
        """Treat an empty environment variable as "not set".

        docker compose substitutes an unset variable with an empty string, and
        pydantic would turn that into ``Path(".")`` — which would make us read
        the working directory as a JSON file.
        """
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("kdc_hosts", mode="before")
    @classmethod
    def _split_hosts(cls, value: object) -> object:
        # Compose passes a comma-separated string; pydantic would otherwise try
        # to read it as JSON.
        if isinstance(value, str):
            return [host.strip() for host in value.split(",") if host.strip()]
        return value

    @field_validator("log_level", mode="after")
    @classmethod
    def _upper_log_level(cls, value: str) -> str:
        return value.strip().upper()

    @property
    def netbios_name(self) -> str:
        return self.workgroup.strip().upper() or (self.realm.split(".")[0] if self.realm else "")

    # -- connection targets -------------------------------------------------

    @property
    def default_target(self):
        """The container's configured server, or None if it has none."""
        from samfscon.srv.target import ServerTarget

        if not self.server_host:
            return None
        return ServerTarget(
            host=self.server_host,
            mode=self.server_mode,
            realm=self.realm or None,
            workgroup=self.workgroup or None,
            kdcs=tuple(self.kdc_hosts),
            label=None,
            profile_id="default",
        )

    def load_profiles(self) -> list[ServerProfile]:
        """Read the server profiles.

        A broken profile file must not stop the application from starting —
        administrators can still type a server address. It is logged loudly
        instead.
        """
        if self.servers_file is None:
            return []
        if not self.servers_file.exists():
            logger.warning("server profile file not found: %s", self.servers_file)
            return []

        try:
            raw = json.loads(self.servers_file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            logger.error("cannot read server profiles from %s: %s", self.servers_file, exc)
            return []

        if isinstance(raw, dict):
            raw = raw.get("servers", [])
        if not isinstance(raw, list):
            logger.error("%s must contain a list of server profiles", self.servers_file)
            return []

        profiles: list[ServerProfile] = []
        for entry in raw:
            try:
                profiles.append(ServerProfile.model_validate(entry))
            except Exception as exc:  # noqa: BLE001 — skip the bad one, keep the rest
                logger.error("ignoring invalid server profile %r: %s", entry, exc)
        return profiles


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # values come from the environment
