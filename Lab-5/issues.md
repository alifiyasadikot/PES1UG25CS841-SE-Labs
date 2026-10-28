# Lab 5: Static Code Analysis - Issue Log

**Student:** Sadikot Alifiya Mustafabhai (PES1UG25CS841)
**Repository:** L5_64_public-transit-fare-calculator
**File analysed:** `fare_calculator.py`

Line numbers refer to the **original** `fare_calculator.py` (the first commit,
"Add original fare calculator from assigned repo").

## Results before and after

| Tool | Before | After |
|------|--------|-------|
| Pylint | 5.80/10, 34 messages | **10.00/10**, 0 messages |
| Bandit | 5 issues (1 High, 3 Medium, 1 Low) | **No issues identified** (1 reviewed `# nosec B601`) |
| Flake8 | 20 violations | **0 violations** (empty report) |

Full reports: `reports/before/` and `reports/after/` (`pylint_report.txt`,
`bandit_report.txt`, `flake8_report.txt`, plus `program_output.txt`).

## Issue table (high and medium severity first)

| # | Issue | Type | Line(s) | Description | Fix Approach |
|---|-------|------|---------|-------------|--------------|
| 1 | SSH host key auto-accepted | Security - Bandit B507 (**High**) | 80 | `AutoAddPolicy()` trusts any unknown host key, so an attacker could pretend to be the gate machine (man-in-the-middle) and receive the fare file. | Call `load_system_host_keys()` and use `paramiko.RejectPolicy()`, so unknown hosts are refused. |
| 2 | Shell injection in remote command | Security - Bandit B601 (**Medium**) | 82 | `"install_fares " + fare_file` is run by the gate's shell. A name like `f.csv; rm -rf /` would run a second command. There was also no timeout, the exit status was ignored and the client was not closed if an error occurred. | Quote the argument with `shlex.quote(fare_file)`; add connect and command timeouts; check the exit status and raise `RuntimeError` on failure; close the client in `finally`. Bandit flags every `exec_command`, so after review the line is marked `# nosec B601` with a comment explaining why. |
| 3 | Insecure MD5 hash | Security - Bandit B303 (**Medium**) | 60 | MD5 is broken (collisions can be forged), so two different tickets could get the same checksum. | Use SHA-256: `hashes.Hash(hashes.SHA256())`. |
| 4 | Unsafe XML parsing | Security - Bandit B317 (**Medium**) and B406 (Low) | 2, 64-76 | `xml.sax.parseString` on untrusted XML is open to entity-expansion ("billion laughs") and external-entity (XXE) attacks. | Parse with `defusedxml.ElementTree.fromstring(xml_text, forbid_dtd=True)` and read the `stop` elements; the SAX handler class is no longer needed. |
| 5 | Daily cap never applied | Bug - Pylint R1730 (with R1721, R1728) (**Medium**) | 35-41 | The loop only reassigned the loop variable `f`, so nothing was capped: the day in `main()` printed 208.0 instead of 150. Pylint's hint pointed at this dead loop. | Remove the loop and return `min(sum(fares), DAILY_CAP)`. |
| 6 | Mutable default argument | Bug - Pylint W0102 (**Medium**) | 46 | `categories=[]` is created once and shared by every call to `tapOut`. | Default to `None` and create a new list inside the function. |
| 7 | Fare slab boundary | Bug - found by running the program (**Medium**) | 18 | `km < limit` sent exactly 2 km to the Rs.20 slab and exactly 32 km to Rs.60. | Use `km <= limit` (2 km -> 10, 32 km -> 50). |
| 8 | Peak check uses only the hour | Bug - found by running the program (**Medium**) | 23-25 | Only the hour was compared, so 20:45 (and 10:30) counted as peak. | Compare full HH:MM times with 08:00-10:00 and 17:00-20:00; reject invalid times with `ValueError`. |
| 9 | Concessions stacked | Bug - found by running the program (**Medium**) | 31-32 | Student and senior discounts were multiplied together (Rs.10.125 for a 10 km off-peak trip). | Apply only the largest concession the rider has (Rs.13.50). |
| 10 | Card balance can go negative | Bug - found by running the program (**Medium**) | 46-50 | A card with Rs.25 paid for a Rs.50 trip and ended at -25. | `tap_out` raises `ValueError` and leaves the balance unchanged; `top_up` rejects amounts <= 0. |
| 11 | Floating-point money | Bug - found by running the program (Low) | 9-11, 43-54 | Topping up 0.1 then 0.2 printed 0.30000000000000004. | Store fares and balances as `Decimal` rounded to the paisa. |
| 12 | Unused import | Pylint W0611 / Flake8 F401 (Low) | 1 | `import os` was never used. | Removed. |
| 13 | Lambda assigned to a name / unnecessary lambda | Pylint C3001, W0108 / Flake8 E731 (Low) | 14, 57 | `baseOf` only wrapped `fareForDistance`; `sorted(..., key=lambda r: baseOf(r))[0]` sorted the whole list to get one item. | Call `fare_for_distance` directly and use `min(routes, key=fare_for_distance)`. |
| 14 | Useless `else` on loop | Pylint W0120 (Low) | 20-21 | `for ... else` without a `break` is confusing. | Removed the `else`; return `MAX_FARE` after the loop. |
| 15 | Naming and docstrings | Pylint C0103, C0114, C0115, C0116 (Low) | Throughout | camelCase function names; no module, class or function docstrings. | Renamed to snake_case, added docstrings, and run `main()` only under `if __name__ == "__main__":`. |
| 16 | Blank lines | Flake8 E302, E305 (Low) | 16-85, 100 | Only one blank line between top-level functions. | Two blank lines around every top-level function. |
| 17 | Lines too long | Flake8 E501 (Low) | 89, 90, 96, 98 | Lines longer than 79 characters. | Wrapped the long calls and the `day` list. |

## Which commit fixed what

| Commit | Issues |
|--------|--------|
| Fix security issues reported by Bandit | 1, 2, 3, 4 |
| Fix code quality issues reported by Pylint | 5, 6, 12, 13, 14, 15 |
| Fix PEP 8 style issues reported by Flake8 | 16, 17 (F401 and E731 were already gone after the Pylint commit) |
| Fix fare logic bugs found by running the program | 7, 8, 9, 10, 11 |

## How to reproduce

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt pylint bandit flake8
python fare_calculator.py
pylint fare_calculator.py > pylint_report.txt
bandit -r fare_calculator.py > bandit_report.txt
flake8 fare_calculator.py > flake8_report.txt
```
