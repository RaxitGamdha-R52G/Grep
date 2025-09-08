# Regex Engine Architecture Overview

This document outlines the architecture of the simple Python regular expression engine. The engine is designed to parse and match a subset of regular expression syntax using a backtracking, generator-based approach.

## Core Components

The application is logically divided into two main components:

### Main Class
This class serves as the application's entry point and controller. Its primary responsibilities are to handle user interaction, manage the command-line interface (CLI), and orchestrate the overall execution flow.

- **Argument Parsing**: It parses the command-line arguments to extract the regex pattern.  
- **Input Handling**: It reads the input string from standard input.  
- **Orchestration**: It instantiates the `RegexEngine`, initiates the matching process, and outputs the final result.  

### RegexEngine Class
This is the core component responsible for all the logic related to parsing and matching the regular expression. It is designed to be completely decoupled from the user interface.

- **Pattern Parsing**: It breaks down the regex pattern into a sequence of logical units called "expressions" (which can be single characters, character classes, or groups).  
- **State Management**: It manages the state of the matching process, including the text captured by capturing groups.  
- **Backtracking Matcher**: It implements a recursive, generator-based algorithm (`match_inner`) that explores all possible match paths, handling backtracking when a path fails.  
- **Feature Support**: It contains the logic for handling literals, wildcards, character classes (`[...]`, `\d`, `\w`), quantifiers (`+`, `?`), alternation (`|`), capturing groups (`(...)`), backreferences (`\1`), and anchors (`^`, `$`).  

## Matching Strategy: Recursive Backtracking with Generators

The engine employs a powerful and flexible matching strategy based on recursive backtracking, implemented using Python generators.

### Parsing on the Fly
The engine doesn't pre-compile the pattern into a static data structure. Instead, it parses the pattern piece by piece during the matching process. The `parse_expression` method reads the next logical unit from the pattern string.

### Recursive Descent
The core matching function, `match_inner`, is recursive. It parses one expression, attempts to match it against the current position in the input string, and then recursively calls itself with the remainder of the pattern and the remainder of the input string.

### Generators for Backtracking
`match_inner` is a generator function (it uses `yield`). This is the key to handling backtracking efficiently and elegantly.

- When a match is found for a part of the pattern, it yields the result (the length of the match).  
- If the recursive call for the rest of the pattern fails, the control returns to the caller, which can then continue its loop to try another path (e.g., a different alternative in a group `(a|b)`, or a shorter match for a `+` quantifier).  

This avoids complex state management, as the state is naturally saved in the generator's stack frame.

### Handling Ambiguity
For ambiguous patterns like `a+` or `(cat|dog)`, the generator-based approach allows the engine to explore all possibilities.

- For `a+` against `"aaa"`, it will first try to match all three `"a"`s, then two, then one, yielding each possibility to the caller to see if the rest of the pattern can match from that point.  
- For `(cat|dog)`, it will first try the `cat` branch. If that entire path eventually fails, it backtracks and tries the `dog` branch.  

---

This architecture creates a clean separation of concerns between the user-facing logic and the complex state machine of the regex engine itself.
