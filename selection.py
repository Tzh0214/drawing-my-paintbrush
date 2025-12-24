"""
Selection, transformation, and resize handle management for DrawingApp.
"""


def clear_resize_handles(app):
    """Clear all resize and rotation handles from the canvas."""
    app.canvas.delete("handle")
    app.resize_handles.clear()
    app.rotation_handle_id = None


def get_selection_bbox(app):
    """Get the bounding box of all selected items."""
    if not app.selection_group:
        return None
    min_x, min_y, max_x, max_y = float('inf'), float('inf'), float('-inf'), float('-inf')
    has_bbox = False
    for tag in app.selection_group:
        bbox = app.canvas.bbox(tag)
        if bbox:
            has_bbox = True
            min_x = min(min_x, bbox[0])
            min_y = min(min_y, bbox[1])
            max_x = max(max_x, bbox[2])
            max_y = max(max_y, bbox[3])
    return (min_x, min_y, max_x, max_y) if has_bbox else None


def draw_resize_handles(app):
    """Draw resize and rotation handles around the selected items."""
    clear_resize_handles(app)
    bbox = get_selection_bbox(app)
    if not bbox:
        return
    x1, y1, x2, y2 = bbox
    s = 5

    handle_positions = {
        "top-left": (x1, y1), 
        "top-center": ((x1 + x2) / 2, y1), 
        "top-right": (x2, y1),
        "middle-left": (x1, (y1 + y2) / 2), 
        "middle-right": (x2, (y1 + y2) / 2),
        "bottom-left": (x1, y2), 
        "bottom-center": ((x1 + x2) / 2, y2), 
        "bottom-right": (x2, y2)
    }
    
    for name, (x, y) in handle_positions.items():
        app.resize_handles.append(
            app.canvas.create_rectangle(x - s, y - s, x + s, y + s, 
                                        fill="white", outline="blue", tags=("handle", name))
        )
    
    top_center_x, top_y = handle_positions["top-center"]
    handle_line_end_y = top_y - 25
    app.canvas.create_line(top_center_x, top_y, top_center_x, handle_line_end_y, 
                          fill="white", tags="handle")
    
    s_rot = 7
    app.rotation_handle_id = app.canvas.create_oval(
        top_center_x - s_rot, handle_line_end_y - s_rot, 
        top_center_x + s_rot, handle_line_end_y + s_rot,
        fill="cyan", outline="blue", tags=("handle", "rotate")
    )
    app.resize_handles.append(app.rotation_handle_id)
