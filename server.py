from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import requests
from utils.html_parser import HTMLParser

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/getDesignSpecs', methods=['POST'])
def get_design_specs():
    try:
        data = request.get_json()
        
        if 'url' in data:
            # Handle URL input with headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(data['url'], headers=headers)
            if response.status_code != 200:
                return jsonify({'error': f'Failed to fetch URL. Status code: {response.status_code}'}), response.status_code
            html = response.text
        elif 'html' in data:
            html = data['html']
        else:
            return jsonify({'error': 'Either URL or HTML content must be provided'}), 400
            
        # Parse HTML
        parser = HTMLParser()
        parsed = parser.parse(html)
        
        # Convert to dictionary for JSON response
        def node_to_dict(node) -> dict:
            return {
                "tag": node.tag,
                "classes": node.classes,
                "text": node.text,
                "attributes": node.attributes,
                "figma_styles": node.figma_styles,
                "children": [node_to_dict(child) for child in node.children]
            }
        
        design_data = node_to_dict(parsed)
        
        # For debug purposes - write to file
        os.makedirs('output_files', exist_ok=True)
        with open('output_files/design_specs.json', 'w') as f:
            json.dump(design_data, f, indent=2)
            
        return jsonify(design_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)