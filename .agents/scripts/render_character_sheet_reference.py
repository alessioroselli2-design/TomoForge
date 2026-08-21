from pathlib import Path

import fitz


SOURCE = Path("attached_assets/Scheda_personaggio__1787314961790.pdf")
OUTPUT = Path(".agents/outputs/character-sheet-reference")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    document = fitz.open(SOURCE)
    print(f"pages={document.page_count}")
    for index, page in enumerate(document):
        image = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        destination = OUTPUT / f"page-{index + 1}.png"
        image.save(destination)
        print(f"{destination} size={page.rect.width}x{page.rect.height}")


if __name__ == "__main__":
    main()