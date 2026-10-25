# Created By MotherOfProgrammers(MOP)

"""

A simple GameSpy-v1 style master for IGI 2 (gamename projectigi2r)

  UDP 27900 : game servers send heartbeats  \\heartbeat\\<queryport>\\gamename\\projectigi2r
              -> the server's IP is the packet's source address; it is listed for 5 minutes.
  TCP 28900 : clients connect, get  \\basic\\\\secure\\<challenge>, send validate + list request,
              and receive the server list followed by \\final\\ .

Requires the client to ask for enctype 0 (set force_enctype0=1 in igi2hook.ini)
an enctype 2 request is answered in plain text anyway and a warning is logged

    python master_server.py
    python master_server.py --static 192.168.1.20:7778 --static 1.2.3.4:7778
    python master_server.py --key SECRET  (NOTE: optionally log whether validate matches)

Everything is logged to master_server.log

"""

import argparse
import datetime
import os
import random
import re
import socket
import socketserver
import string
import threading
import time

from gsmsalg import gsseckey
import enctype2

# Secret key of the game "projectigi2r", can be derived via find_key.py
DEFAULT_KEY = "j4F9cY"

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(HERE, "master_server.log")
GAMENAME = "projectigi2r"
SERVER_TTL = 300.0

_log_lock = threading.Lock()
_servers = {}
_servers_lock = threading.Lock()


def log(msg):
    line = "[%s] %s" % (datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3], msg)
    with _log_lock:
        print(line, flush=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")


_canon = {}


def _drop_canon(key):
    for c in [c for c, k in _canon.items() if k == key]:
        del _canon[c]


def live_servers():
    now = time.time()
    with _servers_lock:
        for k in [k for k, seen in _servers.items() if seen is not None and now - seen > SERVER_TTL]:
            del _servers[k]
            _drop_canon(k)
            log("expired server %s:%d" % k)
        return sorted(_servers)


"""
Ask a game server \\status\\ (what the browser asks first)
Returns the reply text or None if nothing valid answers
"""
def probe_status(ip, port):
    u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    u.settimeout(2.0)
    try:
        u.sendto(b"\\status\\", (ip, port))
        data, _ = u.recvfrom(8192)
        return data.decode("latin-1") if data.startswith(b"\\") else None
    except OSError:
        return None
    finally:
        u.close()


_warned = {}


def verify_and_register(ip, port, verify):
    key = (ip, port)
    reply = probe_status(ip, port) if verify else ""
    if reply is None and verify:
        # a game that just started hosting may need a moment before it answers
        time.sleep(3)
        reply = probe_status(ip, port)
    with _servers_lock:
        if reply is None:
            if _servers.get(key) is not None and key in _servers:
                del _servers[key]
                _drop_canon(key)
                log("server %s:%d stopped answering, removed" % key)
            elif key not in _servers:
                now = time.time()
                if now - _warned.get(key, 0) > 300: # the game's \hb\ port spams and make the logging rarely
                    _warned[key] = now
                    log("heartbeat for %s:%d ignored: no answer to \\status\\ (firewall/NAT, or wrong port?)" % key)
            return
        canon, hp = key, None
        m = re.search(r"\\hostport\\(\d+)", reply)
        if m:
            hp = int(m.group(1))
            canon = (ip, hp)
        owner = _canon.get(canon)
        if owner is not None and owner != key and owner in _servers:
            if _servers[owner] is not None: # same server announced on another port
                _servers[owner] = time.time()
            return
        _canon[canon] = key
        new = key not in _servers
        if _servers.get(key, 0) is not None:
            _servers[key] = time.time()
    if new:
        log("registered server %s:%d (verified, hostport %s)" % (ip, port, hp))


def build_list(servers, compact):
    out = bytearray()
    for ip, port in servers:
        if compact:
            out += socket.inet_aton(ip) + port.to_bytes(2, "big")
        else:
            out += b"\\ip\\%s:%d" % (ip.encode(), port)
    out += b"\\final\\"
    return bytes(out)


def parse_kv(text):
    parts = text.split("\\")
    return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}


class TcpHandler(socketserver.BaseRequestHandler):
    def handle(self):
        peer = "%s:%d" % self.client_address
        challenge = "".join(random.choice(string.ascii_letters) for _ in range(6))
        log("TCP %s connected, challenge %s" % (peer, challenge))
        buf = b""
        enctype = None
        try:
            self.request.sendall(b"\\basic\\\\secure\\" + challenge.encode())
            self.request.settimeout(30)
            while True:
                chunk = self.request.recv(4096)
                if not chunk:
                    break
                buf += chunk
                text = buf.decode("latin-1")

                m = re.search(r"\\enctype\\(\d+)", text)
                if m and enctype is None:
                    enctype = int(m.group(1))
                    kv = parse_kv(text.split("\\final\\")[0])
                    log("TCP %s client: gamename=%s gamever=%s validate=%s enctype=%d"
                        % (peer, kv.get("gamename"), kv.get("gamever"), kv.get("validate"), enctype))
                    if self.server.key and enctype in (0, 2):
                        want = gsseckey(challenge, self.server.key, enctype)
                        log("TCP %s validate %s" % (peer, "OK" if want == kv.get("validate")
                                                      else "MISMATCH (expected %s)" % want))

                if "\\list\\" in text and "\\final\\" in text.split("\\list\\", 1)[1]:
                    compact = text.split("\\list\\", 1)[1].startswith("cmp")
                    servers = live_servers()
                    plain = build_list(servers, compact)
                    if enctype == 2:
                        reply = enctype2.encode(plain, self.server.key)
                    else:
                        if enctype not in (None, 0):
                            log("WARNING: enctype %s not supported, sending plain text" % enctype)
                        reply = plain
                    self.request.sendall(reply)
                    log("TCP %s sent %d server(s), %s, enctype %s, %d bytes (plain: %s)"
                        % (peer, len(servers), "compact" if compact else "text",
                           enctype, len(reply), plain[:120].hex(" ")))
                    buf = b""
        except socket.timeout:
            pass
        except OSError as e:
            log("TCP %s error: %s" % (peer, e))
        log("TCP %s done" % peer)


class UdpHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data, _sock = self.request
        ip, src_port = self.client_address
        text = data.decode("latin-1", errors="replace")
        log("UDP %d bytes from %s: %r" % (len(data), ip, text[:200]))
        # The game itself sends two kinds of heartbeat (seen in a capture)
        # \heartbeat\0\gamename\projectigi2r (GameSpy; 0 = use the packet's source port)
        # \hb\28973\igi2 (udpsoft style; explicit query port)
        # The hook's own heartbeat is \heartbeat\<port>\gamename\projectigi2r
        m = re.match(r"\\heartbeat\\(\d+)", text) or re.match(r"\\hb\\(\d+)", text)
        if not m:
            return
        port = int(m.group(1)) or src_port
        kv = parse_kv(text)
        name = kv.get("gamename") or text.rstrip("\\").split("\\")[-1]
        if name not in (GAMENAME, "igi2"):
            log("ignoring heartbeat for gamename %s" % name)
            return
        if not 1 <= port <= 65535:
            return
        threading.Thread(target=verify_and_register,
                         args=(ip, port, self.server.verify), daemon=True).start()


class TcpServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class UdpServer(socketserver.ThreadingUDPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tcp-port", type=int, default=28900)
    ap.add_argument("--udp-port", type=int, default=27900)
    ap.add_argument("--bind", default="0.0.0.0")
    ap.add_argument("--static", action="append", default=[],
                    help="always-listed server ip:queryport (repeatable)")
    ap.add_argument("--no-verify", action="store_true",
                    help="list heartbeating servers without probing them first")
    ap.add_argument("--key", default=DEFAULT_KEY,
                    help="game secret key: encrypts enctype-2 lists and checks validate")
    args = ap.parse_args()

    for s in args.static:
        ip, port = s.rsplit(":", 1)
        _servers[(ip, int(port))] = None
        log("static server %s:%s" % (ip, port))

    tcp = TcpServer((args.bind, args.tcp_port), TcpHandler)
    tcp.key = args.key
    udp = UdpServer((args.bind, args.udp_port), UdpHandler)
    udp.verify = not args.no_verify
    threading.Thread(target=tcp.serve_forever, daemon=True).start()
    threading.Thread(target=udp.serve_forever, daemon=True).start()
    log("master up: TCP %d, UDP %d, gamename %s  (Ctrl+C to stop)"
        % (args.tcp_port, args.udp_port, GAMENAME))
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        log("stopping")


if __name__ == "__main__":
    main()
