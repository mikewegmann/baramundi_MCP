import os
import ldap3


class ADError(Exception):
    pass


class ADClient:
    def __init__(self):
        server_url = os.environ.get("AD_SERVER", "")
        if not server_url:
            raise ADError("AD_SERVER ist nicht konfiguriert.")
        self._bind_dn = os.environ.get("AD_BIND_DN", "")
        self._bind_password = os.environ.get("AD_BIND_PASSWORD", "")
        self._base_dn = os.environ.get("AD_BASE_DN", "")

        use_ssl = server_url.startswith("ldaps://")
        host = server_url.replace("ldaps://", "").replace("ldap://", "").rstrip("/")
        port = 636 if use_ssl else 389

        self._server = ldap3.Server(host, port=port, use_ssl=use_ssl, get_info=ldap3.NONE)

    def get_computer(self, hostname: str) -> dict | None:
        """
        Sucht ein Computerkonto per Hostname.
        Gibt None zurück wenn nicht gefunden, wirft ADError bei Verbindungsproblemen.
        """
        sam = hostname.upper().rstrip("$") + "$"
        search_filter = f"(&(objectClass=computer)(sAMAccountName={ldap3.utils.conv.escape_filter_chars(sam)}))"
        attributes = [
            "sAMAccountName",
            "userAccountControl",
            "distinguishedName",
            "operatingSystem",
            "operatingSystemVersion",
            "lastLogonTimestamp",
            "description",
            "whenCreated",
        ]

        conn = ldap3.Connection(
            self._server,
            user=self._bind_dn,
            password=self._bind_password,
            authentication=ldap3.SIMPLE,
            auto_bind=False,
        )
        try:
            if not conn.bind():
                raise ADError(f"AD-Bind fehlgeschlagen: {conn.result}")

            conn.search(
                search_base=self._base_dn,
                search_filter=search_filter,
                search_scope=ldap3.SUBTREE,
                attributes=attributes,
            )

            if not conn.entries:
                return None

            entry = conn.entries[0]
            uac = int(entry.userAccountControl.value or 0)
            # Bit 0x0002: ACCOUNTDISABLE
            enabled = not bool(uac & 0x0002)

            def val(attr):
                try:
                    return entry[attr].value
                except Exception:
                    return None

            last_logon = val("lastLogonTimestamp")

            return {
                "hostname": hostname.upper(),
                "sAMAccountName": str(val("sAMAccountName") or "").rstrip("$"),
                "enabled": enabled,
                "distinguishedName": str(val("distinguishedName") or ""),
                "operatingSystem": val("operatingSystem"),
                "operatingSystemVersion": val("operatingSystemVersion"),
                "description": val("description"),
                "whenCreated": str(val("whenCreated") or ""),
                "lastLogonTimestamp": str(last_logon) if last_logon else None,
            }
        finally:
            conn.unbind()
