# CLI reference

> This document describes docstorage's CLI

---

```text
docstorage <command> [options] [arguments]
```

Run `docstorage <command> --help` for the command's built-in help.

## Commands

| Command                       | Purpose                                           |
|-------------------------------|---------------------------------------------------|
| [`import`](#import)           | Add a file to the document library                |
| [`fetch`](#fetch)             | Copy matching files to the landing directory      |
| [`delete`](#delete)           | Delete matching documents                         |
| [`overview`](#overview)       | Show a summary of the library                     |
| [`healthcheck`](#healthcheck) | Check that the index and stored files are in sync |
| [`config`](#config)           | View or change user configuration                 |

## `import`

Add a file to the library. The source path is required.

```bash
docstorage import [options] <source>
```

Options:

- `--description TEXT`, `-de TEXT` — description, up to 300 characters.
- `--date-created DATE`, `-dc DATE` — creation date in `YYYY-MM-DD` format. Defaults to today.
- `--tags TAGS`, `-t TAGS` — comma-separated tags, for example
  `bank,finance`.

Example:

```bash
docstorage import \
  --description "Bank statement" \
  --date-created 2025-01-05 \
  --tags bank,finance \
  "path/to/statement.pdf"
```

## `fetch`

Copy documents matching the supplied filters to the configured landing directory. With no filters, all documents are
matched.

```bash
docstorage fetch [options] [name]
```

The file name can be supplied either as the positional `name` argument or with `--name` / `-n`, but not both.

### Filters

- `name` or `--name NAME`, `-n NAME` — match a file name.
- `--id ID` — match a file ID shown in a file listing.
- `--description-contains TEXT` — match descriptions containing the given text, up to 300 characters.
- `--date-created DATE | DATE-RANGE`, `-dc DATE | DATE-RANGE` — match by creation date.
  See [Date filters](#date-filters).
- `--date-added DATE | DATE-RANGE`, `-da DATE | DATE-RANGE` — match by date added. See [Date filters](#date-filters).
- `--tags TAGS`, `-t TAGS` — comma-separated tags. A document matches if it contains at least one supplied tag.
- `--keep-existing` — keep files already in the landing directory. Without this option, fetching fails when that
  directory is not clean.
- `--dry-run` — perform checks and show the files that would be fetched without copying anything.

Examples:

```bash
docstorage fetch --tags finance --date-created ">=2025-01-01"
docstorage fetch --name "certificate.pdf"
docstorage fetch --tags finance --dry-run
```

## `delete`

Delete documents matching the same filters as [`fetch`](#fetch).

```bash
docstorage delete [options] [name]
```

It is an error to delete multiple matching documents unless `--all` is provided. The `--all` option is unnecessary when
exactly one document matches.

Additional options:

- `--all`, `-a` — permanently delete all matching documents.
- `--dry-run` — show matching documents and the effect of the operation without deleting anything.

Examples:

```bash
docstorage delete --name "old-statement.pdf"
docstorage delete --tags obsolete --all
docstorage delete --date-created "<2020-01-01" --dry-run
```

## Date filters

`--date-created` and `--date-added` accept either a single date or a date range. Dates use `YYYY-MM-DD`.

```bash
# On an exact date
docstorage fetch --date-created 2025-01-05

# On or after / before a date
docstorage fetch --date-created ">=2025-01-01"
docstorage fetch --date-added "<2025-06-01"

# Between two dates, with independently chosen boundaries
docstorage fetch --date-created ">=2025-01-01,<=2025-03-31"
```

Supported operators are `<`, `<=`, `>`, `>=`, and `=`. A range has the form
`OPERATOR DATE,OPERATOR DATE`; a single comparison such as `>=2025-01-01`
is a shortcut for an open-ended range.

## `overview`

Show the total number of documents, the tags in use, and the minimum and maximum creation dates.

```bash
docstorage overview
```

This command does not accept options or arguments.

## `healthcheck`

Check whether the database index and stored files are in sync. Any mismatches are listed in the output.

```bash
docstorage healthcheck
```

This command does not accept options or arguments.

## `config`

View or update the user configuration.

```bash
docstorage config list
docstorage config set <field> <value>
```

`list` displays the current configuration. `set` updates a configuration field, such as the landing directory:

```bash
docstorage config set landing-directory "/path/to/landing-directory"
```
