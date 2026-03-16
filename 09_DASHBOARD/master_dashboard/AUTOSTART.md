# Auto-start options

## Option A: systemd (Ubuntu/Arch with systemd)
```
systemctl --user daemon-reload
systemctl --user enable aa-dashboard.service
systemctl --user start aa-dashboard.service
```

Status:
```
systemctl --user status aa-dashboard.service
```

## Option B: tmux (portable)
```
/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/master_dashboard/autostart_tmux.sh
```
