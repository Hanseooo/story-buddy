"""Visual pilot fixtures generator for StoryBuddy research annotation pipeline.

Generates 34 distinct 512x512 PNG images (17 pairs: canonical 'a' and scene variation 'b')
using Pillow. Covers PASS cases with realistic variation and FAIL cases targeting the
closed 7-item taxonomy (wrong_colour, wrong_clothing, wrong_body_feature, different_face,
wrong_species, character_absent, wrong_style) plus ambiguous calibration cases.

Invariants:
- 512x512 RGB PNGs.
- Deterministic, reproducible, non-blank visual content.
- Isolated from ground-truth labels and storage paths (pure visual generator).
"""

from dataclasses import dataclass
import io
from typing import Callable
from PIL import Image, ImageDraw


@dataclass(frozen=True)
class PilotFixturePair:
    key: str
    image_a: Image.Image
    image_b: Image.Image
    image_a_bytes: bytes
    image_b_bytes: bytes


def _img_to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _draw_sky_and_ground(draw: ImageDraw.ImageDraw, sky_color=(135, 206, 235), ground_color=(100, 180, 80), horizon=360):
    draw.rectangle([(0, 0), (512, horizon)], fill=sky_color)
    draw.rectangle([(0, horizon), (512, 512)], fill=ground_color)


def _draw_sun(draw: ImageDraw.ImageDraw, x=430, y=80, r=40, color=(255, 220, 50)):
    draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=color)


def _draw_tree(draw: ImageDraw.ImageDraw, x=80, ground_y=380, scale=1.0):
    trunk_w = int(24 * scale)
    trunk_h = int(90 * scale)
    crown_r = int(55 * scale)
    draw.rectangle([(x - trunk_w // 2, ground_y - trunk_h), (x + trunk_w // 2, ground_y)], fill=(120, 70, 30))
    draw.ellipse([(x - crown_r, ground_y - trunk_h - crown_r), (x + crown_r, ground_y - trunk_h + crown_r // 2)], fill=(40, 140, 50))


# ── 1. Puppy (PASS - Pose/angle variation) ───────────────────────────────────

def _draw_puppy(draw: ImageDraw.ImageDraw, cx=256, cy=300, body_color=(218, 165, 32), running=False, tongue=False):
    # Ears
    ear_color = (180, 130, 20)
    if not running:
        # Head
        draw.ellipse([(cx - 70, cy - 80), (cx + 70, cy + 60)], fill=body_color)
        draw.ellipse([(cx - 95, cy - 70), (cx - 50, cy + 20)], fill=ear_color)
        draw.ellipse([(cx + 50, cy - 70), (cx + 95, cy + 20)], fill=ear_color)
        # Eyes
        draw.ellipse([(cx - 35, cy - 20), (cx - 15, cy + 5)], fill=(30, 20, 10))
        draw.ellipse([(cx + 15, cy - 20), (cx + 35, cy + 5)], fill=(30, 20, 10))
        draw.ellipse([(cx - 28, cy - 18), (cx - 20, cy - 8)], fill=(255, 255, 255))
        draw.ellipse([(cx + 22, cy - 18), (cx + 30, cy - 8)], fill=(255, 255, 255))
        # Snout / Nose
        draw.ellipse([(cx - 30, cy + 5), (cx + 30, cy + 45)], fill=(245, 222, 179))
        draw.ellipse([(cx - 14, cy + 10), (cx + 14, cy + 28)], fill=(20, 20, 20))
        # Collar
        draw.rectangle([(cx - 45, cy + 55), (cx + 45, cy + 70)], fill=(220, 30, 30))
        draw.ellipse([(cx - 10, cy + 65), (cx + 10, cy + 85)], fill=(255, 215, 0))
    else:
        # Running body
        draw.ellipse([(cx - 110, cy - 10), (cx + 60, cy + 80)], fill=body_color)
        # Running legs
        draw.polygon([(cx - 90, cy + 50), (cx - 120, cy + 110), (cx - 100, cy + 110)], fill=ear_color)
        draw.polygon([(cx + 30, cy + 50), (cx + 70, cy + 105), (cx + 50, cy + 105)], fill=ear_color)
        # Head (angled)
        draw.ellipse([(cx + 20, cy - 60), (cx + 120, cy + 40)], fill=body_color)
        draw.ellipse([(cx + 10, cy - 70), (cx + 50, cy - 10)], fill=ear_color)
        draw.ellipse([(cx + 70, cy - 70), (cx + 110, cy - 10)], fill=ear_color)
        # Eye
        draw.ellipse([(cx + 70, cy - 20), (cx + 90, cy + 2)], fill=(30, 20, 10))
        draw.ellipse([(cx + 76, cy - 18), (cx + 84, cy - 10)], fill=(255, 255, 255))
        # Snout
        draw.ellipse([(cx + 90, cy - 5), (cx + 135, cy + 30)], fill=(245, 222, 179))
        draw.ellipse([(cx + 120, cy + 0), (cx + 138, cy + 15)], fill=(20, 20, 20))
        if tongue:
            draw.ellipse([(cx + 105, cy + 25), (cx + 125, cy + 50)], fill=(255, 105, 130))
        # Collar
        draw.rectangle([(cx + 25, cy + 25), (cx + 65, cy + 40)], fill=(220, 30, 30))
        draw.ellipse([(cx + 40, cy + 38), (cx + 55, cy + 53)], fill=(255, 215, 0))


def _gen_case_01():
    # Canonical: puppy sitting
    img_a = Image.new("RGB", (512, 512), (180, 225, 250))
    d_a = ImageDraw.Draw(img_a)
    _draw_sky_and_ground(d_a, sky_color=(180, 225, 250), ground_color=(110, 195, 90), horizon=340)
    _draw_puppy(d_a, cx=256, cy=280, running=False)

    # Scene: puppy running in sunny park
    img_b = Image.new("RGB", (512, 512), (140, 210, 245))
    d_b = ImageDraw.Draw(img_b)
    _draw_sky_and_ground(d_b, sky_color=(140, 210, 245), ground_color=(90, 180, 75), horizon=320)
    _draw_sun(d_b, x=420, y=70, r=45)
    _draw_tree(d_b, x=90, ground_y=320, scale=1.1)
    _draw_puppy(d_b, cx=240, cy=270, running=True, tongue=True)

    return img_a, img_b


# ── 2. Robot (PASS - Lighting/Lab variation) ─────────────────────────────────

def _draw_robot(draw: ImageDraw.ImageDraw, cx=256, cy=250, body_color=(70, 140, 210), waving=False):
    # Antenna
    draw.line([(cx, cy - 110), (cx, cy - 70)], fill=(160, 160, 170), width=6)
    draw.ellipse([(cx - 15, cy - 135), (cx + 15, cy - 105)], fill=(50, 230, 80))

    # Head
    draw.rounded_rectangle([(cx - 70, cy - 70), (cx + 70, cy + 20)], radius=20, fill=body_color, outline=(40, 80, 140), width=4)
    # Cyclops eye
    draw.ellipse([(cx - 30, cy - 45), (cx + 30, cy + 5)], fill=(255, 230, 40), outline=(20, 20, 20), width=3)
    draw.ellipse([(cx - 10, cy - 25), (cx + 10, cy - 5)], fill=(20, 20, 20))

    # Torso
    draw.rounded_rectangle([(cx - 85, cy + 30), (cx + 85, cy + 180)], radius=15, fill=body_color, outline=(40, 80, 140), width=4)
    # Chest plate & dials
    draw.rectangle([(cx - 50, cy + 55), (cx + 50, cy + 130)], fill=(200, 205, 215))
    draw.ellipse([(cx - 35, cy + 70), (cx - 15, cy + 90)], fill=(230, 50, 50))
    draw.ellipse([(cx - 5, cy + 70), (cx + 15, cy + 90)], fill=(50, 180, 230))
    draw.ellipse([(cx + 25, cy + 70), (cx + 45, cy + 90)], fill=(230, 200, 50))
    draw.line([(cx - 40, cy + 110), (cx + 40, cy + 110)], fill=(60, 60, 70), width=4)

    # Arms
    if not waving:
        draw.line([(cx - 85, cy + 50), (cx - 120, cy + 120)], fill=(150, 150, 160), width=12)
        draw.line([(cx + 85, cy + 50), (cx + 120, cy + 120)], fill=(150, 150, 160), width=12)
    else:
        draw.line([(cx - 85, cy + 50), (cx - 120, cy + 120)], fill=(150, 150, 160), width=12)
        draw.line([(cx + 85, cy + 50), (cx + 130, cy - 10)], fill=(150, 150, 160), width=12)
        draw.ellipse([(cx + 120, cy - 30), (cx + 150, cy + 0)], fill=(200, 205, 215))


def _gen_case_02():
    # Canonical: clean neutral background
    img_a = Image.new("RGB", (512, 512), (230, 235, 240))
    d_a = ImageDraw.Draw(img_a)
    d_a.rectangle([(0, 400), (512, 512)], fill=(200, 205, 210))
    _draw_robot(d_a, cx=256, cy=240, waving=False)

    # Scene: dark lab at night with stars through window
    img_b = Image.new("RGB", (512, 512), (25, 30, 55))
    d_b = ImageDraw.Draw(img_b)
    # Window with stars
    d_b.rectangle([(30, 30), (180, 180)], fill=(10, 15, 35), outline=(90, 100, 130), width=4)
    for sx, sy in [(50, 50), (120, 70), (80, 130), (150, 120)]:
        d_b.ellipse([(sx - 3, sy - 3), (sx + 3, sy + 3)], fill=(255, 255, 200))
    d_b.rectangle([(0, 420), (512, 512)], fill=(45, 50, 75))
    _draw_robot(d_b, cx=270, cy=250, body_color=(60, 125, 190), waving=True)

    return img_a, img_b


# ── 3. Dragon (PASS - Action/sitting eating) ──────────────────────────────────

def _draw_dragon(draw: ImageDraw.ImageDraw, cx=256, cy=260, dragon_color=(35, 175, 95), sitting=False):
    # Wings
    draw.polygon([(cx - 70, cy - 20), (cx - 140, cy - 90), (cx - 100, cy + 20)], fill=(240, 140, 40))
    draw.polygon([(cx + 70, cy - 20), (cx + 140, cy - 90), (cx + 100, cy + 20)], fill=(240, 140, 40))

    # Horns
    draw.polygon([(cx - 40, cy - 80), (cx - 60, cy - 130), (cx - 25, cy - 80)], fill=(255, 215, 0))
    draw.polygon([(cx + 40, cy - 80), (cx + 60, cy - 130), (cx + 25, cy - 80)], fill=(255, 215, 0))

    # Head
    draw.ellipse([(cx - 60, cy - 90), (cx + 60, cy + 10)], fill=dragon_color)
    # Eyes
    draw.ellipse([(cx - 35, cy - 55), (cx - 10, cy - 25)], fill=(255, 255, 255))
    draw.ellipse([(cx + 10, cy - 55), (cx + 35, cy - 25)], fill=(255, 255, 255))
    draw.ellipse([(cx - 25, cy - 50), (cx - 15, cy - 30)], fill=(20, 20, 20))
    draw.ellipse([(cx + 15, cy - 50), (cx + 25, cy - 30)], fill=(20, 20, 20))
    # Snout
    draw.ellipse([(cx - 30, cy - 25), (cx + 30, cy + 10)], fill=dragon_color)
    draw.ellipse([(cx - 12, cy - 15), (cx - 6, cy - 5)], fill=(20, 80, 40))
    draw.ellipse([(cx + 6, cy - 15), (cx + 12, cy - 5)], fill=(20, 80, 40))

    # Body
    if not sitting:
        draw.ellipse([(cx - 65, cy - 10), (cx + 65, cy + 160)], fill=dragon_color)
        # Belly scales
        draw.ellipse([(cx - 35, cy + 20), (cx + 35, cy + 140)], fill=(175, 90, 210))
    else:
        draw.ellipse([(cx - 75, cy + 10), (cx + 75, cy + 150)], fill=dragon_color)
        draw.ellipse([(cx - 45, cy + 30), (cx + 45, cy + 140)], fill=(175, 90, 210))
        # Apple in hands
        draw.ellipse([(cx - 15, cy + 60), (cx + 25, cy + 100)], fill=(225, 30, 30))
        draw.line([(cx + 5, cy + 60), (cx + 10, cy + 45)], fill=(100, 60, 20), width=3)
        draw.ellipse([(cx + 8, cy + 45), (cx + 20, cy + 55)], fill=(50, 180, 50))


def _gen_case_03():
    img_a = Image.new("RGB", (512, 512), (245, 240, 230))
    d_a = ImageDraw.Draw(img_a)
    _draw_sky_and_ground(d_a, sky_color=(210, 235, 250), ground_color=(160, 210, 130), horizon=380)
    _draw_dragon(d_a, cx=256, cy=240, sitting=False)

    img_b = Image.new("RGB", (512, 512), (230, 245, 235))
    d_b = ImageDraw.Draw(img_b)
    _draw_sky_and_ground(d_b, sky_color=(200, 230, 240), ground_color=(140, 200, 120), horizon=360)
    _draw_tree(d_b, x=430, ground_y=360, scale=0.9)
    _draw_dragon(d_b, cx=230, cy=250, sitting=True)

    return img_a, img_b


# ── 4. Fox (FAIL - wrong_colour: orange vs purple) ───────────────────────────

def _draw_fox(draw: ImageDraw.ImageDraw, cx=256, cy=260, fur_color=(235, 100, 25)):
    # Tail
    draw.ellipse([(cx + 40, cy + 40), (cx + 140, cy + 160)], fill=fur_color)
    draw.ellipse([(cx + 100, cy + 110), (cx + 150, cy + 170)], fill=(250, 250, 250))

    # Body
    draw.ellipse([(cx - 60, cy + 20), (cx + 60, cy + 170)], fill=fur_color)
    draw.ellipse([(cx - 30, cy + 40), (cx + 30, cy + 150)], fill=(250, 250, 250))

    # Ears
    draw.polygon([(cx - 65, cy - 30), (cx - 75, cy - 120), (cx - 20, cy - 50)], fill=fur_color)
    draw.polygon([(cx - 60, cy - 70), (cx - 75, cy - 120), (cx - 40, cy - 65)], fill=(30, 30, 30))
    draw.polygon([(cx + 65, cy - 30), (cx + 75, cy - 120), (cx + 20, cy - 50)], fill=fur_color)
    draw.polygon([(cx + 60, cy - 70), (cx + 75, cy - 120), (cx + 40, cy - 65)], fill=(30, 30, 30))

    # Head
    draw.polygon([(cx - 75, cy - 30), (cx + 75, cy - 30), (cx, cy + 60)], fill=fur_color)
    # White cheeks
    draw.polygon([(cx - 75, cy - 30), (cx - 20, cy + 10), (cx, cy + 60)], fill=(250, 250, 250))
    draw.polygon([(cx + 75, cy - 30), (cx + 20, cy + 10), (cx, cy + 60)], fill=(250, 250, 250))

    # Eyes & Nose
    draw.ellipse([(cx - 40, cy - 15), (cx - 20, cy + 0)], fill=(30, 20, 15))
    draw.ellipse([(cx + 20, cy - 15), (cx + 40, cy + 0)], fill=(30, 20, 15))
    draw.ellipse([(cx - 12, cy + 45), (cx + 12, cy + 65)], fill=(20, 20, 20))


def _gen_case_04():
    # Canonical: bright orange fox
    img_a = Image.new("RGB", (512, 512), (240, 245, 250))
    d_a = ImageDraw.Draw(img_a)
    _draw_sky_and_ground(d_a, sky_color=(210, 235, 245), ground_color=(150, 200, 140), horizon=370)
    _draw_fox(d_a, cx=256, cy=250, fur_color=(235, 100, 25))

    # Scene: neon purple fox (wrong_colour)
    img_b = Image.new("RGB", (512, 512), (240, 245, 250))
    d_b = ImageDraw.Draw(img_b)
    _draw_sky_and_ground(d_b, sky_color=(210, 235, 245), ground_color=(150, 200, 140), horizon=370)
    _draw_fox(d_b, cx=256, cy=250, fur_color=(165, 45, 220))

    return img_a, img_b


# ── 5. Bird (FAIL - wrong_colour: red vs green) ──────────────────────────────

def _draw_bird(draw: ImageDraw.ImageDraw, cx=256, cy=260, feather_color=(225, 40, 40)):
    # Branch
    draw.line([(0, 380), (512, 380)], fill=(110, 70, 30), width=18)
    # Feet
    draw.line([(cx - 20, 350), (cx - 20, 380)], fill=(240, 170, 30), width=6)
    draw.line([(cx + 20, 350), (cx + 20, 380)], fill=(240, 170, 30), width=6)

    # Body
    draw.ellipse([(cx - 75, cy - 60), (cx + 75, cy + 90)], fill=feather_color)
    # Wing
    draw.ellipse([(cx - 65, cy - 20), (cx - 10, cy + 70)], fill=(int(feather_color[0] * 0.75), int(feather_color[1] * 0.75), int(feather_color[2] * 0.75)))

    # Sunglasses
    draw.rectangle([(cx - 45, cy - 25), (cx - 5, cy - 5)], fill=(20, 20, 20))
    draw.rectangle([(cx + 5, cy - 25), (cx + 45, cy - 5)], fill=(20, 20, 20))
    draw.line([(cx - 5, cy - 15), (cx + 5, cy - 15)], fill=(20, 20, 20), width=4)

    # Beak
    draw.polygon([(cx - 15, cy + 5), (cx + 15, cy + 5), (cx, cy + 30)], fill=(255, 195, 0))


def _gen_case_05():
    # Canonical: red bird with sunglasses
    img_a = Image.new("RGB", (512, 512), (235, 245, 255))
    d_a = ImageDraw.Draw(img_a)
    _draw_bird(d_a, cx=256, cy=260, feather_color=(225, 40, 40))

    # Scene: emerald green bird with sunglasses (wrong_colour)
    img_b = Image.new("RGB", (512, 512), (235, 245, 255))
    d_b = ImageDraw.Draw(img_b)
    _draw_bird(d_b, cx=256, cy=260, feather_color=(35, 185, 80))

    return img_a, img_b


# ── 6. Bear (FAIL - wrong_clothing: sailor suit vs astronaut) ────────────────

def _draw_bear_head(draw: ImageDraw.ImageDraw, cx=256, cy=200):
    bear_brown = (145, 90, 50)
    # Ears
    draw.ellipse([(cx - 75, cy - 90), (cx - 25, cy - 40)], fill=bear_brown)
    draw.ellipse([(cx + 25, cy - 90), (cx + 75, cy - 40)], fill=bear_brown)
    draw.ellipse([(cx - 65, cy - 80), (cx - 35, cy - 50)], fill=(200, 150, 110))
    draw.ellipse([(cx + 35, cy - 80), (cx + 65, cy - 50)], fill=(200, 150, 110))
    # Head
    draw.ellipse([(cx - 70, cy - 70), (cx + 70, cy + 40)], fill=bear_brown)
    # Eyes
    draw.ellipse([(cx - 35, cy - 30), (cx - 20, cy - 15)], fill=(20, 20, 20))
    draw.ellipse([(cx + 20, cy - 30), (cx + 35, cy - 15)], fill=(20, 20, 20))
    # Muzzle
    draw.ellipse([(cx - 30, cy - 10), (cx + 30, cy + 30)], fill=(215, 175, 135))
    draw.ellipse([(cx - 15, cy - 5), (cx + 15, cy + 15)], fill=(30, 20, 20))


def _gen_case_06():
    # Canonical: bear in sailor suit
    img_a = Image.new("RGB", (512, 512), (245, 245, 245))
    d_a = ImageDraw.Draw(img_a)
    _draw_bear_head(d_a, cx=256, cy=190)
    # Sailor hat
    d_a.ellipse([(256 - 50, 190 - 95), (256 + 50, 190 - 70)], fill=(255, 255, 255), outline=(20, 40, 120), width=3)
    d_a.rectangle([(256 - 40, 190 - 85), (256 + 40, 190 - 75)], fill=(20, 40, 120))
    # Striped shirt
    d_a.rounded_rectangle([(256 - 75, 240), (256 + 75, 420)], radius=20, fill=(255, 255, 255), outline=(20, 40, 120), width=4)
    for sy in range(270, 410, 30):
        d_a.line([(256 - 70, sy), (256 + 70, sy)], fill=(20, 40, 120), width=10)

    # Scene: bear in astronaut suit (wrong_clothing)
    img_b = Image.new("RGB", (512, 512), (20, 25, 45))
    d_b = ImageDraw.Draw(img_b)
    # Helmet glass bubble behind and over head
    d_b.ellipse([(256 - 105, 90), (256 + 105, 290)], fill=(80, 140, 200, 100), outline=(220, 220, 230), width=8)
    _draw_bear_head(d_b, cx=256, cy=190)
    # Astronaut suit
    d_b.rounded_rectangle([(256 - 90, 260), (256 + 90, 450)], radius=25, fill=(230, 235, 245), outline=(100, 110, 130), width=5)
    # NASA chest badge
    d_b.ellipse([(256 - 35, 300), (256 + 5, 340)], fill=(30, 60, 180))
    d_b.line([(256 - 40, 325), (256 + 10, 315)], fill=(230, 40, 40), width=4)

    return img_a, img_b


# ── 7. Duck (FAIL - wrong_clothing: raincoat vs cape/crown) ──────────────────

def _draw_duck_head(draw: ImageDraw.ImageDraw, cx=256, cy=200):
    # Head
    draw.ellipse([(cx - 60, cy - 60), (cx + 60, cy + 40)], fill=(255, 225, 40))
    # Eye
    draw.ellipse([(cx + 10, cy - 25), (cx + 30, cy - 5)], fill=(20, 20, 20))
    draw.ellipse([(cx + 15, cy - 22), (cx + 22, cy - 15)], fill=(255, 255, 255))
    # Bill
    draw.polygon([(cx + 40, cy), (cx + 90, cy + 15), (cx + 40, cy + 30)], fill=(255, 140, 0))


def _gen_case_07():
    # Canonical: duck in yellow raincoat and boots
    img_a = Image.new("RGB", (512, 512), (220, 235, 245))
    d_a = ImageDraw.Draw(img_a)
    _draw_duck_head(d_a, cx=256, cy=180)
    # Yellow raincoat
    d_a.polygon([(256 - 70, 230), (256 + 70, 230), (256 + 90, 380), (256 - 90, 380)], fill=(255, 200, 0), outline=(200, 150, 0), width=4)
    # Buttons
    for by in [260, 300, 340]:
        d_a.ellipse([(256 - 6, by), (256 + 6, by + 12)], fill=(40, 40, 40))

    # Scene: duck in red royal cape and gold crown (wrong_clothing)
    img_b = Image.new("RGB", (512, 512), (245, 240, 230))
    d_b = ImageDraw.Draw(img_b)
    # Crown
    d_b.polygon([(256 - 45, 125), (256 - 45, 95), (256 - 20, 115), (256, 90), (256 + 20, 115), (256 + 45, 95), (256 + 45, 125)], fill=(255, 215, 0), outline=(180, 140, 0), width=3)
    _draw_duck_head(d_b, cx=256, cy=180)
    # Red royal cape with ermine collar
    d_b.polygon([(256 - 70, 230), (256 + 70, 230), (256 + 100, 390), (256 - 100, 390)], fill=(185, 25, 35))
    d_b.rectangle([(256 - 75, 220), (256 + 75, 250)], fill=(250, 250, 250), outline=(50, 50, 50), width=2)
    for ex in range(256 - 60, 256 + 65, 25):
        d_b.ellipse([(ex, 230), (ex + 6, 240)], fill=(20, 20, 20))

    return img_a, img_b


# ── 8. Alien (FAIL - wrong_body_feature: 2 eyes vs 4 eyes) ───────────────────

def _draw_alien_body(draw: ImageDraw.ImageDraw, cx=256, cy=270):
    # Green tunic
    draw.rounded_rectangle([(cx - 70, cy + 30), (cx + 70, cy + 160)], radius=20, fill=(60, 175, 90), outline=(30, 100, 50), width=4)
    draw.ellipse([(cx - 20, cy + 70), (cx + 20, cy + 110)], fill=(255, 215, 0))


def _gen_case_08():
    alien_purple = (155, 75, 205)

    # Canonical: 2 eyes, 2 antennas
    img_a = Image.new("RGB", (512, 512), (235, 240, 250))
    d_a = ImageDraw.Draw(img_a)
    # 2 Antennas
    d_a.line([(256 - 35, 160), (256 - 60, 90)], fill=alien_purple, width=6)
    d_a.line([(256 + 35, 160), (256 + 60, 90)], fill=alien_purple, width=6)
    d_a.ellipse([(256 - 75, 75), (256 - 45, 105)], fill=(255, 105, 180))
    d_a.ellipse([(256 + 45, 75), (256 + 75, 105)], fill=(255, 105, 180))
    # Head & 2 Eyes
    d_a.ellipse([(256 - 80, 140), (256 + 80, 280)], fill=alien_purple)
    d_a.ellipse([(256 - 50, 180), (256 - 15, 225)], fill=(255, 255, 255))
    d_a.ellipse([(256 + 15, 180), (256 + 50, 225)], fill=(255, 255, 255))
    d_a.ellipse([(256 - 38, 195), (256 - 27, 210)], fill=(20, 20, 20))
    d_a.ellipse([(256 + 27, 195), (256 + 38, 210)], fill=(20, 20, 20))
    _draw_alien_body(d_a, cx=256, cy=260)

    # Scene: 4 eyes, 1 antenna (wrong_body_feature)
    img_b = Image.new("RGB", (512, 512), (235, 240, 250))
    d_b = ImageDraw.Draw(img_b)
    # 1 Centered Antenna
    d_b.line([(256, 160), (256, 80)], fill=alien_purple, width=8)
    d_b.ellipse([(256 - 18, 65), (256 + 18, 101)], fill=(255, 105, 180))
    # Head & 4 Eyes
    d_b.ellipse([(256 - 85, 140), (256 + 85, 280)], fill=alien_purple)
    eye_positions = [(256 - 65, 256 - 38), (256 - 32, 256 - 5), (256 + 5, 256 + 32), (256 + 38, 256 + 65)]
    for x1, x2 in eye_positions:
        d_b.ellipse([(x1, 185), (x2, 220)], fill=(255, 255, 255))
        d_b.ellipse([(x1 + 8, 197), (x2 - 8, 209)], fill=(20, 20, 20))
    _draw_alien_body(d_b, cx=256, cy=260)

    return img_a, img_b


# ── 9. Bunny (FAIL - wrong_body_feature: tall ears vs missing ears) ──────────

def _draw_bunny_face_body(draw: ImageDraw.ImageDraw, cx=256, cy=260):
    # Body
    draw.ellipse([(cx - 70, cy + 10), (cx + 70, cy + 160)], fill=(245, 245, 245), outline=(210, 210, 210), width=3)
    # Head
    draw.ellipse([(cx - 60, cy - 70), (cx + 60, cy + 40)], fill=(255, 255, 255), outline=(210, 210, 210), width=3)
    # Eyes
    draw.ellipse([(cx - 35, cy - 25), (cx - 15, cy - 5)], fill=(30, 20, 20))
    draw.ellipse([(cx + 15, cy - 25), (cx + 35, cy - 5)], fill=(30, 20, 20))
    # Nose & mouth
    draw.polygon([(cx - 10, cy + 5), (cx + 10, cy + 5), (cx, cy + 15)], fill=(255, 140, 160))


def _gen_case_09():
    # Canonical: white bunny with tall upright ears and cotton tail
    img_a = Image.new("RGB", (512, 512), (240, 250, 240))
    d_a = ImageDraw.Draw(img_a)
    # Fluffy tail
    d_a.ellipse([(256 + 55, 330), (256 + 105, 380)], fill=(255, 255, 255), outline=(200, 200, 200), width=3)
    # Tall bunny ears
    d_a.ellipse([(256 - 55, 60), (256 - 15, 210)], fill=(255, 255, 255), outline=(210, 210, 210), width=3)
    d_a.ellipse([(256 - 45, 80), (256 - 25, 190)], fill=(255, 180, 195))
    d_a.ellipse([(256 + 15, 60), (256 + 55, 210)], fill=(255, 255, 255), outline=(210, 210, 210), width=3)
    d_a.ellipse([(256 + 25, 80), (256 + 45, 190)], fill=(255, 180, 195))
    _draw_bunny_face_body(d_a, cx=256, cy=260)

    # Scene: bunny with missing ears & replaced by tiny mouse ears, no tail (wrong_body_feature)
    img_b = Image.new("RGB", (512, 512), (240, 250, 240))
    d_b = ImageDraw.Draw(img_b)
    # Tiny round mouse ears
    d_b.ellipse([(256 - 65, 175), (256 - 35, 205)], fill=(220, 220, 220))
    d_b.ellipse([(256 + 35, 175), (256 + 65, 205)], fill=(220, 220, 220))
    _draw_bunny_face_body(d_b, cx=256, cy=260)

    return img_a, img_b


# ── 10. Cat (FAIL - different_face: anime kitten vs grumpy old cat) ───────────

def _gen_case_10():
    # Canonical: cute round kitten with huge anime eyes and smile
    img_a = Image.new("RGB", (512, 512), (250, 240, 245))
    d_a = ImageDraw.Draw(img_a)
    # Ears
    d_a.polygon([(256 - 70, 180), (256 - 90, 90), (256 - 20, 140)], fill=(245, 170, 60))
    d_a.polygon([(256 + 70, 180), (256 + 90, 90), (256 + 20, 140)], fill=(245, 170, 60))
    # Head
    d_a.ellipse([(256 - 80, 130), (256 + 80, 290)], fill=(245, 170, 60))
    # Huge anime eyes
    d_a.ellipse([(256 - 55, 170), (256 - 15, 230)], fill=(30, 120, 220))
    d_a.ellipse([(256 + 15, 170), (256 + 55, 230)], fill=(30, 120, 220))
    d_a.ellipse([(256 - 45, 175), (256 - 25, 200)], fill=(255, 255, 255))
    d_a.ellipse([(256 + 25, 175), (256 + 45, 200)], fill=(255, 255, 255))
    # Tiny nose & happy smile
    d_a.polygon([(256 - 6, 235), (256 + 6, 235), (256, 242)], fill=(255, 130, 150))
    d_a.arc([(256 - 20, 238), (256, 255)], start=0, end=180, fill=(30, 30, 30), width=3)
    d_a.arc([(256, 238), (256 + 20, 255)], start=0, end=180, fill=(30, 30, 30), width=3)

    # Scene: grumpy old cat with narrow slits, mustache, furrowed brow (different_face)
    img_b = Image.new("RGB", (512, 512), (250, 240, 245))
    d_b = ImageDraw.Draw(img_b)
    # Ears
    d_b.polygon([(256 - 70, 180), (256 - 90, 90), (256 - 20, 140)], fill=(245, 170, 60))
    d_b.polygon([(256 + 70, 180), (256 + 90, 90), (256 + 20, 140)], fill=(245, 170, 60))
    # Head
    d_b.ellipse([(256 - 80, 130), (256 + 80, 290)], fill=(245, 170, 60))
    # Furrowed angry brow
    d_b.line([(256 - 55, 175), (256 - 15, 195)], fill=(40, 20, 10), width=5)
    d_b.line([(256 + 55, 175), (256 + 15, 195)], fill=(40, 20, 10), width=5)
    # Narrow eye slits
    d_b.line([(256 - 50, 205), (256 - 15, 205)], fill=(20, 20, 20), width=6)
    d_b.line([(256 + 15, 205), (256 + 50, 205)], fill=(20, 20, 20), width=6)
    # Heavy mustache & frown
    d_b.polygon([(256 - 45, 235), (256, 235), (256 - 35, 265)], fill=(255, 255, 255))
    d_b.polygon([(256 + 45, 235), (256, 235), (256 + 35, 265)], fill=(255, 255, 255))
    d_b.arc([(256 - 20, 255), (256 + 20, 280)], start=180, end=360, fill=(30, 30, 30), width=4)

    return img_a, img_b


# ── 11. Boy (FAIL - different_face: round freckled face vs sharp angular) ────

def _gen_case_11():
    # Canonical: round cheerful freckled boy
    img_a = Image.new("RGB", (512, 512), (235, 245, 255))
    d_a = ImageDraw.Draw(img_a)
    # Shirt
    d_a.rectangle([(256 - 80, 340), (256 + 80, 512)], fill=(40, 130, 220))
    # Round head
    d_a.ellipse([(256 - 75, 150), (256 + 75, 330)], fill=(255, 218, 185))
    # Curly brown hair
    for hx in range(256 - 80, 256 + 90, 20):
        d_a.ellipse([(hx - 20, 120), (hx + 20, 175)], fill=(100, 60, 30))
    # Big round circular eyes
    d_a.ellipse([(256 - 45, 210), (256 - 15, 245)], fill=(50, 35, 20))
    d_a.ellipse([(256 + 15, 210), (256 + 45, 245)], fill=(50, 35, 20))
    # Freckles
    for fx in [256 - 35, 256 - 25, 256 - 15, 256 + 15, 256 + 25, 256 + 35]:
        d_a.ellipse([(fx, 255), (fx + 4, 259)], fill=(180, 110, 60))
    # Smile
    d_a.arc([(256 - 25, 260), (256 + 25, 300)], start=0, end=180, fill=(180, 40, 40), width=4)

    # Scene: sharp angular jaw, narrow eyes, pointed nose (different_face)
    img_b = Image.new("RGB", (512, 512), (235, 245, 255))
    d_b = ImageDraw.Draw(img_b)
    # Shirt
    d_b.rectangle([(256 - 80, 340), (256 + 80, 512)], fill=(40, 130, 220))
    # Angular sharp jaw polygon
    d_b.polygon([(256 - 75, 170), (256 + 75, 170), (256 + 60, 280), (256, 350), (256 - 60, 280)], fill=(255, 218, 185))
    # Hair
    for hx in range(256 - 80, 256 + 90, 20):
        d_b.ellipse([(hx - 20, 120), (hx + 20, 175)], fill=(100, 60, 30))
    # Narrow almond eyes
    d_b.polygon([(256 - 55, 225), (256 - 35, 215), (256 - 15, 225), (256 - 35, 230)], fill=(50, 35, 20))
    d_b.polygon([(256 + 15, 225), (256 + 35, 215), (256 + 55, 225), (256 + 35, 230)], fill=(50, 35, 20))
    # Pointed nose & thin straight lips
    d_b.line([(256, 225), (256, 270), (256 + 10, 270)], fill=(180, 140, 110), width=3)
    d_b.line([(256 - 25, 300), (256 + 25, 300)], fill=(160, 60, 60), width=3)

    return img_a, img_b


# ── 12. Dog vs Bear (FAIL - wrong_species) ────────────────────────────────────

def _gen_case_12():
    # Canonical: golden retriever dog in red polka-dot bandana
    img_a = Image.new("RGB", (512, 512), (230, 240, 230))
    d_a = ImageDraw.Draw(img_a)
    # Dog head & snout
    d_a.ellipse([(256 - 70, 160), (256 + 70, 300)], fill=(225, 180, 65))
    d_a.ellipse([(256 - 95, 170), (256 - 50, 290)], fill=(195, 145, 40))  # Floppy ear
    d_a.ellipse([(256 + 50, 170), (256 + 95, 290)], fill=(195, 145, 40))  # Floppy ear
    d_a.ellipse([(256 - 40, 225), (256 + 40, 295)], fill=(245, 210, 130)) # Snout
    d_a.ellipse([(256 - 18, 235), (256 + 18, 260)], fill=(20, 20, 20))
    d_a.ellipse([(256 - 35, 195), (256 - 15, 215)], fill=(20, 20, 20))
    d_a.ellipse([(256 + 15, 195), (256 + 35, 215)], fill=(20, 20, 20))
    # Red polka-dot bandana
    d_a.polygon([(256 - 65, 295), (256 + 65, 295), (256, 375)], fill=(220, 30, 40))
    for px, py in [(256 - 30, 315), (256, 315), (256 + 30, 315), (256 - 15, 340), (256 + 15, 340)]:
        d_a.ellipse([(px - 4, py - 4), (px + 4, py + 4)], fill=(255, 255, 255))

    # Scene: massive grizzly bear wearing identical red polka-dot bandana (wrong_species)
    img_b = Image.new("RGB", (512, 512), (230, 240, 230))
    d_b = ImageDraw.Draw(img_b)
    # Bear round ears
    d_b.ellipse([(256 - 95, 130), (256 - 45, 180)], fill=(120, 75, 40))
    d_b.ellipse([(256 + 45, 130), (256 + 95, 180)], fill=(120, 75, 40))
    # Bear wide head & dark snout
    d_b.ellipse([(256 - 90, 150), (256 + 90, 310)], fill=(120, 75, 40))
    d_b.ellipse([(256 - 50, 220), (256 + 50, 295)], fill=(175, 125, 80))
    d_b.ellipse([(256 - 22, 230), (256 + 22, 260)], fill=(20, 20, 20))
    d_b.ellipse([(256 - 45, 190), (256 - 25, 210)], fill=(20, 20, 20))
    d_b.ellipse([(256 + 25, 190), (256 + 45, 210)], fill=(20, 20, 20))
    # Same red polka-dot bandana
    d_b.polygon([(256 - 75, 300), (256 + 75, 300), (256, 385)], fill=(220, 30, 40))
    for px, py in [(256 - 35, 320), (256, 320), (256 + 35, 320), (256 - 15, 350), (256 + 15, 350)]:
        d_b.ellipse([(px - 4, py - 4), (px + 4, py + 4)], fill=(255, 255, 255))

    return img_a, img_b


# ── 13. Playroom Girl (FAIL - character_absent: girl present vs empty room) ──

def _draw_playroom_scenery(draw: ImageDraw.ImageDraw):
    # Wall & Floor
    draw.rectangle([(0, 0), (512, 320)], fill=(255, 240, 220))
    draw.rectangle([(0, 320), (512, 512)], fill=(220, 190, 150))
    # Wall poster
    draw.rectangle([(60, 60), (160, 160)], fill=(200, 230, 255), outline=(150, 180, 210), width=4)
    draw.ellipse([(90, 90), (130, 130)], fill=(255, 200, 50))
    # Yellow beanbag chair
    draw.ellipse([(180, 260), (360, 420)], fill=(255, 200, 20), outline=(210, 160, 10), width=4)
    # Colorful building blocks on the floor
    draw.rectangle([(380, 380), (430, 430)], fill=(230, 50, 50))
    draw.rectangle([(400, 340), (440, 380)], fill=(40, 120, 220))
    draw.polygon([(400, 340), (420, 310), (440, 340)], fill=(50, 200, 70))


def _gen_case_13():
    # Canonical: Little girl in pink dress on beanbag
    img_a = Image.new("RGB", (512, 512), (255, 255, 255))
    d_a = ImageDraw.Draw(img_a)
    _draw_playroom_scenery(d_a)
    # Girl sitting on beanbag
    d_a.ellipse([(256 - 35, 170), (256 + 35, 240)], fill=(255, 220, 190)) # Head
    d_a.ellipse([(256 - 45, 160), (256 + 45, 205)], fill=(120, 70, 30))  # Hair
    d_a.polygon([(256 - 30, 160), (256 - 15, 140), (256, 160)], fill=(255, 105, 180)) # Hair bow
    d_a.polygon([(256 - 45, 235), (256 + 45, 235), (256 + 60, 330), (256 - 60, 330)], fill=(255, 105, 180)) # Pink dress

    # Scene: Scenery identical, girl completely absent (character_absent)
    img_b = Image.new("RGB", (512, 512), (255, 255, 255))
    d_b = ImageDraw.Draw(img_b)
    _draw_playroom_scenery(d_b)

    return img_a, img_b


# ── 14. Lion (FAIL - wrong_style: smooth vector vs 8-bit pixel art) ──────────

def _gen_case_14():
    # Canonical: clean smooth vector lion
    img_a = Image.new("RGB", (512, 512), (250, 245, 235))
    d_a = ImageDraw.Draw(img_a)
    # Mane
    d_a.ellipse([(256 - 110, 130), (256 + 110, 350)], fill=(195, 100, 25))
    # Head & ears
    d_a.ellipse([(256 - 75, 160), (256 + 75, 310)], fill=(245, 185, 45))
    d_a.ellipse([(256 - 70, 150), (256 - 35, 185)], fill=(245, 185, 45))
    d_a.ellipse([(256 + 35, 150), (256 + 70, 185)], fill=(245, 185, 45))
    # Eyes & snout
    d_a.ellipse([(256 - 40, 205), (256 - 20, 230)], fill=(30, 20, 10))
    d_a.ellipse([(256 + 20, 205), (256 + 40, 230)], fill=(30, 20, 10))
    d_a.polygon([(256 - 20, 250), (256 + 20, 250), (256, 275)], fill=(120, 50, 20))

    # Scene: 8-bit chunky pixel-art lion (wrong_style)
    # We render on a 32x32 grid and upscale with nearest neighbor
    img_b_small = Image.new("RGB", (32, 32), (250, 245, 235))
    d_bs = ImageDraw.Draw(img_b_small)
    # Mane block
    d_bs.rectangle([(8, 8), (23, 23)], fill=(195, 100, 25))
    # Head block
    d_bs.rectangle([(11, 10), (20, 19)], fill=(245, 185, 45))
    # Ears
    d_bs.point([(10, 9), (21, 9)], fill=(245, 185, 45))
    # Eyes & nose
    d_bs.point([(13, 13), (18, 13)], fill=(30, 20, 10))
    d_bs.point([(15, 16), (16, 16)], fill=(120, 50, 20))
    img_b = img_b_small.resize((512, 512), resample=Image.Resampling.NEAREST)

    return img_a, img_b


# ── 15. Turtle (FAIL - wrong_style: watercolor pastel vs inverted neon sketch)

def _gen_case_15():
    # Canonical: soft pastel sea turtle on ocean background
    img_a = Image.new("RGB", (512, 512), (205, 235, 245))
    d_a = ImageDraw.Draw(img_a)
    # Flippers
    d_a.ellipse([(256 - 120, 200), (256 - 40, 250)], fill=(110, 195, 160))
    d_a.ellipse([(256 + 40, 200), (256 + 120, 250)], fill=(110, 195, 160))
    # Shell
    d_a.ellipse([(256 - 75, 180), (256 + 75, 330)], fill=(75, 165, 130), outline=(50, 130, 100), width=4)
    # Scutes
    for sx in [256 - 30, 256 + 30]:
        d_a.ellipse([(sx - 15, 220), (sx + 15, 250)], fill=(95, 185, 145))
        d_a.ellipse([(sx - 15, 265), (sx + 15, 295)], fill=(95, 185, 145))
    # Head
    d_a.ellipse([(256 - 30, 130), (256 + 30, 190)], fill=(110, 195, 160))
    d_a.ellipse([(256 - 18, 150), (256 - 10, 160)], fill=(20, 40, 30))
    d_a.ellipse([(256 + 10, 150), (256 + 18, 160)], fill=(20, 40, 30))

    # Scene: pitch black neon inverted wireframe chalkboard sketch (wrong_style)
    img_b = Image.new("RGB", (512, 512), (10, 15, 20))
    d_b = ImageDraw.Draw(img_b)
    # Chalk grid marks in background
    for gy in range(80, 480, 80):
        d_b.line([(40, gy), (472, gy)], fill=(25, 40, 50), width=1)
    for gx in range(80, 480, 80):
        d_b.line([(gx, 40), (gx, 472)], fill=(25, 40, 50), width=1)
    # Flippers outline in neon cyan
    d_b.arc([(256 - 120, 200), (256 - 40, 250)], start=0, end=360, fill=(0, 240, 255), width=3)
    d_b.arc([(256 + 40, 200), (256 + 120, 250)], start=0, end=360, fill=(0, 240, 255), width=3)
    # Shell wireframe in neon green and yellow scutes
    d_b.arc([(256 - 75, 180), (256 + 75, 330)], start=0, end=360, fill=(0, 255, 180), width=4)
    d_b.line([(256, 180), (256, 330)], fill=(0, 255, 180), width=2)
    d_b.line([(256 - 75, 255), (256 + 75, 255)], fill=(0, 255, 180), width=2)
    for sx in [256 - 30, 256 + 30]:
        d_b.arc([(sx - 15, 220), (sx + 15, 250)], start=0, end=360, fill=(255, 240, 50), width=2)
        d_b.arc([(sx - 15, 265), (sx + 15, 295)], start=0, end=360, fill=(255, 240, 50), width=2)
    # Head outline in neon pink
    d_b.arc([(256 - 30, 130), (256 + 30, 190)], start=0, end=360, fill=(255, 80, 180), width=3)
    d_b.ellipse([(256 - 16, 153), (256 - 12, 157)], fill=(255, 255, 255))
    d_b.ellipse([(256 + 12, 153), (256 + 16, 157)], fill=(255, 255, 255))

    return img_a, img_b


# ── 16. Penguin (PASS / Ambiguous - Dramatic shadow) ─────────────────────────

def _draw_penguin(draw: ImageDraw.ImageDraw, cx=256, cy=260):
    # Body
    draw.ellipse([(cx - 70, cy - 60), (cx + 70, cy + 130)], fill=(30, 35, 45))
    # White belly
    draw.ellipse([(cx - 45, cy - 30), (cx + 45, cy + 120)], fill=(245, 245, 250))
    # Wings
    draw.ellipse([(cx - 85, cy - 10), (cx - 55, cy + 80)], fill=(30, 35, 45))
    draw.ellipse([(cx + 55, cy - 10), (cx + 85, cy + 80)], fill=(30, 35, 45))
    # Eyes
    draw.ellipse([(cx - 25, cy - 35), (cx - 10, cy - 20)], fill=(20, 20, 20))
    draw.ellipse([(cx + 10, cy - 35), (cx + 25, cy - 20)], fill=(20, 20, 20))
    # Beak
    draw.polygon([(cx - 12, cy - 15), (cx + 12, cy - 15), (cx, cy + 5)], fill=(255, 160, 0))
    # Red scarf
    draw.rounded_rectangle([(cx - 50, cy - 5), (cx + 50, cy + 20)], radius=6, fill=(220, 35, 45))
    draw.rectangle([(cx + 20, cy + 15), (cx + 40, cy + 65)], fill=(220, 35, 45))


def _gen_case_16():
    # Canonical: daylight ice background
    img_a = Image.new("RGB", (512, 512), (210, 235, 250))
    d_a = ImageDraw.Draw(img_a)
    d_a.rectangle([(0, 350), (512, 512)], fill=(240, 248, 255))
    _draw_penguin(d_a, cx=256, cy=260)

    # Scene: nighttime with dramatic warm torchlight from bottom-left
    img_b = Image.new("RGB", (512, 512), (15, 20, 35))
    d_b = ImageDraw.Draw(img_b)
    # Night ice
    d_b.rectangle([(0, 350), (512, 512)], fill=(30, 40, 60))
    # Torch flame on left
    d_b.ellipse([(70, 310), (110, 360)], fill=(255, 140, 20))
    d_b.ellipse([(80, 320), (100, 350)], fill=(255, 230, 80))
    d_b.line([(90, 360), (90, 440)], fill=(120, 70, 30), width=8)
    _draw_penguin(d_b, cx=270, cy=260)
    # Strong shadow overlay on right half of penguin
    d_b.polygon([(270, 190), (360, 190), (360, 400), (270, 400)], fill=(10, 15, 25))

    return img_a, img_b


# ── 17. Squirrel (PASS / Ambiguous - Minor accessory change) ─────────────────

def _draw_squirrel(draw: ImageDraw.ImageDraw, cx=256, cy=260, holding_acorn=True, backpack=True):
    sq_brown = (170, 95, 40)
    # Tail
    draw.arc([(cx + 20, cy - 100), (cx + 150, cy + 100)], start=270, end=90, fill=sq_brown, width=40)
    # Body & Head
    draw.ellipse([(cx - 50, cy + 10), (cx + 50, cy + 140)], fill=sq_brown)
    draw.ellipse([(cx - 40, cy - 60), (cx + 40, cy + 20)], fill=sq_brown)
    # Ear
    draw.polygon([(cx - 30, cy - 50), (cx - 20, cy - 85), (cx - 10, cy - 50)], fill=sq_brown)
    draw.polygon([(cx + 10, cy - 50), (cx + 20, cy - 85), (cx + 30, cy - 50)], fill=sq_brown)
    # Eye & Nose
    draw.ellipse([(cx + 5, cy - 30), (cx + 25, cy - 10)], fill=(20, 20, 20))
    draw.ellipse([(cx + 12, cy - 25), (cx + 18, cy - 19)], fill=(255, 255, 255))
    draw.polygon([(cx + 30, cy - 5), (cx + 45, cy - 5), (cx + 35, cy + 5)], fill=(30, 20, 20))

    # Backpack
    if backpack:
        draw.rounded_rectangle([(cx - 55, cy + 25), (cx - 30, cy + 75)], radius=6, fill=(100, 60, 20))
        draw.line([(cx - 35, cy + 30), (cx - 15, cy + 50)], fill=(60, 35, 10), width=3)

    # Item in hands
    if holding_acorn:
        # Acorn
        draw.ellipse([(cx + 20, cy + 35), (cx + 50, cy + 75)], fill=(120, 65, 20))
        draw.rectangle([(cx + 20, cy + 30), (cx + 50, cy + 45)], fill=(75, 40, 10))
    else:
        # Pinecone
        draw.polygon([(cx + 20, cy + 75), (cx + 50, cy + 75), (cx + 35, cy + 30)], fill=(90, 50, 15))


def _gen_case_17():
    # Canonical: squirrel holding acorn with backpack
    img_a = Image.new("RGB", (512, 512), (245, 240, 230))
    d_a = ImageDraw.Draw(img_a)
    _draw_sky_and_ground(d_a, sky_color=(220, 240, 250), ground_color=(140, 195, 120), horizon=360)
    _draw_squirrel(d_a, cx=256, cy=250, holding_acorn=True, backpack=True)

    # Scene: same squirrel holding pinecone, no backpack (ambiguous / accessory variance)
    img_b = Image.new("RGB", (512, 512), (245, 240, 230))
    d_b = ImageDraw.Draw(img_b)
    _draw_sky_and_ground(d_b, sky_color=(220, 240, 250), ground_color=(140, 195, 120), horizon=360)
    _draw_squirrel(d_b, cx=256, cy=250, holding_acorn=False, backpack=False)

    return img_a, img_b


# ── Registry of Generators ───────────────────────────────────────────────────

GENERATOR_REGISTRY: list[tuple[str, Callable[[], tuple[Image.Image, Image.Image]]]] = [
    ("case_01_puppy_pose", _gen_case_01),
    ("case_02_robot_lighting", _gen_case_02),
    ("case_03_dragon_action", _gen_case_03),
    ("case_04_fox_color", _gen_case_04),
    ("case_05_bird_color", _gen_case_05),
    ("case_06_bear_clothing", _gen_case_06),
    ("case_07_duck_clothing", _gen_case_07),
    ("case_08_alien_body_feature", _gen_case_08),
    ("case_09_bunny_body_feature", _gen_case_09),
    ("case_10_cat_face", _gen_case_10),
    ("case_11_boy_face", _gen_case_11),
    ("case_12_dog_to_bear_species", _gen_case_12),
    ("case_13_girl_absent", _gen_case_13),
    ("case_14_lion_vector_to_pixel_style", _gen_case_14),
    ("case_15_turtle_sketch_style", _gen_case_15),
    ("case_16_penguin_shadow_ambiguous", _gen_case_16),
    ("case_17_squirrel_accessory_ambiguous", _gen_case_17),
]


def generate_pilot_fixtures() -> dict[str, PilotFixturePair]:
    """Generates all 17 visual pilot pairs (34 images)."""
    fixtures: dict[str, PilotFixturePair] = {}
    for key, gen_fn in GENERATOR_REGISTRY:
        img_a, img_b = gen_fn()
        bytes_a = _img_to_png_bytes(img_a)
        bytes_b = _img_to_png_bytes(img_b)
        fixtures[key] = PilotFixturePair(
            key=key,
            image_a=img_a,
            image_b=img_b,
            image_a_bytes=bytes_a,
            image_b_bytes=bytes_b,
        )
    return fixtures


if __name__ == "__main__":
    fixtures = generate_pilot_fixtures()
    print(f"Generated {len(fixtures)} visual pilot fixture pairs ({len(fixtures) * 2} images).")
