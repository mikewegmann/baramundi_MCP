from mcp.server.fastmcp import FastMCP
from baramundi_mcp.client import BaramundiClient, BaramundiAPIError


def register_job_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def list_job_definitions(
        limit: int = 50,
        page: int = 0,
    ) -> dict:
        """
        Listet alle Job-Definitionen (Vorlagen) im baramundi Management Center auf.
        Eine Job-Definition ist eine wiederverwendbare Aufgabe, z.B. ein Software-Deployment,
        ein Compliance-Scan oder eine OS-Installation.

        Args:
            limit: Anzahl Einträge pro Seite (Standard: 50).
            page: Seitennummer ab 0 (Standard: 0).

        Returns:
            Objekt mit 'data' (Job-Liste), 'totalItems' und 'totalPages'.
            Wichtige Felder: id, name, displayName, type, folder, category, description.
        """
        async with BaramundiClient() as client:
            result = await client.get(
                "jobs/v2.0/JobDefinitions",
                params={"page": page},
            )
        return result

    @mcp.tool()
    async def list_job_instances(
        limit: int = 25,
        page: int = 0,
    ) -> dict:
        """
        Listet die letzten Job-Ausführungen (Instanzen) aller Geräte auf.
        Zeigt den aktuellen Ausführungsstatus, Erfolgs- und Fehleranzahl.

        Args:
            limit: Anzahl Einträge pro Seite (Standard: 25).
            page: Seitennummer ab 0 (Standard: 0).

        Returns:
            Objekt mit 'data' (Instanzliste), 'totalItems' und 'totalPages'.
            Wichtige Felder: id, jobDefinitionName, endpointName, state,
            stateDescription, start, lastAction, successfulExecutions, erroneousExecutions.
        """
        async with BaramundiClient() as client:
            result = await client.get(
                "jobs/v2.0/JobInstances",
                params={"page": page},
            )
        if isinstance(result, dict) and "data" in result:
            result["data"] = _slim_instances(result["data"])
        return result

    @mcp.tool()
    async def get_job_instance(instance_id: str) -> dict:
        """
        Gibt alle Details einer einzelnen Job-Ausführung zurück.

        Args:
            instance_id: Die GUID der Job-Instanz (id-Feld aus list_job_instances).

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
            definition_id: Die GUID der Job-Definition (id-Feld aus list_job_definitions).

        Returns:
            Vollständiges Definition-Objekt mit Typ, Ordner, Kategorie und Beschreibung.
        """
        async with BaramundiClient() as client:
            return await client.get(f"jobs/v2.0/JobDefinitions/{definition_id}")


def _slim_instances(instances: list[dict]) -> list[dict]:
    keep = {"id", "jobDefinitionName", "jobDefinitionDisplayName", "jobDefinitionType",
            "endpointId", "endpointName", "endpointType", "initiator",
            "start", "lastAction", "nextExecution",
            "successfulExecutions", "erroneousExecutions", "state", "stateDescription"}
    return [{k: v for k, v in i.items() if k in keep} for i in instances]
