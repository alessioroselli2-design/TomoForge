from pathlib import Path
import fitz

source = Path("attached_assets/724962906-D-D-5e-Manuale-Del-Dungeon-Master_1787282954664.pdf")
output = Path(".agents/outputs/dm_preview")
output.mkdir(parents=True, exist_ok=True)

document = fitz.open(source)
print(f"pages={document.page_count}")
print(f"metadata={document.metadata}")

text_lengths = []
image_pages = 0
for index, page in enumerate(document):
    text = page.get_text("text").strip()
    text_lengths.append(len(text))
    if any(block.get("type") == 1 for block in page.get_text("dict").get("blocks", [])):
        image_pages += 1

print(f"pages_with_images={image_pages}")
print(f"text_chars_total={sum(text_lengths)}")
print(f"text_chars_nonempty={sum(1 for length in text_lengths if length)}")
print(f"text_chars_min={min(text_lengths)}")
print(f"text_chars_max={max(text_lengths)}")

sample_indexes = sorted({0, 1, 2, document.page_count // 2, document.page_count - 3, document.page_count - 2, document.page_count - 1})
for index in sample_indexes:
    page = document[index]
    preview_path = output / f"page-{index + 1:03d}.png"
    page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(preview_path)
    preview_text = page.get_text("text").strip().replace("\n", " ")
    print(f"sample_page={index + 1} chars={len(preview_text)} text={preview_text[:180]!r} image={preview_path}")