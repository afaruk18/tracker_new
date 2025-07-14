# Unix
kill -TERM <pid>        # emulates shutdown
kill -HUP  <pid>        # emulates log-off
systemctl reboot        # during real reboot your process gets TERM then KILL

# Windows (PowerShell)
Stop-Process <pid>      # raises SIGTERM inside Python
shutdown /l             # log off, raises SIGBREAK
