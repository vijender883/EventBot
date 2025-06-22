# Reference : I wasn't able to test it on my local since GPU RAM is not enough.
# Please find the colab link here : https://colab.research.google.com/drive/16ZHilCbfRyAujb-_fGtbv5A0dLS3RxUi#scrollTo=biXAtKFDXY3L

import pdfplumber
import nltk
from nltk.tokenize import sent_tokenize
from sentence_transformers import SentenceTransformer

nltk.download("punkt")
nltk.download('punkt_tab')

# ✅ Step 1: Extract text from PDF
def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)

pdf_path = "/content/NFL_grocery_data.pdf"  # replace with uploaded file path
pdf_text = extract_text_from_pdf(pdf_path)

# ✅ Step 2: Chunk text by sentences (limit 1000 chars per chunk)
def chunk_text(text, max_chars=1000):
    sentences = sent_tokenize(text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) > max_chars:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk += " " + sentence
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

chunks = chunk_text(pdf_text)
print(chunks)

# ✅ Step 3: Embed with LightOnAI model
model = SentenceTransformer("lightonai/modernbert-embed-large")
prefixed_chunks = [f"search_document: {chunk}" for chunk in chunks]

embeddings = model.encode(
    prefixed_chunks,
    convert_to_tensor=True,
    show_progress_bar=True,
    batch_size=2  # Reduce to fit GPU RAM
)

# pairwise cosine similarity
similarity_matrix = model.similarity(embeddings, embeddings)

print(f"Generated {len(embeddings)} embeddings")
print(f"Similarity matrix shape: {similarity_matrix.shape}")  
