import re
from PIL import Image

def image_to_ascii(image_path, new_width=45):
    # ASCII characters from darkest to lightest
    ASCII_CHARS = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", ".", " "]
    
    try:
        image = Image.open(image_path)
    except Exception as e:
        print(f"Error opening image: {e}")
        return []
    
    # Resize image. Character height is typically roughly twice the width.
    width, height = image.size
    ratio = height / width / 1.65 # adjustment for font aspect ratio
    new_height = int(new_width * ratio)
    # limit height to 25 to fit the svg space
    if new_height > 25:
        new_height = 25
        new_width = int(new_height / ratio)
        
    resized_image = image.resize((new_width, new_height))
    grayscale_image = resized_image.convert("L")
    
    pixels = grayscale_image.getdata()
    
    # Map pixels to ASCII chars
    ascii_str = ""
    for pixel in pixels:
        ascii_str += ASCII_CHARS[pixel * len(ASCII_CHARS) // 256]
        
    img_width = grayscale_image.width
    
    ascii_lines = []
    for i in range(0, len(ascii_str), img_width):
        ascii_lines.append(ascii_str[i:i+img_width])
        
    return ascii_lines

def update_svg(filename, ascii_lines):
    with open(filename, 'r') as f:
        content = f.read()
        
    # Replace the andrew@grant name
    content = content.replace('andrew@grant', 'cmm21')
    content = content.replace('Andrew6rant', 'cmm21')
    content = content.replace('Andrew Grant', 'Christopher Milbourne')
    content = content.replace('Andrew.Grant@ttmtech.com', 'christopher@example.com')
    content = content.replace('agrantnmac@gmail.com', 'christopher.m@gmail.com')
    content = content.replace('andrew@grant.software', '')
    
    # Replace LinkedIn
    # The original SVG has: <tspan class="value">Andrew6rant</tspan> for LinkedIn and Discord.
    content = re.sub(r'(<tspan class="key">LinkedIn</tspan>:<tspan class="cc"> \.* </tspan><tspan class="value">)[^<]+(</tspan>)', r'\g<1>christopher-milbourne-6338b1106\g<2>', content)
    
    # Replace ASCII art. The original ASCII art spans from y="30" to y="490".
    
    for i, line in enumerate(ascii_lines):
        y_val = 30 + i * 20
        # pad line to 50 characters so it replaces cleanly
        padded_line = line.ljust(50)
        pattern = r'(<tspan x="15" y="' + str(y_val) + r'">)[^<]*(</tspan>)'
        replacement = r'\g<1>' + padded_line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') + r'\g<2>'
        content = re.sub(pattern, replacement, content)
        
    # If the new ascii art is shorter than 24 lines, clear the remaining lines
    for i in range(len(ascii_lines), 25):
        y_val = 30 + i * 20
        pattern = r'(<tspan x="15" y="' + str(y_val) + r'">)[^<]*(</tspan>)'
        replacement = r'\g<1>' + (' ' * 50) + r'\g<2>'
        content = re.sub(pattern, replacement, content)
        
    with open(filename, 'w') as f:
        f.write(content)


if __name__ == "__main__":
    img_path = "/Users/chrismilbourne/Downloads/HULC28wbkAA0KTx.jpeg"
    ascii_art = image_to_ascii(img_path)
    
    print("Generated ASCII Art:")
    for line in ascii_art:
        print(line)
        
    update_svg("dark_mode.svg", ascii_art)
    update_svg("light_mode.svg", ascii_art)
    print("SVGs updated!")
