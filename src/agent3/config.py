"""Configuration read from environment variables only. No secrets in code."""
import os
from dataclasses import dataclass


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    api_token: str | None  # optional; never logged


def load_config(env=None) -> Config:
    env = os.environ if env is None else env
    host = env.get("AGENT3_HOST", "127.0.0.1")  # safe default: loopback only
    raw_port = env.get("AGENT3_PORT", "8080")
    try:
        port = int(raw_port)
    except ValueError:
        raise ConfigError("AGENT3_PORT must be an integer") from None
    if not 0 <= port <= 65535:
        raise ConfigError("AGENT3_PORT must be between 0 and 65535")
    return Config(host=host, port=port, api_token=env.get("AGENT3_API_TOKEN") or None)
