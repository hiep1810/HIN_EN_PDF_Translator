# How to Run PDF Translator Locally

This guide explains how to set up and run the Hindi-English PDF Translator web interface on your local machine.

## Prerequisites

- **Python 3.8+** installed.
- **Tesseract OCR** (Optional, for OCR support):
    - Windows: Install via [UB-Mannheim installer](https://github.com/UB-Mannheim/tesseract/wiki). Add it to your PATH.
    - Linux: `sudo apt install tesseract-ocr tesseract-ocr-hin`
    - macOS: `brew install tesseract tesseract-lang`
- **Ghostscript** (Required by `ocrmypdf` if using OCR functionality).

## Setup

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd HIN_EN_PDF_Translator
    ```

2.  **Create a Virtual Environment**:
    ```bash
    # Windows
    python -m venv .venv
    .venv\Scripts\activate

    # Linux/Mac
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install Python Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *Note: This installs PyMuPDF, Streamlit, googletrans, surya-ocr, openai, deepl, and other utilities.*

4.  **First-Time Setup for AI Models (Surya)**:
    - When you run the "Surya AI (Smart)" layout mode for the first time, it will automatically download necessary model weights (approx 500MB+). Ensure you have an internet connection.

## Running the Web Interface

1.  **Start the Streamlit App**:
    ```bash
    streamlit run app.py
    ```

2.  **Access the UI**:
    - The browser should open automatically to `http://localhost:8501`.
    - If not, copy the URL displayed in the terminal.

## Usage Guide

1.  **Upload PDF**: Drag & Drop your Hindi or English PDF.
2.  **Choose Settings**:
    - **Mode**: Use **Hybrid** or **Block** for best general results. Use **Overlay** if you have a specific JSON overlay map.
    - **Layout Method (Hybrid Only)**: 
        - *Heuristic*: Fast, good for simple documents.
        - *Surya AI*: Slower but significantly smarter at detecting columns and correct reading order.
    - **Translate Direction**: Auto-detects by default.
    - **Provider**: Select generic `Google` (free) or provide keys for `DeepL` / `OpenAI` (higher quality).
3.  **Run**: Click **Run translation**.
4.  **Preview & Download**:
    - Scroll down to see the **Side-by-Side Preview** of pages.
    - Click **Download results (ZIP)** to get the translated PDF (and annotated debug files if enabled).

## Troubleshooting

- **OCR Error**: If you see "ocrmypdf not found", ensure Tesseract and Ghostscript are installed and added to your System PATH, or check "Skip OCR" in the sidebar.
- **Model Download Fail**: If Surya fails to download, try running `pip install surya-ocr` again or check your internet/firewall.
- **Async Errors**: If batch translation fails, try reducing `max_workers` in `textlayer.py` (requires code edit) or switch to a stable provider like Google.
