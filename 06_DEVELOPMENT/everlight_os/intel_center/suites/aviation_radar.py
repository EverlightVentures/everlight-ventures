"""Aviation & Maritime suite."""
from suites._runner import run_category

def main():
    return run_category("Aviation & Maritime", max_workers=4, timeout=10)

if __name__ == "__main__":
    main()
