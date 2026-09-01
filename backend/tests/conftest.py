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

import os
import tempfile

import pytest


@pytest.fixture(autouse=True, scope="session")
def _own_data_directory():
    """Run the suite against a store of its own.

    The tests were importing documents into the real one — the same database
    the running app uses — so a test's leftovers were in the user's uploads,
    and a test that counted documents depended on what had been left there by
    the last run. The path is read when a store is opened, so setting it here
    is enough.
    """
    # Windows will not remove a directory whose files are still open, and the
    # store keeps its database open for the life of the process; the folder is
    # the operating system's to clear up either way.
    with tempfile.TemporaryDirectory(prefix="docos-tests-",
                                     ignore_cleanup_errors=True) as directory:
        before = os.environ.get("DOCPILOT_DATA_DIR")
        os.environ["DOCPILOT_DATA_DIR"] = directory
        try:
            yield directory
        finally:
            if before is None:
                os.environ.pop("DOCPILOT_DATA_DIR", None)
            else:
                os.environ["DOCPILOT_DATA_DIR"] = before
