#!/usr/bin/env python3
"""Smoke test for the Cyber Triage build of BitsParser.

Usage: smoke_test.py <BitsParser.exe or BitsParser>

Run it with the Python that has PyInstaller installed, on the platform the exe
was built for.

Needs no BITS database: the real-data check is BITSDbParserTest in Cyber Triage,
which runs the release on qmgr.db files from Windows 11 24H2 and Server 2025.
"""

import json
import os
import re
import subprocess
import sys
import tempfile

from PyInstaller.archive.readers import PKG_ITEM_BINARY, CArchiveReader

# Bundled by PyInstaller, so the exe needs nothing installed on the machine.
if sys.platform == "win32":
    BUNDLED = ("python311.dll", "vcruntime140.dll", "ucrtbase.dll")
else:
    # Everything but glibc, which every mainstream Linux has.
    BUNDLED = ("libpython3.11.so",)

# The Linux exe must run on glibc 2.28 (RHEL 8), the oldest of any Linux still in support.
OLDEST_GLIBC = (2, 28)


def run(arguments):
    """Runs a command and returns its exit code and combined output."""
    result = subprocess.run(
        arguments, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300
    )
    return result.returncode, result.stdout.decode("utf-8", "replace")


def glibc_needed(path):
    """Returns the newest glibc symbol version an ELF file needs, or None."""
    exit_code, output = run(["objdump", "-p", path])
    if exit_code != 0:
        raise RuntimeError(f"objdump -p {path} exited with {exit_code}: {output}")
    versions = re.findall(r"\bGLIBC_(\d+(?:\.\d+)+)", output)
    return max((tuple(int(part) for part in version.split(".")) for version in versions), default=None)


def glibc_needed_by(exe, archive):
    """Returns the newest glibc version the exe and each binary it bundles need."""
    needed = {os.path.basename(exe): glibc_needed(exe)}
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "binary")
        for name, (*_, typecode) in archive.toc.items():
            if typecode == PKG_ITEM_BINARY:
                with open(path, "wb") as file_object:
                    file_object.write(archive.extract(name))
                needed[name] = glibc_needed(path)
    return needed


def dotted(version):
    return ".".join(str(part) for part in version) if version else "none"


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
        # Cyber Triage reports an unreadable database from the exit code
        if exit_code != 1 or document is not None:
            failures.append(
                f"a zero-filled file gave exit code {exit_code} and {document}, "
                "expected exit code 1 and no output"
            )

    archive = CArchiveReader(exe)
    names = [name.lower() for name in archive.toc]
    missing = [name for name in BUNDLED if not any(name in entry for entry in names)]
    print(f"archive: {len(names)} entries, missing {missing}")
    if missing:
        failures.append(f"the exe does not bundle {missing}")

    if sys.platform.startswith("linux"):
        needed = glibc_needed_by(exe, archive)
        newest = max(filter(None, needed.values()), default=None)
        too_new = sorted(
            f"{name} ({dotted(version)})" for name, version in needed.items() if version and version > OLDEST_GLIBC
        )
        print(f"glibc: newest needed {dotted(newest)}, allowed {dotted(OLDEST_GLIBC)}, too new {too_new}")
        if newest is None:
            failures.append("objdump found no glibc versions, so the glibc check did not run")
        elif too_new:
            failures.append(f"these need a glibc newer than {dotted(OLDEST_GLIBC)}: {too_new}")

    for failure in failures:
        print(f"FAIL: {failure}")
    if not failures:
        print("PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
