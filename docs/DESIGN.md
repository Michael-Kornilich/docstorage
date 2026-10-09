# Technical design

> This document lists the technical implementation of docstorage

---

## Architecture

- SQLite for indexing
- python as code glue and file management
- A .json files for configs (user and local)

Main objects:

- CLI parser (`src/parser.py`)
- Database handler (`src/db.py`)
- Orchestrator (`src/main.py`)
- Configs: There are 2 configs - the user config and local config. The former includes the user specified landing
  directory. The latter internal paths to the database and storage. These are filled at install-time via the installer.

The default landing directory is `$HOME/docstorage`. It's recommended to specify the custom directory from the get-go.

## App design

The app ingests files as follows:

- (begin DB commit) write file hash and metadata
- Copy the target file into the internal storage
- (Try to) delete the source file
- If all successful ⇒ commit DB transaction

The app copies files into the landing directory. In case of name collision return filename, filename (1), filename (2)
based on which files were fetched first.

Fail-safes:

- In case a file cannot be moved or any error occurs upon copying or deleting, the program errors out and the DB
  transaction is aborted
- If the process crashes, the user can use a backup to restore the last state (not implemented yet)

The following columns in the index were created:

- id
- name
- description
- date_created
- date_added
- sha256

The primary key will be the ID, hence names can be duplicate

There will also be a `tags` table with:

- document id (foreign key)
- tag

## Development

- pytest for testing

## Deployment

### Tooling

- poetry as a package builder
- pipx as an environment manager. So a wheel is installed with pipx
- GH action as release glue

### Release workflow

- Push to main
- Choose the type of release
- Trigger the `ship-release.yaml` workflow

`ship-release.yaml` workflow automatically does the following:

- Tests the app (all tests must succeed)
- Bumps the version according to the chosen release
- Builds wheels with poetry
- Makes sure the given version is actually bigger than the latest release
- Tags the latest commit (the one being built) with `release-X.YY.ZZZ`
- Pushes the wheels to PyPi

### Peripheral architecture

Both config and persistent storage land in their respective directory. The exact directories are resolved by
`platformdirs`
