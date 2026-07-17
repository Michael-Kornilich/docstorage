## User Story
I need a small database for local document storage. It will include my personal documents such as certificates, registrations, mail, etc.
It has to have the following features:
- Minimal, simple and light-weight because I don't want to manage servers or complex apps
- Local. Cloud support may come later, but now the app is fully local. So a simple install in docker or as an agent tool will be enough
- Heavy metadata indexed like document name, description, date created, date added, tags, comment
- The app should fully own files to reduce complexity
- I want smooth ingestion. This will not be done with SQL because of awkward handling of file content
- and smooth flag-based querying.
- Both ingestion and queries will be flag based because there are too many edge cases with SQL to safely handle (for example prevent arbitrary SQL execution or retrieval of random columns w.o. file content)
- I expect the databse to ingest files hashed and python manage the actual files. That is, move and serve (into a designated directory) upon calls. Pure filepaths won't cut it.
- The original files will be deleted (effectively moved)
- The database engine should be minimal and reliable. 
- The focus is reliability and robustness, not feature-richness

## What will be developed

**A CLI tool for local CR(U)D operations on files** will be developed
It must ingest files (and delete the originals). This will be done as follows:
- (begin DB commit) write file hash and metadata
- Copy the target file into the internal storage
- (Try to) delete the source file
- If all successful => commit DB change
The ingestion will be flag based.

It must retrieve the files and create them in the landing directory. This will be done as follows:
- Query processed
- Files copied from the internal storage into the landing area
- (optionally deleted)
In case of name collision return filename, filename (1), filename (2) based on the date created

The database will store hashes of files while python will manage the actual files
The following columns will be created:
- id
- name
- description
- date_created
- date_added
- comment
- sha256

The primary key will be the ID, hence names can be duplicate

There will also be a document_tags table with:
- document id (foreign key)
- tag
for easier filering

## CLI examples: 
**Create**
- docstorage import 'file/path' (if no date given, set to current date, the name is inferred by the file name)
- docstorage import --description "This is a new file" --date-created '2025-01-05' --tags sparkasse,hvb --comment 'active' 'file/path'

**Read**
- docstorage fetch --date-created '>=2025-01-01,<=2025-01-05' --tags sparkasse,hvb --comment-contains 'active' --keep-existing
- docstorage fetch --tags sparkasse --date-created '>=2026-01-01'
(--keep-existing does not delete files from the landing directory that already were there. If the landing directory is not clean and keep existing is not passed, error)
* docstorage fetch --id 123
* docstorage fetch --name filename
* docstorage overview (gives the number of files, and a table of names + description (shortened) + comment + tags)

**Update**
No concept yet

**Delete**
- docstorage delete --name 'filename' --all (deletes all files with the given name)
- docstorage delete --id 123 (deletes the exact entry)
- docstorage delete --comment-contains 'deprecated' (if only a single occurance - deletes, if many - error)
(--all deletes all that meet the criteria)

**Meta**
- docstorage healthcheck (comprare hashes in the database with the available files, give report of differences)
- docstorage config list (list the current config)
- docstorage config set landing-dir file/path (to change the landing directory)

A json file for config (like the landing directory)

## Architecture
- sqlite for indexing
- python as code glue and file managment

Main objects:
- CLI parser
- Database handler
- Orchestrator
