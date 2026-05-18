"""Self-Hosting & Privacy -- 59 OSS tools, VPNs, encrypted services."""
from suites._runner import run_category

def main():
    return run_category("Self-Hosting & Privacy", max_workers=6, timeout=10)

if __name__ == "__main__":
    main()
