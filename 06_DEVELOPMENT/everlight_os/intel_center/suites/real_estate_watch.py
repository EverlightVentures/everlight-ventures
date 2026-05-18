"""Real Estate & Property -- property data, parcels, comps."""
from suites._runner import run_category

def main():
    return run_category("Real Estate & Property", max_workers=4, timeout=10)

if __name__ == "__main__":
    main()
