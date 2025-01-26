from bs4 import BeautifulSoup, Tag, NavigableString
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from .bootstrap_to_figma_resolver import resolve_bootstrap_styles
from .tailwind_to_figma_resolver import resolve_tailwind_styles
import re
import cssutils
import requests
import os
import json
from flask import Flask, request, jsonify # Enable CORS for all routes


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
        self.font_size_regex = re.compile(r'^text-(xs|sm|base|lg|xl|2xl|3xl|4xl|5xl|6xl)$')
        self.dimension_regex = re.compile(r'^([wh])-(\d+)$')

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

    def _process_image_dimensions(self, html_node: HTMLNode):
        """
        Process dimension-related classes for both Tailwind and Bootstrap.
        Handles classes like:
        - Tailwind: w-24, h-40, w-full, h-screen
        - Bootstrap: w-25, h-50, w-100, h-100
        """
        if html_node.tag != 'img':
            return  # Only process dimensions for image nodes

        # Mapping for special dimension classes (Tailwind and Bootstrap)
        dimension_classes = {
            # Tailwind
            'w-full': '100%',
            'w-screen': '100vw',
            'h-full': '100%',
            'h-screen': '100vh',
            # Bootstrap
            'w-100': '100%',
            'h-100': '100%',
        }

        # Process numeric width/height classes
        for cls in html_node.classes:
            if cls.startswith(('w-', 'h-')):
                try:
                    # Extract the numeric value from the class
                    value = int(cls.split('-')[1])
                    # Determine the framework and convert to pixels
                    if self.framework == 'tailwind':
                        # Tailwind: 1 unit = 4px
                        pixels = value * 4
                    elif self.framework == 'bootstrap':
                        # Bootstrap: w-25 = 25%, w-50 = 50%, etc.
                        pixels = f"{value}%"
                    else:
                        # Default to Tailwind behavior if framework is not detected
                        pixels = value * 4

                    # Set the dimension in figma_styles
                    if cls.startswith('w-'):
                        html_node.figma_styles['width'] = pixels
                    elif cls.startswith('h-'):
                        html_node.figma_styles['height'] = pixels
                except (IndexError, ValueError):
                    # Skip invalid or non-numeric classes (e.g., w-auto)
                    continue

        # Handle special classes (e.g., w-full, w-100)
        for cls in html_node.classes:
            if cls in dimension_classes:
                if cls.startswith('w-'):
                    html_node.figma_styles['width'] = dimension_classes[cls]
                elif cls.startswith('h-'):
                    html_node.figma_styles['height'] = dimension_classes[cls]

    def _parse_node(self, node: Tag) -> HTMLNode:
        html_node = HTMLNode(
            tag=node.name,
            classes=node.get('class', []),
            attributes=self._get_attributes(node),
            framework=self.framework
        )

        # Handle text content
        if node.string and node.string.strip():
            html_node.text = node.string.strip()

        # Handle images
        if node.name == 'img':
            self._process_image_node(html_node, node)

        # Handle inline styles
        if 'style' in node.attrs:
            parsed_styles = self._parse_inline_styles(node['style'])
            html_node.styles.update(parsed_styles)
            self._apply_font_styles(html_node, parsed_styles)
            self._apply_color_styles(html_node, parsed_styles)

        self._process_text_color_classes(html_node)
        self._process_image_dimensions(html_node)

        # Resolve framework-specific styles
        if self.framework == 'bootstrap':
            html_node.figma_styles = resolve_bootstrap_styles(html_node.classes)
        elif self.framework == 'tailwind':
            html_node.figma_styles = resolve_tailwind_styles(html_node.classes)

        # Additional font style handling
        self._process_font_classes(html_node)
        self._process_dimension_classes(html_node)

        # Process child nodes
        for child in node.children:
            if isinstance(child, Tag):
                html_node.children.append(self._parse_node(child))
            elif isinstance(child, NavigableString) and child.strip():
                html_node.text = child.strip()

        return html_node

    def _process_image_node(self, html_node: HTMLNode, node: Tag):
        # Handle image source
        if 'src' in node.attrs:
            html_node.attributes['src'] = node['src']
        
        # Handle image dimensions
        html_node.figma_styles.update({
            'constraints': {'horizontal': 'SCALE', 'vertical': 'SCALE'},
            'layoutMode': 'NONE'
        })

    def _process_font_classes(self, html_node: HTMLNode):
        # Handle font-related classes
        font_styles = {}
        for cls in html_node.classes:
            # Font weight
            if cls.startswith('font-'):
                weight = cls.split('-')[-1]
                font_styles['fontWeight'] = {
                    'light': 300,
                    'normal': 400,
                    'medium': 500,
                    'semibold': 600,
                    'bold': 700
                }.get(weight, 400)
            
            # Font size
            size_match = self.font_size_regex.match(cls)
            if size_match:
                sizes = {
                    'xs': 12, 'sm': 14, 'base': 16, 'lg': 18,
                    'xl': 20, '2xl': 24, '3xl': 30, '4xl': 36,
                    '5xl': 48, '6xl': 60
                }
                font_styles['fontSize'] = sizes.get(size_match.group(1), 16)
            
            # Text alignment
            if cls in ['text-left', 'text-center', 'text-right', 'text-justify']:
                font_styles['textAlign'] = cls.split('-')[-1].upper()

        html_node.figma_styles.update(font_styles)

    def _process_dimension_classes(self, html_node: HTMLNode):
        # Handle width/height classes
        dimensions = {'w': 'width', 'h': 'height'}
        for cls in html_node.classes:
            match = self.dimension_regex.match(cls)
            if match:
                prop = dimensions[match.group(1)]
                value = int(match.group(2)) * 4  # Convert tailwind units to pixels (1 = 4px)
                html_node.figma_styles[prop] = value

    def _apply_font_styles(self, html_node: HTMLNode, styles: dict):
        # Map CSS font properties to Figma properties
        font_mapping = {
            'font-size': ('fontSize', lambda v: int(float(v.replace('px', '')))),
            'font-weight': ('fontWeight', lambda v: int(v)),
            'text-align': ('textAlign', lambda v: v.upper()),
            'line-height': ('lineHeight', lambda v: {'unit': 'PIXELS', 'value': int(float(v.replace('px', '')))})
        }

        for css_prop, (figma_prop, converter) in font_mapping.items():
            if css_prop in styles:
                try:
                    html_node.figma_styles[figma_prop] = converter(styles[css_prop])
                except Exception as e:
                    print(f"Error converting {css_prop}: {e}")

    def _apply_color_styles(self, html_node: HTMLNode, styles: dict):
        # Handle text and background colors
        if 'color' in styles:
            html_node.figma_styles.setdefault('fills', []).append({
                'type': 'SOLID',
                'color': self._normalize_color(styles['color'])
            })
        
        if 'background-color' in styles:
            html_node.figma_styles.setdefault('background', []).append({
                'type': 'SOLID',
                'color': self._normalize_color(styles['background-color'])
            })

    def _parse_inline_styles(self, style_str: str) -> Dict[str, str]:
        """Parse inline CSS styles into a dictionary"""
        sheet = cssutils.parseStyle(style_str)
        return {prop.name: prop.value for prop in sheet}

    def _process_text_color_classes(self, html_node: HTMLNode):
        color_mapping = {
            'text-textPrimary': {'r': 0.1, 'g': 0.1, 'b': 0.1},
            'text-textSecondary': {'r': 0.4, 'g': 0.4, 'b': 0.4},
            'text-primary': {'r': 0, 'g': 0.47, 'b': 1},  # Example primary color
            'text-warning': {'r': 1, 'g': 0.8, 'b': 0}    # Example warning color
        }
        
        for cls in html_node.classes:
            if cls in color_mapping:
                html_node.figma_styles.setdefault('fills', []).append({
                    'type': 'SOLID',
                    'color': color_mapping[cls]
                })

    def _process_image_node(self, html_node: HTMLNode, node: Tag):
        # Handle image source
        if 'src' in node.attrs:
            html_node.attributes['src'] = node['src']
            html_node.figma_styles['imageHash'] = self._get_image_hash(node['src'])
        
        # Handle image dimensions from classes
        dimensions = {
            'w-full': '100%',
            'h-40': 160,  # 40 * 4 = 160px
            'w-24': 96,   # 24 * 4 = 96px
            'h-24': 96
        }
    
        for cls in html_node.classes:
            if cls in dimensions:
                prop = 'width' if cls.startswith('w-') else 'height'
                html_node.figma_styles[prop] = dimensions[cls]
        
        # Default constraints
        html_node.figma_styles.update({
            'constraints': {'horizontal': 'SCALE', 'vertical': 'SCALE'},
            'layoutMode': 'NONE'
        })

    def _get_image_hash(self, url: str) -> str:
        # Implement actual image fetching and hashing logic
        return f"image-{hash(url)}"  # Simplified example

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


# @app.route('/getDesignSpecs', methods=['POST'])
# def get_design_specs():
#     try:
#         data = request.get_json()
        
#         if 'url' in data:
#             # Handle URL input with headers
#             headers = {
#                 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
#             }
#             response = requests.get(data['url'], headers=headers)
#             if response.status_code != 200:
#                 return jsonify({'error': f'Failed to fetch URL. Status code: {response.status_code}'}), response.status_code
#             html = response.text
#         elif 'html' in data:
#             html = data['html']
#         else:
#             return jsonify({'error': 'Either URL or HTML content must be provided'}), 400
            
#         # Parse HTML
#         parser = HTMLParser()
#         parsed = parser.parse(html)
        
#         # Convert to dictionary for JSON response
#         def node_to_dict(node: HTMLNode) -> dict:
#             return {
#                 "tag": node.tag,
#                 "classes": node.classes,
#                 "text": node.text,
#                 "attributes": node.attributes,
#                 "figma_styles": node.figma_styles,
#                 "children": [node_to_dict(child) for child in node.children]
#             }
        
#         design_data = node_to_dict(parsed)
        
#         # For debug purposes - write to file
#         # Comment out or remove in production
#         os.makedirs('output_files', exist_ok=True)
#         with open('output_files/design_specs.json', 'w') as f:
#             json.dump(design_data, f, indent=2)
            
#         return jsonify(design_data)
        
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# if __name__ == '__main__':
#     app.run(debug=True, port=5000)

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

