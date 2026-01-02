# Security Notes

ZeroTerm exposes a real terminal without authentication, command restrictions,
or sandboxing. Treat access to the web UI the same way you treat SSH access.

Recommendations:
- Run on a trusted or isolated management network.
- Use firewall rules to limit inbound access.
- Add access control at the network edge (VPN or reverse proxy) if needed.
- Do not expose the service directly to the public Internet.
