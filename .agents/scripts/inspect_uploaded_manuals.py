from pathlib import Path
import fitz

FILES = [
    Path("attached_assets/731764731-D-D-Manual-Del-Jugador-5e_1787286581630.pdf"),
    Path("attached_assets/847921086-Manuale-Dei-Mostri-5e_ok_1787286581630.pdf"),
]
OUTPUT = Path(".agents/outputs/uploaded_manual_previews")
OUTPUT.mkdir(parents=True, exist_ok=True)

for source in FILES:
    document = fitz.open(source)
    lengths = []
    for page in document:
        lengths.append(len(page.get_text("text").strip()))

    print(f"\nfile={source.name}")
    print(f"pages={document.page_count}")
    print(f"text_chars_total={sum(lengths)}")
    print(f"text_pages={sum(length > 0 for length in lengths)}")
    print(f"text_chars_min={min(lengths)}")
    print(f"text_chars_max={max(lengths)}")

    sample_indexes = sorted({
        0,
        1 if document.page_count > 1 else 0,
        2 if document.page_count > 2 else 0,
        document.page_count // 2,
        document.page_count - 1,
    })
    prefix = source.stem[:32]
    for index in sample_indexes:
        page = document[index]
        preview = OUTPUT / f"{prefix}-page-{index + 1:03d}.png"
        page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(preview)
        text = " ".join(page.get_text("text").split())
        print(f"sample_page={index + 1} chars={len(text)} text={text[:160]!r} image={preview}")

    document.close()