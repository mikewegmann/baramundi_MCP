import re
from mcp.server.fastmcp import FastMCP
from baramundi_mcp.macmon_client import MacmonClient, MacmonAPIError
from baramundi_mcp.client import BaramundiClient
from baramundi_mcp.tools.devices import _resolve_to_guid


def _normalize_mac(mac: str) -> str:
    """Normalisiert MAC auf macmon-Format: AA-BB-CC-DD-EE-FF"""
    clean = mac.upper().replace(":", "").replace("-", "").replace(".", "")
    if len(clean) != 12 or not all(c in "0123456789ABCDEF" for c in clean):
        raise ValueError(f"Ungültige MAC-Adresse: '{mac}'")
    return "-".join(clean[i:i+2] for i in range(0, 12, 2))


def _is_mac(value: str) -> bool:
    return bool(re.fullmatch(
        r"[0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}[:\-]"
        r"[0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}",
        value.strip(),
    ) or re.fullmatch(r"[0-9a-fA-F]{12}", value.strip()))


async def _resolve_mac(identifier: str) -> tuple[str, str]:
    """
    Gibt (mac_normalisiert, hostname) zurück.
    Akzeptiert direkte MAC-Adresse oder Hostname (Lookup via baramundi).
    """
    if _is_mac(identifier):
        return _normalize_mac(identifier), identifier

    # Hostname → MAC via baramundi
    async with BaramundiClient() as bmc:
        guid = await _resolve_to_guid(bmc, identifier)
        if not guid:
            raise ValueError(f"Kein Gerät mit Hostname '{identifier}' in baramundi gefunden.")
        device = await bmc.get(f"endpoints/v2.0/Endpoints/{guid}")

    mac_raw = device.get("primaryMAC")
    if not mac_raw:
        raise ValueError(f"Gerät '{identifier}' hat keine MAC-Adresse in baramundi.")

    return _normalize_mac(mac_raw), device.get("hostName", identifier)


def register_macmon_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_vlan_status(identifier: str) -> dict:
        """
        Fragt den VLAN- und NAC-Status eines Clients in macmon ab.
        Akzeptiert einen Hostnamen (z.B. 'PCSWIT1984') oder eine MAC-Adresse.
        Bei Hostnamen wird die MAC automatisch über baramundi ermittelt.

        Args:
            identifier: Hostname (z.B. 'PCSWIT1984') oder MAC-Adresse
                        (Format: 'AA:BB:CC:DD:EE:FF' oder 'AABBCCDDEEFF').

        Returns:
            Objekt mit:
            - mac: MAC-Adresse im macmon-Format
            - active: True = Client aktiv/erlaubt, False = gesperrt
            - authorizedVlans: Direkt am Client konfigurierte VLAN-IDs
            - activeVlans: Aktuell aktive VLANs aus laufender Netzwerk-Session
            - lastIp: Zuletzt gesehene IP-Adresse
            - online: Aktuell im Netz sichtbar?
            - endpointGroup: Zugewiesene Endpoint-Gruppe (bestimmt VLAN-Policy)
        """
        try:
            mac, hostname = await _resolve_mac(identifier)
        except ValueError as e:
            return {"error": str(e)}

        try:
            async with MacmonClient() as macmon:
                result = await macmon.get(f"api/v1.2/endpoints/{mac}")

                # Endpoint-Gruppe nachladen wenn VLANs dort konfiguriert sind
                group_id = result.get("endpointGroupId")
                group_detail = {}
                if group_id:
                    try:
                        group_detail = await macmon.get(f"api/v1.2/endpointgroups/{group_id}")
                    except MacmonAPIError:
                        pass

        except MacmonAPIError as e:
            if e.status_code == 404:
                return {"error": f"MAC {mac} ist macmon nicht bekannt."}
            return {"error": str(e)}

        # Aktive VLANs aus Network-Sessions extrahieren
        active_vlans = []
        for session in (result.get("networkSessions") or []):
            vlans = session.get("macVlans") or []
            if session.get("active") is not False:
                active_vlans.extend(vlans)
        active_vlans = sorted(set(active_vlans))

        status = result.get("endpointDeviceStatus") or {}
        authorized_vlans = result.get("authorizedVlans") or []

        # VLAN-Policy aus Gruppe (Low/Medium/High) zusammenfassen
        group_vlans = {}
        if group_detail:
            for level in ("Low", "Medium", "High"):
                vlans = group_detail.get(f"authorizedVlans{level}") or []
                if vlans:
                    group_vlans[level.lower()] = vlans

        return {
            "hostname": hostname if not _is_mac(identifier) else None,
            "mac": mac,
            "active": result.get("active"),
            "blocked": not result.get("active", True),
            "authorizedVlans": authorized_vlans,
            "activeVlans": active_vlans,
            "lastIp": status.get("lastIp"),
            "online": status.get("online"),
            "lastSeen": status.get("lastSeen"),
            "endpointGroup": {
                "id": group_id,
                "name": group_detail.get("name") if group_detail else None,
                "vlans": group_vlans or None,
            },
            "type": result.get("type"),
        }
