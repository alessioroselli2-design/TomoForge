from pathlib import Path
import json
import re

import fitz


ROOT = Path("attached_assets")
OUTPUT = Path(".agents/outputs/spell-pdf-previews")
OUTPUT.mkdir(parents=True, exist_ok=True)

records = []
for pdf_path in sorted(ROOT.glob("*.pdf")):
    document = fitz.open(pdf_path)
    pages = []
    for page_number, page in enumerate(document):
        text = page.get_text("text")
        pages.append({
            "page": page_number + 1,
            "characters": len(text),
            "preview": re.sub(r"\s+", " ", text).strip()[:500],
            "images": len(page.get_images(full=True)),
        })
        if page_number == 0:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            pixmap.save(OUTPUT / f"{pdf_path.stem}.page-01.png")

    records.append({
        "filename": pdf_path.name,
        "pages": len(document),
        "metadata": document.metadata,
        "total_characters": sum(page["characters"] for page in pages),
        "pages_detail": pages,
    })
    document.close()

Path(".agents/outputs/spell-pdf-analysis.json").write_text(
    json.dumps(records, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print(json.dumps(records, ensure_ascii=False, indent=2))