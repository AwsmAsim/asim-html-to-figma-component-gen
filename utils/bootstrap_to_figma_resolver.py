from typing import List, Dict

# Style Resolution Matrix for Bootstrap to Figma
BOOTSTRAP_TO_FIGMA = {
    # Layout
    "d-flex": {"layoutMode": "HORIZONTAL", "primaryAxisAlignItems": "MIN", "counterAxisAlignItems": "MIN"},
    "flex-column": {"layoutMode": "VERTICAL", "primaryAxisAlignItems": "MIN", "counterAxisAlignItems": "MIN"},
    "align-items-center": {"counterAxisAlignItems": "CENTER"},
    "justify-content-center": {"primaryAxisAlignItems": "CENTER"},
    "gap-3": {"itemSpacing": 16},  # Bootstrap uses rem units (1rem = 16px)

    # Sizing
    "w-100": {"constraints": {"horizontal": "SCALE", "vertical": "SCALE"}, "minWidth": 0},
    "h-25": {"height": "25%"},  # Percentage-based heights
    "mw-100": {"maxWidth": "100%"},

    # Spacing
    "p-3": {"paddingTop": 16, "paddingBottom": 16, "paddingLeft": 16, "paddingRight": 16},
    "py-2": {"paddingTop": 8, "paddingBottom": 8},
    "px-4": {"paddingLeft": 24, "paddingRight": 24},
    "mb-4": {"marginBottom": 24},

    # Typography
    "fs-4": {"fontSize": 24, "lineHeight": 32},  # Bootstrap's fs-4 = 1.5rem (24px)
    "fs-6": {"fontSize": 16, "lineHeight": 24},  # Bootstrap's fs-6 = 1rem (16px)
    "fw-bold": {"fontWeight": 700},
    "text-white": {"fills": [{"type": "SOLID", "color": {"r": 1, "g": 1, "b": 1}}]},

    # Background
    "bg-primary": {"fills": [{"type": "SOLID", "color": {"r": 0.13, "g": 0.53, "b": 0.96}}]},  # Bootstrap primary color
    "bg-light": {"fills": [{"type": "SOLID", "color": {"r": 0.96, "g": 0.96, "b": 0.96}}]},

    # Borders
    "border": {"strokes": [{"type": "SOLID", "color": {"r": 0.9, "g": 0.9, "b": 0.9}}], "strokeWeight": 1},
    "rounded": {"cornerRadius": 4},
    "rounded-3": {"cornerRadius": 16},  # Bootstrap's rounded-3 = 1rem (16px)

    # Shadows
    "shadow-sm": {"effects": [{"type": "DROP_SHADOW", "color": {"r": 0, "g": 0, "b": 0, "a": 0.1}, "offset": {"x": 0, "y": 1}, "radius": 2}]},

    # Positioning
    "position-absolute": {"positioning": "ABSOLUTE"},
    "top-0": {"y": 0},
    "start-0": {"x": 0},
}

# Function to resolve Bootstrap classes to Figma styles
def resolve_bootstrap_styles(classes: List[str]) -> Dict[str, any]:
    styles = {}
    for cls in classes:
        if cls in BOOTSTRAP_TO_FIGMA:
            styles.update(BOOTSTRAP_TO_FIGMA[cls])
    return styles

# Example usage
if __name__ == "__main__":
    # Example Bootstrap classes from a parsed node
    example_classes = ["d-flex", "align-items-center", "justify-content-center", "p-3", "bg-primary", "rounded"]

    # Resolve styles
    resolved_styles = resolve_bootstrap_styles(example_classes)
    print("Resolved Figma Styles:", resolved_styles)