# VPN won't connect

Before anything else, confirm you have working internet access by opening any public website.

If the VPN client shows error 809 on Windows, the network is blocking UDP ports 500 and 4500, which is common on hotel, airport and some home routers. Open the VPN client, choose the profile named Northwind-TCP instead of Northwind-UDP, and connect again. The TCP profile uses port 443, which is rarely blocked.

If the client reports "Authentication failed", your password has probably expired or your account is locked. Reset your password in the self-service portal, then try again.

If the client hangs on "Connecting", quit it completely, restart the VPN service from the Services app, and reconnect. If none of these steps work, open a ticket and attach the client log file from the Help menu.
