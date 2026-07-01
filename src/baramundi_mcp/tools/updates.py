from mcp.server.fastmcp import FastMCP
from baramundi_mcp.client import BaramundiClient
from baramundi_mcp.tools.devices import _fetch_all, _resolve_to_guid


def register_update_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_device_update_status(device_id: str) -> dict:
        """
        Gibt den Windows-Update-Status eines einzelnen Geräts zurück.
        Zeigt fehlende Updates (Critical, Security, Other) sowie letzten Scan- und Update-Zeitpunkt.

        Args:
            device_id: Hostname (z.B. 'PCSWIT1984') oder GUID des Geräts.

        Returns:
            Objekt mit Update-Profil, Anzahl fehlender Updates je Kategorie,
            Zeitpunkt des letzten Inventars und letzten erfolgreichen Updates.
        """
        async with BaramundiClient() as client:
            guid = await _resolve_to_guid(client, device_id)
            if guid is None:
                return {"error": f"Kein Gerät mit Hostname '{device_id}' gefunden."}
            result = await client.get(f"updatemanagement/v2.0/WindowsEndpoints/{guid}")

        missing_total = (
            (result.get("missingCriticalUpdates") or 0)
            + (result.get("missingSecurityUpdates") or 0)
            + (result.get("missingOtherUpdates") or 0)
        )
        return {
            "endpointName": result.get("endpointName"),
            "updateProfile": result.get("updateProfileName"),
            "updateState": result.get("updateState"),
            "missing": {
                "critical": result.get("missingCriticalUpdates", 0),
                "security": result.get("missingSecurityUpdates", 0),
                "other": result.get("missingOtherUpdates", 0),
                "total": missing_total,
            },
            "featureUpdatesAvailable": result.get("featureUpdatesAvailable"),
            "deferredUpdates": result.get("deferredUpdates"),
            "blockedUpdates": result.get("blockedUpdates"),
            "lastInventory": result.get("lastInventory"),
            "lastSuccessfulUpdate": result.get("lastSuccessfulUpdate"),
            "targetReleaseVersion": result.get("targetReleaseVersion"),
        }

    @mcp.tool()
    async def report_update_compliance(
        min_missing: int = 1,
        category: str = "any",
        limit: int = 50,
    ) -> dict:
        """
        Zeigt eine Compliance-Übersicht aller Windows-Geräte nach Update-Status.
        Ideal um veraltete oder nicht gepatchte Geräte zu identifizieren.

        Args:
            min_missing: Mindestanzahl fehlender Updates, damit ein Gerät gelistet wird
                         (Standard: 1 — alle Geräte mit mindestens einem fehlenden Update).
            category: Welche Update-Kategorie berücksichtigt werden soll:
                      'critical', 'security', 'other' oder 'any' (Standard).
            limit: Maximale Anzahl Geräte im Ergebnis (Standard: 50).

        Returns:
            Objekt mit 'summary' (Gesamtübersicht) und 'devices' (sortiert nach fehlenden Updates).
        """
        async with BaramundiClient() as client:
            all_endpoints = await _fetch_all(client, "updatemanagement/v2.0/WindowsEndpoints")

        cat = category.lower()
        result_devices = []
        total_critical = 0
        total_security = 0
        fully_patched = 0

        for e in all_endpoints:
            crit = e.get("missingCriticalUpdates") or 0
            sec = e.get("missingSecurityUpdates") or 0
            other = e.get("missingOtherUpdates") or 0
            total = crit + sec + other

            total_critical += crit
            total_security += sec
            if total == 0:
                fully_patched += 1

            if cat == "critical":
                count = crit
            elif cat == "security":
                count = sec
            elif cat == "other":
                count = other
            else:
                count = total

            if count >= min_missing:
                result_devices.append({
                    "endpointName": e.get("endpointName"),
                    "updateProfile": e.get("updateProfileName"),
                    "missingCritical": crit,
                    "missingSecurity": sec,
                    "missingOther": other,
                    "missingTotal": total,
                    "lastInventory": e.get("lastInventory"),
                    "lastSuccessfulUpdate": e.get("lastSuccessfulUpdate"),
                    "featureUpdatesAvailable": e.get("featureUpdatesAvailable"),
                })

        result_devices.sort(key=lambda x: x["missingTotal"], reverse=True)

        return {
            "summary": {
                "totalDevices": len(all_endpoints),
                "fullyPatched": fully_patched,
                "withMissingUpdates": len(result_devices),
                "totalMissingCritical": total_critical,
                "totalMissingSecurity": total_security,
            },
            "devices": result_devices[:limit],
        }
