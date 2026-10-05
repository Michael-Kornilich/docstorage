# Product description

> This documents lists the product requirements for the docstorage.

---

### Why the product exists

I need a small database for local document storage. It will include my personal documents such as certificates,
registrations, mail, etc. It has to have the following features:

- Minimal, simple and light-weight because I don't want to manage servers or complex apps
- Local. Cloud support may come later, but now the app is fully local. So a simple installation in docker or as an agent
  tool will be enough
- Heavy metadata indexed like document name, description, date created, date added, tags
- The app should fully own (store) files to reduce complexity and increase robustness since paths are fragile.
- I expect the app to serve the queried files into a landing directory
- I want smooth, flag-based ingestion and querying.
- The focus is reliability and robustness, not feature-richness

### Common workflows

**Ingest**

- The user will call the cli with filepath, and provide optional metadata.
- The system moves the file into the internal storage and stores the metadata.

**Fetch**

- The user will call the cli with name, or id or any other metadata
- The app will find all the files that match the conditions
- The files will be copied from the storage into the landing directory

**Delete**

- The user will call the cli with name, or id or any other metadata
- If multiple files match the restrictions, the user will be explicitly prompted to delete them
- The files will be (irreversibly) deleted after confirmation

The landing directory is the one-stop working area. Instead of searching across Downloads, email exports, old project
etc. you query the library and receive the relevant files in one place.

### Non-development

- No SQL querying, because of awkward handling of file content and too many edge cases to safely handle (for example,
  arbitrary SQL execution or retrieval of random columns without file content).
