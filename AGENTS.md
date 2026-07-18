## This file defines project's context invariant best practices and workflows

Run the app (run from `docstorage/`): `poetry run python src/main.py <args>`

**Function best practices:**
- Where reasonable, ALWAYS type-annotate parameters. Annotation is not required for functions whose parameters are internally required boilerplate (for example argparse.Action custom actions)
- ALWAYS write a concise docsting

**Overall best-practice:** keep is as simple as possible
