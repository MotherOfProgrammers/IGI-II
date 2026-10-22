# Created By MotherOfProgrammers(MOP)
import os
from pathlib import Path
import sys
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_WEAPONS_DIR = os.path.join(BASE_DIR,"out","weapons_textures")
WEAPONS_TEXTURE_DIR = os.path.join(BASE_DIR,"igi2_collected","weapons")

def generate_weapon_textures():
	Path(OUTPUT_WEAPONS_DIR).mkdir(parents=True,exist_ok=True)

	# locate the IGI2 converter directory
	IGI2CONV_DIR = next((os.path.join(BASE_DIR,obj,"igi2conv.exe") for obj in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR,obj)) and obj.startswith("igi2conv") and os.path.isfile(os.path.join(BASE_DIR,obj,"igi2conv.exe"))),None)
	if not IGI2CONV_DIR:
		raise FileNotFoundError("Could not find igi2conv.exe in an igi2conv* directory.")

	IGI2CONV_DIR = os.path.dirname(IGI2CONV_DIR)
	weapon_files = sorted(obj for obj in os.listdir(WEAPONS_TEXTURE_DIR) if os.path.isfile(os.path.join(WEAPONS_TEXTURE_DIR,obj)) and obj.lower().endswith(".spr"))
	weapon_dirs = {}

	print("Creating weapon texture directories...")
	for weapon_encodes in weapon_files:
		weapon_name = os.path.splitext(weapon_encodes)[0]
		if "_" not in weapon_name:
			target_dir_name = weapon_name.upper()
			target_dir = os.path.join(OUTPUT_WEAPONS_DIR,target_dir_name)
			Path(target_dir).mkdir(parents=True,exist_ok=True)
			weapon_dirs[weapon_encodes] = target_dir

	print("Converting weapon textures...")
	for weapon_encodes in weapon_files:
		weapon_name = os.path.splitext(weapon_encodes)[0]
		target_dir = weapon_dirs.get(weapon_encodes,os.path.join(OUTPUT_WEAPONS_DIR,weapon_name.split("_")[0].upper()))

		if not os.path.isdir(target_dir):
			print(f"Skipping {weapon_encodes}: weapon directory not found.")
			continue

		source_file = os.path.join(WEAPONS_TEXTURE_DIR,weapon_encodes)
		texture_file = os.path.join(target_dir,weapon_name+".0.tga")
		png_file = os.path.join(target_dir,weapon_name+".png")

		if not os.path.isfile(texture_file):
			try:
				result = subprocess.run(
					[
					IGI2CONV_DIR,
					"tex",
					"extract",
					source_file,
					target_dir
					],
					stdout=subprocess.DEVNULL,
					stderr=subprocess.DEVNULL,
					creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0),
					check=False
					)
				if result.returncode != 0:
					print(f"Failed to extract {weapon_encodes} (exit code {result.returncode}).")
			except OSError as e:
				print(f"Extraction error for {weapon_encodes}: {e}")
				continue

		# convert extracted TGA textures to PNG
		for weapon_decodes in os.listdir(target_dir):
			if not os.path.isfile(os.path.join(target_dir,weapon_decodes)) or not weapon_decodes.lower().endswith(".tga"):
				continue

			png_output = os.path.splitext(weapon_decodes)[0].replace(".0","")+".png"
			png_path = os.path.join(target_dir,png_output)

			if not os.path.isfile(png_path):
				try:
					result = subprocess.run(
						[
						IGI2CONV_DIR,
						"image",
						"convert",
						os.path.join(target_dir,weapon_decodes),
						png_path
						],
						stdout=subprocess.DEVNULL,
						stderr=subprocess.DEVNULL,
						creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0),
						check=False
						)
					if result.returncode != 0:
						print(f"Failed to convert {weapon_decodes} (exit code {result.returncode}).")
				except OSError as e:
					print(f"Conversion error for {weapon_decodes}: {e}")

	return True

#def main():
#	weapon_textures = generate_weapon_textures()
#	if weapon_textures:
#		print("Weapon textures generated successfully!")

#if __name__ == '__main__':
#	main()
