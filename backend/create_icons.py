import os
from PIL import Image

def generate_icons():
    workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    icon_source = os.path.join(workspace_dir, "design", "icon.jpg")
    icons_dir = os.path.join(workspace_dir, "extension", "icons")
    
    os.makedirs(icons_dir, exist_ok=True)
    
    if not os.path.exists(icon_source):
        print(f"Source icon not found at {icon_source}, creating placeholder colored squares.")
        # Create solid color placeholder if source JPEG is missing
        for size in [16, 48, 128]:
            img = Image.new("RGBA", (size, size), color=(74, 144, 226, 255))
            img.save(os.path.join(icons_dir, f"icon{size}.png"))
        return

    # Load source image
    try:
        img = Image.open(icon_source)
        # Crop to square if it's not square
        width, height = img.size
        min_dim = min(width, height)
        left = (width - min_dim) / 2
        top = (height - min_dim) / 2
        right = (width + min_dim) / 2
        bottom = (height + min_dim) / 2
        img_cropped = img.crop((left, top, right, bottom))
        
        # Save resized versions
        for size in [16, 48, 128]:
            resized = img_cropped.resize((size, size), Image.Resampling.LANCZOS)
            resized.save(os.path.join(icons_dir, f"icon{size}.png"))
        print("Extension icons generated successfully from source image!")
    except Exception as e:
        print(f"Error processing source icon: {e}. Falling back to solid placeholders.")
        for size in [16, 48, 128]:
            img = Image.new("RGBA", (size, size), color=(74, 144, 226, 255))
            img.save(os.path.join(icons_dir, f"icon{size}.png"))

if __name__ == "__main__":
    generate_icons()
