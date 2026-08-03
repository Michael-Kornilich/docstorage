# Docstorage

docstorage is a small, local document library for people who want their files organized without running a server, configuring a web application, or sending anything to the cloud.

It is designed for personal documents such as mail, registrations, letters, invoices and certificates. Its focus is deliberately narrow: reliably storing raw files, attaching useful metadata, and making matching files available when you need them.

## The mental model

Think of docstorage as a personal document vault with a simple command-line interface:

1. Give the app a file from anywhere on your machine.
2. The app moves the file into its own internal storage.
3. Ask for documents using metadata such as name, date, description, or tags.
4. The matching files are served into one landing directory.

The landing directory is your one-stop working area. Instead of searching across Downloads, email exports, old project folders, and external drives, you query the library and receive the relevant files in one place.

## Your files are fully managed

When a file is imported, docstorage takes ownership of it. The file is moved away from its original location and stored internally.

This is an intentional choice. Paths are fragile: files get renamed, folders get reorganized, drives get disconnected, and a library based on pointers eventually sends you looking through the entire machine to gather your own documents. docstorage keeps the file and its record together so that a document remains available through the library even after its original location is gone.

## Find files by what you know about them

Each document can have metadata including:

- name
- description
- date created
- date added
- tags

Names do not need to be unique. Documents have their own identities, so multiple files with the same filename can coexist. Queries can combine criteria, such as a date range, tags, and text in a description.

When results are served, docstorage handles filename collisions automatically by creating names such as document.pdf, document (1).pdf, and document (2).pdf. The landing directory can be configured to suit your workflow.

## Raw files, rich metadata

docstorage does not process the contents of your files. There are no embeddings, semantic search, OCR pipeline, or language-based queries. The files remain raw files, while the app maintains a substantial metadata index around them.

This keeps the behavior understandable, lightweight, and predictable. You decide what a document means by giving it a description, date, and tags; docstorage handles reliable storage and retrieval. Content indexing and embeddings may be considered later, but they are not part of the current model.

## Why use it instead of a larger text-processing app?

docstorage is for users who value control and low operational overhead over an all-in-one knowledge system.

- **No infrastructure:** one local process and one directory are enough. There is no server, web interface, database service, or account to maintain.
- **Private by default:** documents stay on the local machine and the app does not require an internet connection.
- **Predictable retrieval:** queries use explicit metadata filters and produce ordinary files in a known landing directory.
- **Less hidden processing:** docstorage does not transform, chunk, embed, or reinterpret document contents.
- **Fewer broken references:** the app stores the files itself instead of depending on paths that can become invalid.
- **Easy to audit:** the stored files are raw, and each entry has visible metadata plus a file hash for integrity checks.

The tradeoff is equally intentional: docstorage is not a full text-search engine, collaborative workspace, or document management suite. It provides a dependable local foundation rather than a large collection of features.

## Philosophy

**1 process. 1 directory. No server. No web. No internet connection. Stateless CLI.**

The app is operated through short commands. A command reads the local index, performs its requested file operation, and exits. There is no daemon running in the background and no remote service that must remain available.

## Brief technical notes

The index uses SQLite, while Python manages the actual file movement and serving. Files are tracked with SHA-256 hashes. Import and retrieval operations are flag-based so common document workflows do not require writing SQL.

### Examples

Import a file:

    docstorage import "path/to/certificate.pdf"
    docstorage import --description "Bank statement" --date-created 2025-01-05 --tags bank,finance "path/to/file.pdf"

Fetch matching files into the configured landing directory:

    docstorage fetch --tags finance --date-created ">=2025-01-01"
    docstorage fetch --name "certificate.pdf"

Inspect or maintain the library:

    docstorage overview
    docstorage healthcheck
    docstorage config list
