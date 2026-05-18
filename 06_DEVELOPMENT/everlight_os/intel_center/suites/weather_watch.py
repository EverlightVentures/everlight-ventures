"""Weather & Disaster Intel suite."""
from suites._runner import run_category

def main():
    return run_category("Weather & Disaster Intel", max_workers=6, timeout=10)

if __name__ == "__main__":
    main()
