import pymupdf as fitz

def read_resume(path):
    doc = fitz.open(path)
    text = "\n".join(page.get_text() for page in doc)
    if not text.strip():
        raise ValueError("No text found. The PDF may be scanned or image-only.")
    return text

if __name__ == "__main__":
    print(read_resume("resume.pdf")[:500])