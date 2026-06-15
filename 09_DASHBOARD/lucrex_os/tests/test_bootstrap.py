import pathlib, subprocess, os

BOOT = pathlib.Path("bootstrap.sh")
DAEMON = pathlib.Path("daemon.sh")

def test_bootstrap_dry_run_uses_root_env(tmp_path):
    env = dict(os.environ, LUCREX_OS_ROOT=str(tmp_path), LX_DRY_RUN="1")
    out = subprocess.run(["bash", str(BOOT)], capture_output=True, text=True, env=env)
    assert out.returncode == 0
    assert str(tmp_path) in out.stdout

def test_daemon_has_singleton_guard():
    txt = DAEMON.read_text()
    assert "LUCREX_OS_ROOT" in txt
    assert "pidfile" in txt.lower() or "flock" in txt.lower()
    assert "crontab" not in txt   # must NOT be a cron entry (phone crond is dead)
