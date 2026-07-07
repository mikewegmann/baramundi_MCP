import re
import asyncio
import os
from mcp.server.fastmcp import FastMCP
from baramundi_mcp.client import BaramundiClient

ENDPOINT_TYPES = {
    "windows": "endpoints/v2.0/WindowsEndpoints",
    "mac":     "endpoints/v2.0/MacEndpoints",
    "linux":   "endpoints/v2.0/LinuxEndpoints",
    "ios":     "endpoints/v2.0/IosEndpoints",
}

async def _fetch_all(client: BaramundiClient, path: str) -> list[dict]:
    """Holt alle Seiten einer paginierten Ressource parallel (1 Request pro Seite gleichzeitig)."""
    first = await client.get(path, params={"pageSize": 1000, "page": 0})
    items = list(first.get("data", []))
    total_pages = first.get("totalPages", 1)

    if total_pages > 1:
        pages = await asyncio.gather(*[
            client.get(path, params={"pageSize": 1000, "page": p})
            for p in range(1, total_pages)
        ])
        for result in pages:
            items.extend(result.get("data", []))

    return items


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
        Gibt eine einzelne Seite der Geräteliste zurück — NUR für seitenweise Übersichten.
        NICHT für Suchen verwenden! Für Suchen nach Benutzer, Name, IP oder Gruppe
        stattdessen search_devices(query=...) nutzen — ein einziger Call, alle Geräte.

        Args:
            type: Gerätetyp — 'windows' (Standard), 'mac' oder 'linux'.
            limit: Anzahl Geräte pro Seite (Standard: 50, Max: 100).
            page: Seitennummer, beginnend bei 0 (Standard: 0).

        Returns:
            Objekt mit 'data' (Geräteliste), 'totalItems', 'totalPages' und 'currentPage'.
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
        Enthält automatisch macmon NAC-Infos (VLAN, Sperrstatus), falls macmon konfiguriert ist.

        Args:
            device_id: GUID des Geräts (aus list_devices) ODER Hostname (z.B. 'PCSWIT1984').

        Returns:
            Vollständiges Geräte-Objekt mit allen Feldern inkl. Hardware,
            OS-Version, letzter Benutzer, Gruppe, Agent-Status und macmon NAC-Status.
        """
        async with BaramundiClient() as client:
            guid = await _resolve_to_guid(client, device_id)
            if guid is None:
                return {"error": f"Kein Gerät mit Hostname '{device_id}' gefunden."}
            device = await client.get(f"endpoints/v2.0/Endpoints/{guid}")

        # macmon NAC-Infos anreichern (nur wenn macmon konfiguriert)
        if os.environ.get("MACMON_API_URL") and device.get("primaryMAC"):
            device["macmon"] = await _fetch_macmon_status(device["primaryMAC"])

        return device

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


async def _fetch_macmon_status(mac_raw: str) -> dict:
    """Holt VLAN- und NAC-Status aus macmon für eine MAC-Adresse. Gibt {} bei Fehler zurück."""
    from baramundi_mcp.macmon_client import MacmonClient, MacmonAPIError
    from baramundi_mcp.tools.macmon import _normalize_mac

    try:
        mac = _normalize_mac(mac_raw)
    except ValueError:
        return {"error": f"Ungültige MAC-Adresse: {mac_raw}"}

    try:
        async with MacmonClient() as macmon:
            result = await macmon.get(f"api/v1.2/endpoints/{mac}")

            group_id = result.get("endpointGroupId")
            group_detail = {}
            if group_id:
                try:
                    group_detail = await macmon.get(f"api/v1.2/endpointgroups/{group_id}")
                except MacmonAPIError:
                    pass

    except MacmonAPIError as e:
        if e.status_code == 404:
            return {"known": False}
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}

    active_vlans = []
    for session in (result.get("networkSessions") or []):
        if session.get("active") is not False:
            active_vlans.extend(session.get("macVlans") or [])
    active_vlans = sorted(set(active_vlans))

    group_vlans = {}
    if group_detail:
        for level in ("Low", "Medium", "High"):
            vlans = group_detail.get(f"authorizedVlans{level}") or []
            if vlans:
                group_vlans[level.lower()] = vlans

    return {
        "known": True,
        "blocked": not result.get("active", True),
        "authorizedVlans": result.get("authorizedVlans") or [],
        "activeVlans": active_vlans,
        "endpointGroup": {
            "id": group_id,
            "name": group_detail.get("name") if group_detail else None,
            "vlans": group_vlans or None,
        },
        "type": result.get("type"),
    }


def _slim_devices(devices: list[dict]) -> list[dict]:
    keep = {"id", "displayName", "hostName", "primaryIP", "operatingSystem",
            "osVersionText", "lastSeen", "logicalGroup", "clientAgentState",
            "registeredUser", "isDeactivated", "type", "manufacturer", "modelName"}
    return [{k: v for k, v in d.items() if k in keep} for d in devices]
