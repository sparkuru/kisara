# Implementation and validation

- Result callbacks now quote the user command that starts each save attempt. Direct partial-failure retry selection still stores the bot result message ID.
- Setu transfer caps now load only K/M/G size strings; `"100M"` and `"1G"` retain the prior byte limits. The private ignored config and tracked example were updated.
- The first full test run passed 186 and failed 3 unrelated settings tests because they read the repository's private news config. Those tests now run from `tmp_path`, leaving the private config untouched.
- Review found that a size with over 4,300 decimal digits raised raw `ValueError`; it now raises `ConfigurationError` and has a regression test.
- Final `./dev.sh --all`: 191 passed in Python 3.12.14. `git diff --check` and task context validation passed.
- Work commit: `0cd7419`. Live QQ rendering was not verified; both preview containers were stopped when checked.
