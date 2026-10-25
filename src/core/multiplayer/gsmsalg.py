# Created By MotherOfProgrammers(MOP)

"""
GameSpy "secure/validate" response (gsseckey)
Written from knowledge of Luigi Auriemma's gsmsalg reference

enctype 0 : plain
enctype 2 : XOR with the key before encoding
enctype 1 : needs a 256-byte table that is not included here (unsupported)
"""


def _val(r):
    # A-Z
    if r < 26:
        return chr(r + 65)
    # a-z
    if r < 52:
        return chr(r + 71)
    # 0-9
    if r < 62:
        return chr(r - 4)
    return "+" if r == 62 else "/"


def gsseckey(challenge, key, enctype=0):
    s = challenge.encode("latin-1")
    k = key.encode("latin-1")
    if not (1 <= len(s) <= 65) or not k:
        return ""
    if enctype == 1:
        raise NotImplementedError("enctype 1 table not included")

    t = list(range(256))
    a = 0
    for i in range(256):
        a = (a + t[i] + k[i % len(k)]) & 0xFF
        t[a], t[i] = t[i], t[a]

    a = b = 0
    tmp = []
    for c in s:
        a = (a + c + 1) & 0xFF
        x = t[a]
        b = (b + x) & 0xFF
        y = t[b]
        t[b] = x
        t[a] = y
        tmp.append(c ^ t[(x + y) & 0xFF])

    while len(tmp) % 3:
        tmp.append(0)

    if enctype == 2:
        tmp = [v ^ k[i % len(k)] for i, v in enumerate(tmp)]

    out = []
    for i in range(0, len(tmp), 3):
        x, y, z = tmp[i], tmp[i + 1], tmp[i + 2]
        out.append(_val(x >> 2))
        out.append(_val(((x & 3) << 4) | (y >> 4)))
        out.append(_val(((y & 15) << 2) | (z >> 6)))
        out.append(_val(z & 63))
    return "".join(out)
