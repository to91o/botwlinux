#!/usr/bin/env python3
"""Report Linux sampler instruction-pointer counts by ELF function (self samples, not wall time)."""
import argparse
import bisect
import collections
import pathlib
import subprocess


def symbols(path):
    for flags in ([], ["-D"]):
        out = subprocess.run(["nm", "-S", "--defined-only", *flags, path], capture_output=True, text=True)
        rows = []
        for line in out.stdout.splitlines():
            p = line.split(maxsplit=3)
            if len(p) == 4 and p[2] in "TtWwIi":
                try:
                    rows.append((int(p[0], 16), int(p[1], 16), p[3]))
                except ValueError:
                    continue
        if rows:
            return sorted(rows)
    return []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("samples", type=pathlib.Path)
    parser.add_argument("--top", type=int, default=25)
    parser.add_argument("--thread", type=int)
    args = parser.parse_args()
    modules, samples, exe = [], [], None
    for line in args.samples.read_text().splitlines():
        p = line.split(maxsplit=3)
        if p and p[0] == "E":
            exe = line[2:]
        elif len(p) == 4 and p[0] == "M":
            path = exe if p[3] == "/proc/self/exe" else p[3]
            rows = symbols(path) if path and pathlib.Path(path).is_file() else []
            modules.append((int(p[1], 16), int(p[2], 16), path, rows, [r[0] for r in rows]))
        elif len(p) == 4 and p[0] == "S" and (args.thread is None or int(p[1]) == args.thread):
            samples.append(int(p[2], 16))
    counts = collections.Counter()
    for pc in samples:
        label = f"unknown@{pc:x}"
        for base, size, path, rows, starts in modules:
            if base <= pc < base + size:
                offset = pc - base
                i = bisect.bisect_right(starts, offset) - 1
                name = rows[i][2] if i >= 0 and offset < rows[i][0] + rows[i][1] else f"+0x{offset:x}"
                label = f"{pathlib.Path(path).name}:{name}"
                break
        counts[label] += 1
    print(f"{len(samples)} CPU samples; percentages include library waits. Sampling overhead is not subtracted.")
    for name, count in counts.most_common(max(1, args.top)):
        print(f"{100 * count / max(1, len(samples)):6.2f}% {count:7d} {name}")


if __name__ == "__main__":
    main()
