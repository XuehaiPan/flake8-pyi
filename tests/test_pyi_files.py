import glob
import os
import re
import subprocess
import sys
from itertools import zip_longest

import pytest


@pytest.mark.parametrize("path", glob.glob("tests/*.pyi"))
def test_pyi_file(path: str) -> None:
    flags = []
    expected_output = ""

    match = re.search(r"_py3(\d+)\.pyi$", path)
    if match is not None:
        if sys.version_info < (3, int(match.group(1))):
            pytest.skip(f"Python {sys.version_info} is too old for {path}")

    with open(path, encoding="UTF-8") as file:
        file_contents = file.read()

    for lineno, line in enumerate(file_contents.splitlines(), start=1):
        if line.startswith("# flags: "):
            flags.extend(line.split()[2:])
            continue
        if line.startswith("#"):
            continue

        error_codes = list(re.finditer(r"# ([A-Z]\d\d\d )", line))

        for match, next_match in zip_longest(error_codes, error_codes[1:]):
            end_pos = len(line) if next_match is None else next_match.start()
            message = line[match.end() : end_pos].strip()
            expected_output += f"{path}:{lineno}: {match.group(1)}{message}\n"

    run_results = [
        # Passing a file on command line
        subprocess.run(
            ["flake8", "-j0", *flags, path],
            env={**os.environ, "PYTHONPATH": "."},
            stdout=subprocess.PIPE,
        ),
        # Passing "-" as the file, and reading from stdin instead
        subprocess.run(
            ["flake8", "-j0", "--stdin-display-name", path, *flags, "-"],
            env={**os.environ, "PYTHONPATH": "."},
            input=file_contents.encode("utf-8"),
            stdout=subprocess.PIPE,
        ),
    ]

    for run_result in run_results:
        output = run_result.stdout.decode("utf-8")
        output = re.sub(":[0-9]+: ", ": ", output)  # ignore column numbers
        assert output == expected_output
