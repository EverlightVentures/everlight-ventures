"""AI & Automation -- 7 LLM/agent/automation platforms."""
from suites._runner import run_category

def main():
    return run_category("AI & Automation", max_workers=4, timeout=10)

if __name__ == "__main__":
    main()
