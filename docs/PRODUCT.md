# Product description

This documents lists the requirements for the docstorage.

## User Story

I need a small database for local document storage. It will include my personal documents such as certificates,
registrations, mail, etc. It has to have the following features:

- Minimal, simple and light-weight because I don't want to manage servers or complex apps
- Local. Cloud support may come later, but now the app is fully local. So a simple installation in docker or as an agent tool
  will be enough
- Heavy metadata indexed like document name, description, date created, date added, tags
- The app should fully own (store) files to reduce complexity and increase robustness since paths are fragile
- I want smooth, flag-based ingestion and querying. This will not be done with SQL because of awkward handling of file
  content and too many edge cases to safely handle (for example, arbitrary SQL execution or retrieval of random
  columns without file content).
- I expect the database to ingest files hashed and python manage the actual files. That is, move and serve (into a
  designated directory) upon calls. Pure filepaths won't cut it.
- The original files will be deleted (effectively moved)
- The database engine should be minimal and reliable.
- The focus is reliability and robustness, not feature-richness

Think of docstorage as a personal document vault with a simple command-line interface:

1. Give the app a file from anywhere on your machine.
2. The app moves the file into its own internal storage.
3. Ask for documents using metadata such as name, date, description, or tags.
4. The matching files are served into one landing directory.

The landing directory is your one-stop working area. Instead of searching across Downloads, email exports, old project
folders, and external drives, you query the library and receive the relevant files in one place.

### Philosophy

**1 process. 1 directory. No server. No web. No internet connection. Stateless CLI.**

The app is operated through short commands. A command reads the local index, performs its requested file operation, and
exits. There is no daemon running in the background and no remote service that must remain available.

### Why use it instead of a larger text-processing app?

docstorage is for users who value control and low operational overhead over an all-in-one knowledge system.

- **No infrastructure:** one local process and one directory are enough. There is no server, web interface, database
  service, or account to maintain.
- **Private by default:** documents stay on the local machine and the app does not require an internet connection.
- **Predictable retrieval:** queries use explicit metadata filters and produce ordinary files in a known landing
  directory.
- **Less hidden processing:** docstorage does not transform, chunk, embed, or reinterpret document contents.
- **Fewer broken references:** the app stores the files itself instead of depending on paths that can become invalid.
- **Easy to audit:** the stored files are raw, and each entry has visible metadata plus a file hash for integrity
  checks.

The tradeoff is equally intentional: docstorage is not a full text-search engine, collaborative workspace, or document
management suite. It provides a dependable local foundation rather than a large collection of features.

## What will be developed

**A CLI tool for local CR(U)D operations on files** will be developed. It must ingest files. This will be done as
follows:

- (begin DB commit) write file hash and metadata
- Copy the target file into the internal storage
- (Try to) delete the source file
- If all successful ⇒ commit DB change The ingestion will be flag based.

It must retrieve the files and create them in the landing directory. This will be done as follows:

- Query processed
- Files copied from the internal storage into the landing area In case of name collision return filename, filename (1),
  filename (2) based on the date created

The following columns will be created:

- id
- name
- description
- date_created
- date_added
- sha256

The primary key will be the ID, hence names can be duplicate

There will also be a document_tags table with:

- document id (foreign key)
- tag for easier filtering
