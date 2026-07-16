from mcp.server.fastmcp import FastMCP

from baramundi_mcp.tools.devices import register_device_tools
from baramundi_mcp.tools.jobs import register_job_tools
from baramundi_mcp.tools.reports import register_report_tools
from baramundi_mcp.tools.updates import register_update_tools
from baramundi_mcp.tools.macmon import register_macmon_tools
from baramundi_mcp.tools.compliance import register_compliance_tools
from baramundi_mcp.tools.ad import register_ad_tools

mcp = FastMCP(
    name="baramundi-mcp",
    instructions=(
        "Du hast Zugang zum baramundi Management Center (bMC) — einem IT-Management-System "
        "für Windows-, Mac-, Linux- und iOS-Geräte in einem Unternehmensnetzwerk.\n\n"
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
        "  Gerätetypen: 'windows' (Standard), 'mac', 'linux', 'ios'\n"
        "- Jobs und Software-Deployments: search_job_definitions, start_job (mit dry_run)\n"
        "- Reports: OS-Verteilung, inaktive Geräte, Agent-Health, fehlgeschlagene Jobs\n"
        "- Windows Updates: get_device_update_status (Gerät), report_update_compliance (alle Geräte)\n"
        "- macmon NAC: get_vlan_status (VLAN und Sperrstatus per Hostname oder MAC)\n"
        "- Compliance: list_compliance_rules, report_compliance_overview, get_device_compliance, "
        "check_software_compliance, get_device_vulnerabilities, search_vulnerabilities\n"
        "- Active Directory: get_computer_ad_status (Konto aktiv/deaktiviert, OS, letzter Logon), "
        "get_laps_password (LAPS-Passwort — NUR auf explizite Anfrage!)\n\n"
        "Schreibende Aktionen (start_job mit dry_run=False) nur nach expliziter Bestätigung.\n\n"
        "AUSGABEFORMAT für get_device — IMMER diese Struktur, ohne Ausnahme:\n"
        "Trenne die drei Blöcke mit einer Leerzeile und einer Überschrift (##).\n"
        "Innerhalb jedes Blocks: eine Zeile pro Feld im Format '- **Feld:** Wert'.\n"
        "Block 1 '## Gerät (baramundi)': Hostname, Benutzer, Gruppe, OS, OS-Version, "
        "Hersteller/Modell, Seriennummer, primäre IP, primäre MAC, Agent-Version, zuletzt gesehen, letzter Boot.\n"
        "Block 2 '## macmon NAC': nur ausgeben wenn macmon-Daten vorhanden. "
        "Felder: Bekannt, Gesperrt, Endpoint-Gruppe (Name + VLANs), Typ.\n"
        "Block 3 '## Active Directory': nur ausgeben wenn AD-Daten vorhanden. "
        "Felder: Konto aktiviert, DN, Erstellt, Letzter Logon.\n"
        "Keine Tabellen, keine Fließtext-Zusammenfassung — ausschließlich diese Block-Listen-Form."
    ),
)

register_device_tools(mcp)
register_job_tools(mcp)
register_report_tools(mcp)
register_update_tools(mcp)
register_macmon_tools(mcp)
register_compliance_tools(mcp)
register_ad_tools(mcp)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
