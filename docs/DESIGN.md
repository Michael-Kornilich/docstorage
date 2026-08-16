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

## Developer environment

### Dev install

...

### Develop

...

## Deployment environment & pipeline

### Deployment

...

### Prod install

...
