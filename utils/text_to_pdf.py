from reportlab.lib.pagesizes import LETTER
from reportlab.pdfbase import canvas

def text_to_pdf(input_path, output_path):
    c = canvas.Canvas(output_path, pagesize=LETTER)
    with open(input_path) as f:
        text = f.read().splitlines()
        
    y =750
    for line in text:
        c.drawString(50,y,line)
        y -= 12
        if y < 50:
            c.showPage()
            y = 750
    c.save()