# Created By MotherOfProgrammers(MOP)

# Send the GameSpy-v1 query commands the IGI 2 browser uses to a game server and print exactly what comes back

import argparse
import datetime
import os
import socket

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)),"probe.log")


def out(msg):
    line = "[%s] %s" % (datetime.datetime.now().strftime("%H:%M:%S"), msg)
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("host")
    ap.add_argument("port", type=int)
    ap.add_argument("--wait", type=float, default=2.0, help="seconds to wait per reply")
    ap.add_argument("--cmds", default="status,info,basic,rules,players")
    args = ap.parse_args()

    for cmd in args.cmds.split(","):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(args.wait)
        msg = ("\\%s\\" % cmd).encode()
        s.sendto(msg, (args.host, args.port))
        out("sent %r to %s:%d" % (msg, args.host, args.port))
        got = 0
        try:
            while True:
                data, addr = s.recvfrom(8192)
                got += 1
                text = "".join(chr(b) if 32 <= b < 127 else "." for b in data)
                out("  reply %d from %s:%d (%d bytes): %s" % (got, addr[0], addr[1], len(data), text))
                if any(not (32 <= b < 127) for b in data):
                    out("    hex: %s" % data[:128].hex(" "))
        except socket.timeout:
            pass
        if not got:
            out("  no reply")
        s.close()


if __name__ == "__main__":
    main()
