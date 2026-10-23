# Created By MotherOfProgrammers(MOP)
import ast
import json
from pathlib import Path
import re

BASE_DIR = Path(__file__).resolve().parent
WEAPONS_DATA_DIR = BASE_DIR/"igi2_converted"/"weapons"
OUT_DIR = BASE_DIR/"out"
OUTPUT_DIR = OUT_DIR/"weapons_data"



def find_matching_paren(source, open_pos):
    depth = 0
    quote = None
    escaped = False

    for i in range(open_pos, len(source)):
        ch = source[i]
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
        elif ch in ('"', "'"):
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i

    raise ValueError("Unclosed parentheses")


def split_arguments(text):
    arguments = []
    start = 0
    depth = 0
    quote = None
    escaped = False

    for i, ch in enumerate(text):
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
        elif ch in ('"', "'"):
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            arguments.append(text[start:i].strip())
            start = i + 1

    last = text[start:].strip()
    if last:
        arguments.append(last)

    return arguments


def parse_value(raw):
    raw = raw.strip()

    if raw.startswith("Task_New"):
        open_pos = raw.find("(")
        close_pos = find_matching_paren(raw, open_pos)

        if close_pos == len(raw) - 1:
            args = split_arguments(raw[open_pos + 1:close_pos])
            values = [parse_value(arg) for arg in args]
            if len(values) < 2:
                raise ValueError(f"Invalid Task_New call: {raw[:100]}")
            return {"task_id": values[0], "type": values[1], "args": values[2:]}

    try:
        return ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return raw


def parse_declarations(source):
    headers = []

    for call_info in extract_top_level_calls(source, "Task_DeclareParameters"):
        call = call_info["text"]
        open_pos = call.find("(")
        close_pos = find_matching_paren(call, open_pos)
        args = split_arguments(call[open_pos + 1:close_pos])

        if not args:
            continue

        task_type = parse_value(args[0])
        fields = args[1:]

        if len(fields) % 2 != 0:
            raise ValueError(f"Unmatched header field/type pair in {task_type}")

        headers.append({"task_type": task_type, "fields": [{"name": parse_value(fields[i]), "type": parse_value(fields[i + 1])} for i in range(0, len(fields), 2)]})

    return headers


def extract_top_level_calls(source, function_name):
    calls = []
    depth = 0
    quote = None
    escaped = False
    i = 0

    while i < len(source):
        ch = source[i]
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            i += 1
            continue

        if ch in ('"', "'"):
            quote = ch
            i += 1
            continue

        if depth == 0 and source.startswith(function_name, i):
            before = source[i - 1] if i else " "
            end_name = i + len(function_name)
            after = source[end_name:end_name + 1]

            if (not (before.isalnum() or before == "_")and not (after.isalnum() or after == "_")):
                open_pos = end_name

                while (open_pos < len(source)and source[open_pos].isspace()):
                    open_pos += 1

                if open_pos < len(source) and source[open_pos] == "(":
                    close_pos = find_matching_paren(source, open_pos)

                    # Preserve the exact original source expression.
                    calls.append({
                        "text": source[i:close_pos + 1],
                        "start": i,
                        "end": close_pos + 1
                    })
                    i = close_pos + 1
                    continue

        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        i += 1
    return calls


def parse_weapons(source):
    weapons = {}

    for call_info in extract_top_level_calls(source, "Task_New"):
        call = call_info["text"]
        open_pos = call.find("(")
        close_pos = find_matching_paren(call, open_pos)
        raw_args = split_arguments(call[open_pos + 1:close_pos])

        if len(raw_args) < 3:
            continue

        task_type = parse_value(raw_args[1])

        # Only top-level WeaponType definitions.
        if task_type != "WeaponType":
            continue

        weapon_id = parse_value(raw_args[2])

        if not isinstance(weapon_id, str):
            raise ValueError(f"Invalid weapon ID: {weapon_id!r}")

        prefix = "WEAPON_ID_"
        name = (
            weapon_id[len(prefix):]
            if weapon_id.startswith(prefix)
            else weapon_id
        )

        name = re.sub(r"[^A-Za-z0-9_-]", "_", name).upper()

        if not name:
            raise ValueError(f"Cannot create a folder for {weapon_id!r}")

        if name in weapons:
            raise ValueError(
                f"Duplicate weapon folder {name!r}: {weapon_id}"
            )

        weapons[name] = {
            "weapon_id": weapon_id,
            "data": parse_value(call),
            "qsc": call + ";",
        }

    return weapons


def parse_weapon_data():
    source_file = WEAPONS_DATA_DIR/"weapon.qsc"

    if not source_file.is_file():
        raise FileNotFoundError(f"Cannot find {source_file}")

    source = source_file.read_text(encoding="utf-8")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    headers = parse_declarations(source)
    weapons = parse_weapons(source)
    (OUTPUT_DIR/"headers.json").write_text(json.dumps(headers, indent=4, ensure_ascii=False) + "\n",encoding="utf-8")

    for name, weapon in weapons.items():
        weapon_dir = OUTPUT_DIR/name
        weapon_dir.mkdir(parents=True, exist_ok=True)
        json_data = {
            "weapon_id": weapon["weapon_id"],
            "data": weapon["data"],
        }

        (weapon_dir/f"{name}.json").write_text(json.dumps(json_data, indent=4, ensure_ascii=False) + "\n",encoding="utf-8")
        # The QSC file contains the original weapon expression,
        # not a reconstruction from parsed JSON.
        (weapon_dir/f"{name}.qsc").write_text(weapon["qsc"].rstrip().removesuffix(";") + ";\n",encoding="utf-8")

    print(f"Headers: {len(headers)}")
    print(f"Weapons: {len(weapons)}")
    print(f"Output:  {OUTPUT_DIR}")


#def main():
#    parse_weapon_data()


#if __name__ == "__main__":
#    main()
