import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_DIR = ROOT / "ui"


def run(command: list[str]) -> tuple[int, str, str]:
    process = subprocess.run(
        command,
        cwd=UI_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    return process.returncode, process.stdout, process.stderr


def main() -> None:
    steps: list[dict[str, object]] = []

    install_code, install_out, install_err = run(
        ["npx", "playwright", "install", "chromium"]
    )
    steps.append(
        {
            "step": "install-browser",
            "ok": install_code == 0,
            "exit_code": install_code,
            "stdout_tail": install_out.splitlines()[-20:],
            "stderr_tail": install_err.splitlines()[-20:],
        }
    )

    test_code, test_out, test_err = run(["npm", "run", "test:e2e"])
    steps.append(
        {
            "step": "run-playwright",
            "ok": test_code == 0,
            "exit_code": test_code,
            "stdout_tail": test_out.splitlines()[-40:],
            "stderr_tail": test_err.splitlines()[-40:],
        }
    )

    print(
        json.dumps(
            {
                "ok": all(bool(step["ok"]) for step in steps),
                "steps": steps,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
