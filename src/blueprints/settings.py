from flask import Blueprint, request, jsonify, current_app, render_template

settings_bp = Blueprint("settings", __name__)

@settings_bp.route('/settings')
def settings_page():
    device_config = current_app.config['DEVICE_CONFIG']
    return render_template('settings.html', device_settings=device_config.get_config())

@settings_bp.route('/save_settings', methods=['POST'])
def save_settings():
    device_config = current_app.config['DEVICE_CONFIG']

    try:
        form_data = request.form.to_dict()
        settings = {
            "name": form_data.get("deviceName"),
            "orientation": form_data.get("orientation")
        }
        device_config.update_config(settings)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    return jsonify({"success": True, "message": "Saved settings."})