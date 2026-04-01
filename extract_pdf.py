import fitz

pdf_path = 'mockup/ilovepdf_merged.pdf'
output_dir = 'mockup/'

doc = fitz.open(pdf_path)
print(f"Total pages: {len(doc)}")

# Extract all pages as images
for i in range(min(10, len(doc))):  # First 10 pages
    page = doc[i]
    mat = fitz.Matrix(2, 2)
    pix = page.get_pixmap(matrix=mat)
    output_path = f"{output_dir}page_{i+1:02d}.png"
    pix.save(output_path)
    print(f"Saved: {output_path}")

doc.close()
print("Done!")
