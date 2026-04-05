"""
Computer Use Agent - Claude controls a virtual desktop via screenshots + actions.

Flow:
1. Receive task description
2. Take screenshot
3. Send to Claude with computer_use tool
4. Execute Claude's action (click, type, scroll)
5. Take new screenshot
6. Repeat until task complete or max iterations
"""
import os
import subprocess
import base64
import time
import json
import logging
from pathlib import Path
from anthropic import Anthropic

log = logging.getLogger("computer-use-agent")
logging.basicConfig(level=logging.INFO)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = os.environ.get("MODEL", "claude-sonnet-4-6")
WIDTH = int(os.environ.get("WIDTH", 1280))
HEIGHT = int(os.environ.get("HEIGHT", 720))
MAX_ITERATIONS = int(os.environ.get("MAX_ITERATIONS", 30))
SCREENSHOT_DIR = Path("/app/screenshots")


def take_screenshot() -> str:
    """Capture screen and return base64-encoded PNG."""
    path = SCREENSHOT_DIR / "current.png"
    subprocess.run(
        ["scrot", "-o", str(path)],
        env={**os.environ, "DISPLAY": ":99"},
        timeout=5,
    )
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode()


def execute_action(action: dict) -> str:
    """Execute a computer use action via xdotool."""
    env = {**os.environ, "DISPLAY": ":99"}
    action_type = action.get("action")

    if action_type == "screenshot":
        return "screenshot_taken"

    elif action_type == "left_click":
        x, y = action["coordinate"]
        subprocess.run(["xdotool", "mousemove", str(x), str(y)], env=env, timeout=5)
        subprocess.run(["xdotool", "click", "1"], env=env, timeout=5)
        return f"clicked ({x}, {y})"

    elif action_type == "right_click":
        x, y = action["coordinate"]
        subprocess.run(["xdotool", "mousemove", str(x), str(y)], env=env, timeout=5)
        subprocess.run(["xdotool", "click", "3"], env=env, timeout=5)
        return f"right_clicked ({x}, {y})"

    elif action_type == "double_click":
        x, y = action["coordinate"]
        subprocess.run(["xdotool", "mousemove", str(x), str(y)], env=env, timeout=5)
        subprocess.run(["xdotool", "click", "--repeat", "2", "1"], env=env, timeout=5)
        return f"double_clicked ({x}, {y})"

    elif action_type == "type":
        text = action.get("text", "")
        subprocess.run(["xdotool", "type", "--clearmodifiers", text], env=env, timeout=15)
        return f"typed {len(text)} chars"

    elif action_type == "key":
        key = action.get("text", "")
        subprocess.run(["xdotool", "key", key], env=env, timeout=5)
        return f"pressed {key}"

    elif action_type == "scroll":
        x, y = action["coordinate"]
        direction = action.get("direction", "down")
        amount = action.get("amount", 3)
        subprocess.run(["xdotool", "mousemove", str(x), str(y)], env=env, timeout=5)
        button = "5" if direction == "down" else "4"
        for _ in range(amount):
            subprocess.run(["xdotool", "click", button], env=env, timeout=5)
        return f"scrolled {direction} {amount}x at ({x}, {y})"

    elif action_type == "mouse_move":
        x, y = action["coordinate"]
        subprocess.run(["xdotool", "mousemove", str(x), str(y)], env=env, timeout=5)
        return f"moved to ({x}, {y})"

    elif action_type == "cursor_position":
        result = subprocess.run(
            ["xdotool", "getmouselocation"],
            env=env, capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip()

    else:
        return f"unknown action: {action_type}"


def run_task(task: str) -> dict:
    """Run a computer use task. Returns result dict with steps and final screenshot."""
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    steps = []
    messages = []

    # System prompt
    system = (
        f"You are a computer use agent controlling a Linux desktop ({WIDTH}x{HEIGHT}). "
        "You have a Firefox browser, file manager, and terminal available. "
        "Complete the user's task by interacting with the desktop. "
        "Be efficient -- minimize unnecessary actions."
    )

    # Initial screenshot
    screenshot_b64 = take_screenshot()
    messages.append({
        "role": "user",
        "content": [
            {"type": "text", "text": task},
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": screenshot_b64},
            },
        ],
    })

    tools = [
        {
            "type": "computer_20250124",
            "name": "computer",
            "display_width_px": WIDTH,
            "display_height_px": HEIGHT,
            "display_number": 99,
        }
    ]

    for iteration in range(MAX_ITERATIONS):
        log.info(f"Iteration {iteration + 1}/{MAX_ITERATIONS}")

        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system,
            tools=tools,
            messages=messages,
        )

        # Check if Claude wants to use a tool
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        text_blocks = [b for b in response.content if b.type == "text"]

        if not tool_uses:
            # Claude is done
            final_text = " ".join(b.text for b in text_blocks)
            steps.append({"iteration": iteration + 1, "action": "complete", "text": final_text})
            break

        # Process each tool use
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []

        for tool_use in tool_uses:
            action = tool_use.input
            log.info(f"  Action: {action.get('action')} {action.get('coordinate', '')}")

            result_text = execute_action(action)
            steps.append({
                "iteration": iteration + 1,
                "action": action.get("action"),
                "detail": result_text,
            })

            # Take screenshot after action
            time.sleep(0.5)
            screenshot_b64 = take_screenshot()

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": [
                    {"type": "text", "text": result_text},
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": screenshot_b64},
                    },
                ],
            })

        messages.append({"role": "user", "content": tool_results})

    # Save final screenshot
    final_path = SCREENSHOT_DIR / f"task_{int(time.time())}.png"
    subprocess.run(["cp", str(SCREENSHOT_DIR / "current.png"), str(final_path)], timeout=5)

    return {
        "status": "complete" if len(steps) < MAX_ITERATIONS else "max_iterations",
        "iterations": len(steps),
        "steps": steps,
        "final_screenshot": str(final_path),
    }
