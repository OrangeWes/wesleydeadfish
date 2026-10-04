#!/usr/bin/env python3
"""
Deadfish variation breaker.

Standard Deadfish uses four command letters:
    i = +1      d = -1      s = square      o = output
(and the number resets to 0 whenever it becomes exactly 256 or -1).

If someone has scrambled which letter does which job, this script tries all
24 possible assignments, decodes the code with each one, and prints every
result next to the scrambling that produced it, most readable first.

Usage:
    python deadfish_variants.py "iiisdsiiiiiiiio"      code typed directly
    python deadfish_variants.py manuscript.txt         code read from a file
    python deadfish_variants.py < manuscript.txt       code read from stdin
    python deadfish_variants.py                        asks you to paste it

Options:
    --numbers        also print the raw numbers for each variation
    --no-reset       turn off the "256 or -1 becomes 0" rule
    --letters xkcd   use these four command letters instead of auto-detecting
    --count-after    read shorthand as d7 (letter then count) instead of 7d
    --no-expand      do not expand shorthand like 7d into ddddddd
    --top N          only show the N most readable variations
"""

import argparse
import os
import re
import sys
from itertools import permutations

OPERATIONS = ("+1", "-1", "square", "output")
STANDARD_LETTERS = "idso"
TOO_BIG = 10 ** 30          # a wrong guess can square forever; stop it here
MAX_REPEAT = 1_000_000      # safety limit for shorthand like 999999999d


def expand_shorthand(code, count_after=False):
    """Turn run-length shorthand into plain commands: 7d5s -> dddddddsssss."""
    def repeat(letter, count):
        return letter * min(int(count), MAX_REPEAT)

    if count_after:
        return re.sub(r"([a-z])\s*(\d+)", lambda m: repeat(m.group(1), m.group(2)), code)
    return re.sub(r"(\d+)\s*([a-z])", lambda m: repeat(m.group(2), m.group(1)), code)


def find_letters(code):
    """Work out which four letters the code uses as commands."""
    used = sorted(set(c for c in code if c.isalpha()))
    if set(used) <= set(STANDARD_LETTERS):
        return STANDARD_LETTERS
    if len(used) == 4:
        return "".join(used)
    raise ValueError(
        f"The code uses {len(used)} different letters ({' '.join(used)}), so I can't tell "
        "which four are commands. Pass them yourself, e.g. --letters xkcd"
    )


def run(code, mapping, reset=True):
    """
    Run code where mapping says what each letter does, e.g. {'i': '+1', ...}.
    Returns (list of output numbers, overflowed).
    """
    value = 0
    outputs = []
    for char in code:
        operation = mapping.get(char)
        if operation is None:
            continue                      # spaces, newlines, punctuation
        if operation == "output":
            outputs.append(value)
            continue
        if operation == "+1":
            value += 1
        elif operation == "-1":
            value -= 1
        elif operation == "square":
            value *= value
        if reset and (value == 256 or value == -1):
            value = 0
        if abs(value) > TOO_BIG:
            return outputs, True
    return outputs, False


def to_text(numbers):
    """Turn output numbers into characters, marking anything unprintable with '?'."""
    chars = []
    for number in numbers:
        if number in (9, 10):
            chars.append(chr(number))
        elif 0 <= number <= 0x10FFFF and chr(number).isprintable():
            chars.append(chr(number))
        else:
            chars.append("?")
    return "".join(chars)


def readability(numbers):
    """Score from 0 to 1: how much of the output looks like ordinary text."""
    if not numbers:
        return 0.0
    score = 0.0
    for number in numbers:
        if number == 10 or 32 <= number <= 126:
            score += 0.6
            if chr(number).isalpha() or number == 32:
                score += 0.4
    score /= len(numbers)
    # Real text rarely repeats the same character back to back; junk such as
    # "xxxxxxxx" does, so mark it down.
    if len(numbers) > 1:
        repeats = sum(1 for a, b in zip(numbers, numbers[1:]) if a == b)
        score *= 1 - repeats / (len(numbers) - 1)
    return score


def all_variations(code, letters, reset=True):
    """Try every assignment of the four letters to the four operations."""
    results = []
    for order in permutations(OPERATIONS):
        mapping = dict(zip(letters, order))
        numbers, overflowed = run(code, mapping, reset)
        results.append({
            "mapping": mapping,
            "numbers": numbers,
            "text": to_text(numbers),
            "overflowed": overflowed,
            "score": readability(numbers),
        })
    # Most readable first; ties keep their original order.
    results.sort(key=lambda r: -r["score"])
    return results


def describe(mapping, letters):
    return "   ".join(f"{letter} = {mapping[letter]}" for letter in letters)


def read_input(argument):
    if argument is None:
        if sys.stdin.isatty():
            return input("Paste the Deadfish code: ")
        return sys.stdin.read()
    if os.path.isfile(argument):
        with open(argument, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    return argument


def main():
    parser = argparse.ArgumentParser(
        description="Decode Deadfish under every possible letter scrambling.")
    parser.add_argument("code", nargs="?", help="Deadfish code, or the name of a file containing it")
    parser.add_argument("--numbers", action="store_true", help="also print the raw numbers")
    parser.add_argument("--no-reset", action="store_true", help="turn off the 256 / -1 reset rule")
    parser.add_argument("--letters", help="the four command letters, e.g. xkcd")
    parser.add_argument("--count-after", action="store_true", help="shorthand is d7, not 7d")
    parser.add_argument("--no-expand", action="store_true", help="do not expand shorthand like 7d")
    parser.add_argument("--top", type=int, help="only show the N most readable variations")
    args = parser.parse_args()

    code = read_input(args.code).lower()
    if not args.no_expand and re.search(r"\d", code):
        code = expand_shorthand(code, args.count_after)

    try:
        if args.letters:
            letters = args.letters.lower()
            if len(letters) != 4 or len(set(letters)) != 4:
                raise ValueError("--letters needs exactly four different letters, e.g. xkcd")
        else:
            letters = find_letters(code)
    except ValueError as error:
        sys.exit(f"Error: {error}")

    results = all_variations(code, letters, reset=not args.no_reset)
    if args.top:
        results = results[:args.top]

    print(f"Command letters: {' '.join(letters)}")
    print(f"Showing {len(results)} of 24 variations, most readable first.")
    print("A '?' in the text is a number that is not a printable character.\n")

    for rank, result in enumerate(results, start=1):
        standard = [result["mapping"][l] for l in letters] == list(OPERATIONS) and letters == STANDARD_LETTERS
        label = "   (standard Deadfish)" if standard else ""
        print(f"#{rank:<2} {describe(result['mapping'], letters)}{label}")
        print(f"    readable: {result['score']:.0%}")
        if result["numbers"]:
            for line in result["text"].split("\n"):
                print(f"    text:    {line}")
            if args.numbers:
                print("    numbers: " + " ".join(str(n) for n in result["numbers"]))
        else:
            print("    text:    (nothing was output)")
        if result["overflowed"]:
            print("    note:    stopped early, the number grew far too large")
        print()


if __name__ == "__main__":
    main()