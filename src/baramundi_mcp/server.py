from mcp.server.fastmcp import FastMCP

from baramundi_mcp.tools.devices import register_device_tools
from baramundi_mcp.tools.jobs import register_job_tools
from baramundi_mcp.tools.reports import register_report_tools

mcp = FastMCP(
    name="baramundi-mcp",
    instructions=(
        "Du hast Zugang zum baramundi Management Center (bMC) — einem IT-Management-System "
        "für Windows-, Mac- und Linux-Geräte in einem Unternehmensnetzwerk.\n\n"
        "SUCHREGELN — strikte Reihenfolge:\n"
        "1. Hostname oder GUID bekannt → get_device (ein einziger API-Call, sofort fertig).\n"
        "2. Suche nach Name, Benutzer, IP, Gruppe → search_devices (ein einziger API-Call, "
        "durchsucht ALLE Geräte intern). NIEMALS list_devices über mehrere Seiten iterieren!\n"
        "3. list_devices NUR verwenden, wenn explizit eine seitenweise Übersicht gewünscht ist "
        "— nicht zum Suchen.\n\n"
        "Beispiele:\n"
        "- 'Geräte von Müller' → search_devices(query='müller')\n"
        "- 'PC in der Gruppe Köln' → search_devices(query='köln')\n"
        "- 'IP 192.168.9' → search_devices(query='192.168.9')\n"
        "- 'PCSWIT1984' → get_device(device_id='PCSWIT1984')\n\n"
        "Fähigkeiten:\n"
        "- Geräte abfragen: get_device, search_devices (bevorzugt), list_devices (Übersicht)\n"
        "- Jobs und Software-Deployments: search_job_definitions, start_job (mit dry_run)\n"
        "- Reports: OS-Verteilung, inaktive Geräte, Agent-Health, fehlgeschlagene Jobs\n\n"
        "Schreibende Aktionen (start_job mit dry_run=False) nur nach expliziter Bestätigung."
    ),
)

register_device_tools(mcp)
register_job_tools(mcp)
register_report_tools(mcp)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
