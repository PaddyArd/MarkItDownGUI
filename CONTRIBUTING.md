# Contributing

1. Fork and create a branch.
2. `python -m venv .venv`, activate it, `pip install -r requirements-dev.txt`.
3. Run the tests: `pytest`.
4. Keep Qt out of `engine.py`, since the engine must run without PyQt5 imported.
5. Follow Fluent Design conventions: use `qfluentwidgets` components and `FluentIcon`s, and respect the
   system theme. Do not hard-code colours.
6. Open a pull request describing the change and how you tested it (include Windows version if relevant).
