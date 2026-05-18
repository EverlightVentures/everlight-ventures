"""Education & Training -- 91 learning/research platforms."""
from suites._runner import run_category

def main():
    return run_category("Education & Training", max_workers=8, timeout=8)

if __name__ == "__main__":
    main()
