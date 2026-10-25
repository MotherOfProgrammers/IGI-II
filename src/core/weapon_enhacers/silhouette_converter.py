
# Created By MotherOfProgrammers(MOP)

"""
GenIGI Weapon Silhouette Generator

Automatically scans every weapon directory inside out/weapons_textures
And converts weapon PNG images into solid white silhouettes with quality upscaling
And then exports .png, .0.tga, and .spr files into matching directories under v1.0.0
uses igi2conv for SPR packing with original SPR templates.
"""

import cv2
import numpy as np
from PIL import Image
import os
import sys
from pathlib import Path
import subprocess
import json
import tempfile
import shutil

BASE_DIR = Path(__file__).resolve().parent
TEXTURE_DIR = BASE_DIR/"out"/"weapons_textures"
TARGET_DIR = TEXTURE_DIR/"v1.0.0"
IGI2CONV_DIR = next((path for folder in BASE_DIR.iterdir() if folder.is_dir() and folder.name.startswith("igi2conv") for path in [folder/"igi2conv.exe",folder/"igi2conv"/"igi2conv.exe"] if path.is_file()), None)

SCALE_FACTOR = 4.0
ALPHA_THRESHOLD = 0
BACKGROUND_TOLERANCE = 12
SUPPORTED_FORMATS = {".png"}
OUTPUT_VERSION = "v1.0.0"

def extract_weapon_mask(img):
    alpha = img[:,:,3]

    # use the original transparency when available
    if np.any(alpha < 255):
        return alpha.copy()

    # estimate the background for images without transparency
    bgr = img[:,:,:3]
    h, w = bgr.shape[:2]
    corners = np.array([bgr[0, 0], bgr[0, w - 1], bgr[h - 1, 0], bgr[h - 1, w - 1]], dtype=np.float32)
    background = np.median(corners, axis=0)

    difference = np.linalg.norm(bgr.astype(np.float32) - background, axis=2)
    mask = np.clip((difference - BACKGROUND_TOLERANCE)*(255.0/24.0), 0, 255).astype(np.uint8)

    return mask


def enhance_weapon_texture(input_path, scale_factor=4.0, unsharp_strength=0.0):
    img = cv2.imread(str(input_path), cv2.IMREAD_UNCHANGED)

    if img is None:
        raise FileNotFoundError(f"Weapon image not found: {input_path}")

    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
    elif img.shape[2] == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    elif img.shape[2] != 4:
        raise ValueError(f"Unsupported image format: {input_path}")

    original_height, original_width = img.shape[:2]
    alpha = extract_weapon_mask(img)

    # upscale the alpha mask internally for high-resolution processing
    upscale_width = max(1, round(original_width * scale_factor))
    upscale_height = max(1, round(original_height * scale_factor))

    alpha_image = Image.fromarray(alpha)
    high_resolution_mask = alpha_image.resize((upscale_width, upscale_height), Image.Resampling.LANCZOS)

    # apply a subtle edge-smoothing pass at the higher resolution
    high_resolution_mask = np.array(high_resolution_mask)
    high_resolution_mask = cv2.GaussianBlur(high_resolution_mask, (3, 3), 0.35)

    # downsample back to the exact original resolution
    final_alpha = Image.fromarray(high_resolution_mask).resize((original_width, original_height), Image.Resampling.LANCZOS)
    final_alpha = np.asarray(final_alpha, dtype=np.uint8)

    # preserve the original silhouette's visible coverage
    final_alpha = np.maximum(final_alpha, np.where(alpha == 255, 255, 0).astype(np.uint8))

    # construct the final solid-white RGBA weapon silhouette
    silhouette = np.empty((original_height, original_width, 4), dtype=np.uint8)
    silhouette[:,:,:3] = 255
    silhouette[:,:,3] = final_alpha

    return silhouette


def generate_silhouette(enhanced_img, output_silhouette_path, output_json_path=None, target_width=None, target_height=None, padding=0):
    h, w = enhanced_img.shape[:2]

    if target_width is not None and target_height is not None and (target_width, target_height) != (w, h):
        alpha_image = Image.fromarray(enhanced_img[:,:,3], mode="L")
        resized_alpha = np.asarray(alpha_image.resize((target_width, target_height), Image.Resampling.LANCZOS), dtype=np.uint8)
        enhanced_img = np.empty((target_height, target_width, 4), dtype=np.uint8)
        enhanced_img[:,:,:3] = 255
        enhanced_img[:,:,3] = resized_alpha

    output_silhouette_path = Path(output_silhouette_path)
    output_silhouette_path.parent.mkdir(parents=True,exist_ok=True)

    rgba = cv2.cvtColor(enhanced_img, cv2.COLOR_BGRA2RGBA)
    Image.fromarray(rgba).save(output_silhouette_path, "PNG")

    print(f"[SUCCESS] PNG => {output_silhouette_path.name}")
    return enhanced_img

def generate_tga(silhouette, output_tga_path):
    output_tga_path = Path(output_tga_path)
    output_tga_path.parent.mkdir(parents=True,exist_ok=True)

    rgba = cv2.cvtColor(silhouette, cv2.COLOR_BGRA2RGBA)
    Image.fromarray(rgba).save(output_tga_path, format="TGA")

    print(f"[SUCCESS] TGA => {output_tga_path.name}")
    return output_tga_path

def find_spr_template(weapon_dir, weapon_name, image_name):
    templates = sorted(weapon_dir.glob("*.spr"), key=lambda p: p.name.lower())

    if not templates:
        return None

    for template in templates:
        if template.stem.lower() == image_name.lower():
            return template

    for template in templates:
        if template.stem.lower() == weapon_name.lower():
            return template

    if len(templates) == 1:
        return templates[0]

    return None

def generate_spr(input_tga_path, output_spr_path, template_spr_path):
    if IGI2CONV_DIR is None:
        raise FileNotFoundError("igi2conv.exe could not be found")

    if template_spr_path is None or not Path(template_spr_path).is_file():
        raise FileNotFoundError("Original SPR template is missing")

    input_tga_path = Path(input_tga_path).resolve()
    output_spr_path = Path(output_spr_path).resolve()
    template_spr_path = Path(template_spr_path).resolve()

    output_spr_path.parent.mkdir(parents=True,exist_ok=True)

    # extract the original template to preserve its required texture layout
    with tempfile.TemporaryDirectory(prefix="genigi_spr_") as temporary:
        bitmap_dir = Path(temporary)/"bitmaps"
        bitmap_dir.mkdir(parents=True,exist_ok=True)

        extract_command = [str(IGI2CONV_DIR),"tex","extract",str(template_spr_path), str(bitmap_dir)]
        extracted = subprocess.run(extract_command,capture_output=True,text=True)

        if extracted.returncode != 0:
            raise RuntimeError(f"SPR extraction failed: {extracted.stderr.strip()}")

        # locate the bitmap representing the original sprite
        candidates = sorted([p for p in bitmap_dir.rglob("*") if p.is_file() and p.suffix.lower() in {".tga", ".png", ".bmp"}])

        if len(candidates) != 1:
            raise RuntimeError(f"Expected one sprite bitmap, found {len(candidates)}. Template layout needs inspection")

        # replace the extracted bitmap while preserving its filename
        replacement = candidates[0]
        with Image.open(input_tga_path) as image:
            image.convert("RGBA").save(replacement, format="TGA" if replacement.suffix.lower() == ".tga" else "PNG" if replacement.suffix.lower() == ".png" else "BMP")

        pack_command = [str(IGI2CONV_DIR),"tex","pack",str(template_spr_path),str(bitmap_dir),str(output_spr_path)]
        packed = subprocess.run(pack_command, capture_output=True, text=True)

        if packed.returncode != 0:
            raise RuntimeError(f"SPR packing failed: {packed.stderr.strip()}")

    if not output_spr_path.is_file() or output_spr_path.stat().st_size == 0:
        raise RuntimeError("SPR file was not generated correctly")

    print(f"[SUCCESS] SPR => {output_spr_path.name}")
    return output_spr_path

def process_weapon_image(image_path, weapon_dir, output_dir):
    weapon_name = weapon_dir.name
    image_name = image_path.stem

    png_path = output_dir/f"{image_name}.png"
    tga_path = output_dir/f"{image_name}.0.tga"
    spr_path = output_dir/f"{image_name}.spr"

    print(f"\n[INFO] Processing weapon: {weapon_name}")
    print(f"[INFO] Image: {image_path.name}")

    if not image_path.name.endswith("_pickup.png"):
        enhanced_texture = enhance_weapon_texture(image_path, scale_factor=SCALE_FACTOR)
        silhouette = generate_silhouette(enhanced_texture, png_path)
        generate_tga(silhouette, tga_path)

        original = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
        print(f"[INFO] Resolution: {original.shape[1]}x{original.shape[0]} => {silhouette.shape[1]}x{silhouette.shape[0]}")

        template = find_spr_template(weapon_dir, weapon_name, image_name)

        if template is None:
            print(f"[WARN] SPR template unavailable for {weapon_name}. SPR skipped")
            return False

        if IGI2CONV_DIR is None:
            print("[WARN] igi2conv.exe not found. SPR skipped")
            return False

        generate_spr(tga_path, spr_path, template)
        return True
    else:
        print("Copying the pickup image...")
        copy_image_path = image_path
        tga_filename = f"{copy_image_path.stem}.0.tga"
        tga_image_path = copy_image_path.with_name(tga_filename)
        shutil.copy(copy_image_path,output_dir)
        shutil.copy(tga_image_path,output_dir)

def generate_all_weapon_silhouettes():
    if not TEXTURE_DIR.is_dir():
        raise FileNotFoundError(f"Weapon texture directory does not exist: {TEXTURE_DIR}")

    TARGET_DIR.mkdir(parents=True,exist_ok=True)
    print(f"[INFO] Source: {TEXTURE_DIR}")
    print(f"[INFO] Target: {TARGET_DIR}")
    print(f"[INFO] Upscaling: {SCALE_FACTOR}x")
    print(f"[INFO] igi2conv: {IGI2CONV_DIR if IGI2CONV_DIR else 'Not found'}")

    weapon_directories = sorted([folder for folder in TEXTURE_DIR.iterdir() if folder.is_dir() and folder.resolve() != TARGET_DIR.resolve()], key=lambda p: p.name.lower())

    total_images = 0
    successful_spr = 0
    failed_images = 0
    skipped_spr = 0
    for weapon_dir in weapon_directories:
        image_files = sorted([file for file in weapon_dir.iterdir() if file.is_file() and file.suffix.lower() in SUPPORTED_FORMATS], key=lambda p: p.name.lower())

        if not image_files:
            continue

        output_dir = TARGET_DIR/weapon_dir.name
        output_dir.mkdir(parents=True,exist_ok=True)

        for image_path in image_files:
            total_images += 1

            try:
                created_spr = process_weapon_image(image_path, weapon_dir, output_dir)
                if created_spr:
                    successful_spr += 1
                else:
                    skipped_spr += 1
            except Exception as error:
                failed_images += 1
                print(f"[ERROR] {weapon_dir.name}/{image_path.name}: {error}")

    print(f"[INFO] Weapon directories scanned: {len(weapon_directories)}")
    print(f"[INFO] Images processed: {total_images}")
    print(f"[INFO] SPR generated: {successful_spr}")
    print(f"[INFO] SPR skipped: {skipped_spr}")
    print(f"[INFO] Processing failures: {failed_images}")
    print(f"[INFO] Output directory: {TARGET_DIR}")

if __name__ == "__main__":
    try:
        generate_all_weapon_silhouettes()
    except Exception as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        sys.exit(1)