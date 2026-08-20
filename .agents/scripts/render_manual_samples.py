from pathlib import Path
import json
import re

import fitz


INPUTS = [
    Path("attached_assets/Manuale_del_giocatore__1787259882002.pdf"),
    Path("attached_assets/Guida_onnicomprensiva_di_Xanathar__1787259928030.pdf"),
    Path("attached_assets/Calderone-Omnicomprensivo-di-TASHA_1787259976040.pdf"),
]
OUTPUT = Path(".agents/outputs/manual-samples")
OUTPUT.mkdir(parents=True, exist_ok=True)

report = []
for pdf_path in INPUTS:
    document = fitz.open(pdf_path)
    page_indexes = sorted({0, 1, 2, len(document) // 2, len(document) - 1})
    pages = []
    for page_index in page_indexes:
        page = document[page_index]
        pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        output_path = OUTPUT / f"{pdf_path.stem}.page-{page_index + 1:03d}.png"
        pixmap.save(output_path)
        text = re.sub(r"\s+", " ", page.get_text("text")).strip()
        pages.append({
            "page": page_index + 1,
            "image": str(output_path),
            "text_chars": len(text),
            "text_preview": text[:400],
            "image_blocks": len(page.get_images(full=True)),
            "size": [round(page.rect.width), round(page.rect.height)],
        })
    report.append({
        "filename": pdf_path.name,
        "pages": len(document),
        "metadata": document.metadata,
        "samples": pages,
    })
    document.close()

Path(".agents/outputs/manual-sample-report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print(json.dumps(report, ensure_ascii=False, indent=2))