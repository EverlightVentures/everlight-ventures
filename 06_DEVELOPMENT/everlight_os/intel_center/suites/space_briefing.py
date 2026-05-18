"""Space & Science suite."""
from suites._runner import run_category

def main():
    return run_category("Space & Science", max_workers=6, timeout=10)

if __name__ == "__main__":
    main()
