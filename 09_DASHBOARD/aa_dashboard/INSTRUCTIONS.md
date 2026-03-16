# AA Dashboard – Run + Alias

## One-shot run
```
/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/aa_dashboard/run.sh
```

## Master restart (kills conflicts, restarts clean)
```
/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/aa_dashboard/master_restart.sh
```

## Alias (zsh)
Add this to `~/.zshrc`:
```
alias aadash="/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/aa_dashboard/run.sh"
alias aadash-master="/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/aa_dashboard/master_restart.sh"
```
Then reload:
```
source ~/.zshrc
```
