# Lab 5: Reflection

**Student:** Sadikot Alifiya Mustafabhai (PES1UG25CS841)

### 1. Which issues were the easiest to fix, and which were the hardest? Why?

The easiest were the Flake8 and Pylint style issues: the missing blank lines
(E302/E305), long lines (E501), the unused `os` import, camelCase names and
missing docstrings. Each message named the exact line and the fix was
mechanical.

The hardest were the security issues and the daily cap. For Bandit B601 I had
to understand why string-joining a file name into a remote shell command is
dangerous and fix it with `shlex.quote`, and then accept that Bandit still
reports the line because it cannot see the quoting. Moving from `xml.sax` to
`defusedxml` meant rewriting how the stops are read. The daily cap was tricky
because Pylint's suggestion (`f = min(f, DAILY_CAP)`) would have silenced the
warning but kept the bug; the real fix was to cap the total. The other logic
bugs (2 km and 32 km slab limits, 20:45 counted as peak, stacked concessions,
a negative card balance, 0.30000000000000004) were not reported by any tool.
I only found them by running the program and checking each printed value.

### 2. Did the static analysis tools report any false positives? If so, describe one example.

Yes. After I quoted the argument with `shlex.quote`, Bandit still reported
B601 ("possible shell injection via Paramiko call") on `exec_command`. Bandit
flags every `exec_command` call because it cannot tell whether the input is
sanitised. I reviewed the line, added a comment explaining why it is safe and
marked it `# nosec B601`, so Bandit now lists it as skipped instead of hiding
it silently.

Another example: on my first Pylint run, before installing the program's
packages in my virtual environment, Pylint reported E0401 "Unable to import
'paramiko'" and "'cryptography'". The code was fine; the environment was
missing the packages.

### 3. How would you integrate static analysis tools into your actual software development workflow?

- **Locally:** run Flake8 and Pylint in the editor, and add a pre-commit hook
  that runs Flake8, `pylint --fail-under=9.5` and `bandit -ll` before each
  commit, so problems are caught before they reach the repository.
- **In CI:** add a GitHub Actions job that runs all three tools on every push
  and pull request, and fails the build on any Bandit Medium/High issue, any
  Flake8 error or a Pylint score below the agreed threshold.
- **Configuration:** keep the rules in `.flake8`, `.pylintrc` or
  `pyproject.toml` so everyone uses the same settings, and review every
  `# nosec` or `# pylint: disable` in code review so suppressions need a reason.
- **Alongside tests:** static analysis does not replace unit tests. The fare
  bugs in this lab show that tests on real inputs are still needed.

### 4. What tangible improvements did you observe in the code quality, readability, or potential robustness after applying the fixes?

- **Scores:** Pylint went from 5.80/10 to 10.00/10, Bandit from 5 issues
  (1 High, 3 Medium, 1 Low) to none, and Flake8 from 20 violations to 0.
- **Security:** the gate connection now rejects unknown SSH hosts, the remote
  command cannot be injected into, ticket checksums use SHA-256, and XML is
  parsed with `defusedxml`.
- **Correctness:** the daily cap is applied and `tap_out` no longer shares one
  default list between calls. Running the program also led to fixing the slab
  boundaries, peak hours, concessions, negative balances and float money.
- **Readability:** snake_case names, docstrings, commented fare rules and no
  unnecessary lambdas make the code easier to follow.
- **Robustness:** the SSH step has timeouts, checks the remote exit status and
  always closes the connection; invalid times and top-ups raise clear errors.

The main lesson was that a clean report is a good baseline, but it does not
prove the program is correct.
