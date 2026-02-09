from flask import Blueprint, request, jsonify, current_app, render_template, send_file
import os
import time
from datetime import datetime

main_bp = Blueprint("main", __name__)

@main_bp.route('/')
def main_page():
    device_config = current_app.config['DEVICE_CONFIG']
    loop_enabled = device_config.get_config("loop_enabled", default=True)
    return render_template('inky.html',
                         config=device_config.get_config(),
                         plugins=device_config.get_plugins(),
                         loop_enabled=loop_enabled)

@main_bp.route('/api/current_image')
def get_current_image():
    """Serve current_image.png with conditional request support (If-Modified-Since)."""
    image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'images', 'current_image.png')
    
    if not os.path.exists(image_path):
        return jsonify({"error": "Image not found"}), 404
    
    # Get the file's last modified time (truncate to seconds to match HTTP header precision)
    file_mtime = int(os.path.getmtime(image_path))
    last_modified = datetime.fromtimestamp(file_mtime)
    
    # Check If-Modified-Since header
    if_modified_since = request.headers.get('If-Modified-Since')
    if if_modified_since:
        try:
            # Parse the If-Modified-Since header
            client_mtime = datetime.strptime(if_modified_since, '%a, %d %b %Y %H:%M:%S %Z')
            client_mtime_seconds = int(client_mtime.timestamp())
            
            # Compare (both now in seconds, no sub-second precision)
            if file_mtime <= client_mtime_seconds:
                return '', 304
        except (ValueError, AttributeError):
            pass
    
    # Send the file with Last-Modified header
    response = send_file(image_path, mimetype='image/png')
    response.headers['Last-Modified'] = last_modified.strftime('%a, %d %b %Y %H:%M:%S GMT')
    response.headers['Cache-Control'] = 'no-cache'
    return response


@main_bp.route('/api/plugin_order', methods=['POST'])
def save_plugin_order():
    """Save the custom plugin order."""
    device_config = current_app.config['DEVICE_CONFIG']

    data = request.get_json() or {}
    order = data.get('order', [])

    if not isinstance(order, list):
        return jsonify({"error": "Order must be a list"}), 400

    device_config.set_plugin_order(order)

    return jsonify({"success": True})

@main_bp.route('/toggle_loop', methods=['POST'])
def toggle_loop():
    """Enable or disable loop rotation."""
    device_config = current_app.config['DEVICE_CONFIG']

    data = request.get_json() or {}
    enabled = data.get('enabled')

    if enabled is None:
        return jsonify({"error": "enabled field is required"}), 400

    try:
        device_config.update_value("loop_enabled", enabled, write=True)

        # Signal refresh task to pause/resume based on new setting
        refresh_task = current_app.config['REFRESH_TASK']
        refresh_task.signal_config_change()

        return jsonify({
            "success": True,
            "message": f"Loop rotation {'enabled' if enabled else 'disabled'}",
            "enabled": enabled
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main_bp.route('/api/next_change_time')
def get_next_change_time():
    """Get time remaining until next loop/display change."""
    device_config = current_app.config['DEVICE_CONFIG']
    refresh_task = current_app.config.get('REFRESH_TASK')

    if not refresh_task or not refresh_task.running:
        return jsonify({"error": "Refresh task not running"}), 503

    # Get the rotation interval from loop manager
    loop_manager = device_config.get_loop_manager()
    interval_seconds = loop_manager.rotation_interval_seconds

    # Get the last refresh time and current plugin from device config
    refresh_info = device_config.get_refresh_info()
    last_refresh = refresh_info.get_refresh_datetime()

    # Get current plugin display name
    current_plugin_id = refresh_info.plugin_id
    current_plugin_name = "Unknown"
    if current_plugin_id:
        plugin_config = device_config.get_plugin(current_plugin_id)
        if plugin_config:
            current_plugin_name = plugin_config.get("display_name", current_plugin_id)

    # Determine next plugin from loop
    next_plugin_name = "Unknown"
    loop = loop_manager.determine_active_loop(datetime.now(refresh_info.get_refresh_datetime().tzinfo) if last_refresh else datetime.now())
    if loop and loop.plugin_order:
        # Find current plugin in order
        current_idx = next((i for i, ref in enumerate(loop.plugin_order) if ref.plugin_id == current_plugin_id), -1)
        if current_idx >= 0:
            # Current plugin is in the loop, get the next one
            next_idx = (current_idx + 1) % len(loop.plugin_order)
        else:
            # Current plugin is not in the loop (manually displayed), next will be first in loop
            next_idx = 0
        next_plugin_id = loop.plugin_order[next_idx].plugin_id
        next_plugin_config = device_config.get_plugin(next_plugin_id)
        if next_plugin_config:
            next_plugin_name = next_plugin_config.get("display_name", next_plugin_id)

    if last_refresh:
        # Calculate seconds since last refresh
        now = datetime.now(last_refresh.tzinfo)
        elapsed = (now - last_refresh).total_seconds()
        remaining = max(0, interval_seconds - elapsed)
    else:
        # No refresh yet, assume full interval remaining
        remaining = interval_seconds

    # Check if loop is enabled
    loop_enabled = device_config.get_config("loop_enabled", default=True)

    return jsonify({
        "success": True,
        "loop_enabled": loop_enabled,
        "interval_seconds": interval_seconds,
        "remaining_seconds": int(remaining),
        "next_change_in": format_time(int(remaining)),
        "current_plugin": current_plugin_name,
        "next_plugin": next_plugin_name
    })

def format_time(seconds):
    """Format seconds into human-readable time."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"