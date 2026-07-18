import sqlite3

# resolve_db
# ensure that .db file exists, and the schema is exactly as expected.

# insert - insert an entry and move the file. The db receives metadata and the path. Then it handles the move
# read - read an entry and serve the file into the landing directory
# drop - remove an entry
# healthcheck - checks to what extent the index and the storage agree
