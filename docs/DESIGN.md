# Technical design

This document lists the technical implementation of requirements listed in `PRODUCT.md`

## Architecture

- sqlite for indexing
- python as code glue and file management
- A .json files for configs (user and local)

Main objects:

- CLI parser
- Database handler
- Orchestrator

### App usage

There are 2 configs: the user config and local config. The former includes the user specified landing directory. The
latter internal paths to the database and storage. These are filled at install-time via the installer.

## Development

### Dev install

...

### Develop

...

## Deployment

### Tooling

...

### Pipeline

...

### Production install

1. Make sure you have python (>=3.12) and pipx (>=1.4.0) installed
2. Run `pipx install docstorage`
3. Reopen terminal and set up the landing directory of your choice with
   `docstorage config set landing-directory <your directory>`

The default landing directory is `$HOME/docstorage`. It's recommended to specify the custom directory from the get-go.

