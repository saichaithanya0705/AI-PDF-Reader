from reportlab.pdfgen import canvas

def create_pdf(filename):
    c = canvas.Canvas(filename)
    c.drawString(100, 750, "CONFIDENTIAL DOCUMENT")
    c.drawString(100, 700, "This is a test document for the RAG system.")
    c.drawString(100, 650, "The project identifier is: PROJECT-TEST-ALPHA.")
    c.drawString(100, 600, "This is for verification purposes only.")
    c.save()

if __name__ == "__main__":
    create_pdf("d:\\adobe-hackathon-finale-main\\test_rag.pdf")
    print("PDF created successfully: test_rag.pdf")
