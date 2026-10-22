
# Created By MotherOfProgrammers(MOP)
import os
from pathlib import Path
import subprocess

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_WEAPONS_DIR = BASE_DIR/"out"/"weapons_textures"
WEAPONS_TEXTURE_DIR = BASE_DIR/"igi2_collected"/"weapons"

def generate_weapon_textures():
	if not WEAPONS_TEXTURE_DIR.is_dir():
		raise FileNotFoundError(f"Weapon texture directory not found: {WEAPONS_TEXTURE_DIR}")

	OUTPUT_WEAPONS_DIR.mkdir(parents=True,exist_ok=True)

	# locate the IGI2 converter executable
	IGI2CONV_DIR = next((path for folder in BASE_DIR.iterdir() if folder.is_dir() and folder.name.startswith("igi2conv") for path in [folder/"igi2conv.exe",folder/"igi2conv"/"igi2conv.exe"] if path.is_file()),None)
	if not IGI2CONV_DIR:
		raise FileNotFoundError("Could not find igi2conv.exe.")

	weapon_files = sorted((path for path in WEAPONS_TEXTURE_DIR.iterdir() if path.is_file() and path.suffix.lower() == ".spr"),key=lambda path: path.name.lower())
	weapon_names = {path.stem.upper(): path.stem for path in weapon_files if "_" not in path.stem}
	weapon_dirs = {}

	# map every texture to its correct weapon directory
	for weapon_encodes in weapon_files:
		weapon_name = weapon_encodes.stem.removesuffix("_pickup")
		matches = [name for name in weapon_names if weapon_name.upper().startswith(name)]
		if not matches:
			continue

		target_name = max(matches,key=len)
		target_dir = OUTPUT_WEAPONS_DIR/target_name
		target_dir.mkdir(parents=True,exist_ok=True)
		weapon_dirs[weapon_encodes] = target_dir

	print("Creating weapon texture directories...")
	print(f"Weapon directories: {len(set(weapon_dirs.values()))}")

	print("Converting weapon textures...")
	failures = 0

	for weapon_encodes, target_dir in weapon_dirs.items():
		print(f"Weapon: {weapon_encodes.name}")
		print(f"Target-DIR: {target_dir.name}")

		source_file = weapon_encodes
		expected_tga = target_dir/f"{weapon_encodes.stem}.0.tga"

		if not expected_tga.is_file():
			try:
				result = subprocess.run([str(IGI2CONV_DIR),"tex","extract",str(source_file),str(target_dir)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0),check=False)
				if result.returncode != 0:
					print(f"Extraction failed: {weapon_encodes.name} (exit code {result.returncode})")
					failures += 1
			except OSError as e:
				print(f"Extraction error: {weapon_encodes.name}: {e}")
				failures += 1
				continue

		# convert extracted TGA textures to PNG
		for weapon_decodes in sorted(target_dir.glob("*.tga")):
			png_name = weapon_decodes.stem.removesuffix(".0")+".png"
			png_path = target_dir/png_name

			if png_path.is_file():
				continue

			try:
				result = subprocess.run([str(IGI2CONV_DIR),"image","convert",str(weapon_decodes),str(png_path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0),check=False)
				if result.returncode != 0 or not png_path.is_file():
					print(f"Conversion failed: {weapon_decodes.name} (exit code {result.returncode})")
					failures += 1
			except OSError as e:
				print(f"Conversion error: {weapon_decodes.name}: {e}")
				failures += 1

	print(f"Weapon directories: {len(set(weapon_dirs.values()))}")
	print(f"Conversion failures: {failures}")
	return failures == 0


#def main():
#	weapon_textures = generate_weapon_textures()
#	if weapon_textures:
#		print("Weapon textures generated successfully!")

#if __name__ == '__main__':
#	main()
