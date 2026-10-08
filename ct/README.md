# BitsParser for Cyber Triage

This fork builds the `BitsParser.exe` that Cyber Triage runs to parse the BITS
job database (`qmgr.db`, and `qmgr0.dat`/`qmgr1.dat` on older Windows).

Work happens on `master`. Upstream is
[fireeye/BitsParser](https://github.com/fireeye/BitsParser), unchanged since
2021.

## What differs from upstream

- **Valid JSON output.** Upstream prints each job as its own JSON object; the
  fork writes one document, `{"jobs": [...]}`.
- **Newer ESE databases.** From ESE format 0x620 revision 0x122 (Windows 11
  24H2, Server 2025), the upper 4 bits of a page header's tag count are reserved,
  and `ese/ese.py` masks them. It also handles tables with no long-value tree.
- **XP job delimiter.** `requirements.txt` pins
  [ANSSI-FR/bits_parser](https://github.com/ANSSI-FR/bits_parser) to a commit
  that has the XP job delimiter the PyPI release lacks.
- **`--no-sid-lookup`.** Writes only `OwnerSID`, without resolving it against
  the accounts of the machine running BitsParser. Cyber Triage passes it.
- **Failure exit code.** Exits 1, without writing output, when a file named by
  `-i` is not a recognized BITS database or cannot be parsed. Cyber Triage
  reports that exit code as a host analysis issue.
- **Pinned build.** `requirements-build.txt` pins PyInstaller and its
  dependencies, and `.github/workflows/ct_release.yml` builds the exe.

## Getting the exe

Do not build locally. Download a release from this repository's Releases page.
Each release has:

| File | Contents |
|---|---|
| `BitsParser-<tag>-windows-x64.zip` | `BitsParser.exe`, a PyInstaller one-file build |
| `SHA256SUMS` | SHA-256 of the archive |

The archive also carries `LICENSE`, `Apache-1.1-Impacket.txt`, both
requirements files and a `SOURCE.txt` naming the exact source commit and build.

The exe bundles Python 3.11 and its C runtime, so it needs nothing installed.

Every push to `master` builds the same archive and keeps it as a workflow
artifact for the run. Only a tag publishes a release.

## Making a release

1. Make sure the `ct_release` workflow passes on `master`.
2. Tag the commit `ct-<yyyymmdd>.<n>`, for example `ct-20261002.1`.
3. Push the tag. The workflow publishes the release.

Never move or reuse a tag. Cyber Triage pins a release by its SHA-256.

The smoke test in the workflow needs no BITS database. Before pinning a new
release in Cyber Triage, run its `BITSDbParserTest`, which parses qmgr.db files
from Windows 11 24H2 and Server 2025.

## Updating a dependency

Change its pin in `requirements.txt` or `requirements-build.txt` in its own
commit, then release.

## Licence

Apache-2.0, the same as upstream. `ese/` comes from Impacket, under the Apache
Software License 1.1 in `Apache-1.1-Impacket.txt`. The source for every release
is this repository at the commit named in its `SOURCE.txt`.
