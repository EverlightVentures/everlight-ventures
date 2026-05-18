"""OSINT & Investigation suite -- the largest, ~173 domains."""
from suites._runner import run_category

def main():
    return run_category("OSINT & Investigation", max_workers=8, timeout=8)

if __name__ == "__main__":
    main()
