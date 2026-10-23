# Created By MotherOfProgrammers(MOP)

"""
Requirements:

OS - Windows
Python - Version 3.13+

Required File Structure:


igi2_collected/
igi2_converted/
igi2conv-windows-x86_64-qt-r9/
	igi2conv/
			------------> *
			------------> igi2conv.exe
out/
	weapon_data/
				{WEAPON_ID}/
							------------> {WEAPON_ID}.json
							------------> {WEAPON_ID}.qsc
							{MOD_VERSION}/
										 ------------> {WEAPON_ID}.qsc
	weapon_textures/
				{WEAPON_ID}/
							------------> {WEAPON_ID}.0.tga
							------------> {WEAPON_ID}_pickup.0.tga
							------------> {WEAPON_ID}.png
							------------> {WEAPON_ID}_pickup.png
							{MOD_VERSION}/
										 ------------> {WEAPON_ID}.0.tga
										 ------------> {WEAPON_ID}_pickup.0.tga
										 ------------> {WEAPON_ID}.png
										 ------------> {WEAPON_ID}_pickup.png
src/
	core/
		weapon_parsers/
			--------------> decode_weapon_textures.py
			--------------> diff_weapon_data.py
		player_parsers/
			-------------->
		world_parsers/
			-------------->
		multiplayer/
			-------------->
	utils/
		debugs/
			--------------> debug_symbols.py
		banners/
			--------------> banner.py
drit/ <= Data Route Index Tree
	------------> weapons_drit.txt
	------------> player_drip.txt
	------------> world_drit.txt
	------------> multiplayer_drit.txt
igipy.json
prep.py
main.py
weapon_data_info.txt
requirements.txt
README.md


"""

import os
import sys
from pathlib import Path
import platform
import hashlib
from zipfile import ZipFile, BadZipFile
import requests
from bs4 import BeautifulSoup

from src.datastore import entry_data_store
from src.utils.debugs import debug_symbols
from src.utils.banners import project_banner

store = entry_data_store.DataStore.load()

BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR/"out"

URL = "https://www.mediafire.com/file/g75m6y2anuen34g/igi2conv-windows-x86_64-qt-r9.zip/file"
ZIP_NAME = "igi2conv-windows-x86_64-qt-r9.zip"
OUTPUT_DIR = Path("igi2conv-windows-x86_64-qt-r9")

HEADERS = {"User-Agent": "Mozilla/5.0"}

def download_igi2conv():
	try:
        with requests.Session() as session:
            response = session.get(URL, headers=HEADERS, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            button = soup.select_one("#downloadButton")

            if not button or not button.get("href"):
                raise RuntimeError(
                    "Could not find MediaFire download link. "
                    "The page may require verification."
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
                                    f"\rDownloading: {percent}% "
                                    f"({received:,}/{total:,} bytes)",
                                    end="",
                                    flush=True,
                                )

            print("\nDownload finished.")

        if not ZipFile.is_zipfile(ZIP_NAME):
            Path(ZIP_NAME).unlink(missing_ok=True)
            raise RuntimeError("Downloaded content is not a valid ZIP file.")

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        with ZipFile(ZIP_NAME, "r") as archive:
            # Prevent ZIP path traversal when extracting untrusted files.
            root = OUTPUT_DIR.resolve()
            for member in archive.infolist():
                target = (OUTPUT_DIR / member.filename).resolve()
                if target != root and root not in target.parents:
                    raise RuntimeError(
                        f"Unsafe path in ZIP: {member.filename}"
                    )

            archive.extractall(OUTPUT_DIR)

        print(f"Extracted to: {OUTPUT_DIR.resolve()}")

    except (requests.RequestException, BadZipFile, OSError,
            RuntimeError) as error:
        print(f"\nError: {error}")

def main():
	if not "out" in os.listdir():
		Path(OUT_DIR).mkdir(parents=True,exist_ok=True)
	if not "igi2conv-windows-x86_64-qt-r9" in os.listdir():
		download_igi2conv()


if __name__ == '__main__':
	if hashlib.sha512(str(platform.uname()[0]).encode()).hexdigest() == store.entry_key:
		print("YES")
	else:
		raise OSError("Unsupported Operating System!")
		sys.exit(-1)
	#main()