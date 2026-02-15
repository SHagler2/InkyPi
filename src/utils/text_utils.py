from PIL import ImageDraw, ImageFont


def wrap_text(draw, text, font, max_width):
    """Wrap text to fit within max_width, returning list of lines."""
    if not text:
        return []

    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip() if current_line else word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            # If a single word exceeds max_width, add it anyway
            current_line = word
    if current_line:
        lines.append(current_line)

    return lines


def truncate_text(draw, text, font, max_width, suffix="..."):
    """Truncate text to fit within max_width, adding suffix if truncated."""
    if not text:
        return ""

    bbox = draw.textbbox((0, 0), text, font=font)
    if bbox[2] - bbox[0] <= max_width:
        return text

    for i in range(len(text), 0, -1):
        truncated = text[:i].rstrip() + suffix
        bbox = draw.textbbox((0, 0), truncated, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return truncated

    return suffix


def draw_multiline_text(draw, text, position, font, fill, max_width,
                        line_spacing=4, align="left"):
    """Wrap text and draw it, returning the total height used."""
    lines = wrap_text(draw, text, font, max_width)
    x, y = position
    total_height = 0

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_height = bbox[3] - bbox[1]
        line_width = bbox[2] - bbox[0]

        if align == "center":
            line_x = x + (max_width - line_width) // 2
        elif align == "right":
            line_x = x + max_width - line_width
        else:
            line_x = x

        draw.text((line_x, y + total_height), line, font=font, fill=fill)
        total_height += line_height + line_spacing

    return total_height


def measure_text_block(draw, text, font, max_width, line_spacing=4):
    """Measure the total height a wrapped text block would occupy."""
    lines = wrap_text(draw, text, font, max_width)
    if not lines:
        return 0

    total_height = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        total_height += (bbox[3] - bbox[1]) + line_spacing

    # Remove trailing line_spacing
    return total_height - line_spacing if lines else 0


def get_text_dimensions(draw, text, font):
    """Get width and height of a text string."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]
