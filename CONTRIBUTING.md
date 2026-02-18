# Contributing Guidelines

## Security Concerns

Before any further discussion, a point about security needs to be addressed.
**If you find a serious security vulnerability that could affect current users,
please report it to maintainers via email or some form of private
communication**. For other issue reports, see below.

## Thanks!

First, thank you for your interest in contributing to site-nine! Even
though this is a small Python package project, it takes a bit of work to keep
it maintained. All contributions help and improve the package.

## Contact Us

The maintainers of site-nine can be reached most easily via email:

* Tucker Beck <tucker.beck@gmail.com>

## Conduct

Everyone's conduct should be respectful and friendly. For most folks, these
things don't need to be spelled out. However, to establish a baseline of
acceptable conduct, the site-nine project expects contributors to adhere
to the [Code of Conduct](CONDUCT.md).
Any issues working with other contributors should be reported to the maintainers.

## Contribution Recommendations

### Github Issues

The first and primary source of contributions is opening issues on github.
Please feel free to open issues when you find problems or wish to request a
feature. All issues will be treated seriously and taken under consideration.
However, the maintainers may disregard/close issues at their discretion.

Issues are most helpful when they contain specifics about the problem they
address. Specific error messages, references to specific lines of code,
environment contexts, and such are extremely helpful.

### Code Contributions

Code contributions should be submitted via pull-requests on github. Project
maintainers will review pull-requests and may test new features out. All
merge requests should come with commit messages that describe the changes as
well as a reference to the issue that the code addresses.

**All commits should include the issue #**

Commit messages should follow this format:

```
Issue #56: Fixed gizmo component that was parfolecting

The parfolection happening in the gizmo component was causing a vulnerability
in the anti-parfolection checks during the enmurulation process.

This was addressed by caching the results of parfolection prior to
enmurulation.

Also:
* Added and updated unit tests
* Added documentation
* Cleaned up some code
```

Code contributions should follow best-practices where possible. Use the
[Zen of Python](https://www.python.org/dev/peps/pep-0020/) as a guideline.
All code must stick to style guidelines enforced by ruff.

### Docstring Style

Docstrings should follow these conventions:

- **Single-line docstrings**: Triple quotes on same line as text
  ```python
  def simple_function():
      """Return the answer to everything."""
      return 42
  ```

- **Multi-line docstrings**: Opening and closing triple quotes on their own lines (symmetric style)
  ```python
  class MyClass:
      """
      Short summary on first line after opening quotes.

      More detailed explanation here, possibly spanning
      multiple paragraphs or including attributes/parameters.
      """
      pass
  ```

### Comments

Comments should be used sparingly and only to clarify confusing or non-obvious code. **Do not** use comments to restate what the code is already clearly doing.

**Bad (redundant):**
```python
# Validate the user input
validate_input(user_data)

# Loop through all items
for item in items:
    process(item)
```

**Good (clarifies intent):**
```python
# Use binary search since list is pre-sorted by timestamp
result = bisect_left(items, target_time)

# Workaround for API bug #1234 - remove when fixed
if response.status == 418:
    response.status = 200
```

If code needs extensive comments to be understood, consider refactoring it to be more self-documenting through better naming, decomposition, or docstrings.

Adding additional dependencies should be limited except where needed
functionality can be easily added through pip packages. Please include
dependencies that are only applicable to development and testing in the
dev dependency list. Packages should only be added to the dependency lists if:

* They are actively maintained
* They are widely used
* They are hosted on pypi.org
* They have source code hosted on a public repository (github, gitlab, bitbucket, etc)
* They include tests in their repositories
* They include a software license

### Documentation

Help with documentation is **always** welcome.

The site-nine project uses [sphinx](http://www.sphinx-doc.org/en/master/) for document generation.

Documentation lives in the `docs` subdirectory. Added pages should be
referenced from the table of contents.

Documentation should be clear, include examples where possible, and reference
source material as much as possible.

Documentation through code comments should be kept to a minimum. Code should
be as self-documenting as possible. If a section of code needs some explanation,
the bulk of it should be presented as sphinx-compatible
[docstrings](https://www.python.org/dev/peps/pep-0257/) for methods, modules,
and classes.

## Non-preferred Contributions

There are some types of contribution that aren't as helpful and are not as
welcome:

* Complaints without suggestion
* Criticism about the overall approach of the package
* Copied code without attribution
* Promotion of personal packages/projects without due need
* Sarcasm/ridicule of contributions or design choices
