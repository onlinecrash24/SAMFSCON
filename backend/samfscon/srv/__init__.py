"""Everything that talks to a Samba file server.

The whole module speaks only what the server already offers: SMB, and the
DCE/RPC pipes carried over it — srvsvc for shares, sessions and open files,
samr for local accounts, lsarpc for name/SID resolution, winreg for the
registry-backed configuration. Nothing here reads or writes a file of the
server's own file system, and nothing needs to be installed on it.
"""
