# Developer Workflows

> This file defines project's context invariant best practices and workflows.

---

## Workflows

### Local setup

1. Make sure to have poetry installed
2. Clone the repo
3. cd to the project root
4. Run

```bash
   poetry install --no-root --with dev 
```

### Deploy

- Push to main, trigger the `ship-release.yaml` action

### Local development

- **Run code**: `cd` to the project root; Run with `DOCSTORAGE_ENV="dev" poetry run python -m src.<file> <arguments>`
- **Run the whole app**: `cd` to the project root; the entrypoint is `src/main.py`; run with
  `DOCSTORAGE_ENV="dev" poetry run python -m src.main <args>`
- **Test**: Run `DOCSTORAGE_ENV="test" poetry run python -m pytest` from `docstorage/`

> Note: when creating a new test file, always `from fixtures import *`. Because fixtures adjust sys.path so that source
> code can be discovered

- For a local installation run `pipx install --force .` from the project root

### Production install

1. Make sure you have python (>=3.12) and pipx (>=1.4.0) installed
2. Run `pipx install docstorage`
3. Reopen terminal and set up the landing directory of your choice with
   `docstorage config set landing-directory <your directory>`

## Best practices

### Overall best-practice

Keep it as simple as possible.

### For function

- Where reasonable, ALWAYS type-annotate parameters. Annotation is not required for functions whose parameters are
  internally required boilerplate (for example, argparse.Action)
- ALWAYS write a concise docstring
