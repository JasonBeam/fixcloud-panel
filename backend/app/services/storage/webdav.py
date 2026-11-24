from datetime import datetime
from urllib.parse import quote, unquote, urljoin, urlparse

import httpx
from defusedxml import ElementTree

from .base import StorageEntry, StorageStat


class WebDavStorage:
    source_type = "webdav"

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        display_name: str = "WebDAV",
    ):
        self.base_url = base_url.rstrip("/") + "/"
        self.display_name = display_name
        self._auth = httpx.BasicAuth(username, password)

    def _url(self, path: str) -> str:
        encoded = "/".join(quote(part) for part in path.strip("/").split("/") if part)
        return urljoin(self.base_url, encoded)

    async def status(self) -> dict:
        if not self.base_url.strip():
            return {
                "type": self.source_type,
                "name": self.display_name,
                "connected": False,
                "readOnly": True,
                "message": "尚未配置",
            }
        try:
            async with httpx.AsyncClient(auth=self._auth, timeout=8, follow_redirects=False) as client:
                response = await client.request("PROPFIND", self.base_url, headers={"Depth": "0"})
            connected = response.status_code in {200, 207}
            if response.status_code in {401, 403}:
                message, reason = "认证失败", "authentication"
            elif response.status_code == 404:
                message, reason = "目录不存在", "not_found"
            elif connected:
                message, reason = "已连接", "ok"
            else:
                message, reason = f"连接失败（{response.status_code}）", "connection"
            return {
                "type": self.source_type,
                "name": self.display_name,
                "connected": connected,
                "readOnly": False if connected else True,
                "root": self.base_url,
                "message": message,
                "reasonCode": reason,
            }
        except httpx.TimeoutException:
            return {
                "type": self.source_type,
                "name": self.display_name,
                "connected": False,
                "readOnly": True,
                "root": self.base_url,
                "message": "连接超时",
                "reasonCode": "timeout",
            }
        except httpx.HTTPError:
            return {
                "type": self.source_type,
                "name": self.display_name,
                "connected": False,
                "readOnly": True,
                "root": self.base_url,
                "message": "连接失败",
                "reasonCode": "connection",
            }

    async def list_dir(self, path: str = "/") -> list[StorageEntry]:
        body = """<?xml version="1.0" encoding="utf-8"?>
<d:propfind xmlns:d="DAV:"><d:prop>
<d:displayname/><d:resourcetype/><d:getcontentlength/>
<d:getlastmodified/><d:getetag/>
</d:prop></d:propfind>"""
        async with httpx.AsyncClient(auth=self._auth, timeout=12, follow_redirects=False) as client:
            response = await client.request(
                "PROPFIND",
                self._url(path),
                headers={"Depth": "1", "Content-Type": "application/xml"},
                content=body,
            )
            response.raise_for_status()
        root = ElementTree.fromstring(response.content)
        namespace = {"d": "DAV:"}
        entries: list[StorageEntry] = []
        base_path = unquote(urlparse(self.base_url).path).rstrip("/") + "/"
        requested_path = path.strip("/")
        for item in root.findall("d:response", namespace):
            prop = item.find("d:propstat/d:prop", namespace)
            href = item.findtext("d:href", default="", namespaces=namespace)
            if prop is None:
                continue
            decoded_path = unquote(urlparse(href).path)
            name = prop.findtext("d:displayname", default="", namespaces=namespace)
            if not name:
                name = decoded_path.rstrip("/").split("/")[-1]
            if decoded_path.rstrip("/") == unquote(urlparse(self._url(path)).path).rstrip("/"):
                continue
            relative = decoded_path
            if relative.startswith(base_path):
                relative = relative[len(base_path):]
            relative = relative.strip("/")
            normalized_path = "/" + "/".join(
                part for part in [requested_path, relative.split("/")[-1]] if part
            )
            resource = prop.find("d:resourcetype/d:collection", namespace)
            modified_raw = prop.findtext("d:getlastmodified", default="", namespaces=namespace)
            try:
                modified = datetime.strptime(modified_raw, "%a, %d %b %Y %H:%M:%S %Z")
            except ValueError:
                modified = None
            entries.append(
                StorageEntry(
                    path=normalized_path,
                    name=name,
                    size=int(prop.findtext("d:getcontentlength", default="0", namespaces=namespace) or 0),
                    modified_at=modified,
                    etag=prop.findtext("d:getetag", default="", namespaces=namespace),
                    is_directory=resource is not None,
                )
            )
        return entries

    async def stat(self, path: str) -> StorageStat:
        async with httpx.AsyncClient(auth=self._auth, timeout=8, follow_redirects=False) as client:
            response = await client.head(self._url(path))
            response.raise_for_status()
        modified = None
        if response.headers.get("last-modified"):
            try:
                modified = datetime.strptime(
                    response.headers["last-modified"],
                    "%a, %d %b %Y %H:%M:%S %Z",
                )
            except ValueError:
                pass
        return StorageStat(
            path=path,
            size=int(response.headers.get("content-length", 0)),
            modified_at=modified,
            etag=response.headers.get("etag", ""),
        )

    async def read_bytes(self, path: str) -> bytes:
        async with httpx.AsyncClient(auth=self._auth, timeout=15, follow_redirects=False) as client:
            response = await client.get(self._url(path))
            response.raise_for_status()
        return response.content

    async def write_bytes(
        self,
        path: str,
        content: bytes,
        *,
        overwrite: bool = False,
    ) -> None:
        headers = {"If-None-Match": "*"} if not overwrite else {}
        async with httpx.AsyncClient(auth=self._auth, timeout=20, follow_redirects=False) as client:
            response = await client.put(self._url(path), content=content, headers=headers)
            response.raise_for_status()

    async def copy(self, source: str, destination: str, *, overwrite: bool = False) -> None:
        headers = {
            "Destination": self._url(destination),
            "Overwrite": "T" if overwrite else "F",
        }
        async with httpx.AsyncClient(auth=self._auth, timeout=20, follow_redirects=False) as client:
            response = await client.request("COPY", self._url(source), headers=headers)
            response.raise_for_status()

    async def move(self, source: str, destination: str, *, overwrite: bool = False) -> None:
        headers = {
            "Destination": self._url(destination),
            "Overwrite": "T" if overwrite else "F",
        }
        async with httpx.AsyncClient(auth=self._auth, timeout=20, follow_redirects=False) as client:
            response = await client.request("MOVE", self._url(source), headers=headers)
            response.raise_for_status()

    async def delete(self, path: str) -> None:
        async with httpx.AsyncClient(auth=self._auth, timeout=12, follow_redirects=False) as client:
            response = await client.delete(self._url(path))
            if response.status_code not in {404, 410}:
                response.raise_for_status()
