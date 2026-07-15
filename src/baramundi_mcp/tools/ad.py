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

    @mcp.tool()
    async def get_laps_password(device_id: str) -> dict:
        """
        Liest das LAPS-Passwort (Local Administrator Password Solution) für ein Gerät aus
        Active Directory aus. NUR auf explizite Anfrage verwenden — niemals automatisch
        oder als Teil einer allgemeinen Geräteabfrage ausgeben.

        Unterstützt Legacy LAPS (ms-Mcs-AdmPwd) und Windows LAPS (msLAPS-Password).
        Erfordert, dass der AD-Serviceaccount Leserecht auf das jeweilige Attribut hat.

        Args:
            device_id: Hostname des Geräts (z.B. 'PCSWIT1984').

        Returns:
            Objekt mit 'password', 'account', 'lapsVersion' ('legacy' oder 'windows'),
            'expiresAt' und 'hostname'. Enthält 'error' wenn kein Zugriff möglich.
        """
        if not os.environ.get("AD_SERVER"):
            return {"error": "Active Directory ist nicht konfiguriert (AD_SERVER fehlt in .env)."}

        from baramundi_mcp.ad_client import ADClient, ADError
        try:
            client = ADClient()
            result = client.get_laps_password(device_id)
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

    @mcp.tool()
    async def set_computer_ad_enabled(
        device_id: str,
        enabled: bool = True,
        dry_run: bool = True,
    ) -> dict:
        """
        Aktiviert oder deaktiviert ein Computerkonto in Active Directory.
        Setzt das ACCOUNTDISABLE-Bit in userAccountControl.

        dry_run=True (Standard): Zeigt nur an, was geändert würde — keine Änderung.
        dry_run=False: Führt die Änderung tatsächlich durch — NUR nach expliziter Bestätigung!

        Args:
            device_id: Hostname des Geräts (z.B. 'PCSWIT1984').
            enabled: True = Konto aktivieren, False = Konto deaktivieren.
            dry_run: True = Vorschau (kein Schreibzugriff), False = Änderung durchführen.
        """
        if not os.environ.get("AD_SERVER"):
            return {"error": "Active Directory ist nicht konfiguriert (AD_SERVER fehlt in .env)."}

        from baramundi_mcp.ad_client import ADClient, ADError

        if dry_run:
            # Aktuellen Status lesen und zeigen was sich ändern würde
            try:
                client = ADClient()
                current = client.get_computer(device_id)
            except ADError as e:
                return {"error": str(e)}
            except Exception as e:
                return {"error": f"AD-Fehler: {e}"}

            if current is None:
                return {"hostname": device_id.upper(), "found": False,
                        "message": f"Kein Computerkonto '{device_id}' in Active Directory gefunden."}

            action = "aktivieren" if enabled else "deaktivieren"
            already = current.get("enabled") == enabled
            return {
                "dry_run": True,
                "hostname": device_id.upper(),
                "dn": current.get("distinguishedName"),
                "currentState": "aktiviert" if current.get("enabled") else "deaktiviert",
                "requestedChange": action,
                "changeNeeded": not already,
                "message": (
                    f"Kein Schreibzugriff — dry_run=True. "
                    f"{'Konto ist bereits ' + ('aktiviert' if enabled else 'deaktiviert') + ', keine Änderung nötig.' if already else 'Mit dry_run=False wird das Konto ' + action + '.'}"
                ),
            }

        # Tatsächliche Änderung
        try:
            client = ADClient()
            result = client.set_computer_enabled(device_id, enabled)
        except ADError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"AD-Fehler: {e}"}

        result["dry_run"] = False
        result["message"] = f"Computerkonto '{device_id.upper()}' wurde {'aktiviert' if enabled else 'deaktiviert'}."
        return result

    @mcp.tool()
    async def get_laps_password(device_id: str) -> dict:
        """
        Liest das LAPS-Passwort (Local Administrator Password Solution) für ein Gerät aus
        Active Directory aus. NUR auf explizite Anfrage verwenden — niemals automatisch
        oder als Teil einer allgemeinen Geräteabfrage ausgeben.

        Unterstützt Legacy LAPS (ms-Mcs-AdmPwd) und Windows LAPS (msLAPS-Password).
        Erfordert, dass der AD-Serviceaccount Leserecht auf das jeweilige Attribut hat.

        Args:
            device_id: Hostname des Geräts (z.B. 'PCSWIT1984').

        Returns:
            Objekt mit 'password', 'account', 'lapsVersion' ('legacy' oder 'windows'),
            'expiresAt' und 'hostname'. Enthält 'error' wenn kein Zugriff möglich.
        """
        if not os.environ.get("AD_SERVER"):
            return {"error": "Active Directory ist nicht konfiguriert (AD_SERVER fehlt in .env)."}

        from baramundi_mcp.ad_client import ADClient, ADError
        try:
            client = ADClient()
            result = client.get_laps_password(device_id)
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

        if result.get("lapsVersion") is None:
            return {
                "hostname": device_id.upper(),
                "found": True,
                "lapsVersion": None,
                "message": (
                    "Kein LAPS-Passwort gefunden. Entweder ist LAPS für dieses Gerät nicht "
                    "konfiguriert oder der Serviceaccount hat keine Leseberechtigung auf "
                    "ms-Mcs-AdmPwd / msLAPS-Password."
                ),
            }

        return {"found": True, **result}
