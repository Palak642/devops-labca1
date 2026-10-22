"""Run isolated, safe examples that should be detected by the named scanners."""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run_demo(scanner: str) -> int:
    executable = shutil.which(scanner)
    if executable is None and scanner == "gitleaks":
        local_executable = Path(__file__).resolve().parents[1] / ".tools" / "gitleaks.exe"
        if local_executable.is_file():
            executable = str(local_executable)
    if executable is None:
        print(
            f"Required scanner '{scanner}' was not found on PATH. "
            "For Gitleaks, run .\\scripts\\install_gitleaks.ps1.",
            file=sys.stderr,
        )
        return 2

    with tempfile.TemporaryDirectory(prefix=f"devsecops-{scanner}-") as directory:
        demo_file = Path(directory) / "scanner_demo.py"
        if scanner == "bandit":
            demo_file.write_text(
                "import subprocess\n"
                "user_input = 'harmless demo text'\n"
                "subprocess.call(user_input, shell=True)\n",
                encoding="utf-8",
            )
            command = [executable, "-q", "-r", str(demo_file)]
        else:
            # Keep the complete dummy value out of the repository scanned by Gitleaks.
            dummy_value = "aB3xY9qL2mN7pR4s" + "T6vW8kH5jD1fG0cZ"
            demo_file.write_text(
                f'api_key = "{dummy_value}"  # synthetic demo value only\n',
                encoding="utf-8",
            )
            command = [
                executable,
                "dir",
                str(directory),
                "--no-banner",
                "--redact",
                "--exit-code",
                "1",
            ]

        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)

        if result.returncode == 0:
            print(f"{scanner} did not detect the demonstration finding.", file=sys.stderr)
            return 1
        if result.returncode != 1:
            print(
                f"{scanner} failed unexpectedly with exit code {result.returncode}.",
                file=sys.stderr,
            )
            return result.returncode

        print(f"PASS: {scanner} detected the isolated demonstration finding.")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scanner", choices=("bandit", "gitleaks"))
    args = parser.parse_args()
    return run_demo(args.scanner)


if __name__ == "__main__":
    raise SystemExit(main())
