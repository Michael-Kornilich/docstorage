# Developer Workflows

> This file defines project's context invariant best practices and workflows.

---

## Workflows

### Local setup

1. Make sure to have poetry installed
2. Clone the repo
3. cd to the project root
4. Install all the dependencies *and* the docstorage package itself with:

```bash
   poetry install --with dev 
```

by default, it installs it in editable mode.

> Warning: the source code is editable, but not the `pyproject.toml`. Therefore, a re-installation is required to update
> it

### Deploy

- Push to main, trigger the `ship-release.yaml` action

### Local development

- **Run code**: `cd` to `src`; Run with `DOCSTORAGE_ENV="dev" poetry run python -m src.<file> <arguments>`
- **Run the whole app**: `cd` to `src`; the entrypoint is `src/main.py`; run with
  `DOCSTORAGE_ENV="dev" poetry run docstorage <args>`
- **Test**: Run `poetry run pytest` from `docstorage/`

The testing pipeline is:

```text
(poetry install == installs the docstorage package in the environment =>) 
run tests => 
the tests import the package from the poetry index. Changes are synced since editable mode 
```

This was implemented this way for multiple reasons:

- To catch packaging errors early on. If `pyproject.toml` is invalid the package won't install
- To avoid `sys.path.append` hacks for development since tests cannot discover `docstorage` package.

### Local build

- Run `poetry build` from the project root to build a wheel and the sdist

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
