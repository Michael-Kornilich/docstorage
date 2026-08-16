# Technical design

This document lists the technical implementation of requirements listed in `docs/PRODUCT.md`

## Architecture

- SQLite for indexing
- python as code glue and file management
- A .json files for configs (user and local)
- poetry as a package manager

Main objects:

- CLI parser (`src/parser.py`)
- Database handler (`src/db.py`)
- Orchestrator (`src/main.py`)
- Configs: There are 2 configs - the user config and local config. The former includes the user specified landing
  directory. The latter internal paths to the database and storage. These are filled at install-time via the installer.

The default landing directory is `$HOME/docstorage`. It's recommended to specify the custom directory from the get-go.

## Development

### Tooling for the local build

...

### Tooling for deployment

...



