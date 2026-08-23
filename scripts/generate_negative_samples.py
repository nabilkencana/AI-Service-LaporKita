"""
Generate and collect 350 diverse negative / Out-of-Distribution (OOD) images
for the 6th class 'bukan_fasilitas'.
Includes:
- Solid colors (gray, black, white, primary, pastel colors at multiple resolutions)
- Gradients (linear, radial, multi-stop)
- Synthetic noise (Gaussian, uniform, salt-and-pepper, Perlin-like patterns)
- Text documents, diagrams, geometric shapes, textures
- Natural non-infrastructure subjects (synthetic/rendered animals, food, indoor objects, sky)
"""

import os
import math
import random
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "dataset_staging" / "bukan_fasilitas"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_solid_colors(count=50):
    resolutions = [(224, 224), (320, 240), (480, 480), (640, 480), (800, 600), (1920, 1080), (4000, 3000)]
    colors = [
        (128, 128, 128), # Medium Gray
        (64, 64, 64),    # Dark Gray
        (192, 192, 192), # Light Gray
        (255, 255, 255), # Pure White
        (0, 0, 0),       # Pure Black
        (255, 0, 0),     # Red
        (0, 255, 0),     # Green
        (0, 0, 255),     # Blue
        (255, 255, 0),   # Yellow
        (0, 255, 255),   # Cyan
        (255, 0, 255),   # Magenta
        (240, 240, 245), # Off-white
        (30, 35, 45),    # Dark blue-gray
        (139, 69, 19),   # Saddle brown
        (255, 192, 203), # Pink
    ]
    
    idx = 0
    for res in resolutions:
        for c in colors:
            if idx >= count:
                return
            img = Image.new("RGB", res, color=c)
            img.save(OUTPUT_DIR / f"solid_color_{idx:04d}_{res[0]}x{res[1]}.jpg", format="JPEG", quality=90)
            idx += 1


def generate_gradients(count=50):
    resolutions = [(224, 224), (320, 320), (480, 480), (640, 480), (1280, 720)]
    for i in range(count):
        res = random.choice(resolutions)
        w, h = res
        c1 = [random.randint(0, 255) for _ in range(3)]
        c2 = [random.randint(0, 255) for _ in range(3)]
        
        # Horizontal, vertical or diagonal
        mode = random.choice(["h", "v", "diag", "radial"])
        img_arr = np.zeros((h, w, 3), dtype=np.uint8)
        
        if mode == "h":
            for x in range(w):
                ratio = x / max(1, w - 1)
                img_arr[:, x] = [int(c1[k] * (1 - ratio) + c2[k] * ratio) for k in range(3)]
        elif mode == "v":
            for y in range(h):
                ratio = y / max(1, h - 1)
                img_arr[y, :] = [int(c1[k] * (1 - ratio) + c2[k] * ratio) for k in range(3)]
        elif mode == "diag":
            for y in range(h):
                for x in range(w):
                    ratio = (x + y) / max(1, w + h - 2)
                    img_arr[y, x] = [int(c1[k] * (1 - ratio) + c2[k] * ratio) for k in range(3)]
        else: # Radial
            cx, cy = w // 2, h // 2
            max_r = math.sqrt(cx**2 + cy**2)
            y_indices, x_indices = np.ogrid[:h, :w]
            dist = np.sqrt((x_indices - cx)**2 + (y_indices - cy)**2) / max_r
            dist = np.clip(dist, 0.0, 1.0)
            for k in range(3):
                img_arr[:, :, k] = (c1[k] * (1 - dist) + c2[k] * dist).astype(np.uint8)
                
        img = Image.fromarray(img_arr)
        img.save(OUTPUT_DIR / f"gradient_{i:04d}_{mode}.jpg", format="JPEG", quality=90)


def generate_noise(count=60):
    resolutions = [(224, 224), (320, 320), (480, 480), (640, 480)]
    for i in range(count):
        res = random.choice(resolutions)
        w, h = res
        noise_type = random.choice(["uniform_color", "uniform_gray", "gaussian", "salt_pepper", "blurred_noise"])
        
        if noise_type == "uniform_color":
            arr = np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)
        elif noise_type == "uniform_gray":
            g = np.random.randint(0, 256, (h, w), dtype=np.uint8)
            arr = np.stack([g, g, g], axis=-1)
        elif noise_type == "gaussian":
            mean = random.randint(100, 160)
            std = random.randint(30, 70)
            g = np.clip(np.random.normal(mean, std, (h, w, 3)), 0, 255).astype(np.uint8)
            arr = g
        elif noise_type == "salt_pepper":
            arr = np.full((h, w, 3), 128, dtype=np.uint8)
            prob = 0.15
            rnd = np.random.random((h, w))
            arr[rnd < prob / 2] = [0, 0, 0]
            arr[rnd > 1 - prob / 2] = [255, 255, 255]
        else: # blurred noise
            arr = np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)
            img = Image.fromarray(arr).filter(ImageFilter.GaussianBlur(radius=random.randint(3, 10)))
            img.save(OUTPUT_DIR / f"noise_{i:04d}_{noise_type}.jpg", format="JPEG", quality=90)
            continue
            
        img = Image.fromarray(arr)
        img.save(OUTPUT_DIR / f"noise_{i:04d}_{noise_type}.jpg", format="JPEG", quality=90)


def generate_documents_and_text(count=50):
    resolutions = [(480, 640), (600, 800), (800, 600), (320, 320)]
    for i in range(count):
        res = random.choice(resolutions)
        w, h = res
        bg_color = random.choice([(255, 255, 255), (250, 250, 240), (240, 245, 255), (30, 30, 30)])
        text_color = (0, 0, 0) if bg_color[0] > 128 else (255, 255, 255)
        
        img = Image.new("RGB", (w, h), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        # Draw mock text lines / document paragraphs
        num_lines = random.randint(10, 30)
        y = 20
        for _ in range(num_lines):
            line_len = random.randint(w // 3, w - 40)
            line_h = random.randint(8, 16)
            draw.rectangle([20, y, 20 + line_len, y + line_h], fill=text_color)
            y += line_h + random.randint(6, 12)
            if y > h - 30:
                break
                
        # Draw mock tables or charts
        if random.random() > 0.5:
            draw.rectangle([20, h // 2, w - 20, h - 40], outline=text_color, width=2)
            draw.line([w // 2, h // 2, w // 2, h - 40], fill=text_color, width=2)
            
        img.save(OUTPUT_DIR / f"document_{i:04d}.jpg", format="JPEG", quality=90)


def generate_geometric_patterns(count=60):
    resolutions = [(320, 320), (480, 480), (640, 480)]
    for i in range(count):
        res = random.choice(resolutions)
        w, h = res
        bg = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        img = Image.new("RGB", (w, h), color=bg)
        draw = ImageDraw.Draw(img)
        
        pattern_type = random.choice(["circles", "rectangles", "checkerboard", "stripes", "polygons", "stars"])
        
        if pattern_type == "checkerboard":
            sq = random.choice([20, 40, 60])
            c_alt = (255 - bg[0], 255 - bg[1], 255 - bg[2])
            for y in range(0, h, sq):
                for x in range(0, w, sq):
                    if ((x // sq) + (y // sq)) % 2 == 0:
                        draw.rectangle([x, y, x + sq, y + sq], fill=c_alt)
        elif pattern_type == "stripes":
            step = random.randint(15, 40)
            c_alt = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            for x in range(0, w * 2, step * 2):
                draw.polygon([(x, 0), (x + step, 0), (x + step - h, h), (x - h, h)], fill=c_alt)
        elif pattern_type == "circles":
            for _ in range(random.randint(10, 40)):
                r = random.randint(10, 80)
                cx = random.randint(0, w)
                cy = random.randint(0, h)
                c_rand = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c_rand, outline=(0, 0, 0))
        else:
            for _ in range(random.randint(10, 30)):
                x1, y1 = random.randint(0, w), random.randint(0, h)
                x2, y2 = random.randint(0, w), random.randint(0, h)
                c_rand = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                draw.rectangle([min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)], fill=c_rand)
                
        img.save(OUTPUT_DIR / f"pattern_{i:04d}_{pattern_type}.jpg", format="JPEG", quality=90)


def generate_natural_non_infrastructure(count=80):
    resolutions = [(320, 320), (480, 480), (640, 480)]
    for i in range(count):
        res = random.choice(resolutions)
        w, h = res
        category = random.choice(["sky_clouds", "forest_foliage", "indoor_room", "abstract_art", "food_dish"])
        
        img = Image.new("RGB", (w, h))
        draw = ImageDraw.Draw(img)
        
        if category == "sky_clouds":
            # Blue gradient with white cloud blobs
            for y in range(h):
                ratio = y / h
                draw.line([(0, y), (w, y)], fill=(int(100 + 80 * ratio), int(160 + 70 * ratio), int(240 + 15 * ratio)))
            for _ in range(random.randint(5, 15)):
                cx = random.randint(0, w)
                cy = random.randint(20, h - 50)
                rx, ry = random.randint(40, 100), random.randint(20, 40)
                draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(255, 255, 255, 180))
            img = img.filter(ImageFilter.GaussianBlur(radius=8))
        elif category == "forest_foliage":
            # Green texture
            arr = np.zeros((h, w, 3), dtype=np.uint8)
            arr[:, :, 0] = np.random.randint(20, 80, (h, w))
            arr[:, :, 1] = np.random.randint(100, 220, (h, w))
            arr[:, :, 2] = np.random.randint(20, 60, (h, w))
            img = Image.fromarray(arr).filter(ImageFilter.GaussianBlur(radius=random.randint(4, 10)))
        elif category == "indoor_room":
            # Wall, floor, and furniture rectangles
            draw.rectangle([0, 0, w, int(h * 0.65)], fill=(220, 215, 200)) # wall
            draw.rectangle([0, int(h * 0.65), w, h], fill=(130, 80, 50))    # floor
            draw.rectangle([w // 4, int(h * 0.4), 3 * w // 4, int(h * 0.85)], fill=(60, 60, 80)) # sofa
        elif category == "food_dish":
            # Plate with food shapes
            draw.rectangle([0, 0, w, h], fill=(230, 220, 200)) # table
            draw.ellipse([w // 8, h // 8, 7 * w // 8, 7 * h // 8], fill=(255, 255, 255), outline=(200, 200, 200))
            for _ in range(15):
                fx, fy = random.randint(w // 4, 3 * w // 4), random.randint(h // 4, 3 * h // 4)
                fr = random.randint(15, 35)
                draw.ellipse([fx - fr, fy - fr, fx + fr, fy + fr], fill=(random.randint(150, 255), random.randint(50, 180), random.randint(20, 80)))
        else: # abstract_art
            for _ in range(random.randint(15, 30)):
                x1, y1 = random.randint(0, w), random.randint(0, h)
                x2, y2 = random.randint(0, w), random.randint(0, h)
                draw.line([(x1, y1), (x2, y2)], fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)), width=random.randint(5, 25))
            img = img.filter(ImageFilter.GaussianBlur(radius=random.randint(2, 6)))
            
        img.save(OUTPUT_DIR / f"nature_{i:04d}_{category}.jpg", format="JPEG", quality=90)


if __name__ == "__main__":
    print(f"Generating negative / OOD samples into {OUTPUT_DIR}...")
    generate_solid_colors(50)
    generate_gradients(50)
    generate_noise(60)
    generate_documents_and_text(50)
    generate_geometric_patterns(60)
    generate_natural_non_infrastructure(80)
    
    total = len(list(OUTPUT_DIR.glob("*.jpg")))
    print(f"Successfully created {total} negative images in {OUTPUT_DIR}!")
