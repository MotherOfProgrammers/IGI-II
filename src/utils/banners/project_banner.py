# Created By MotherOfProgrammers(MOP)

import sys
import time
import colorama
from colorama import Fore, Style

colorama.init(autoreset=True)

C = Fore.CYAN
B = Fore.BLUE
W = Fore.WHITE
BR = Style.BRIGHT
R = Style.RESET_ALL

LOGO = [
    r"   _____                _____ _____ _____ ",
    r"  / ____|              |_   _/ ____|_   _|",
    r" | |  __  ___ _ __       | || |  __  | |  ",
    r" | | |_ |/ _ \ '_ \      | || | |_ | | |  ",
    r" | |__| |  __/ | | |    _| || |__| |_| |_ ",
    r"  \_____|\___|_| |_|   |_____\_____|_____|",
]


def animate_banner(delay=0.002):
    print()

    for i, line in enumerate(LOGO):
        color = B if i < 3 else C
        for char in line:
            print(f"{BR}{color}{char}{R}", end="", flush=True)
            time.sleep(delay)
        print()

    print()
    print(f"{B}{BR}  {'=' * 47}{R}")
    print(f"{C}{BR}       G  --- => E  --- => N --- =>  I G I  {R}")
    print(f"{B}{BR}  {'=' * 47}{R}")
    print()


#if __name__ == "__main__":
#    animate_banner()
