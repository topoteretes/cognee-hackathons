#!/usr/bin/env python3
"""Driver for wipe.sh (--wipe) and wipe_check.sh (--check)."""
import os
import sys
import urllib.error

sys.path.insert(0, os.path.dirname(__file__))
import cognee_http  # noqa: E402


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("--wipe", "--check"):
        print("usage: wipe_dataset.py --wipe|--check <dataset-name>", file=sys.stderr)
        return 2
    mode, dataset = sys.argv[1], sys.argv[2]

    if mode == "--wipe":
        try:
            cognee_http.forget_dataset(dataset)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Repeat 1: nothing was ever written to this dataset yet,
                # so "not found" already means empty, not a failed wipe.
                print(f"wipe: dataset {dataset!r} did not exist yet -- already empty")
                return 0
            print(f"wipe: forget failed: {e.code} {e.read()[:500]}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"wipe: forget failed: {e}", file=sys.stderr)
            return 1
        print(f"wipe: cleared dataset {dataset!r}")
        return 0

    # --check
    try:
        datasets = cognee_http.list_datasets()
    except Exception as e:
        print(f"wipe_check: could not list datasets: {e}", file=sys.stderr)
        return 1
    names = {d.get("name") for d in datasets}
    if dataset in names:
        print(f"wipe_check: dataset {dataset!r} still present", file=sys.stderr)
        return 1
    print(f"wipe_check: dataset {dataset!r} absent, wipe confirmed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
