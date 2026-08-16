# Docstorage

Docstorage is a small, local document library for people who want their files organized without running a server,
configuring a web application, or sending anything to the cloud.

It is designed for personal documents such as mail, registrations, letters, invoices and certificates. Its focus is
deliberately narrow: reliably storing raw files, attaching useful metadata, and making matching files available when you
need them.

You can find more on the product and the user story in `docs/PRODUCT.md`.

## Technical description

The index uses SQLite, while Python manages the actual file movement and serving. Files are tracked with SHA-256 hashes.
Import and retrieval operations are flag-based so common document workflows do not require writing SQL.

### Installation guide

1. Make sure you have python (>=3.12) and pipx (>=1.4.0) installed
2. Run `pipx install docstorage`
3. Reopen terminal and set up the landing directory of your choice with
   `docstorage config set landing-directory <your directory>`

The default landing directory is `$HOME/docstorage`. It's recommended to specify the custom directory from the get-go.

### CLI Examples

Import a file:

    docstorage import "path/to/doc.pdf"
    docstorage import --description "Bank statement" --date-created 2025-01-05 --tags bank,finance "path/to/file.pdf"

Fetch matching files into the configured landing directory:

    docstorage fetch --tags finance --date-created ">=2025-01-01"
    docstorage fetch --name "certificate.pdf"

Inspect or maintain the library:

    docstorage overview
    docstorage config list

You can find the complete CLI reference in `docs/CLI.md`.

You can find detailed technical description in `docs/DESIGN.md`.