"""CLI entrypoint: python -m verify.explorer <path> [--json]."""

import sys

from .agent import explore


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m verify.explorer <path> [--json]", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    json_mode = "--json" in sys.argv

    result = explore(path)

    if json_mode:
        print(result.to_json())
    else:
        print(result.format_report())


if __name__ == "__main__":
    main()
