## This file defines project's context invariant best practices and workflows

## Workflows

### Local setup

1. Make sure to have poetry installed
2. Clone the repo
3. cd to the project root
4. Run

```bash
   poetry install --no-root && \
   poetry run python scripts/dev-install.py
```

### Local build

...

### Deploy

...

### Local development

- **Run**: `cd` to the project root; the entrypoint is `src/docstorage`; run with `sh src/docstorage <args>`
- **Test**: Run `clear && poetry run python -m pytest -q` from `docstorage/`

- **Get / set config**: use `utility.get_config and utility.set_config`; specify which type to get/set - user config
  (the users can change it) or the local config (it's set up at install-time)

### Production install

1. Make sure you have python (>=3.12) and pipx (>=1.4.0) installed
2. Run `pipx install docstorage`
3. Reopen terminal and set up the landing directory of your choice with
   `docstorage config set landing-directory <your directory>`

## Best practices

### Overall best-practice

Keep is as simple as possible.

### For function

- Where reasonable, ALWAYS type-annotate parameters. Annotation is not required for functions whose parameters are
  internally required boilerplate (for example, argparse.Action)
- ALWAYS write a concise docstring
