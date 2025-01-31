# app.py
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from music21 import *
import os
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image
import io
import tempfile
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static')
CORS(app, origins=["https://music-transposer.onrender.com"])

# Configure Tesseract path (Render will install it during build)
TESSERACT_PATH = '/usr/bin/tesseract'
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

def extract_music_from_pdf(pdf_bytes):
    try:
        # Convert PDF to images
        images = convert_from_bytes(pdf_bytes)
        
        # Create temporary directory for intermediate files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Process each page
            for i, image in enumerate(images):
                # Save image temporarily
                image_path = os.path.join(temp_dir, f'page_{i}.png')
                image.save(image_path)
                
                # Use pytesseract to detect musical symbols
                text = pytesseract.image_to_string(
                    Image.open(image_path),
                    config='--psm 6'
                )
                
                # Convert detected symbols to music21 format
                score = converter.parse(text)
                
                return score
    except Exception as e:
        logger.error(f"Error in extract_music_from_pdf: {str(e)}")
        raise

def transpose_score(score, from_key, to_key):
    try:
        # Determine interval for transposition
        from_pitch = pitch.Pitch(from_key)
        to_pitch = pitch.Pitch(to_key)
        interval = interval.Interval(from_pitch, to_pitch)
        
        # Transpose the score
        transposed_score = score.transpose(interval)
        
        return transposed_score
    except Exception as e:
        logger.error(f"Error in transpose_score: {str(e)}")
        raise

@app.route('/')
def serve_frontend():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy'}), 200

@app.route('/transpose', methods=['POST'])
def transpose():
    try:
        # Get file and keys from request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file.filename.endswith('.pdf'):
            return jsonify({'error': 'File must be a PDF'}), 400
        
        from_key = request.form.get('fromKey', 'C')
        to_key = request.form.get('toKey', 'C')
        
        # Read PDF file
        pdf_bytes = file.read()
        
        # Extract music from PDF
        score = extract_music_from_pdf(pdf_bytes)
        
        # Transpose score
        transposed_score = transpose_score(score, from_key, to_key)
        
        # Create temporary file for the output
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            # Export to PDF
            transposed_score.write('pdf', fp=temp_file.name)
            
            # Send the file back to client
            return send_file(
                temp_file.name,
                mimetype='application/pdf',
                as_attachment=True,
                download_name='transposed_score.pdf'
            )
            
    except Exception as e:
        logger.error(f"Error in transpose endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
