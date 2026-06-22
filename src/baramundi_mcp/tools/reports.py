from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP
from baramundi_mcp.client import BaramundiClient
from baramundi_mcp.tools.devices import ENDPOINT_TYPES, _fetch_all


def register_report_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def report_os_distribution(type: str = "windows") -> dict:
        """
        Erstellt eine Übersicht der Betriebssystem-Versionen aller verwalteten Geräte.
        Hilfreich um veraltete OS-Versionen zu identifizieren (z.B. Windows 7 / Windows 10).

        Args:
            type: Gerätetyp — 'windows' (Standard), 'mac' oder 'linux'.

        Returns:
            Objekt mit 'total' und 'distribution' (Anzahl je OS-Version, absteigend sortiert).
        """
        path = ENDPOINT_TYPES.get(type.lower(), ENDPOINT_TYPES["windows"])
        distribution: dict[str, int] = {}

        async with BaramundiClient() as client:
            for device in await _fetch_all(client, path):
                os_ver = device.get("operatingSystem") or "Unbekannt"
                distribution[os_ver] = distribution.get(os_ver, 0) + 1

        sorted_dist = dict(sorted(distribution.items(), key=lambda x: x[1], reverse=True))
        return {"total": sum(distribution.values()), "distribution": sorted_dist}

    @mcp.tool()
    async def report_inactive_devices(
        days: int = 30,
        type: str = "windows",
        limit: int = 50,
    ) -> dict:
        """
        Findet Geräte, die seit einer bestimmten Anzahl von Tagen nicht mehr gesehen wurden.

        Args:
            days: Schwellwert in Tagen (Standard: 30).
            type: Gerätetyp — 'windows' (Standard), 'mac' oder 'linux'.
            limit: Maximale Anzahl zurückgegebener Geräte (Standard: 50).

        Returns:
            Objekt mit 'total' und 'devices' (sortiert nach daysSinceLastSeen, absteigend).
        """
        path = ENDPOINT_TYPES.get(type.lower(), ENDPOINT_TYPES["windows"])
        now = datetime.now(timezone.utc)
        inactive = []

        async with BaramundiClient() as client:
            for d in await _fetch_all(client, path):
                last = d.get("lastSeen")
                if not last:
                    continue
                delta = (now - datetime.fromisoformat(last.replace("Z", "+00:00"))).days
                if delta >= days:
                    inactive.append({
                        "hostName": d.get("hostName"),
                        "primaryIP": d.get("primaryIP"),
                        "lastSeen": last,
                        "daysSinceLastSeen": delta,
                        "logicalGroup": d.get("logicalGroup"),
                        "registeredUser": d.get("registeredUser"),
                        "clientAgentState": d.get("clientAgentState"),
                    })

        inactive.sort(key=lambda x: x["daysSinceLastSeen"], reverse=True)
        return {"total": len(inactive), "devices": inactive[:limit]}

    @mcp.tool()
    async def report_agent_health(type: str = "windows") -> dict:
        """
        Zeigt den Gesundheitsstatus des baramundi Client-Agenten über alle Geräte hinweg.
        Identifiziert Geräte mit gestopptem oder fehlendem Agent.

        Args:
            type: Gerätetyp — 'windows' (Standard), 'mac' oder 'linux'.

        Returns:
            Objekt mit 'total', 'byState' (Anzahl je Agent-Status) und
            'problematic' (Geräte mit nicht laufendem Agent).
        """
        path = ENDPOINT_TYPES.get(type.lower(), ENDPOINT_TYPES["windows"])
        by_state: dict[str, int] = {}
        problematic = []

        async with BaramundiClient() as client:
            for d in await _fetch_all(client, path):
                state = d.get("clientAgentState") or "Unknown"
                by_state[state] = by_state.get(state, 0) + 1
                if state != "Running":
                    problematic.append({
                        "hostName": d.get("hostName"),
                        "primaryIP": d.get("primaryIP"),
                        "clientAgentState": state,
                        "clientAgentVersion": d.get("clientAgentVersion"),
                        "logicalGroup": d.get("logicalGroup"),
                        "lastSeen": d.get("lastSeen"),
                    })

        return {
            "total": sum(by_state.values()),
            "byState": dict(sorted(by_state.items(), key=lambda x: x[1], reverse=True)),
            "problematic": problematic,
        }

    @mcp.tool()
    async def report_failed_jobs(limit: int = 50) -> dict:
        """
        Listet Job-Instanzen mit Fehlern auf, sortiert nach Fehleranzahl.

        Args:
            limit: Maximale Anzahl zurückgegebener Einträge (Standard: 50).

        Returns:
            Objekt mit 'total' und 'instances' (sortiert nach erroneousExecutions, absteigend).
        """
        async with BaramundiClient() as client:
            result = await client.get("jobs/v2.0/JobInstances", params={"$top": 200})

        failed = [
            {
                "endpointName": i.get("endpointName"),
                "jobDefinitionDisplayName": i.get("jobDefinitionDisplayName"),
                "erroneousExecutions": i.get("erroneousExecutions", 0),
                "successfulExecutions": i.get("successfulExecutions", 0),
                "state": i.get("state"),
                "stateDescription": i.get("stateDescription"),
                "lastAction": i.get("lastAction"),
            }
            for i in result.get("data", [])
            if (i.get("erroneousExecutions") or 0) > 0
        ]
        failed.sort(key=lambda x: x["erroneousExecutions"], reverse=True)
        return {"total": len(failed), "instances": failed[:limit]}
