"""News & Journalism suite -- pings every news source for liveness."""
from suites._runner import run_category

def main():
    return run_category("News & Journalism", max_workers=6, timeout=10)

if __name__ == "__main__":
    main()
