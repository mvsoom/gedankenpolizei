
"""
Replay a .jsonl file containing narrations from `seer.narrate.stream`
"""

import argparse
import json
from time import sleep, time


def main(args):
    with open(args.file, "r") as file:
        data = [json.loads(line) for line in file]

    for n in range(len(data)):
        if args.jsonl:
            # Update the timestamp to match the current time
            new_data = data[n].copy()
            new_data["t"] = time()

            print(json.dumps(new_data), flush=True)
        else:
            print(data[n]["text"], flush=True)

        if n < len(data) - 1:
            dt = data[n + 1]["t"] - data[n]["t"]
            sleep(dt * args.scale)

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", help="Path to the .jsonl file")
    parser.add_argument(
        "--jsonl",
        action="store_true",
        help="Echo the narrations in JSONL format (default: %(default)s)",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="Speed up or slow down the replay by this factor",
    )

    args = parser.parse_args()

    exit(main(args))
