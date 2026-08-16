# CLI logic

**The file explains full CLI logic.**

First-order positional arguments. They are strictly mutually exclusive

**(docstorage) import**

Flags:

- --description | -de: accepts a string (300 characters limit). Optional: defaults to None
- --date-created | -dc: accepts a YYYY-MM-DD date. Optional: defaults to the current date
- --tags | -t: accepts a comma-separated string. Optional: defaults to an empty list

Positional arguments:

- filepath: string. Their parser does NOT check for validity (this is handled by the main)

**fetch**

Flags:

- --name | -n: file name
- --id: accepts an integer. The validation is handled by the main. Optional: defaults to None
- --description-contains: accepts a string (300 characters limit). Optional: defaults to None
- --date-created | -dc: accepts a YYYY-MM-DD date OR a date range. Optional: defaults to None The date range should have
  the following form: {<|<=|>|>=|=}YYYY-MM-DD,{<|<=|>|>=|=}YYYY-MM-DD or {<|<=|>|>=|=}YYYY-MM-DD as a shortcut. The
  resulting object in the Namespace object should be a DateRange data class with min, max and left/right date closed
  attributes. None for missing values (both for dates and left/right close)
- --date-added | -da: accepts a YYYY-MM-DD date OR a date range. Optional: defaults to None
- --tags | -t: accepts a comma-separated string or a string. Returns a list in the Namespace. Optional: defaults to an
  empty list
- --keep-existing: a boolean flag. Does not accept a value. Optional: defaults to false
- --dry-run: a boolean flag. If invoked nothing changes until the actual serving. Then the app just prints which files
  will be fetched without actually fetching them

Positional arguments:

- name. This is mutually exclusive with --name flag. Either the name positional argument or the flag. Can work in
  combination with other flags

**overview**
No arguments are accepted. just a boolean value if invoked

**delete**
Same semantics as fetch (without --keep-existing), but in this case the items are deleted. That is you can call a fetch
command, then an identical delete command, such that the fetched files will be deleted

Flags:

- --all | -a: if there are multiple items that fit the criteria, all will delete all of them. Otherwise, error. If only 1
  item the flag has no effect and the item is deleted anyway

**config**
Positional arguments:

- list: show the current config
- set <field> <value>: set value to the given field

**healthcheck**
No arguments are accepted. just a boolean value if invoked