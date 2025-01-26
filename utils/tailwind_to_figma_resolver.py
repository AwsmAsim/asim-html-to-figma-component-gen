from typing import List, Dict

# Style Resolution Matrix for Tailwind to Figma
TAILWIND_TO_FIGMA = {
    # Layout
    "flex": {"layoutMode": "HORIZONTAL", "primaryAxisAlignItems": "MIN", "counterAxisAlignItems": "MIN"},
    "flex-col": {"layoutMode": "VERTICAL", "primaryAxisAlignItems": "MIN", "counterAxisAlignItems": "MIN"},
    "items-center": {"primaryAxisAlignItems": "CENTER", "counterAxisAlignItems": "CENTER"},
    "justify-center": {"primaryAxisAlignItems": "CENTER"},
    "gap-4": {"itemSpacing": 16},  # 1 unit = 4px in Tailwind

    # Sizing
    "w-full": {"constraints": {"horizontal": "SCALE", "vertical": "SCALE"}, "minWidth": 0},
    "h-24": {"height": 96},  # 24 * 4px = 96px
    "w-24": {"width": 96},
    "min-w-[72px]": {"minWidth": 72},

    # Spacing
    "p-4": {"paddingTop": 16, "paddingBottom": 16, "paddingLeft": 16, "paddingRight": 16},
    "py-2": {"paddingTop": 8, "paddingBottom": 8},
    "px-3": {"paddingLeft": 12, "paddingRight": 12},
    "mb-4": {"marginBottom": 16},

    # Typography
    "text-lg": {"fontSize": 18, "lineHeight": 28},
    "text-sm": {"fontSize": 14, "lineHeight": 20},
    "font-semibold": {"fontWeight": 600},
    "text-textPrimary": {"fills": [{"type": "SOLID", "color": {"r": 0.1, "g": 0.1, "b": 0.1}}]},

    # Background
    "bg-surface": {"fills": [{"type": "SOLID", "color": {"r": 1, "g": 1, "b": 1}}]},
    "bg-primary/10": {"fills": [{"type": "SOLID", "color": {"r": 0.9, "g": 0.9, "b": 0.9}, "opacity": 0.1}]},

    # Borders
    "border": {"strokes": [{"type": "SOLID", "color": {"r": 0.9, "g": 0.9, "b": 0.9}}], "strokeWeight": 1},
    "rounded-xl": {"cornerRadius": 12},
    "rounded-lg": {"cornerRadius": 8},

    # Shadows
    "shadow-sm": {"effects": [{"type": "DROP_SHADOW", "color": {"r": 0, "g": 0, "b": 0, "a": 0.1}, "offset": {"x": 0, "y": 1}, "radius": 2}]},

    # Positioning
    "absolute": {"positioning": "ABSOLUTE"},
    "top-3": {"y": 12},
    "left-3": {"x": 12},
}

# Function to resolve Tailwind classes to Figma styles
def resolve_tailwind_styles(classes: List[str]) -> Dict[str, any]:
    styles = {}
    for cls in classes:
        if cls in TAILWIND_TO_FIGMA:
            styles.update(TAILWIND_TO_FIGMA[cls])
    return styles

# Example usage
if __name__ == "__main__":
    # Example Tailwind classes from a parsed node
    example_classes = ["flex", "items-center", "justify-center", "p-4", "bg-surface", "rounded-xl"]
    
    # Resolve styles
    resolved_styles = resolve_tailwind_styles(example_classes)
    print("Resolved Figma Styles:", resolved_styles)