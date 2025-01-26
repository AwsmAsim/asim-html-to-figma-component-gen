from bs4 import BeautifulSoup, Tag, NavigableString
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from bootstrap_to_figma_resolver import resolve_bootstrap_styles
from tailwind_to_figma_resolver import resolve_tailwind_styles
import re
import cssutils
import requests
import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


@dataclass
class HTMLNode:
    tag: str
    classes: List[str] = field(default_factory=list)
    children: List['HTMLNode'] = field(default_factory=list)
    text: Optional[str] = None
    attributes: Dict[str, str] = field(default_factory=dict)
    framework: Optional[str] = None
    styles: Dict[str, str] = field(default_factory=dict)
    figma_styles: Dict[str, any] = field(default_factory=dict)  

class HTMLParser:
    def __init__(self):
        self.framework = None
        self.color_regex = re.compile(
            r'^#([a-fA-F0-9]{3,4}|[a-fA-F0-9]{6}|[a-fA-F0-9]{8})$|^rgb(a?)\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)$'
        )

    def parse(self, html: str) -> HTMLNode:
        soup = BeautifulSoup(html, 'html.parser')
        self._detect_framework(soup)
        return self._parse_node(soup.body) if soup.body else HTMLNode(tag='body')

    def _detect_framework(self, soup: BeautifulSoup):
        # Check for Bootstrap
        bootstrap_links = soup.find_all('link', href=lambda x: x and 'bootstrap' in x)
        if bootstrap_links:
            self.framework = 'bootstrap'
            return

        # Check for Tailwind
        tailwind_scripts = soup.find_all('script', src=lambda x: x and 'tailwind' in x)
        tailwind_classes = soup.find_all(class_=lambda x: x and re.match(r'^(bg|text|border)-[a-z]+-\d{3}$', x))
        if tailwind_scripts or tailwind_classes:
            self.framework = 'tailwind'
            return

    def _parse_node(self, node: Tag) -> HTMLNode:
        html_node = HTMLNode(
            tag=node.name,
            classes=node.get('class', []),
            attributes=self._get_attributes(node),
            framework=self.framework
        )

        # Handle inline styles
        if 'style' in node.attrs:
            html_node.styles = self._parse_inline_styles(node['style'])

        # Resolve framework-specific styles
        if self.framework == 'bootstrap':
            html_node.figma_styles = resolve_bootstrap_styles(html_node.classes)
        elif self.framework == 'tailwind':
            html_node.figma_styles = resolve_tailwind_styles(html_node.classes)

        # Process child nodes
        for child in node.children:
            if isinstance(child, Tag):
                html_node.children.append(self._parse_node(child))
            elif isinstance(child, NavigableString) and child.strip():
                html_node.text = child.strip()

        return html_node

    def _get_attributes(self, node: Tag) -> Dict[str, str]:
        return {attr: node[attr] for attr in node.attrs if attr != 'class'}

    def _parse_inline_styles(self, style_str: str) -> Dict[str, str]:
        """Parse inline CSS styles into a dictionary"""
        sheet = cssutils.parseStyle(style_str)
        return {prop.name: prop.value for prop in sheet}

    def _normalize_color(self, color: str) -> Dict[str, float]:
        """Convert CSS color values to RGB(A) format"""
        match = self.color_regex.match(color)
        if not match:
            return {'r': 0, 'g': 0, 'b': 0, 'a': 1}

        if match.group(1):  # Hex color
            hex_color = match.group(1)
            return self._hex_to_rgb(hex_color)
        else:  # RGB(A)
            return self._rgb_str_to_dict(color)

    def _hex_to_rgb(self, hex_color: str) -> Dict[str, float]:
        # Hex conversion logic
        length = len(hex_color)
        if length == 3:
            hex_color = ''.join([c * 2 for c in hex_color])
        elif length == 4:
            hex_color = ''.join([c * 2 for c in hex_color[:3]]) + hex_color[3] * 2

        return {
            'r': int(hex_color[0:2], 16) / 255,
            'g': int(hex_color[2:4], 16) / 255,
            'b': int(hex_color[4:6], 16) / 255,
            'a': int(hex_color[6:8], 16) / 255 if len(hex_color) > 6 else 1
        }

    def _rgb_str_to_dict(self, rgb_str: str) -> Dict[str, float]:
        # RGB/RGBA conversion logic
        parts = [float(p) for p in re.findall(r'[\d.]+', rgb_str)]
        if len(parts) == 3:
            return {'r': parts[0]/255, 'g': parts[1]/255, 'b': parts[2]/255, 'a': 1}
        if len(parts) == 4:
            return {'r': parts[0]/255, 'g': parts[1]/255, 'b': parts[2]/255, 'a': parts[3]}
        return {'r': 0, 'g': 0, 'b': 0, 'a': 1}

def export_to_json(parsed_node: HTMLNode, filename: str = "design_specs.json"):
    def node_to_dict(node: HTMLNode) -> dict:
        return {
            "tag": node.tag,
            "classes": node.classes,
            "text": node.text,
            "attributes": node.attributes,
            "figma_styles": node.figma_styles,
            "children": [node_to_dict(child) for child in node.children]
        }
    
    design_data = node_to_dict(parsed_node)
    with open(f"output_files/{filename}", "w") as f:
        json.dump(design_data, f, indent=2)


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
        def node_to_dict(node: HTMLNode) -> dict:
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
        # Comment out or remove in production
        os.makedirs('output_files', exist_ok=True)
        with open('output_files/design_specs.json', 'w') as f:
            json.dump(design_data, f, indent=2)
            
        return jsonify(design_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

# Usage example
# if __name__ == "__main__":
#     url = "https://cades.dev/api/html/00HuDrGzyQ18MuIfWH50/preview/2_20241129_021609.html"  # Replace with your target URL
#     response = requests.get(url)
#     html = response.text
    
#     parser = HTMLParser()
#     parsed = parser.parse(html)
    
#     # Print the parsed structure
#     def print_node(node: HTMLNode, indent=0, file=None, is_first_call=True):
#         if file is None:
#             # Create output directory if it doesn't exist
#             os.makedirs('output_files', exist_ok=True)
#             # Open file in write mode to clear it
#             file = open('output_files/parsed_html.txt', 'w')
#             should_close = True
#         else:
#             should_close = False
#         file.write('\n')
#         file.write(' ' * indent + f"Tag: {node.tag}\n")
#         file.write(' ' * indent + f"Classes: {node.classes}\n")
#         file.write(' ' * indent + f"Framework: {node.framework}\n")
#         file.write(' ' * indent + f"Attributes: {node.attributes}\n")
#         file.write(' ' * indent + f"Styles: {node.styles}\n")
#         file.write(' ' * indent + f"Figma Styles: {node.figma_styles}")
#         if node.text:
#             file.write(' ' * indent + f"Text: {node.text}\n")
#         for child in node.children:
#             print_node(child, indent + 2, file, False)

#         if should_close:
#             file.close()

#     print_node(parsed)
#     export_to_json(parsed)

