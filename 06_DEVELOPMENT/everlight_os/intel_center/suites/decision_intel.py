"""Decision Intelligence -- 179 research / analysis / dashboard tools."""
from suites._runner import run_category

def main():
    return run_category("Decision Intelligence", max_workers=8, timeout=8)

if __name__ == "__main__":
    main()
