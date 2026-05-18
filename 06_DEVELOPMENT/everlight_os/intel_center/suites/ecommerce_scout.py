"""eCommerce & Product Research -- 2 marketplaces/product DBs."""
from suites._runner import run_category

def main():
    return run_category("eCommerce & Product Research", max_workers=4, timeout=10)

if __name__ == "__main__":
    main()
