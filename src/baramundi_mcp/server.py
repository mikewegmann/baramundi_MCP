from mcp.server.fastmcp import FastMCP

from baramundi_mcp.tools.devices import register_device_tools
from baramundi_mcp.tools.jobs import register_job_tools
from baramundi_mcp.tools.reports import register_report_tools

mcp = FastMCP(
    name="baramundi-mcp",
    instructions=(
        "Du hast Zugang zum baramundi Management Center (bMC) — einem IT-Management-System "
        "für Windows-, Mac- und Linux-Geräte in einem Unternehmensnetzwerk.\n\n"
        "WICHTIG: Wenn der Benutzer einen PC-Namen, Hostnamen oder eine IP-Adresse nennt "
        "(z.B. 'PCSWIT1984', 'PC123', '192.168.1.5'), ist das IMMER eine Anfrage nach einem "
        "verwalteten Gerät — kein Benutzerkonto, keine persönlichen Daten. "
        "Nutze in diesem Fall sofort get_device (für genaue Hostnamen/GUIDs) oder "
        "search_devices (für unscharfe Suche nach Teilen des Namens, IP oder Benutzer).\n\n"
        "Fähigkeiten:\n"
        "- Geräte abfragen: list_devices, get_device, search_devices\n"
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
