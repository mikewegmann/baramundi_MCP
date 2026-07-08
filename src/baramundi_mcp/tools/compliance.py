from mcp.server.fastmcp import FastMCP
from baramundi_mcp.client import BaramundiClient
from baramundi_mcp.tools.devices import _fetch_all, _resolve_to_guid


def register_compliance_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def list_compliance_rules() -> dict:
        """
        Listet alle definierten Compliance-Regeln im baramundi Management Center.

        Returns:
            Objekt mit 'total' und 'rules' (id, ruleName, type, severity, description).
        """
        async with BaramundiClient() as client:
            result = await client.get("compliance/v2.0/Rules", params={"pageSize": 200, "page": 0})
        rules = [
            {
                "id": r.get("id"),
                "ruleName": r.get("ruleName"),
                "type": r.get("type"),
                "severity": r.get("severity"),
                "description": r.get("description"),
            }
            for r in result.get("data", [])
        ]
        return {"total": len(rules), "rules": rules}

    @mcp.tool()
    async def report_compliance_overview(
        state: str = "",
        limit: int = 50,
    ) -> dict:
        """
        Gibt eine Compliance-Übersicht aller verwalteten Geräte zurück.
        Zeigt wie viele Geräte compliant, nicht-compliant oder unbekannt sind.

        Args:
            state: Optionaler Filter auf einen bestimmten Status:
                   'Compliant', 'NotCompliantWarning', 'Unknown', 'ComplianceInactive'.
                   Leer = alle Geräte.
            limit: Maximale Anzahl Geräte in der Detailliste (Standard: 50).

        Returns:
            Objekt mit 'summary' (Anzahl je Status) und 'devices' (gefilterte Liste).
        """
        async with BaramundiClient() as client:
            all_endpoints = await _fetch_all(client, "compliance/v2.0/Endpoints")

        summary: dict[str, int] = {}
        for e in all_endpoints:
            s = e.get("complianceState") or "Unknown"
            summary[s] = summary.get(s, 0) + 1

        q = state.strip()
        filtered = [
            {
                "endpointName": e.get("endpointName"),
                "endpointId": e.get("endpointId"),
                "complianceState": e.get("complianceState"),
                "checkCategory": e.get("checkCategory"),
            }
            for e in all_endpoints
            if not q or (e.get("complianceState") or "").lower() == q.lower()
        ]

        return {
            "summary": dict(sorted(summary.items(), key=lambda x: -x[1])),
            "totalDevices": len(all_endpoints),
            "devices": filtered[:limit],
        }

    @mcp.tool()
    async def get_device_compliance(device_id: str) -> dict:
        """
        Gibt den Compliance-Status eines einzelnen Geräts zurück.
        Akzeptiert Hostname (z.B. 'PCSWIT1984') oder GUID.

        Args:
            device_id: Hostname oder GUID des Geräts.

        Returns:
            Objekt mit complianceState, checkCategory und den aktiven Compliance-Regeln.
        """
        async with BaramundiClient() as client:
            guid = await _resolve_to_guid(client, device_id)
            if guid is None:
                return {"error": f"Kein Gerät mit Hostname '{device_id}' gefunden."}
            all_endpoints = await _fetch_all(client, "compliance/v2.0/Endpoints")

        match = next(
            (e for e in all_endpoints if e.get("endpointId") == guid),
            None,
        )
        if match is None:
            return {
                "endpointId": guid,
                "complianceState": "NotTracked",
                "message": "Dieses Gerät wird in baramundi Compliance nicht erfasst.",
            }

        return {
            "endpointId": match.get("endpointId"),
            "endpointName": match.get("endpointName"),
            "complianceState": match.get("complianceState"),
            "checkCategory": match.get("checkCategory"),
            "checkDisabledFrom": match.get("checkDisabledFrom"),
            "checkDisabledUntil": match.get("checkDisabledUntil"),
        }

    @mcp.tool()
    async def check_software_compliance(
        device_id: str,
        required: list[str] = [],
        prohibited: list[str] = [],
    ) -> dict:
        """
        Prüft auf einem Gerät, ob Pflicht-Software installiert und
        verbotene Software NICHT installiert ist.

        Args:
            device_id: Hostname (z.B. 'PCSWIT1984') oder GUID des Geräts.
            required: Liste von Softwarenamen, die vorhanden sein müssen
                      (z.B. ['CrowdStrike', 'Microsoft 365']).
            prohibited: Liste von Softwarenamen, die NICHT vorhanden sein dürfen
                        (z.B. ['TeamViewer', 'AnyDesk']).

        Returns:
            Objekt mit 'compliant' (bool), 'missing' (fehlende Pflicht-Software)
            und 'found_prohibited' (gefundene verbotene Software).
        """
        if not required and not prohibited:
            return {"error": "Mindestens 'required' oder 'prohibited' muss angegeben werden."}

        async with BaramundiClient() as client:
            guid = await _resolve_to_guid(client, device_id)
            if guid is None:
                return {"error": f"Kein Gerät mit Hostname '{device_id}' gefunden."}
            installed_raw = await _fetch_all(
                client,
                f"software/v2.0/WindowsEndpoints/{guid}/InstalledWindowsSoftware",
            )

        installed_names = [(s.get("name") or "").lower() for s in installed_raw]

        missing = [
            req for req in required
            if not any(req.lower() in name for name in installed_names)
        ]
        found_prohibited = [
            proh for proh in prohibited
            if any(proh.lower() in name for name in installed_names)
        ]

        compliant = not missing and not found_prohibited
        return {
            "compliant": compliant,
            "device": device_id,
            "checked": {"required": required, "prohibited": prohibited},
            "missing": missing,
            "found_prohibited": found_prohibited,
            "installedTotal": len(installed_raw),
        }

    @mcp.tool()
    async def get_device_vulnerabilities(
        device_id: str,
        include_ignored: bool = False,
    ) -> dict:
        """
        Gibt alle bekannten CVE-Schwachstellen eines Windows-Geräts zurück.
        Akzeptiert Hostname (z.B. 'PCSWIT1984') oder GUID.

        Args:
            device_id: Hostname oder GUID des Geräts.
            include_ignored: True = auch ignorierte Schwachstellen anzeigen (Standard: False).

        Returns:
            Objekt mit 'total', 'ignored' (Anzahl ignoriert) und 'vulnerabilities'
            (cveId, detected, ignored, sowie Details aus der CVE-Datenbank).
        """
        async with BaramundiClient() as client:
            guid = await _resolve_to_guid(client, device_id)
            if guid is None:
                return {"error": f"Kein Gerät mit Hostname '{device_id}' gefunden."}
            detected = await _fetch_all(
                client,
                f"compliance/v2.0/WindowsEndpoints/{guid}/DetectedVulnerabilities",
            )
            # CVE-Details aus der Vulnerability-Datenbank nachladen
            vuln_ids = [v["vulnerabilityId"] for v in detected if v.get("vulnerabilityId")]
            vuln_details: dict[str, dict] = {}
            for v in detected:
                vid = v.get("vulnerabilityId")
                if vid:
                    try:
                        detail = await client.get(f"compliance/v2.0/Vulnerabilities/{vid}")
                        vuln_details[vid] = detail
                    except Exception:
                        pass

        if not include_ignored:
            detected = [v for v in detected if not v.get("ignored")]

        result = []
        for v in detected:
            detail = vuln_details.get(v.get("vulnerabilityId"), {})
            result.append({
                "cveId": v.get("cveId"),
                "detected": v.get("detected"),
                "ignored": v.get("ignored"),
                "severity": detail.get("severity"),
                "cvssScore": detail.get("cvssScore"),
                "description": (detail.get("description") or "")[:200],
                "affectedProducts": detail.get("affectedProducts"),
            })

        result.sort(key=lambda x: (x.get("cvssScore") or 0), reverse=True)
        ignored_count = sum(1 for v in detected if v.get("ignored"))

        return {
            "device": device_id,
            "total": len(result),
            "ignoredCount": ignored_count,
            "vulnerabilities": result,
        }

    @mcp.tool()
    async def search_vulnerabilities(
        severity: str = "",
        query: str = "",
        limit: int = 20,
    ) -> dict:
        """
        Durchsucht die CVE-Vulnerability-Datenbank in baramundi.

        Args:
            severity: Filter nach Schweregrad: 'Critical', 'High', 'Medium', 'Low'.
                      Leer = alle.
            query: Suchbegriff in CVE-ID oder betroffenen Produkten
                   (z.B. 'Chrome', 'CVE-2024', 'Java').
            limit: Maximale Anzahl Ergebnisse (Standard: 20).

        Returns:
            Objekt mit 'total' und 'vulnerabilities' (cveId, severity, cvssScore,
            description, affectedProducts).
        """
        async with BaramundiClient() as client:
            all_vulns = await _fetch_all(client, "compliance/v2.0/Vulnerabilities")

        sev_filter = severity.strip().lower()
        q = query.strip().lower()

        matches = []
        for v in all_vulns:
            if sev_filter and (v.get("severity") or "").lower() != sev_filter:
                continue
            if q:
                searchable = " ".join(filter(None, [
                    v.get("cveId") or "",
                    v.get("affectedProducts") or "",
                    v.get("description") or "",
                ])).lower()
                if q not in searchable:
                    continue
            matches.append({
                "cveId": v.get("cveId"),
                "severity": v.get("severity"),
                "cvssScore": v.get("cvssScore"),
                "description": (v.get("description") or "")[:200],
                "affectedProducts": v.get("affectedProducts"),
            })

        return {"total": len(matches), "vulnerabilities": matches[:limit]}
