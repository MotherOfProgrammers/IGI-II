# Created By MotherOfProgrammers(MOP)

"""
GameSpy "enctype 2" server-list encoder (and a matching decoder for tests).

Port of the encoder in Luigi Auriemma's enctype2 reference (GPL), taken from the C
reference preserved in the comments of the Nightfire master server's enctype2.vb and its VB port

Layout produced by encode() is like below:

    byte 0        : 8 ^ 0xEC
    bytes 1..8    : header = 8 zero bytes with the secret key XORed in (seed for the cipher)
    bytes 9..     : payload + 6 zero bytes, XORed with the keystream

The client recovers the seed by XORing the header with its own copy of the secret key,
so the key must be the game's real key (IGI 2: see master_server.py)

If you distribute this file, note it derives from GPL code
"""

_M = 0xFFFFFFFF


def _ror8(x):
    return ((x << 24) | (x >> 8)) & _M


def _rol8(x):
    return ((x >> 24) | (x << 8)) & _M


def _encshare3(d, n1, n2):
    t2 = n1 & _M
    t1 = 0
    t4 = 1
    d[304] = 0
    i = 32768
    while i:
        t2 = (t2 + t4) & _M
        t1 = (t1 + t2) & _M
        t2 = (t2 + t1) & _M
        if n2 & i:
            t2 = (~t2) & _M
            t4 = ((t4 << 1) + 1) & _M
            t3 = _ror8(t2)
            t3 ^= d[t3 & 255]
            t1 ^= d[t1 & 255]
            t2 = _ror8(t3)
            t3 = _rol8(t1)
            t2 ^= d[t2 & 255]
            t3 ^= d[t3 & 255]
            t1 = _rol8(t3)
        else:
            c = d[304]
            d[c + 256] = t2
            d[c + 272] = t1
            d[c + 288] = t4
            d[304] = c + 1
            t3 = _ror8(t1)
            t2 ^= d[t2 & 255]
            t3 ^= d[t3 & 255]
            t1 = _ror8(t3)
            t3 = _rol8(t2)
            t3 ^= d[t3 & 255]
            t1 ^= d[t1 & 255]
            t2 = _rol8(t3)
            t4 = (t4 << 1) & _M
        i >>= 1
    d[305] = t2
    d[306] = t1
    d[307] = t4
    d[308] = n1


def _encshare4(src, size):
    d = [0] * 326
    for y in range(4):
        for i in range(256):
            d[i] = ((d[i] << 8) + i) & _M
        pos = y
        for _x in range(2):
            for i in range(256):
                tmp = d[i]
                pos = (pos + tmp + src[i % size]) & 255
                d[i] = d[pos]
                d[pos] = tmp
    for i in range(256):
        d[i] ^= i
    _encshare3(d, 0, 0)
    return d


def _encshare2(tb, length, base):
    t2 = tb[304]
    t1 = tb[305]
    t3 = tb[306]
    t5 = tb[307]
    for i in range(length):
        p = t2 + 272
        while t5 < 65536:
            t1 = (t1 + t5) & _M
            p += 1
            t3 = (t3 + t1) & _M
            t1 = (t1 + t3) & _M
            tb[p - 17] = t1
            tb[p - 1] = t3
            t4 = _ror8(t3)
            tb[p + 15] = t5
            t5 = (t5 << 1) & _M
            t2 = (t2 + 1) & _M
            t1 ^= tb[t1 & 255]
            t4 ^= tb[t4 & 255]
            t3 = _ror8(t4)
            t4 = _rol8(t1)
            t4 ^= tb[t4 & 255]
            t3 ^= tb[t3 & 255]
            t1 = _rol8(t4)
        t3 ^= t1
        tb[base + i] = t3
        t2 = (t2 - 1) & _M
        t1 = tb[t2 + 256]
        t5 = tb[t2 + 272]
        t1 = (~t1) & _M
        t3 = _ror8(t1)
        t3 ^= tb[t3 & 255]
        t5 ^= tb[t5 & 255]
        t1 = _ror8(t3)
        t4 = _rol8(t5)
        t1 ^= tb[t1 & 255]
        t4 ^= tb[t4 & 255]
        t3 = _rol8(t4)
        t5 = ((tb[t2 + 288] << 1) + 1) & _M
    tb[304] = t2
    tb[305] = t1
    tb[306] = t3
    tb[307] = t5


def _encshare1(tb, data, length):
    idx = 0
    lal = 309
    bp = 4
    word = b"\x00\x00\x00\x00"
    while length > 0:
        if idx % 63 == 0:
            lal = 309
            bp = 4
            _encshare2(tb, 16, 309)
        if bp > 3:
            word = tb[lal].to_bytes(4, "little")
            bp = 0
            lal += 1
        data[idx] ^= word[bp]
        idx += 1
        bp += 1
        length -= 1


"""
Encrypt `payload` (bytes) for a client that holds secret key `key` (str)
"""
def encode(payload, key):
    size = len(payload)
    data = bytearray(payload) + bytearray(6)
    header = bytearray(8)
    d = _encshare4(header, 8)
    _encshare1(d, data, size + 6)
    out = bytearray(1 + 8 + len(data))
    out[0] = 8
    out[1:9] = header
    out[9:] = data
    for i, c in enumerate(key.encode("latin-1")):
        out[1 + i] ^= c
    out[0] ^= 0xEC
    return bytes(out)


"""
Inverse of encode() 
returns payload + the 6 trailing zero bytes. For tests.
"""
def decode(blob, key):
    b = bytearray(blob)
    hdr_len = (b[0] ^ 0xEC)
    header = bytearray(b[1:1 + hdr_len])
    for i, c in enumerate(key.encode("latin-1")):
        header[i] ^= c
    d = _encshare4(header, hdr_len)
    data = bytearray(b[1 + hdr_len:])
    _encshare1(d, data, len(data))
    return bytes(data)