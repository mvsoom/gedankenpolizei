
"""
Replay a .jsonl file containing narrations from `seer.narrate.stream`
"""

import argparse
import json
import time


def main(args):
    with open(args.file, "r") as file:
        data = [json.loads(line) for line in file]

    for n in range(len(data)):
        print(data[n]["text"], flush=True)

        if n < len(data) - 1:
            dt = data[n + 1]["t"] - data[n]["t"]
            time.sleep(dt * args.scale)

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", help="Path to the .jsonl file")
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="Speed up or slow down the replay by this factor",
    )

    args = parser.parse_args()

    exit(main(args))
