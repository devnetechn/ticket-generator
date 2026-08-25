import glob
import os

import img2pdf

PAGES_DIR = os.path.join("output", "pages")
OUT_PDF = os.path.join("output", "tickets.pdf")

pages = sorted(glob.glob(os.path.join(PAGES_DIR, "page_*.png")))
print(f"Found {len(pages)} page images.")

if not pages:
    raise SystemExit("No page images found.")

with open(OUT_PDF, "wb") as f:
    f.write(img2pdf.convert(pages))

size_mb = os.path.getsize(OUT_PDF) / (1024 * 1024)
print(f"Saved {OUT_PDF} ({len(pages)} pages, {size_mb:.1f} MB)")
