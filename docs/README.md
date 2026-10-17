# Docstorage

* GitHub - https://github.com/Michael-Kornilich/docstorage

Docstorage is a small, local document library for people who want their files organized without running a server,
configuring a web application, or sending anything to the cloud.

It is designed for personal documents such as mail, registrations, letters, invoices and certificates. Its focus is
deliberately narrow: reliably storing raw files, attaching useful metadata, and making matching files available when you
need them.

The app stores a copy of the files given to it in its internal storage. By default, the original files remain at their
source locations. If desired, set the `delete-original` configuration option to `True` to remove each source file after
it has been imported successfully. All further management is then done via the CLI.

You can find more on the product and the user story in `docs/PRODUCT.md`
on GitHub.

## Installation guide

1. Make sure you have python (>=3.12) and pipx (>=1.4.0) installed
2. Run `pipx install docstorage`
3. Reopen terminal and set up the landing directory of your choice with
   `docstorage config set landing-directory <your directory>`

The default landing directory is `<DOCUMENT-DIR>/docstorage`. It's recommended to specify the custom directory from the
get-go.

## CLI Examples

Import a file:

    docstorage import "path/to/doc.pdf"
    docstorage import --description "Bank statement" --date-created 2025-01-05 --tags bank,finance "path/to/file.pdf"

Imports copy files by default. To move files instead, enable source deletion:

    docstorage config set delete-original True

Fetch matching files into the configured landing directory:

    docstorage fetch --tags finance --date-created ">=2025-01-01"
    docstorage fetch --name "certificate.pdf"
    docstorage fetch "*"

Inspect or maintain the library:

    docstorage overview
    docstorage config list

You can find the complete CLI reference in `docs/CLI.md`
on GitHub.

## Technical description

The index uses SQLite, while Python manages file copying, optional source deletion, and serving. Files are tracked with
SHA-256 hashes.
Import and retrieval operations are flag-based so common document workflows do not require writing SQL.

You can find detailed technical description in `docs/DESIGN.md`
on GitHub.

A developer / contributor getting-started guide is in `docs/DEV.md`
on GitHub.
