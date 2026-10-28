
# Created By MotherOfProgrammers(MOP)

import os
import sys
from pathlib import Path
import platform
import hashlib
from zipfile import ZipFile, BadZipFile
import requests
from bs4 import BeautifulSoup
import subprocess
import json

from src.datastore import entry_data_store
from src.utils.debugs import debug_literals
from src.utils.banners import comm_banner

store = entry_data_store.DataStore.load()

BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR/"out"
DUMMY_DIR = BASE_DIR/"igi1_dummy"

URL = "https://www.mediafire.com/file/g75m6y2anuen34g/igi2conv-windows-x86_64-qt-r9.zip/file"
ZIP_NAME = "igi2conv-windows-x86_64-qt-r9.zip"
OUTPUT_DIR = Path("igi2conv-windows-x86_64-qt-r9")

HEADERS = {"User-Agent": "Mozilla/5.0"}


debugger = debug_literals.debug

def download_igi2conv():
    try:
        with requests.Session() as session:
            response = session.get(URL, headers=HEADERS, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            button = soup.select_one("#downloadButton")

            if not button or not button.get("href"):
                raise RuntimeError(
                    f"{debugger.symbol("error")}{debugger.cl(""" Could not find MediaFire download link.
                    	The page may require verification.""","red-br")}"
                )

            download_url = button["href"]

            with session.get(download_url,headers=HEADERS,stream=True,timeout=(30, 120)) as download:
                download.raise_for_status()

                total = int(download.headers.get("content-length", 0))
                received = 0

                with open(ZIP_NAME, "wb") as file:
                    for chunk in download.iter_content(1024 * 1024):
                        if chunk:
                            file.write(chunk)
                            received += len(chunk)

                            if total:
                                percent = received * 100 // total
                                print(
                                    f"{debugger.symbol("info")}\r Downloading: {percent}% ({received:,}/{total:,} bytes)",
                                    end="",
                                    flush=True,
                                )

            print(f"\n{debugger.symbol("success")} Download finished successfully!")

        if not ZipFile.is_zipfile(ZIP_NAME):
            Path(ZIP_NAME).unlink(missing_ok=True)
            raise RuntimeError(f"{debugger.symbol("error")}{debugger.cl("Downloaded content is not a valid ZIP file.","red-br")}")

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        with ZipFile(ZIP_NAME, "r") as archive:
            # Prevent ZIP path traversal when extracting untrusted files.
            root = OUTPUT_DIR.resolve()
            for member in archive.infolist():
                target = (OUTPUT_DIR / member.filename).resolve()
                if target != root and root not in target.parents:
                    raise RuntimeError(f"{debugger.symbol("error")}{debugger.cl(f" Unsafe path in ZIP: {member.filename}","red-br")}")

            archive.extractall(OUTPUT_DIR)

        print(f"{debugger.symbol("success")} Extracted to: {OUTPUT_DIR.resolve()}")
        return True

    except (requests.RequestException, BadZipFile, OSError,
            RuntimeError) as error:
        print(f"\n{debugger.symbol("error")}{debugger.cl(f" Error: {error}","red-br")}")
        return False

def main():
    fs_objs = os.listdir()
    print(f"{debugger.symbol("info")} Creating Missing Directories...")
    if not "out" in fs_objs:
        Path(OUT_DIR).mkdir(parents=True,exist_ok=True)

    if not "igi2conv-windows-x86_64-qt-r9" in fs_objs:
        status = download_igi2conv()
        if status == False:
            sys.exit(-1)

    print(f"{debugger.symbol("info")} Initializing IGIPY...")
    if not "igipy.json" in fs_objs:
        try:
            result = subprocess.run(
                ["igipy"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0),
                check=False
                )
            if result.returncode != 0:
                print(f"{debugger.symbol("error")}{debugger.cl(" IGIPY module initalization unsuccessful!","red-br")}")
        except OSError as e:
            print(f"{debugger.symbol("error")}{debugger.cl(f" An unknown error occured due to => {e}")}")
            sys.exit(-1)

    Path(DUMMY_DIR).mkdir(parents=True,exist_ok=True)
    with open("igipy.json",'r') as igipy_conf:
        conf_data = json.load(igipy_conf)

    conf_data["igi1"]["game_dir"] = str(DUMMY_DIR)
    conf_data["igi2"]["game_dir"] = str(input(f"{debugger.symbol("info")} Enter the path for IGI-2 game directory: "))

    if len(conf_data["igi2"]["game_dir"]) == 0:
        raise ValueError(f"{debugger.symbol("error")}{debugger.cl(" Input cannot be empty."),"red-br"}")

    root_count, dir_count, files_count = 0, 0, 0
    for root, dir, files in os.walk(conf_data["igi2"]["game_dir"]):
        if root != '':
            root_count += 1
        if len(dir) > 0:
            dir_count += 1
        if len(files) > 0:
            files_count += 1
    if ((root_count == 0) or (dir_count == 0) or (files_count == 0)):
        print(f"{debugger.symbol("error")}{debugger.cl(f" The given {conf_data["igi2"]["game_dir"]} is not a genuine path!","red-br")}")
        sys.exit(-1)

    print(f"{debugger.symbol("info")} Extracting Data...")
    if not "igi2_collected" in fs_objs:
        try:
            result = subprocess.run(
                [
                "igipy",
                "igi2",
                "extensions-of-game"
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0),
                check=False
                )
            try:
                result = subprocess.run(
                [
                "igipy",
                "igi2",
                "collect"
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0),
                check=False
                )
                if result.returncode != 0:
                    print(f"{debugger.symbol("error")}{debugger.cl(f" IGIPY module parsing of igi2 is unsuccessful!","red-br")}")
                    sys.exit(-1)
            except OSError as e:
                print(f"{debugger.symbol("error")}{debugger.cl(f" An unknown error occured due to => {e}","red-br")}")
                sys.exit(-1)

            if result.returncode != 0:
                print(f"{debugger.symbol("error")}{debugger.cl(f" IGIPY module parsing of igi2 is unsuccessful!","red-br")}")
                sys.exit(-1)
        except OSError as e:
            print(f"{debugger.symbol("error")}{debugger.cl(f" An unknown error occured due to => {e}","red-br")}")
            sys.exit(-1)

    print(f"{debugger.symbol("info")} Converting Data...")
    if not "igi2_converted" in fs_objs:
        final_args = [
        "convert-qvm-to-qsc",
        "convert-tex-to-tga",
        "convert-thm-to-tga",
        "convert-tmm-to-tga",
        "convert-tlm-to-tga",
        "convert-olm-to-tga"
        ]
        for arg in final_args:
            try:
                result = subprocess.run(
                    [
                    "igipy",
                    "igi2",
                    arg
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0),
                    check=False
                    )
                if result.returncode != 0:
                    print(f"{debugger.symbol("error")}{debugger.cl(f" IGIPY module parsing of igi2 is unsuccessful!","red-br")}")
                    sys.exit(-1)
            except OSError as e:
                print(f"{debugger.symbol("error")}{debugger.cl(f" An unknown error occured due to => {e}","red-br")}")
                sys.exit(-1)
    return True


if __name__ == '__main__':
    if hashlib.sha512(str(platform.uname()[0]).encode()).hexdigest() == store.entry_key:
        comm_banner.initiate_banner()
        status = main()
        if status == True:
            print(f"{debugger.symbol("success")} Preparation successful!")
            print(f"{debugger.symbol("success")} Ready to go!")
            sys.exit(0)
    else:
        raise OSError("Unsupported Operating System!")
        sys.exit(-1)
