"""Health & Environment suite."""
from suites._runner import run_category

def main():
    return run_category("Health & Environment", max_workers=6, timeout=10)

if __name__ == "__main__":
    main()
