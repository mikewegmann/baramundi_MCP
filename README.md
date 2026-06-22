# baramundi MCP Server

MCP (Model Context Protocol) Server für das baramundi Management Center.
Erlaubt Claude, Geräte abzufragen, Jobs zu starten und Compliance-Reports zu generieren.

## Voraussetzungen

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (`pip install uv`)
- Zugang zum baramundi Management Center mit REST API und Bearer Token

## Einrichtung

### 1. Abhängigkeiten installieren

```bash
uv sync
```

### 2. Konfiguration

Erstelle eine `.env`-Datei (basierend auf `.env.example`):

```bash
BARAMUNDI_API_URL=https://dein-bmc-server/api
BARAMUNDI_API_TOKEN=dein-bearer-token
# Optional: SSL-Verifikation deaktivieren (nur für Testumgebungen!)
# BARAMUNDI_SSL_VERIFY=false
```

### 3. Server testen

```bash
# Alle Tools im Browser testen (MCP Inspector)
uv run mcp dev src/baramundi_mcp/server.py
```

## In Claude Desktop einbinden

Füge folgendes in `%APPDATA%\Claude\claude_desktop_config.json` ein:

```json
{
  "mcpServers": {
    "baramundi": {
      "command": "uv",
      "args": ["--directory", "C:\\INST\\Git\\Antigravity\\baramundi_MCP", "run", "baramundi-mcp"]
    }
  }
}
```

## Verfügbare Tools

| Tool | Beschreibung |
|---|---|
| `list_devices` | Alle verwalteten Geräte auflisten |
| `get_device` | Details zu einem Gerät abrufen |
| `get_device_status` | Patch-Level und Status eines Geräts |
| `list_jobs` | Jobs auflisten (aktiv, geplant, abgeschlossen) |
| `get_job_status` | Status eines laufenden Jobs |
| `start_job` | Job auf einem Gerät starten (**schreibend!**) |
| `get_compliance_report` | Patch-Compliance-Übersicht |
| `list_software_inventory` | Software-Inventar abfragen |
