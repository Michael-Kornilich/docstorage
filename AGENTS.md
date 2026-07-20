## This file defines project's context invariant best practices and workflows

### Run

The `src/docstorage` is the entrypoint to the app
Hence, run with `sh src/docstorage <args>`

### Test

Run `poetry run python -m pytest tests/` from `docstorage/`

### Best practices

**Function best practices:**

- Where reasonable, ALWAYS type-annotate parameters.
  Annotation is not required for functions whose parameters are
  internally required boilerplate (for example, argparse.Action)
- ALWAYS write a concise docsting

**Overall best-practice:** keep is as simple as possible
