"""Compatibility entry point: evaluate materials through the shared runner."""

import sys

from run_examples import main

if __name__ == "__main__":
    raise SystemExit(main(["--example", "materials", *sys.argv[1:]]))
