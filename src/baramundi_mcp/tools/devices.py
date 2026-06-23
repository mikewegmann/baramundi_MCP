import re
from mcp.server.fastmcp import FastMCP
from baramundi_mcp.client import BaramundiClient

ENDPOINT_TYPES = {
    "windows": "endpoints/v2.0/WindowsEndpoints",
    "mac":     "endpoints/v2.0/MacEndpoints",
    "linux":   "endpoints/v2.0/LinuxEndpoints",
}

async def _fetch_all(client: BaramundiClient, path: str) -> list[dict]:
    """Holt alle Einträge einer paginierten Ressource in möglichst wenigen Requests.
    pageSize=1000 holt bis zu 1000 Items auf einmal; bei mehr wird paginiert."""
    all_items: list[dict] = []
    page = 0

    while True:
        result = await client.get(path, params={"pageSize": 1000, "page": page})
        batch = result.get("data", [])
        if not batch:
            break
        all_items.extend(batch)
        if page >= result.get("totalPages", 1) - 1:
            break
        page += 1

    return all_items


async def _resolve_to_guid(client: BaramundiClient, device_id: str) -> str | None:
    """Löst Hostname oder GUID zu einer Endpoint-GUID auf. None = nicht gefunden."""
    is_guid = bool(re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        device_id.strip(),
    ))
    if is_guid:
        return device_id.strip()
    hostname = device_id.strip().upper()
    for path in ENDPOINT_TYPES.values():
        for d in await _fetch_all(client, path):
            if (d.get("hostName") or "").upper() == hostname:
                return d["id"]
    return None


def register_device_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def list_devices(
        type: str = "windows",
        limit: int = 50,
        page: int = 0,
    ) -> dict:
        """
        Listet verwaltete Geräte/Endpoints im baramundi Management Center auf.

        Args:
            type: Gerätetyp — 'windows' (Standard), 'mac' oder 'linux'.
            limit: Anzahl Geräte pro Seite (Standard: 50, Max: 100).
            page: Seitennummer, beginnend bei 0 (Standard: 0).

        Returns:
            Objekt mit 'data' (Geräteliste), 'totalItems', 'totalPages' und 'currentPage'.
            Wichtige Felder je Gerät: id, displayName, hostName, primaryIP,
            operatingSystem, lastSeen, logicalGroup, clientAgentState, registeredUser.
        """
        path = ENDPOINT_TYPES.get(type.lower(), ENDPOINT_TYPES["windows"])
        async with BaramundiClient() as client:
            result = await client.get(path, params={"page": page})
        if isinstance(result, dict) and "data" in result:
            return {
                "data": _slim_devices(result["data"]),
                "totalItems": result.get("totalItems"),
                "totalPages": result.get("totalPages"),
                "currentPage": result.get("currentPage"),
            }
        return result

    @mcp.tool()
    async def get_device(device_id: str) -> dict:
        """
        Ruft alle Details zu einem einzelnen Gerät ab.
        Akzeptiert sowohl eine GUID als auch einen Hostnamen (z.B. 'PCSWIT1984').

        Args:
            device_id: GUID des Geräts (aus list_devices) ODER Hostname (z.B. 'PCSWIT1984').

        Returns:
            Vollständiges Geräte-Objekt mit allen Feldern inkl. Hardware,
            OS-Version, letzter Benutzer, Gruppe, Agent-Status, etc.
        """
        async with BaramundiClient() as client:
            guid = await _resolve_to_guid(client, device_id)
            if guid is None:
                return {"error": f"Kein Gerät mit Hostname '{device_id}' gefunden."}
            return await client.get(f"endpoints/v2.0/Endpoints/{guid}")

    @mcp.tool()
    async def get_software_inventory(
        device_id: str,
        query: str = "",
    ) -> dict:
        """
        Gibt die installierte Software auf einem Gerät zurück.
        Akzeptiert Hostname (z.B. 'PCSWIT1984') oder GUID.

        Args:
            device_id: Hostname oder GUID des Geräts.
            query: Optionaler Suchbegriff im Software-Namen (z.B. 'Chrome', 'Office').
                   Leer = alle installierten Programme.

        Returns:
            Objekt mit 'total' und 'software' (alphabetisch sortiert).
            Felder je Eintrag: name, version, publisher, installDate.
        """
        async with BaramundiClient() as client:
            guid = await _resolve_to_guid(client, device_id)
            if guid is None:
                return {"error": f"Kein Gerät mit Hostname '{device_id}' gefunden."}
            raw = await _fetch_all(client, f"software/v2.0/WindowsEndpoints/{guid}/InstalledWindowsSoftware")

        if query:
            q = query.strip().lower()
            raw = [s for s in raw if q in (s.get("name") or "").lower()]

        software = sorted(
            [
                {
                    "name": s.get("name"),
                    "version": s.get("version"),
                    "publisher": s.get("publisher"),
                    "installDate": s.get("installDate"),
                }
                for s in raw
            ],
            key=lambda x: (x.get("name") or "").lower(),
        )
        return {"total": len(software), "software": software}

    @mcp.tool()
    async def search_devices(
        query: str,
        type: str = "windows",
        limit: int = 20,
    ) -> dict:
        """
        Sucht Geräte nach Hostname, IP-Adresse, Benutzer oder Gruppe.
        Die Suche ist case-insensitiv und prüft auf Teilübereinstimmung.

        Args:
            query: Suchbegriff — wird in Hostname, IP, registeredUser und
                   logicalGroup gesucht (z.B. 'PCSWIT1984', '192.168.50', 'Köln').
            type: Gerätetyp — 'windows' (Standard), 'mac' oder 'linux'.
            limit: Maximale Anzahl Ergebnisse (Standard: 20).

        Returns:
            Objekt mit 'data' (gefundene Geräte) und 'total'.
        """
        path = ENDPOINT_TYPES.get(type.lower(), ENDPOINT_TYPES["windows"])
        q = query.strip().lower()
        matches = []

        async with BaramundiClient() as client:
            for d in await _fetch_all(client, path):
                searchable = " ".join(filter(None, [
                    d.get("hostName") or "",
                    d.get("primaryIP") or "",
                    d.get("registeredUser") or "",
                    d.get("logicalGroup") or "",
                    d.get("displayName") or "",
                ])).lower()
                if q in searchable:
                    matches.append(d)

        return {"data": _slim_devices(matches[:limit]), "total": len(matches)}


def _slim_devices(devices: list[dict]) -> list[dict]:
    keep = {"id", "displayName", "hostName", "primaryIP", "operatingSystem",
            "osVersionText", "lastSeen", "logicalGroup", "clientAgentState",
            "registeredUser", "isDeactivated", "type", "manufacturer", "modelName"}
    return [{k: v for k, v in d.items() if k in keep} for d in devices]
