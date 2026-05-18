"""Trading & Finance suite -- big batch, slightly higher concurrency."""
from suites._runner import run_category

def main():
    return run_category("Trading & Finance", max_workers=8, timeout=10)

if __name__ == "__main__":
    main()
