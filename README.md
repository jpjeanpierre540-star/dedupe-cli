# dedupe-cli

A tiny, dependency-free command-line tool that finds byte-for-byte duplicate files in a directory tree and (optionally, and only when you ask it to) removes the redundant copies.

No third-party packages required — just the Python standard library.

## Install
```bash
pip install .
# or, without installing:
python -m dedupe_cli.cli /path/to/scan
```
Requires Python 3.8+.

## Usage
```bash
dedupe-cli ~/Downloads                      # dry run (default)
dedupe-cli ~/Downloads --json               # machine-readable output
dedupe-cli ~/Downloads --apply              # actually delete redundant copies
dedupe-cli ~/Downloads --apply --trash-dir ~/.dedupe-trash
dedupe-cli ~/Downloads --min-size 1024
dedupe-cli ~/Downloads --keep shortest-path
```

Safety: dry run by default, symlinks skipped by default, `--trash-dir` option to avoid permanent deletion.

## Development
```bash
python -m unittest discover -s tests -v
```

## License
MIT — see LICENSE.

## Funding
This project is set up on [Drips](https://www.drips.network/) — see [FUNDING.json](./FUNDING.json).
