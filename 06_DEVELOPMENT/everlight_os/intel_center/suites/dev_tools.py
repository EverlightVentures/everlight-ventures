"""APIs & Developer Tools -- 3 API repos / dev libraries."""
from suites._runner import run_category

def main():
    return run_category("APIs & Developer Tools", max_workers=4, timeout=10)

if __name__ == "__main__":
    main()
