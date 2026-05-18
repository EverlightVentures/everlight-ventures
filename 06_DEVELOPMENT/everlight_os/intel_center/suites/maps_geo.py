"""Maps & Geospatial -- 11 mapping / GIS / geo data sources."""
from suites._runner import run_category

def main():
    return run_category("Maps & Geospatial", max_workers=4, timeout=10)

if __name__ == "__main__":
    main()
