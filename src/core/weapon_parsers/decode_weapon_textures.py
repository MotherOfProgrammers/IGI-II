# Created By MotherOfProgrammers(MOP)
import os
from pathlib import Path
import sys
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_WEAPONS_DIR = os.path.join(BASE_DIR,"out","weapons_textures")
WEAPONS_TEXTURE_DIR = os.path.join(BASE_DIR,"igi2_collected","weapons")

def generate_weapon_textures():
	os.chdir(os.path.join(BASE_DIR,"out"))
	folders_out = [obj for obj in os.listdir() if not os.path.isfile(obj)]

	# check whether if the weapon_textures folder is already available in the user FS, if not create
	if not "weapons_textures" in folders_out:
		Path(OUTPUT_WEAPONS_DIR).mkdir(parents=True,exist_ok=True)

	os.chdir(BASE_DIR)
	IGI2CONV_DIR = os.path.join(BASE_DIR,
		"".join([objs for objs in os.listdir() if (bool(os.path.isfile(objs)) == False and objs.startswith("igi2conv"))]))
	os.chdir(WEAPONS_TEXTURE_DIR)

	print("Creating weapon texture directories...")
	for weapon_encodes in os.listdir():
		if os.path.isfile(weapon_encodes) and weapon_encodes.endswith(".spr"):
			if not "_" in weapon_encodes: # created only the folders one time(unique)
				os.chdir(OUTPUT_WEAPONS_DIR)

				# create new/missing weapon texture directories
				if not os.path.join(OUTPUT_WEAPONS_DIR,weapon_encodes.split(".spr")[0].upper()) in os.listdir():
					Path(os.path.join(OUTPUT_WEAPONS_DIR,weapon_encodes.split(".spr")[0].upper())).mkdir(parents=True,exist_ok=True)

		os.chdir(WEAPONS_TEXTURE_DIR)
	os.chdir(WEAPONS_TEXTURE_DIR)

	print("Converting weapon textures...")
	for weapon_encodes in os.listdir():
		if os.path.isfile(weapon_encodes) and weapon_encodes.endswith(".spr"):
			os.chdir(OUTPUT_WEAPONS_DIR)
			check = [weapon_texture_dir in weapon_encodes.split(".spr")[0].upper() for weapon_texture_dir in os.listdir() if not os.path.isfile(weapon_texture_dir)]
			if True in check:
				target_dir_name = [weapon_texture_dir for weapon_texture_dir in os.listdir()][check.index(True)]
				os.chdir(os.path.join(OUTPUT_WEAPONS_DIR,target_dir_name))
				if not weapon_encodes.replace(".spr",".0.tga") in os.listdir():
					try:
						# executes no-console process(silent-process)
						subprocess.run(
						[
						f"{IGI2CONV_DIR}\\igi2conv\\igi2conv.exe",
						"tex",
						"extract",
						f"{os.path.join(WEAPONS_TEXTURE_DIR,weapon_encodes)}",
						f"{os.path.join(OUTPUT_WEAPONS_DIR,target_dir_name)}",
						],
						stdout=subprocess.DEVNULL,
		    			stderr=subprocess.DEVNULL,
		    			creationflags=subprocess.CREATE_NO_WINDOW,
						)
					except Exception as e:
						print(e)

				if not weapon_encodes.replace(".spr",".png") in os.listdir():
					for weapon_decodes in os.listdir():
						if os.path.isfile(weapon_decodes):
							try:
								subprocess.run(
								[
								f"{IGI2CONV_DIR}\\igi2conv\\igi2conv.exe",
								"image",
								"convert",
								f"{os.path.join(OUTPUT_WEAPONS_DIR,target_dir_name,weapon_decodes)}",
								f"{os.path.join(OUTPUT_WEAPONS_DIR,target_dir_name)}\\{weapon_decodes.replace(".0.tga",".png")}",
								],
								stdout=subprocess.DEVNULL,
				    			stderr=subprocess.DEVNULL,
				    			creationflags=subprocess.CREATE_NO_WINDOW,
								)
							except Exception as e:
								print(e)
		os.chdir(WEAPONS_TEXTURE_DIR)
	return True

#def main():
#	weapon_textures = generate_weapon_textures()
#	if weapon_textures:
#		print("Weapon textures generated successfully!")

#if __name__ == '__main__':
#	main()
