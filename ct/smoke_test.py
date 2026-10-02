#!/usr/bin/env python3
"""Smoke test for the Cyber Triage build of BitsParser.exe.

Usage: smoke_test.py <BitsParser.exe>

Run it with the Python that has PyInstaller installed.

Needs no BITS database: the real-data check is BITSDbParserTest in Cyber Triage,
which runs the release on qmgr.db files from Windows 11 24H2 and Server 2025.
"""

import json
import os
import subprocess
import sys
import tempfile

# Bundled by PyInstaller, so the exe needs nothing installed on the machine.
BUNDLED = ("python311.dll", "vcruntime140.dll", "ucrtbase.dll")


def run(arguments):
    """Runs a command and returns its exit code and combined output."""
    result = subprocess.run(
        arguments, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300
    )
    return result.returncode, result.stdout.decode("utf-8", "replace")


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2

    exe = os.path.abspath(sys.argv[1])
    failures = []

    exit_code, output = run([exe, "-h"])
    print(f"-h: exit code {exit_code}")
    if exit_code != 0 or "--no-sid-lookup" not in output:
        failures.append(f"-h exited with {exit_code} or does not offer --no-sid-lookup")

    with tempfile.TemporaryDirectory() as directory:
        zeros = os.path.join(directory, "zeros.db")
        with open(zeros, "wb") as file_object:
            file_object.write(bytes(65536))
        out = os.path.join(directory, "zeros.json")

        # The arguments Cyber Triage passes, in BitsParserCommand.
        exit_code, output = run(
            [exe, "-i", zeros, "-o", out, "--carvedb", "--no-sid-lookup"]
        )
        document = None
        if os.path.isfile(out):
            with open(out, encoding="utf-8") as file_object:
                document = json.load(file_object)
        print(f"zero-filled file: exit code {exit_code}, output {document}")
        if exit_code != 0 or document != {"jobs": []}:
            failures.append(
                f'a zero-filled file gave {document}, expected {{"jobs": []}}'
            )

    # pyi-archive_viewer, from the PyInstaller that runs this script.
    viewer = [sys.executable, "-m", "PyInstaller.utils.cliutils.archive_viewer"]
    exit_code, output = run([*viewer, "-l", "-r", exe])
    listing = output.lower()
    missing = [name for name in BUNDLED if name not in listing]
    print(f"pyi-archive_viewer: exit code {exit_code}, missing {missing}")
    if exit_code != 0 or missing:
        failures.append(f"the exe does not bundle {missing}")

    for failure in failures:
        print(f"FAIL: {failure}")
    if not failures:
        print("PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
