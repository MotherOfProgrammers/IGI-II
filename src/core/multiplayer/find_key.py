# Created By MotherOfProgrammers(MOP)

"""
find the GameSpy secret key inside igi2.exe by brute force
Every printable string in the exe is tried as the key against the (challenge, validate) pair captured from your own game
"""

import argparse
import re

from gsmsalg import gsseckey


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exe")
    ap.add_argument("--challenge", default="ABCDEF")
    ap.add_argument("--validate", default="vBZ2xPuX")
    ap.add_argument("--minlen", type=int, default=3)
    ap.add_argument("--maxlen", type=int, default=24)
    args = ap.parse_args()

    data = open(args.exe, "rb").read()
    pat = re.compile(rb"[\x21-\x7e]{%d,%d}" % (args.minlen, args.maxlen))
    cands = sorted({m.group().decode("ascii") for m in pat.finditer(data)})
    print("trying %d candidate strings x enctype 0,2 ..." % len(cands))

    hits = 0
    for c in cands:
        for et in (0, 2):
            if gsseckey(args.challenge, c, et) == args.validate:
                print("FOUND  key=%r  enctype=%d" % (c, et))
                hits += 1
    if not hits:
        print("no match")


if __name__ == "__main__":
    main()
