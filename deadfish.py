#!/usr/bin/env python3
"""
Deadfish translator: text <-> Deadfish code.

Deadfish has one number (the accumulator, starting at 0) and four commands:
    i  increment (+1)
    d  decrement (-1)
    s  square
    o  output the number
Quirk: if the accumulator ever becomes exactly 256 or -1, it resets to 0.

Text is encoded by outputting each character's code (A = 65, a = 97, ...).

Usage:
    python deadfish.py encode "Hello"
    python deadfish.py decode "iisiiiisiiiiiiiio"
    python deadfish.py decode --numbers "iiisso"
    python deadfish.py              (interactive menu)
"""

import argparse
import sys
from collections import deque
from functools import lru_cache


def step(value, command):
    """Apply one Deadfish command to the accumulator and return the new value."""
    if command == "i":
        value += 1
    elif command == "d":
        value -= 1
    elif command == "s":
        value *= value
    if value == 256 or value == -1:
        value = 0
    return value


@lru_cache(maxsize=None)
def shortest_path(start, target):
    """Shortest string of i/d/s commands that takes the accumulator from start to target."""
    if start == target:
        return ""

    # Allow overshooting (e.g. square to 100, then step down to 99).
    limit = max(start, target) * 2 + 300
    parent = {start: None}
    queue = deque([start])

    while queue:
        value = queue.popleft()
        for command in "ids":
            new_value = step(value, command)
            if new_value > limit or new_value in parent:
                continue
            parent[new_value] = (value, command)
            if new_value == target:
                commands = []
                node = new_value
                while parent[node] is not None:
                    node, cmd = parent[node]
                    commands.append(cmd)
                return "".join(reversed(commands))
            queue.append(new_value)

    raise ValueError(f"Cannot reach {target} from {start}")


def encode(text):
    """Translate text into Deadfish code."""
    code = []
    value = 0
    for char in text:
        target = ord(char)
        if target == 256:
            # Deadfish resets the accumulator at 256, so it can never be output.
            raise ValueError(f"{char!r} (code 256) cannot be written in Deadfish")
        code.append(shortest_path(value, target) + "o")
        value = target
    return "".join(code)


def run(code):
    """Run Deadfish code and return the list of numbers it outputs."""
    value = 0
    outputs = []
    for command in code:
        if command == "o":
            outputs.append(value)
        elif command in "ids":
            value = step(value, command)
        # anything else (spaces, newlines, typos) is ignored
    return outputs


def decode(code):
    """Translate Deadfish code back into text."""
    chars = []
    for number in run(code):
        try:
            chars.append(chr(number))
        except (ValueError, OverflowError):
            chars.append("?")
    return "".join(chars)


def interactive():
    print("Deadfish translator")
    print("  1) Text -> Deadfish")
    print("  2) Deadfish -> Text")
    print("  q) Quit")
    while True:
        choice = input("\nChoose 1, 2 or q: ").strip().lower()
        if choice == "1":
            try:
                print(encode(input("Text: ")))
            except ValueError as error:
                print("Error:", error)
        elif choice == "2":
            code = input("Deadfish: ")
            print("Text:   ", decode(code))
            print("Numbers:", " ".join(map(str, run(code))))
        elif choice in ("q", "quit", "exit"):
            break
        else:
            print("Please type 1, 2 or q.")


def main():
    if len(sys.argv) == 1:
        interactive()
        return

    parser = argparse.ArgumentParser(description="Translate text to and from Deadfish.")
    sub = parser.add_subparsers(dest="mode", required=True)

    enc = sub.add_parser("encode", help="text -> Deadfish")
    enc.add_argument("text", nargs="?", help="text to encode (reads stdin if omitted)")

    dec = sub.add_parser("decode", help="Deadfish -> text")
    dec.add_argument("code", nargs="?", help="Deadfish code (reads stdin if omitted)")
    dec.add_argument("--numbers", action="store_true",
                     help="print the raw numbers instead of characters")

    args = parser.parse_args()

    if args.mode == "encode":
        text = args.text if args.text is not None else sys.stdin.read().rstrip("\n")
        try:
            print(encode(text))
        except ValueError as error:
            sys.exit(f"Error: {error}")
    else:
        code = args.code if args.code is not None else sys.stdin.read()
        if args.numbers:
            print(" ".join(map(str, run(code))))
        else:
            print(decode(code))


if __name__ == "__main__":
    main()