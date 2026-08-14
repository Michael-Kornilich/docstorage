## This file defines project's context invariant best practices and workflows

## Workflows

- **Run**: `cd` to the project root; the entrypoint is `src/docstorage`; run with `sh src/docstorage <args>`
- **Test**: Run `poetry run python -m pytest .` from `docstorage/`
- **Get / set config**: use `utility.get_config and utility.set_config`; specify which type to get/set - user config
  (the users can change it) or the local config (it's set up at install-time)

## Best practices

### For function

- Where reasonable, ALWAYS type-annotate parameters. Annotation is not required for functions whose parameters are
  internally required boilerplate (for example, argparse.Action)
- ALWAYS write a concise docstring

### Overall best-practice

Keep is as simple as possible

