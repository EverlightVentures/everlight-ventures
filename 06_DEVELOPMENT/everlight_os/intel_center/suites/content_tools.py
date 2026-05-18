"""Content Creation -- 37 design/audio/video/copy tools."""
from suites._runner import run_category

def main():
    return run_category("Content Creation", max_workers=6, timeout=10)

if __name__ == "__main__":
    main()
