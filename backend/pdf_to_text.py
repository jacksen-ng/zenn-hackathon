import pypdfium2 as pdfium

def pdf_to_text(file_bytes, file_name):
    try:
        text = ""  
        pdf = pdfium.PdfDocument(file_bytes)
        for page in pdf:
            textpage = page.get_textpage()
            text += textpage.get_text_range()  
            text += "\n"
        return text.strip()
    except Exception as e:
        return f"Error: {e}"
