"""Student photos live in a private Supabase Storage bucket. Only the server holds the key,
so photos are never publicly reachable; the API streams them out at /media/<filename>."""
import httpx

from . import config


class StorageError(Exception):
    pass


def _url(filename: str) -> str:
    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_KEY:
        raise StorageError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set on the server")
    return f"{config.SUPABASE_URL}/storage/v1/object/{config.PHOTO_BUCKET}/{filename}"


def _headers() -> dict[str, str]:
    key = config.SUPABASE_SERVICE_KEY
    # New "sb_secret_..." keys go only in the apikey header; Supabase rejects them as a Bearer token.
    # The legacy service_role key is a JWT ("eyJ...") and also needs the Authorization header.
    headers = {"apikey": key}
    if key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {key}"
    return headers


def _call(method: str, filename: str, **kwargs) -> httpx.Response:
    try:
        return httpx.request(method, _url(filename), headers={**_headers(), **kwargs.pop("headers", {})},
                             timeout=20, **kwargs)
    except httpx.HTTPError as e:
        raise StorageError(f"Photo storage is unreachable: {e}") from e


def upload(filename: str, content: bytes, content_type: str) -> None:
    r = _call("POST", filename, content=content, headers={"Content-Type": content_type})
    if r.status_code != 200:
        raise StorageError(f"Photo upload failed ({r.status_code}): {r.text[:200]}")


def download(filename: str) -> tuple[bytes, str] | None:
    """Returns (bytes, content type), or None if the photo doesn't exist."""
    r = _call("GET", filename)
    if r.status_code in (400, 404):  # Supabase answers 400 "not_found" for missing objects
        return None
    if r.status_code != 200:
        raise StorageError(f"Photo download failed ({r.status_code}): {r.text[:200]}")
    return r.content, r.headers.get("content-type", "application/octet-stream")


def delete(filename: str) -> None:
    """Best effort: a leftover photo is harmless, so failures are ignored."""
    try:
        _call("DELETE", filename)
    except StorageError:
        pass
