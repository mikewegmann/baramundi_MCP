from mcp.server.fastmcp import FastMCP

from baramundi_mcp.tools.devices import register_device_tools
from baramundi_mcp.tools.jobs import register_job_tools
from baramundi_mcp.tools.reports import register_report_tools

mcp = FastMCP(
    name="baramundi-mcp",
    instructions=(
        "Du hast Zugang zum baramundi Management Center. "
        "Du kannst verwaltete Geräte abfragen, Jobs/Software-Deployments starten "
        "und Compliance-Reports abrufen. "
        "Führe schreibende Aktionen (start_job) nur aus, wenn der Benutzer "
        "explizit eine Aktion bestätigt hat."
    ),
)

register_device_tools(mcp)
register_job_tools(mcp)
register_report_tools(mcp)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
