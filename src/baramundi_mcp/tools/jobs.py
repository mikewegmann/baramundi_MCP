from mcp.server.fastmcp import FastMCP
from baramundi_mcp.client import BaramundiClient
from baramundi_mcp.tools.devices import _fetch_all

# Bekannte Job-Präfixe in dieser Umgebung
JOB_PREFIXES = {
    "install":   "INST:",
    "uninstall": "DEINST:",
    "run":       "RUN:",
    "update":    "UPD:",
    "scan":      "SCAN:",
    "os":        "OS:",
    "reg":       "REG:",
    "inv":       "INV:",
}


def register_job_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def search_job_definitions(
        query: str = "",
        type: str = "",
        limit: int = 30,
    ) -> dict:
        """
        Sucht Job-Definitionen nach Name oder Typ (Präfix).
        Jobs folgen der Namenskonvention: INST: (Installation), DEINST: (Deinstallation),
        RUN: (Skript/Aktion), UPD: (Update), SCAN:, OS:, REG:, INV:.

        Args:
            query: Suchbegriff im Job-Namen (z.B. 'Chrome', 'Edge', 'Office').
                   Leer = alle Jobs des angegebenen Typs.
            type: Job-Typ als Präfix oder Kurzname:
                  'install' / 'INST:', 'uninstall' / 'DEINST:', 'run' / 'RUN:',
                  'update' / 'UPD:', 'scan' / 'SCAN:', 'os' / 'OS:'.
                  Leer = alle Typen durchsuchen.
            limit: Maximale Anzahl Ergebnisse (Standard: 30).

        Returns:
            Objekt mit 'data' (Job-Liste) und 'total'.
            Felder: id, name, displayName, type, folder, category.
        """
        # Präfix auflösen
        prefix = JOB_PREFIXES.get(type.lower(), type.upper() if type and not type.endswith(":") else type)
        q = query.strip().lower()

        async with BaramundiClient() as client:
            all_jobs = await _fetch_all(client, "jobs/v2.0/JobDefinitions")

        matches = []
        for j in all_jobs:
            name = j.get("name") or ""
            # Präfix-Filter
            if prefix and not name.upper().startswith(prefix.upper()):
                continue
            # Keyword-Filter
            if q and q not in name.lower():
                continue
            matches.append({
                "id": j.get("id"),
                "name": j.get("name"),
                "displayName": j.get("displayName"),
                "type": j.get("type"),
                "folder": j.get("folder"),
                "category": j.get("category"),
            })

        return {"data": matches[:limit], "total": len(matches)}

    @mcp.tool()
    async def list_job_definitions(page: int = 0) -> dict:
        """
        Listet alle Job-Definitionen seitenweise auf (20 pro Seite).
        Für gezielte Suche besser search_job_definitions verwenden.

        Args:
            page: Seitennummer ab 0 (Standard: 0).

        Returns:
            Objekt mit 'data', 'totalItems' und 'totalPages'.
        """
        async with BaramundiClient() as client:
            return await client.get("jobs/v2.0/JobDefinitions", params={"page": page})

    @mcp.tool()
    async def list_job_instances(page: int = 0) -> dict:
        """
        Listet die letzten Job-Ausführungen aller Geräte auf.

        Args:
            page: Seitennummer ab 0 (Standard: 0).

        Returns:
            Objekt mit 'data', 'totalItems' und 'totalPages'.
            Felder: jobDefinitionName, endpointName, state, stateDescription,
            start, lastAction, successfulExecutions, erroneousExecutions.
        """
        async with BaramundiClient() as client:
            result = await client.get("jobs/v2.0/JobInstances", params={"page": page})
        if isinstance(result, dict) and "data" in result:
            result["data"] = _slim_instances(result["data"])
        return result

    @mcp.tool()
    async def get_job_instance(instance_id: str) -> dict:
        """
        Gibt alle Details einer einzelnen Job-Ausführung zurück.

        Args:
            instance_id: GUID der Job-Instanz (id-Feld aus list_job_instances).

        Returns:
            Vollständiges Instanz-Objekt inkl. steps, Zeitstempel und Statusbeschreibung.
        """
        async with BaramundiClient() as client:
            return await client.get(f"jobs/v2.0/JobInstances/{instance_id}")

    @mcp.tool()
    async def get_job_definition(definition_id: str) -> dict:
        """
        Gibt alle Details einer Job-Definition zurück.

        Args:
            definition_id: GUID der Job-Definition (id-Feld aus search_job_definitions).

        Returns:
            Vollständiges Definition-Objekt mit Typ, Ordner, Kategorie und Beschreibung.
        """
        async with BaramundiClient() as client:
            return await client.get(f"jobs/v2.0/JobDefinitions/{definition_id}")

    @mcp.tool()
    async def start_job(
        job_definition_id: str,
        endpoint_id: str,
        dry_run: bool = True,
        start_if_already_assigned: bool = True,
    ) -> dict:
        """
        Startet einen Job auf einem Endpunkt (Softwareverteilung, Scan, Skript etc.).

        WICHTIG: Standardmäßig ist dry_run=True — der Job wird NICHT wirklich gestartet,
        sondern nur angezeigt, was passieren würde. Zum echten Starten dry_run=False setzen.
        Immer zuerst mit dry_run=True bestätigen lassen, bevor der echte Start erfolgt.

        Workflow:
          1. search_job_definitions(query='Chrome', type='install') → job_definition_id
          2. get_device(identifier='PCSWIT1234') oder search_devices(query='PCSWIT1234') → endpoint_id
          3. start_job(job_definition_id=..., endpoint_id=..., dry_run=True)  → Vorschau
          4. start_job(job_definition_id=..., endpoint_id=..., dry_run=False) → Ausführen

        Args:
            job_definition_id:        GUID der Job-Definition (aus search_job_definitions).
            endpoint_id:              GUID des Ziel-Endpunkts (aus get_device / search_devices).
            dry_run:                  True (Standard) = nur Vorschau, kein API-Aufruf.
                                      False = Job wird wirklich gestartet.
            start_if_already_assigned: True (Standard) = Job auch starten wenn bereits zugewiesen.
                                       False = nur starten wenn noch nicht zugewiesen.

        Returns:
            Bei dry_run=True: Vorschau-Objekt mit job- und endpoint-Details.
            Bei dry_run=False: Neue Job-Instanz von der API (id, state, start, ...).
        """
        async with BaramundiClient() as client:
            # Job-Definition und Endpunkt auflösen für Anzeige / Validierung
            job_def = await client.get(f"jobs/v2.0/JobDefinitions/{job_definition_id}")
            endpoint = await client.get(f"endpoints/v2.0/WindowsEndpoints/{endpoint_id}")

            if dry_run:
                return {
                    "dry_run": True,
                    "message": "Vorschau — Job wurde NICHT gestartet. Rufe mit dry_run=False auf, um wirklich zu starten.",
                    "job": {
                        "id": job_def.get("id"),
                        "name": job_def.get("name"),
                        "displayName": job_def.get("displayName"),
                        "type": job_def.get("type"),
                    },
                    "endpoint": {
                        "id": endpoint.get("id"),
                        "hostName": endpoint.get("hostName"),
                        "primaryIP": endpoint.get("primaryIP"),
                        "logicalGroup": endpoint.get("logicalGroup"),
                    },
                }

            result = await client.post("jobs/v2.0/JobInstances", body={
                "jobDefinitionId": job_definition_id,
                "endpointId": endpoint_id,
                "startIfAlreadyAssigned": start_if_already_assigned,
            })
            return {
                "dry_run": False,
                "message": "Job wurde gestartet.",
                "instance": result,
            }


def _slim_instances(instances: list[dict]) -> list[dict]:
    keep = {"id", "jobDefinitionName", "jobDefinitionDisplayName", "jobDefinitionType",
            "endpointId", "endpointName", "endpointType", "initiator",
            "start", "lastAction", "nextExecution",
            "successfulExecutions", "erroneousExecutions", "state", "stateDescription"}
    return [{k: v for k, v in i.items() if k in keep} for i in instances]
