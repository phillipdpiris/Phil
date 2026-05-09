from __future__ import annotations
import base64, time
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from ..config import BotConfig

@dataclass(slots=True)
class KalshiRestClient:
    cfg: BotConfig
    session: requests.Session

    @classmethod
    def build(cls, cfg: BotConfig) -> "KalshiRestClient":
        session = requests.Session()
        session.headers.update({"User-Agent": "kalshi-btc15m-bot/0.1"})
        return cls(cfg=cfg, session=session)

    def public_get(self, path: str, params: dict | None = None, timeout: int = 15) -> dict:
        url = urljoin(self.cfg.public_rest_base_url + "/", path.lstrip("/"))
        response = self.session.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()

    def auth_get(self, path: str, params: dict | None = None, timeout: int = 15) -> dict:
        url = urljoin(self.cfg.rest_base_url + "/", path.lstrip("/"))
        response = self.session.get(url, params=params, headers=build_auth_headers(self.cfg, "GET", path), timeout=timeout)
        response.raise_for_status()
        return response.json()

    def auth_post(self, path: str, payload: dict, timeout: int = 15) -> dict:
        url = urljoin(self.cfg.rest_base_url + "/", path.lstrip("/"))
        response = self.session.post(url, json=payload, headers=build_auth_headers(self.cfg, "POST", path), timeout=timeout)
        response.raise_for_status()
        return response.json() if response.text else {}

    def auth_delete(self, path: str, timeout: int = 15) -> dict:
        url = urljoin(self.cfg.rest_base_url + "/", path.lstrip("/"))
        response = self.session.delete(url, headers=build_auth_headers(self.cfg, "DELETE", path), timeout=timeout)
        response.raise_for_status()
        return response.json() if response.text else {}

def load_private_key(path: str):
    with open(path, "rb") as fh:
        return serialization.load_pem_private_key(fh.read(), password=None, backend=default_backend())

def canonical_signing_path(path: str) -> str:
    parsed = urlparse(path)
    return parsed.path or path.split("?")[0]

def create_signature(private_key, timestamp_ms: str, method: str, path: str) -> str:
    signing_path = canonical_signing_path(path)
    payload = f"{timestamp_ms}{method.upper()}{signing_path}".encode("utf-8")
    signature = private_key.sign(payload, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH), hashes.SHA256())
    return base64.b64encode(signature).decode("utf-8")

def build_auth_headers(cfg: BotConfig, method: str, path: str) -> dict[str, str]:
    if not cfg.api_key_id or not cfg.private_key_path:
        raise RuntimeError("Missing Kalshi credentials")
    ts_ms = str(int(time.time() * 1000))
    private_key = load_private_key(cfg.private_key_path)
    return {"KALSHI-ACCESS-KEY": cfg.api_key_id, "KALSHI-ACCESS-TIMESTAMP": ts_ms,
            "KALSHI-ACCESS-SIGNATURE": create_signature(private_key, ts_ms, method, path),
            "Content-Type": "application/json", "Accept": "application/json"}
