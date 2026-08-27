"""Pytest configuration for the backend suite.

`test_all.py` is not a pytest module. It is the standalone smoke script named in
its own docstring — `python tests/test_all.py` — and it runs its checks at import
time against a live server, finishing with `sys.exit(1)` if any fail. Pytest
collects it because of the file name, executes the whole script while importing
it, and the exit call kills the run with INTERNALERROR before the real tests
report. Which of the two happens depends on whether a server is up, so the suite
failed intermittently and for reasons that had nothing to do with the code.

The script stays runnable exactly as documented; it is only kept out of
collection.
"""
collect_ignore = ["test_all.py"]
