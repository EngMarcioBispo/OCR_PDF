import pytesseract
from pdf2image import convert_from_path
from PIL import Image, ImageFilter, ImageEnhance
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.units import inch
import os
import streamlit as st
from io import BytesIO
import re

def preprocess_image(image):
    """
    Aplica pré-processamento na imagem para melhorar os resultados do OCR.

    Args:
        image (PIL.Image): Objeto de imagem.

    Returns:
        PIL.Image: Imagem pré-processada.
    """
    # Converte a imagem para escala de cinza
    gray_image = image.convert('L')

    # Aumenta o contraste
    enhancer = ImageEnhance.Contrast(gray_image)
    enhanced_image = enhancer.enhance(2)

    # Aplica filtro de nitidez
    sharpened_image = enhanced_image.filter(ImageFilter.SHARPEN)

    return sharpened_image

def pdf_to_images(pdf_path):
    """
    Converte um arquivo PDF em uma lista de imagens.

    Args:
        pdf_path (str): Caminho para o arquivo PDF.

    Returns:
        list: Lista de objetos de imagem.
    """
    # Convertendo PDF em lista de imagens
    images = convert_from_path(pdf_path)
    return images

def clean_text(text):
    """
    Limpa o texto para remover caracteres que possam causar problemas no ReportLab,
    mantendo caracteres Unicode como acentos.

    Args:
        text (str): Texto original.

    Returns:
        str: Texto limpo.
    """
    # Remove tags HTML-like e caracteres não desejados
    text = re.sub(r'<[^>]+>', '', text)  # Remove tags HTML-like
    cleaned_text = text.strip()
    return cleaned_text

def extract_text_from_image(image):
    """
    Extrai e limpa o texto de uma imagem usando OCR.

    Args:
        image (PIL.Image): Objeto de imagem.

    Returns:
        str: Texto extraído e limpo da imagem.
    """
    # Pré-processa a imagem antes de aplicar OCR
    preprocessed_image = preprocess_image(image)

    # Extraindo texto da imagem
    custom_config = r'--oem 3 --psm 6'  # Configuração customizada do Tesseract
    text = pytesseract.image_to_string(preprocessed_image, lang='por', config=custom_config)

    # Limpa o texto extraído, remove tags HTML-like
    cleaned_text = clean_text(text)
    
    return cleaned_text

def is_title(line):
    """
    Determina se uma linha de texto é provavelmente um título.

    Args:
        line (str): Linha de texto.

    Returns:
        bool: True se a linha for considerada um título, False caso contrário.
    """
    # Simples heurística: assume que uma linha toda em maiúsculas é um título
    return line.isupper() and len(line.split()) < 10

def escape_paragraph_text(text):
    """
    Remove caracteres não seguros que podem ser interpretados como tags ou causar problemas na formatação do parágrafo.

    Args:
        text (str): Texto original.

    Returns:
        str: Texto sem caracteres problemáticos.
    """
    # Remove tags HTML-like
    text = re.sub(r'<[^>]+>', '', text)
    # Remove qualquer outro caractere não ASCII que possa causar problemas
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    return text

def pdf_to_single_output_pdf(input_pdf_path):
    """
    Converte um arquivo PDF em outro PDF, extraindo textos presentes
    em cada uma das imagens das páginas do PDF e salvando-as em um único PDF,
    tentando preservar a formatação original.

    Args:
        input_pdf_path (str): Caminho para o arquivo PDF a ser processado.

    Returns:
        bytes: O conteúdo do PDF gerado em bytes.
    """
    # Verifica se o PDF existe
    if not os.path.exists(input_pdf_path):
        print(f"O arquivo {input_pdf_path} não existe.")
        return

    # Converta PDF para imagens
    images = pdf_to_images(input_pdf_path)

    # Inicializa PDF para saída em um buffer de bytes
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch,
        topMargin=1.0*inch,    # Maior margem superior
        bottomMargin=0.5*inch
    )
    styles = getSampleStyleSheet()

    # Estilos customizados para texto e títulos
    normal_style = styles['Normal']
    title_style = ParagraphStyle(name='Title', fontSize=14, spaceAfter=12)

    content = []

    # Extrai o texto de cada imagem
    for image in images:
        text = extract_text_from_image(image)
        paragraphs = text.split("\n\n")  # Tentativa de preservar parágrafos

        for paragraph in paragraphs:
            lines = paragraph.split("\n")
            for line in lines:
                line = escape_paragraph_text(line)
                if is_title(line):
                    # Adiciona como título
                    content.append(Paragraph(line, title_style))
                else:
                    # Adiciona como parágrafo normal
                    content.append(Paragraph(line, normal_style))
            content.append(Spacer(1, 0.2 * inch))

        # Adiciona um separador de página para manter as páginas separadas
        content.append(PageBreak())

    # Constrói o PDF com os conteúdos
    doc.build(content)
    buffer.seek(0)

    return buffer.getvalue()

# Streamlit App
st.title("Processador de PDF com OCR")

# Upload do arquivo PDF
uploaded_file = st.file_uploader("Escolha um arquivo PDF", type="pdf")

if uploaded_file is not None:
    # Salva o arquivo carregado temporariamente
    with open("temp.pdf", "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Processa o PDF e gera o novo PDF com o texto extraído
    output_pdf_content = pdf_to_single_output_pdf("temp.pdf")

    # Cria um botão de download para o arquivo PDF resultante
    st.download_button(
        label="Baixar PDF Processado",
        data=output_pdf_content,
        file_name="output.pdf",
        mime="application/pdf"
    )

    # Apaga o arquivo temporário
    os.remove("temp.pdf")