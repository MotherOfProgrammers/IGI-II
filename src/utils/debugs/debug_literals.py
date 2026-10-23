# Created By MotherOfProgrammers(MOP)

"""
Basic Debug Symbols: [INFO], [ERROR], [WARN], [SUCCESS]
Basic Process Debug Symbols: =>, ->, <-, <=, ==, !=
Foreground Color Consolations: Red, Green, Blue, Yellow, Magenta
Text Styling Consolations: Bright, Dim

Color codes:
    red-br       Bright Red
    green-br     Bright Green
    blue-br      Bright Blue
    yellow-br    Bright Yellow
    magenta-br   Bright Magenta

    red-di       Dim Red
    green-di     Dim Green
    blue-di      Dim Blue
    yellow-di    Dim Yellow
    magenta-di   Dim Magenta
"""

import re
import colorama
from colorama import Fore, Style

colorama.init(autoreset=True)


class debug:
    colors = {
        "red": Fore.RED,
        "green": Fore.GREEN,
        "blue": Fore.BLUE,
        "yellow": Fore.YELLOW,
        "magenta": Fore.MAGENTA,
    }

    styles = {
        "br": Style.BRIGHT,
        "di": Style.DIM,
    }

    symbols = {
        "info": ("INFO", Fore.BLUE),
        "error": ("ERROR", Fore.RED),
        "warn": ("WARN", Fore.YELLOW),
        "success": ("SUCCESS", Fore.GREEN),
    }

    operators = ("=>", "->", "<-", "<=", "==", "!=")
    color_pattern = re.compile(r"(red|green|blue|yellow|magenta)-(br|di)",re.IGNORECASE)
    symbol_pattern = re.compile(r"\[(INFO|ERROR|WARN|SUCCESS)\]",re.IGNORECASE)
    operator_pattern = re.compile(r"=>|->|<-|<=|==|!=")

    @classmethod
    def cl(cls, text, code):
        match = cls.color_pattern.fullmatch(code.strip())

        if not match:
            raise ValueError(f"Invalid color code: {code}")

        color_name, style_name = match.groups()
        color = cls.colors[color_name.lower()]
        style = cls.styles[style_name.lower()]

        return f"{style}{color}{text}{Style.RESET_ALL}"

    @classmethod
    def symbol(cls, name):
        name = name.lower()

        if name not in cls.symbols:
            raise ValueError(f"Unknown debug symbol: {name}")

        symbol, color = cls.symbols[name]

        return f"[{color}{symbol}{Style.RESET_ALL}]"

    @classmethod
    def parse(cls, text):
        def replace_symbol(match):
            name = match.group(1).lower()
            return cls.symbol(name)

        return cls.symbol_pattern.sub(replace_symbol, text)

    @classmethod
    def find_operators(cls, text):
        return cls.operator_pattern.findall(text)


"""
if __name__ == "__main__":
    print(debug.cl("Bright Green", "green-br"))
    print(debug.cl("Dim Green", "green-di"))
    print(debug.cl("Bright Red", "red-br"))
    print(debug.cl("Dim Blue", "blue-di"))

    print(debug.symbol("info"))
    print(debug.symbol("error"))
    print(debug.symbol("warn"))
    print(debug.symbol("success"))

    print(debug.parse("[INFO] Server starting"))
    print(debug.parse("[ERROR] Connection failed"))
    print(debug.parse("[SUCCESS] Download complete"))

    print(debug.find_operators("Client -> Server => Response"))
"""