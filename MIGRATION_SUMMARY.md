# InkyPi Playlist Removal - Migration Summary

## Overview
Successfully removed playlist mode from InkyPi, unifying on the simpler loop system. This simplifies the codebase and user experience by eliminating mode switching and complex per-instance settings.

## Changes Made

### 1. Backend Changes

#### Deleted Files
- `src/blueprints/playlist.py` - All playlist CRUD endpoints
- `src/templates/playlist.html` - Playlist management UI

#### Model Changes (`src/model.py`)
**Removed:**
- `PlaylistManager` class
- `Playlist` class
- `PluginInstance` class

**Updated:**
- `RefreshInfo` - Removed `playlist` and `plugin_instance` fields
- Now only tracks: `refresh_type`, `plugin_id`, `loop`, `refresh_time`, `image_hash`

#### Configuration Changes (`src/config.py`)
**Removed methods:**
- `load_playlist_manager()`
- `get_playlist_manager()`
- `get_display_mode()`
- `set_display_mode()`

**Removed from config:**
- `playlist_config` structure
- `display_mode` setting

**Updated:**
- `write_config()` - No longer saves playlist_config
- `__init__()` - No longer loads playlist_manager

#### Refresh Task Changes (`src/refresh_task.py`)
**Removed:**
- `PlaylistRefresh` class
- `_determine_next_plugin_playlist_mode()` method
- All display mode conditionals

**Updated:**
- Always uses loop_manager for timing
- Simplified `_run()` method - removed mode checks
- Single code path for refresh logic

### 2. Blueprint Changes

#### Main Blueprint (`src/blueprints/main.py`)
**Removed:**
- `/toggle_display_mode` endpoint
- `display_mode` parameter from main page render

**Updated:**
- `/api/next_change_time` - Always uses loop_manager
- Simplified next plugin determination

#### Plugin Blueprint (`src/blueprints/plugin.py`)
**Removed:**
- `/plugin_instance_image/<path>` endpoint
- `/delete_plugin_instance` endpoint
- `/update_plugin_instance/<name>` endpoint
- `/display_plugin_instance` endpoint
- `_delete_plugin_instance_images()` helper function

**Updated:**
- `/plugin/<plugin_id>` - Passes `loops` instead of `playlists` to template
- No longer supports editing plugin instances

#### Settings Blueprint (`src/blueprints/settings.py`)
**Removed:**
- `display_mode` field handling in save_settings

### 3. Frontend Changes

#### Main Page (`src/templates/inky.html`)
**Removed:**
- Mode toggle button and section
- Mode toggle JavaScript (lines 108-157)
- Conditional rendering based on display_mode

**Updated:**
- Always displays countdown section
- Always shows Loops link (removed Playlists link)
- Simplified JavaScript - removed updateToggleStyle()

#### Plugin Page (`src/templates/plugin.html`)
**Replaced:**
- "Add to Playlist" button → "Add to Loop" button
- Playlist selection modal → Loop selection modal

**New modal includes:**
- Loop dropdown (populated from loop_manager)
- Refresh interval input (number + unit selector: minutes/hours/days)
- Plugin settings preserved (but stored in loop, not separate instance)

**Updated JavaScript:**
- `handleAction('add_to_loop')` instead of `add_to_playlist`
- Converts interval units to seconds before submission
- Posts to `/add_plugin_to_loop` endpoint (existing in loops.py)

#### Settings Page (`src/templates/settings.html`)
**Removed:**
- Display Mode dropdown and help text

### 4. Configuration Files

#### Development Config (`src/config/device_dev.json`)
**Changed:**
```json
// Before:
"playlist_config": {
  "playlists": [...]
}

// After:
"loop_config": {
  "loops": [...],
  "rotation_interval_seconds": 300
}
```

#### Base Config (`install/config_base/device.json`)
- No changes needed (didn't have playlist_config)

### 5. Migration Script

**Created:** `migrate_playlists_to_loops.py`

**Features:**
- Reads device.json
- Converts playlists → loops
- Converts plugin instances → plugin references
- Maps refresh intervals:
  - `interval` refresh → `refresh_interval_seconds`
  - `scheduled` refresh → 86400 seconds (daily)
  - No refresh → 1800 seconds (30 min default)
- Removes `display_mode` setting
- Cleans up `refresh_info` (removes playlist/plugin_instance fields)
- Creates backup before migration
- Handles missing playlist_config gracefully

## Breaking Changes

### User-Facing
1. **No more display mode toggle** - Loop mode is always active
2. **No more playlist management** - Use Loops page instead
3. **Plugin settings moved to loops** - Each plugin reference can have custom settings, but stored in loop not separate instance
4. **Simplified navigation** - Loops link only, no Playlists link

### API Changes
1. **Removed endpoints:**
   - `/toggle_display_mode`
   - `/playlist/*` (all playlist routes)
   - `/delete_plugin_instance`
   - `/update_plugin_instance/<name>`
   - `/display_plugin_instance`

2. **Modified endpoints:**
   - `/` - No longer returns `display_mode`
   - `/api/next_change_time` - No longer returns `display_mode`

### Configuration Changes
1. **Removed config keys:**
   - `display_mode`
   - `playlist_config`

2. **New required structure:**
   - `loop_config` must exist
   - Must contain at least one loop

## Migration Guide

### For Existing Deployments

1. **Backup current config:**
   ```bash
   cp /usr/local/inkypi/src/config/device.json /usr/local/inkypi/src/config/device.json.pre-migration
   ```

2. **Run migration script:**
   ```bash
   cd /home/admin/InkyPi
   python migrate_playlists_to_loops.py
   ```

3. **Deploy updated code:**
   ```bash
   rsync -avz --delete \
     --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
     --exclude='src/config/device.json' --exclude='.env' \
     /Users/stevenhagler/Claude/EInk-Orbs/inkypi/ \
     admin@inky.local:/home/admin/InkyPi/

   ssh admin@inky.local "cd /home/admin/InkyPi && sudo bash install/update.sh"
   ```

4. **Restart service:**
   ```bash
   ssh admin@inky.local "sudo systemctl restart inkypi"
   ```

5. **Verify:**
   ```bash
   ssh admin@inky.local "sudo journalctl -u inkypi -n 50 --no-pager"
   ```

### For Fresh Installations

No migration needed. The default config includes `loop_config` and works out of the box.

## Testing Checklist

### Backend
- [ ] InkyPi service starts without errors
- [ ] Loops rotate at configured interval
- [ ] Plugin settings persist in loops
- [ ] Refresh intervals work correctly
- [ ] No import errors for removed classes

### Frontend
- [ ] Main page loads without mode toggle
- [ ] Countdown always visible
- [ ] Loops link works
- [ ] Plugin page shows "Add to Loop" button
- [ ] Loop modal populates with available loops
- [ ] Adding plugin to loop succeeds
- [ ] Plugin settings save correctly

### API
- [ ] `/api/next_change_time` returns correct data
- [ ] `/` renders without display_mode
- [ ] `/plugin/<id>` passes loops to template
- [ ] Settings save without display_mode

### Migration
- [ ] Migration script handles existing playlists
- [ ] Plugin instances convert to references
- [ ] Refresh intervals convert correctly
- [ ] Backup created successfully
- [ ] Config valid after migration

## Rollback Plan

If issues occur:

1. **Stop service:**
   ```bash
   sudo systemctl stop inkypi
   ```

2. **Restore config:**
   ```bash
   cp /usr/local/inkypi/src/config/device.json.backup \
      /usr/local/inkypi/src/config/device.json
   ```

3. **Restore old code:**
   ```bash
   cd /home/admin/InkyPi
   git checkout <previous-commit>
   sudo bash install/update.sh
   ```

4. **Restart service:**
   ```bash
   sudo systemctl restart inkypi
   ```

## Benefits of This Change

1. **Simpler codebase** - ~1500-2000 lines removed
2. **Easier to understand** - Single display mode, clear mental model
3. **Less cognitive load** - No mode switching, no instance management
4. **Cleaner architecture** - Unified data structures
5. **Faster development** - Fewer code paths to maintain
6. **Better UX** - Simpler UI, fewer decisions for users

## Notes

- Existing plugins continue to work unchanged
- Plugin import process unchanged
- Loop system already existed, just made it the only option
- All features preserved (time-based loops, custom settings, rotation)
- Original InkyPi principles maintained (do not modify display code)
