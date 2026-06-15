# sync.py
import os, sys, pathlib, difflib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # run from any cwd (bootstrap)
from registry import load_registry, validate
from theme.tokens import emit_css_vars

ROOT = pathlib.Path(os.environ.get("LUCREX_OS_ROOT", pathlib.Path(__file__).resolve().parents[2]))
OS_DIR = ROOT / "09_DASHBOARD/lucrex_os"
SHELL_BANNER = ROOT / "03_AUTOMATION_CORE/01_Scripts/everlight_shell.zsh"
LUCREX_CSS = OS_DIR / "theme/lucrex.css"
BANNER_MARK = ("# LX:DASH:START", "# LX:DASH:END")
TOKENS_MARK = ("/* LUCREX-OS:TOKENS:START */", "/* LUCREX-OS:TOKENS:END */")
BANNER_DESC = "# GENERATED FROM registry.yaml by lucrex_os/sync.py -- DO NOT EDIT"

def inject_block(path, mark, content):
    start, end = mark
    text = pathlib.Path(path).read_text()
    block = f"{start}\n{content}\n{end}"
    has_start, has_end = (start in text), (end in text)
    if has_start != has_end:
        raise ValueError(f"corrupted markers in {path}: exactly one of {start!r}/{end!r} present")
    if has_start and has_end:
        pre = text.split(start, 1)[0]
        post = text.split(end, 1)[1]
        new = pre + block + post
    else:
        new = text.rstrip() + "\n" + block + "\n"
    pathlib.Path(path).write_text(new)

def generate_shell_banner(reg) -> str:
    lines = [BANNER_DESC]
    for b in reg.bands:
        ds = [d for d in reg.dashboards if d.band == b.port]
        lines.append(f'_ev_row "{b.name}  {b.port}"')
        for d in ds:
            lines.append(f'_ev_row "  {d.id}  http://127.0.0.1:{d.band}{d.sub_route}  {d.description}"')
    return "\n".join(lines)

def generate_tokens_css(reg) -> str:
    # tokens.py is the canonical CSS color source; reg.tokens is validated-only.
    return "/* GENERATED FROM registry.yaml by lucrex_os/sync.py -- DO NOT EDIT */\n" + emit_css_vars()

# (path_fn, marker, generator) -- add Plan B surfaces here
SURFACES = [
    (lambda: SHELL_BANNER, BANNER_MARK, generate_shell_banner),
    (lambda: LUCREX_CSS, TOKENS_MARK, generate_tokens_css),
]

def run_sync(reg, dry_run=False) -> list[str]:
    errs = validate(reg)
    if errs:
        sys.stderr.write("REGISTRY INVALID -- zero files written:\n" + "\n".join(errs) + "\n")
        raise SystemExit(1)
    changed = []
    for path_fn, mark, gen in SURFACES:
        path = path_fn()
        content = gen(reg)
        current = pathlib.Path(path).read_text() if pathlib.Path(path).exists() else ""
        block = f"{mark[0]}\n{content}\n{mark[1]}"
        if block not in current:
            changed.append(str(path))
            if dry_run:
                sys.stdout.write("\n".join(difflib.unified_diff(
                    current.splitlines(), block.splitlines(),
                    fromfile=str(path), tofile=str(path)+" (new)", lineterm="")) + "\n")
            else:
                inject_block(path, mark, content)
    return changed

def main(argv):
    path = OS_DIR / "registry.yaml"
    if not path.exists():
        print(f"registry.yaml not found at {path}; nothing to sync (Plan B populates it)")
        return 0
    reg = load_registry(path)
    dry = "--check" in argv or "--dry-run" in argv
    print("would change:" if dry else "synced:", run_sync(reg, dry_run=dry))
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
