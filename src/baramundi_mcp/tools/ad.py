import os
from mcp.server.fastmcp import FastMCP


def register_ad_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_computer_ad_status(device_id: str) -> dict:
        """
        Ruft den Active-Directory-Status eines Computerkontos per Hostname ab.
        Gibt zurück ob das Konto aktiv oder deaktiviert ist, Betriebssystem,
        letzten Logon-Zeitstempel und weitere AD-Attribute.

        Args:
            device_id: Hostname des Geräts (z.B. 'PCSWIT1984').

        Returns:
            Objekt mit 'enabled' (bool), 'distinguishedName', 'operatingSystem',
            'lastLogonTimestamp' und weiteren AD-Feldern.
        """
        if not os.environ.get("AD_SERVER"):
            return {"error": "Active Directory ist nicht konfiguriert (AD_SERVER fehlt in .env)."}

        from baramundi_mcp.ad_client import ADClient, ADError
        try:
            client = ADClient()
            result = client.get_computer(device_id)
        except ADError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"AD-Fehler: {e}"}

        if result is None:
            return {
                "hostname": device_id.upper(),
                "found": False,
                "message": f"Kein Computerkonto '{device_id}' in Active Directory gefunden.",
            }

        result["found"] = True
        return result
