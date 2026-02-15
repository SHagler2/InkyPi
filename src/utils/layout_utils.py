from PIL import ImageDraw


def draw_rounded_rect(draw, rect, radius, fill=None, outline=None, width=1):
    """Draw a rounded rectangle."""
    x0, y0, x1, y1 = rect
    # Clamp radius to half the smallest dimension
    max_radius = min((x1 - x0) // 2, (y1 - y0) // 2)
    radius = min(radius, max_radius)

    if radius <= 0:
        draw.rectangle(rect, fill=fill, outline=outline, width=width)
        return

    draw.rounded_rectangle(rect, radius=radius, fill=fill, outline=outline, width=width)


def draw_progress_bar(draw, position, size, progress, fill_color, bg_color,
                      border_color=None, border_width=1, radius=0):
    """Draw a progress bar. progress is 0.0 to 1.0."""
    x, y = position
    w, h = size
    progress = max(0.0, min(1.0, progress))

    # Background
    bg_rect = (x, y, x + w, y + h)
    if radius > 0:
        draw_rounded_rect(draw, bg_rect, radius, fill=bg_color)
    else:
        draw.rectangle(bg_rect, fill=bg_color)

    # Filled portion
    fill_w = int(w * progress)
    if fill_w > 0:
        fill_rect = (x, y, x + fill_w, y + h)
        if radius > 0:
            draw_rounded_rect(draw, fill_rect, radius, fill=fill_color)
        else:
            draw.rectangle(fill_rect, fill=fill_color)

    # Border
    if border_color:
        if radius > 0:
            draw_rounded_rect(draw, bg_rect, radius, outline=border_color, width=border_width)
        else:
            draw.rectangle(bg_rect, outline=border_color, width=border_width)


def calculate_grid(area, rows, cols, spacing=0):
    """Calculate grid cell positions. area is (x, y, w, h). Returns list of (x, y, w, h)."""
    ax, ay, aw, ah = area
    cell_w = (aw - spacing * (cols - 1)) // cols if cols > 0 else aw
    cell_h = (ah - spacing * (rows - 1)) // rows if rows > 0 else ah
    cells = []
    for row in range(rows):
        for col in range(cols):
            cx = ax + col * (cell_w + spacing)
            cy = ay + row * (cell_h + spacing)
            cells.append((cx, cy, cell_w, cell_h))
    return cells


def draw_dotted_rect(draw, rect, dot_color, dot_spacing=5, dot_radius=1):
    """Fill a rectangle area with a dot pattern (for unfilled progress bars)."""
    x0, y0, x1, y1 = rect
    y = y0 + dot_spacing // 2
    while y < y1:
        x = x0 + dot_spacing // 2
        while x < x1:
            draw.ellipse((x - dot_radius, y - dot_radius, x + dot_radius, y + dot_radius),
                         fill=dot_color)
            x += dot_spacing
        y += dot_spacing
