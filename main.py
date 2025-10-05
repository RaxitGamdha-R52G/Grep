import os
import sys

class RegexEngine:
    """
    A simple regular expression engine that supports a subset of regex features,
    including literals, character classes, escape sequences (\\d, \\w), quantifiers (+, ?, *),
    the wildcard (.), groups for alternation (cat|dog), quantifiers on groups,
    multiple and nested backreferences (\\1, \\2), and anchors (^, $).

    This implementation uses a generator-based backtracking approach to find all
    possible matches.
    """
    def __init__(self, pattern: str):
        """
        Initializes the regex engine.

        Args:
            pattern (str): The regular expression pattern to be used for matching.
        """
        # Store the user-provided regex pattern as an instance variable.
        self.pattern = pattern
        # Initialize a list to store the strings captured by groups. Will be sized later.
        self.captures = []
        # Pre-calculate the number of capture groups in the pattern for capture list initialization.
        self.num_capture_groups = self._count_capture_groups(self.pattern)

    def _count_capture_groups(self, pattern: str) -> int:
        """Counts the number of capturing groups '(' in the pattern, ignoring escaped ones."""
        count = 0
        i = 0
        while i < len(pattern):
            # We must ignore escaped parentheses like '\('.
            if pattern[i] == '\\':
                i += 2 # Skip the backslash and the character after it.
            elif pattern[i] == '(':
                count += 1
                i += 1
            else:
                i += 1
        return count

    # ---------- Character Type Checks ----------
    def is_digit(self, c: str) -> bool:
        """Checks if a character is a numeric digit ('0'-'9')."""
        return c.isdigit()

    def is_alpha(self, c: str) -> bool:
        """Checks if a character is an alphabetic letter ('a'-'z', 'A'-'Z')."""
        return c.isalpha()

    def is_underscore(self, c: str) -> bool:
        """Checks if a character is an underscore ('_')."""
        return c == "_"

    # ---------- Utility for Matching Character Classes ----------
    def match_class(self, c: str, class_str: str, negated: bool = False) -> bool:
        """
        Checks if a character `c` matches the rules of a character class string (e.g., "[a-z0-range]").
        """
        matched = False
        i = 0
        while i < len(class_str):
            # Handle character ranges like 'a-z'.
            if i + 2 < len(class_str) and class_str[i + 1] == "-":
                if class_str[i] <= c <= class_str[i + 2]:
                    matched = True
                    break
                i += 3
            # Handle single characters.
            else:
                if class_str[i] == c:
                    matched = True
                    break
                i += 1
        # Apply negation if the class starts with '^'.
        return not matched if negated else matched

    # ---------- Pattern Parsing ----------
    def parse_single_atom(self, pattern: str) -> tuple:
        """
        Parses a single 'atom' (the smallest non-group unit) from the start of the pattern string.
        """
        p = 0
        negated = False
        # Handle escape sequences.
        if pattern[p] == "\\":
            p += 1
            if p >= len(pattern):
                raise RuntimeError("Incomplete escape sequence in pattern")
            esc = pattern[p]
            # Check for backreferences (\1, \2, etc.).
            if esc.isdigit():
                atom_type = "backreference"
                atom = int(esc)
            # Check for character class escapes (\d, \w).
            elif esc in "dw":
                atom_type = "escape"
                atom = esc
            # Treat all other escapes as literal characters.
            else:
                atom_type = "literal"
                atom = esc
            atom_len = p + 1
        # Handle character classes [...].
        elif pattern[p] == "[":
            p += 1
            if p < len(pattern) and pattern[p] == "^":
                negated = True
                p += 1
            start = p
            while p < len(pattern) and pattern[p] != "]":
                p += 1
            if p >= len(pattern):
                raise RuntimeError("Pattern missing closing bracket ']'")
            class_str = pattern[start:p]
            atom_type = "class"
            atom = class_str
            atom_len = p + 1
        # Handle the wildcard '.'.
        elif pattern[p] == ".":
            atom_type = "wildcard"
            atom = "."
            atom_len = 1
        # Handle a literal character.
        else:
            atom_type = "literal"
            atom = pattern[p]
            atom_len = 1
        return atom_type, atom, atom_len, negated

    def find_matching_paren(self, pattern: str, start_index: int = 0) -> int:
        """
        Finds the index of the matching closing parenthesis for a group, handling nested groups.
        """
        open_parens = 1
        for i in range(start_index + 1, len(pattern)):
            if pattern[i] == '(':
                open_parens += 1
            elif pattern[i] == ')':
                open_parens -= 1
            if open_parens == 0:
                return i
        raise RuntimeError("Pattern missing closing parenthesis ')'")

    def split_alternatives(self, group_content: str) -> list[str]:
        """
        Splits a group's content string by the top-level alternation operator '|',
        correctly ignoring '|' inside nested groups.
        """
        alternatives = []
        paren_level = 0
        current_alternative_start = 0
        for i, char in enumerate(group_content):
            if char == '(':
                paren_level += 1
            elif char == ')':
                paren_level -= 1
            elif char == '|' and paren_level == 0:
                alternatives.append(group_content[current_alternative_start:i])
                current_alternative_start = i + 1
        alternatives.append(group_content[current_alternative_start:])
        return alternatives

    def parse_expression(self, pattern: str) -> tuple:
        """
        Parses the next logical expression from the pattern (an atom or a group).
        """
        if pattern.startswith('('):
            end_paren_idx = self.find_matching_paren(pattern, 0)
            group_content = pattern[1:end_paren_idx]
            alternatives = self.split_alternatives(group_content)
            return "group", alternatives, end_paren_idx + 1, False
        else:
            return self.parse_single_atom(pattern)

    def get_match_fn(self, atom_type: str, atom: str, negated: bool) -> callable:
        """
        A factory that returns a specific function to check if a character matches a parsed atom.
        """
        if atom_type == "escape":
            if atom == "d":
                return self.is_digit
            elif atom == "w":
                return lambda c: self.is_alpha(c) or self.is_digit(c) or self.is_underscore(c)
        elif atom_type == "literal":
            return lambda c: c == atom
        elif atom_type == "class":
            return lambda c: self.match_class(c, atom, negated)
        elif atom_type == "wildcard":
            return lambda c: True
        return None

    def match_inner(self, input_line: str, pattern: str, group_counter: int):
        """
        The core matching function, re-implemented as a generator. It yields all
        possible successful matches for a given state.

        Yields:
            tuple: A tuple of (match_length, final_group_counter) for each successful match path.
        """
        # Base case: An empty pattern successfully matches 0 characters.
        if not pattern:
            yield 0, group_counter
            return

        # Parse the next expression and identify any following quantifier.
        expr_type, expr_content, expr_len, negated = self.parse_expression(pattern)
        quantifier = None
        if expr_len < len(pattern) and pattern[expr_len] in "+?*":
            quantifier = pattern[expr_len]
        rest_of_pattern = pattern[expr_len + (1 if quantifier else 0):]

        # --- Handle a GROUP expression ---
        if expr_type == "group":
            this_group_num = group_counter + 1
            alternatives = expr_content

            # A helper generator that matches the group content once.
            # It yields (match_length, updated_group_counter) for each successful alternative.
            def match_group_content_once(inp, grp_counter):
                for alt in alternatives:
                    # Each alternative is a new path, so save/restore captures around it.
                    captures_before_alt = list(self.captures)
                    for alt_len, alt_counter in self.match_inner(inp, alt, grp_counter):
                        self.captures[this_group_num - 1] = inp[:alt_len]
                        yield alt_len, alt_counter
                    self.captures = captures_before_alt

            # Case 1: No quantifier.
            if quantifier is None:
                for match_len, next_counter in match_group_content_once(input_line, this_group_num):
                    for rest_len, rest_counter in self.match_inner(input_line[match_len:], rest_of_pattern, next_counter):
                        yield match_len + rest_len, rest_counter
                return

            # Case 2: '?' quantifier (zero or one).
            if quantifier == "?":
                # Path 1 (Greedy): Try matching once.
                for match_len, next_counter in match_group_content_once(input_line, this_group_num):
                    for rest_len, rest_counter in self.match_inner(input_line[match_len:], rest_of_pattern, next_counter):
                        yield match_len + rest_len, rest_counter
                
                # Path 2: Match zero times.
                for rest_len, rest_counter in self.match_inner(input_line, rest_of_pattern, group_counter):
                    yield rest_len, rest_counter
                return
            
            # Case 3: '+' quantifier (one or more).
            if quantifier == "+":
                # A recursive helper for matching the group one-or-more times.
                # Yields (total_match_length, final_group_counter).
                def match_plus_group(inp, grp_counter):
                    # Greedily match the group content once.
                    for one_len, one_counter in match_group_content_once(inp, grp_counter):
                        # After matching once, we can either stop or continue.
                        # Path 1 (Greedy): Recurse to match more.
                        captures_after_one = list(self.captures)
                        # When recursing, the group counter must start from the same point, as the group
                        # numbers are static in the pattern. Passing the returned `one_counter` would
                        # incorrectly increment the group numbers for each repetition.
                        for rest_plus_len, rest_plus_counter in match_plus_group(inp[one_len:], grp_counter):
                             yield one_len + rest_plus_len, rest_plus_counter
                        self.captures = captures_after_one # Restore for path 2

                        # Path 2: Stop here. This is a valid end for the '+' repetition.
                        yield one_len, one_counter

                # Use the helper to find all possible repetition lengths, then match the rest of the pattern.
                for reps_len, reps_counter in match_plus_group(input_line, this_group_num):
                    for rest_len, rest_counter in self.match_inner(input_line[reps_len:], rest_of_pattern, reps_counter):
                        yield reps_len + rest_len, rest_counter
                return

            return # Should be unreachable

        # --- Handle a BACKREFERENCE expression ---
        if expr_type == "backreference":
            ref_num = expr_content
            if len(self.captures) < ref_num or self.captures[ref_num - 1] is None:
                return # If capture doesn't exist, this path fails.
            captured_text = self.captures[ref_num - 1]
            if input_line.startswith(captured_text):
                cap_len = len(captured_text)
                # Explore matches for the rest of the pattern.
                for rest_len, rest_counter in self.match_inner(input_line[cap_len:], rest_of_pattern, group_counter):
                    yield cap_len + rest_len, rest_counter
            return

        # --- Handle an ATOM expression (literal, class, escape, wildcard) ---
        match_fn = self.get_match_fn(expr_type, expr_content, negated)

        # Case 1: No quantifier.
        if quantifier is None:
            if input_line and match_fn(input_line[0]):
                for rest_len, rest_counter in self.match_inner(input_line[1:], rest_of_pattern, group_counter):
                    yield 1 + rest_len, rest_counter
            return

        # Case 2: '+' quantifier (one or more).
        if quantifier == "+":
            if not input_line or not match_fn(input_line[0]):
                return
            # Greedily find the longest possible sequence of matches.
            reps = 1
            while reps < len(input_line) and match_fn(input_line[reps]):
                reps += 1
            # Backtrack from longest to shortest.
            for curr_reps in range(reps, 0, -1):
                for rest_len, rest_counter in self.match_inner(input_line[curr_reps:], rest_of_pattern, group_counter):
                    yield curr_reps + rest_len, rest_counter
            return

        # Case 3: '?' quantifier (zero or one).
        if quantifier == "?":
            # Path 1: Match the atom once.
            if input_line and match_fn(input_line[0]):
                for rest_len, rest_counter in self.match_inner(input_line[1:], rest_of_pattern, group_counter):
                    yield 1 + rest_len, rest_counter
            # Path 2: Match the atom zero times.
            for rest_len, rest_counter in self.match_inner(input_line, rest_of_pattern, group_counter):
                yield rest_len, rest_counter
            return

        # Case 4: '*' quantifier (zero or more).
        if quantifier == "*":
            # Greedily find the longest possible sequence of matches.
            reps = 0
            while reps < len(input_line) and match_fn(input_line[reps]):
                reps += 1
            # Backtrack from longest to shortest (including zero).
            for curr_reps in range(reps, -1, -1):
                for rest_len, rest_counter in self.match_inner(input_line[curr_reps:], rest_of_pattern, group_counter):
                    yield curr_reps + rest_len, rest_counter
            return

    # ---------- Top-Level Matching Logic ----------
    def strip_anchors(self, pattern: str) -> tuple:
        """Checks for '^' and '$' anchors, removes them, and returns boolean flags."""
        start_anchored = pattern.startswith("^")
        end_anchored = pattern.endswith("$")
        inner = pattern[int(start_anchored):-int(end_anchored) or None]
        return start_anchored, end_anchored, inner

    def has_match(self, input_line: str, pattern: str) -> bool:
        """
        Drives the matching process, handling anchors and consuming the match generator.
        """
        start_anchored, end_anchored, inner = self.strip_anchors(pattern)
        # Initialize the captures list with empty slots for each group.
        self.captures = [None] * self.num_capture_groups

        # If anchored to the start, only try matching from the beginning of the input.
        if start_anchored:
            gen = self.match_inner(input_line, inner, 0)
            if end_anchored:
                # Must consume the entire string.
                return any(poss[0] == len(input_line) for poss in gen)
            else:
                # Any match from the start is sufficient.
                try:
                    next(gen)
                    return True
                except StopIteration:
                    return False
        # If not anchored, try matching from every possible start position.
        else:
            for i in range(len(input_line) + 1):
                gen = self.match_inner(input_line[i:], inner, 0)
                if end_anchored:
                    # The match must go exactly to the end of the original string.
                    if any(i + poss[0] == len(input_line) for poss in gen):
                        return True
                else:
                    # The first successful match from any position is enough.
                    try:
                        next(gen)
                        return True
                    except StopIteration:
                        pass # Continue to the next start position.
            return False

    def match_pattern(self, input_line: str) -> bool:
        """Public entry point for the regex engine."""
        return self.has_match(input_line, self.pattern)


class Main:
    """
    Handles the command-line interface, parsing arguments, reading input,
    and printing the result of the regex match.
    """
    def __init__(self):
        """Initializes the main application controller."""
        self.pattern = None
        self.input_line = None
        self.fileNames = None

    def parse_arguments(self) -> tuple:
        """Parses the regex pattern from the command-line arguments."""
        recursive = False
        if len(sys.argv) >= 5 and sys.argv[1] == '-r' and sys.argv[2] == '-E':
            recursive = True
            pattern = sys.argv[3]
            target = sys.argv[4]
            return pattern, target, recursive
        elif len(sys.argv) < 3 or sys.argv[1] != "-E":
            print("Expected usage: ./your_program.sh [-r] -E <pattern> [<file1> <file2> ...]")
            sys.exit(1)
        else:
            pattern = sys.argv[2]
            filenames = sys.argv[3:] if len(sys.argv) > 3 else None
            return pattern, filenames, recursive

    def recursive_find_files(self, dir_path: str, relative_base: str, files_list: list[str]) -> None:
        """Manually recurse through directories to find all file paths (relative to base)."""
        try:
            for entry in os.listdir(dir_path):
                full_path = os.path.join(dir_path, entry)
                if os.path.isfile(full_path):
                    rel_path = os.path.relpath(full_path, relative_base)
                    files_list.append(rel_path)
                elif os.path.isdir(full_path):
                    self.recursive_find_files(full_path, relative_base, files_list)
        except PermissionError:
            # Ignore permission errors (e.g., can't read some dirs), as per common grep behavior
            pass

    def read_input(self) -> str:
        """Reads the input string from standard input."""
        input_line = sys.stdin.read()
        if input_line.endswith("\n"):
            input_line = input_line[:-1]
        return input_line

    def __str__(self) -> str:
        """Provides a string representation for debug printing."""
        return f"Pattern: {self.pattern}\nInput: '{self.input_line}'"

    def output_result(self, matched: bool):
        """Prints the final result and exits with the appropriate status code."""
        if matched:
            sys.stdout.write("\nPattern matched :)\n")
            return_code = 0
        else:
            sys.stdout.write("\nPattern does not match :(\n")
            return_code = 1
        print(f"\n[DEBUG] Exiting with code {return_code}")
        sys.exit(return_code)

    def run(self):
        """The main execution flow of the program."""
        result = self.parse_arguments()
        self.pattern = result[0]
        engine = RegexEngine(self.pattern)

        if len(result) == 3 and result[2]:  # Recursive mode
            target_dir = result[1]
            if not os.path.isdir(target_dir):
                print(f"Error: {target_dir} is not a directory")
                sys.exit(1)
            # Set relative base to the parent of target_dir to include the directory name in paths
            abs_target = os.path.abspath(target_dir)
            relative_base = os.path.dirname(abs_target) or '.'
            file_paths = []
            self.recursive_find_files(abs_target, relative_base, file_paths)
            # Process each found file
            any_matched = False
            for rel_path in file_paths:
                full_path = os.path.join(relative_base, rel_path)
                try:
                    with open(full_path, 'r') as file:
                        for original_line in file:
                            stripped_line = original_line.rstrip('\n')
                            if engine.match_pattern(stripped_line):
                                sys.stdout.write(f"{rel_path}:{stripped_line}\n")
                                any_matched = True
                except (IOError, PermissionError):
                    # Skip unreadable files, as per common behavior
                    continue
            sys.exit(0 if any_matched else 1)
        elif isinstance(result[1], list) and result[1] is not None:
            # Multi-file mode (non-recursive)
            self.fileNames = result[1]
            # File mode: process each file line by line (multi-file multi-line support)
            any_matched = False
            for fileName in self.fileNames:
                with open(fileName, 'r') as file:
                    for original_line in file:
                        stripped_line = original_line.rstrip('\n')
                        if engine.match_pattern(stripped_line):
                            # For single file only
                            if(len(self.fileNames) == 1):
                                sys.stdout.write(original_line)
                            # For multiple files
                            else:
                                sys.stdout.write(f"{fileName}:{original_line}")
                            any_matched = True
            sys.exit(0 if any_matched else 1)
        else:
            # Stdin mode: keep as single-line (legacy)
            self.input_line = self.read_input()
            print(self)  # Print debug info.
            matched = engine.match_pattern(self.input_line)
            self.output_result(matched)

if __name__ == "__main__":
    Main().run()