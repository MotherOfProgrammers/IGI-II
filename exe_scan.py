# Created By MotherOfProgrammers(MOP)
import hashlib
import re
import sys
import pefile
import sys

def main(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
    except Exception as e:
        print(f"An unknown error occured due to => {e}")
        sys.exit(-1)

    print("File:", path)
    print("Size:", len(data), "bytes")
    print("SHA-256:", hashlib.sha256(data).hexdigest())

    pe = pefile.PE(data=data)
    print("\nMachine:", hex(pe.FILE_HEADER.Machine), "(0x14c = 32-bit)")
    print("ImageBase:", hex(pe.OPTIONAL_HEADER.ImageBase))

    print("\n=== IMPORTED DLLs ===")
    for entry in pe.DIRECTORY_ENTRY_IMPORT:
        print(entry.dll.decode(errors="replace"))

    print("\n=== NETWORK-RELATED IMPORTS ===")
    net_dlls = ("ws2_32", "wsock32", "wininet", "winhttp", "dnsapi", "iphlpapi")
    for entry in pe.DIRECTORY_ENTRY_IMPORT:
        name = entry.dll.decode(errors="replace").lower()
        if any(n in name for n in net_dlls):
            print("\n" + entry.dll.decode(errors="replace"))
            for imp in entry.imports:
                if imp.name:
                    print("  ", imp.name.decode(errors="replace"))
                else:
                    print("   ordinal", imp.ordinal)

    print("\n=== INTERESTING STRINGS ===")
    keywords = re.compile(
        rb"gamespy|master|natneg|available|gamename|heartbeat|secure|validate"
        rb"|\\\\basic\\\\|\\\\info\\\\|\\\\rules\\\\|\\\\players\\\\|qtracker|openspy",
        re.IGNORECASE,
    )
    seen = set()
    for m in re.finditer(rb"[\x20-\x7e]{6,}", data):
        s = m.group()
        if keywords.search(s) and s not in seen:
            seen.add(s)
            print(hex(m.start()), s.decode("ascii", errors="replace"))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
        main(path)
    else:
        print("Invalid command!")
        sys.exit(-1)
