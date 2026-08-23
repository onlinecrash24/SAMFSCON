"""SAMFSCON — Samba FileServer Console.

A web front end for administering Samba file servers, standalone as well as
domain members. Everything runs over the protocols the server already speaks:
SMB and DCE/RPC (srvsvc, samr, lsarpc, winreg) through the Samba python
bindings. Nothing is installed on the server, and no file of its file system is
touched directly.
"""

__version__ = "0.2.0"
