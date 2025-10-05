# Simple Python Regex Engine

A lightweight regular expression engine implemented from scratch in Python.  
This project demonstrates the core principles of regex matching, including parsing, backtracking, and handling of various regex features.  
It uses a hand-written **recursive descent parser** and a **generator-based backtracking algorithm** to find matches.

---

## ✨ Features

This engine supports a useful subset of common regular expression syntax:

### Literals
- Matches specific characters (e.g., `a`, `b`, `1`).

### Wildcard
- `.` → Matches any single character.

### Quantifiers
- `+` → One or more.  
- `?` → Zero or one.
- `*` → Zero or more.

### Character Classes
- `[abc]` → Matches any of `a`, `b`, or `c`.  
- `[a-z0-9]` → Range-based classes.  
- `[^aeiou]` → Negated classes.  

### Escape Sequences
- `\d` → Matches any digit.  
- `\w` → Matches any alphanumeric character (letters, numbers) and underscore.  

### Groups and Alternation
- Capturing groups: `( ... )` for sub-patterns.  
- Alternation: `(cat|dog)` to match either branch.  

### Backreferences
- Match previously captured groups using `\1`, `\2`, etc.  

### Anchors
- `^` → Asserts the start of the string.  
- `$` → Asserts the end of the string.  

### File Search
- Single/multi-line file processing (line-by-line matching).  
- Multi-file support with `<filename>:` prefix.  
- Recursive directory traversal (`-r` flag) with relative paths and `<relpath>:` prefix.  
- Exits with code 0 on matches, 1 otherwise; clean output.

#### Syntax
```bash
python main.py -r -E "<pattern>" [<file1> <file2> ...]
```
```bash
# Search a single file
python main.py -E "appl.*" fruits.txt

# Search multiple files (with filename prefix)
python main.py -E "vegetable" fruits.txt veggies.txt

# Recursive search in directory
python main.py -r -E ".*er" dir/

# Output example:
# dir/fruits.txt:strawberry
# dir/subdir/vegetables.txt:celery
```
---

## 🚀 How to Use

The program is designed to be run from the **command line**, mimicking the behavior of simple `grep`.

### Syntax
```bash
echo "<input_string>" | python main.py -E "<pattern>"
```

### 📌 Example

To check if the pattern `(\w+) and \1` matches the string `"cat and cat"`:

```bash
echo "cat and cat" | python main.py -E "(\w+) and \1"
```

The program will print a **success** or **failure** message and exit with:

- **Status code 0** → Match found.  
- **Status code 1** → No match.  

---

## 🏗️ Architectural Overview

The engine is built on two primary components:

### Main Class
- Handles the command-line interface (CLI): Parses flags (-E, -r), optional filenames/directories, and input (stdin or files).
- Supports line-by-line processing for multi-line files/directories.
- Implements recursive file discovery (manual DFS traversal) for -r.  
- Parses arguments and reads input.  
- Acts as the **entry point** and orchestrates the matching process.  

### RegexEngine Class
- Contains all core regex-matching logic.  
- Implements a **Recursive Descent Parser** that parses and evaluates the pattern *on-the-fly* against the input string.  
- Uses **recursive backtracking with Python generators**.  

The core function, `match_inner`, is a **generator** that yields all possible successful match lengths for a given pattern and position.

---

## 🔮 Future Improvements

- **Additional Quantifiers**: Implement `{m,n}` and lazy quantifiers (e.g., +?).  
- **Performance Optimization**: Introduce memoization (caching) to avoid redundant computations.  
- **Non-Capturing Groups**: Add support for `(?: ... )`.  
- **Lookarounds**: Implement positive and negative lookaheads/lookbehinds.
- **Binary Files**: Handle non-text files gracefully (e.g., skip or warn).
- **More Escapes**: Add \s, \b, etc.