# Playlist Mode Removal - Quick Guide

## What Changed?

InkyPi now uses **loop mode only**. The playlist system has been removed to simplify the codebase and user experience.

### Before vs After

| Feature | Before | After |
|---------|--------|-------|
| Display modes | Playlist & Loop | Loop only |
| Mode toggle | Yes | No |
| Plugin configuration | Complex instances | Simple loop references |
| Settings location | Per-instance | Per-plugin in loop |
| Time-based scheduling | Both systems | Loops only |
| Rotation control | Per-mode | Global loop interval |

## For Users

### What You'll Notice

1. **No mode toggle** - Loop mode is always active
2. **Simpler UI** - Loops link instead of Playlists link
3. **Easier plugin setup** - Just select loop, set refresh interval, done
4. **Always-visible countdown** - Shows time until next plugin

### Adding Plugins to Loops

1. Click any plugin
2. Click "Add to Loop" button
3. Select which loop to add to
4. Set refresh interval (how often plugin data updates)
5. Configure plugin settings if needed
6. Click Save

### Managing Loops

1. Click the 🔁 icon in header
2. Create/edit loops with time windows
3. Add/remove/reorder plugins
4. Set global rotation interval

## For Developers

### Quick Deployment

```bash
# From project root
./deploy_playlist_removal.sh
```

This script:
- Backs up current config
- Runs migration on Pi
- Deploys updated code
- Restarts service
- Shows logs

### Manual Deployment

```bash
# 1. Backup config on Pi
ssh admin@inky.local "cp /usr/local/inkypi/src/config/device.json \
                          /usr/local/inkypi/src/config/device.json.backup"

# 2. Run migration
ssh admin@inky.local "cd /home/admin/InkyPi && \
                      python3 migrate_playlists_to_loops.py"

# 3. Deploy code (excludes .env and device.json)
rsync -avz --delete \
  --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='src/config/device.json' --exclude='.env' \
  /Users/stevenhagler/Claude/EInk-Orbs/inkypi/ \
  admin@inky.local:/home/admin/InkyPi/

# 4. Update and restart
ssh admin@inky.local "cd /home/admin/InkyPi && sudo bash install/update.sh && \
                      sudo systemctl restart inkypi"

# 5. Check logs
ssh admin@inky.local "sudo journalctl -u inkypi -n 50 --no-pager"
```

### Key Files Changed

**Deleted:**
- `src/blueprints/playlist.py`
- `src/templates/playlist.html`

**Major Updates:**
- `src/model.py` - Removed playlist classes
- `src/config.py` - Removed playlist manager
- `src/refresh_task.py` - Loop-only refresh
- `src/templates/plugin.html` - "Add to Loop" button
- `src/templates/inky.html` - No mode toggle
- `src/blueprints/main.py` - Simplified endpoints

**New Files:**
- `migrate_playlists_to_loops.py` - Migration script
- `deploy_playlist_removal.sh` - Deployment script

### Migration Script Usage

```bash
# On Pi or locally
python migrate_playlists_to_loops.py [path/to/device.json]

# Defaults to src/config/device.json if no path given
```

The script:
- Creates backup (device.json.backup)
- Converts playlists → loops
- Converts plugin instances → plugin references
- Removes display_mode setting
- Preserves plugin settings and refresh intervals

### Testing

```bash
# Check service status
sudo systemctl status inkypi

# Watch logs in real-time
sudo journalctl -u inkypi -f

# Test web UI
open http://inky.local

# Verify countdown works
# Verify "Add to Loop" button appears
# Add a plugin to a loop
# Check rotation after interval
```

## Troubleshooting

### Service Won't Start

Check logs:
```bash
sudo journalctl -u inkypi -n 100 --no-pager
```

Common issues:
- Missing loop_config → Run migration script
- Import errors → Restart service, check Python path
- Config syntax → Validate JSON with `python -m json.tool device.json`

### Migration Failed

Restore backup:
```bash
cp /usr/local/inkypi/src/config/device.json.backup \
   /usr/local/inkypi/src/config/device.json
sudo systemctl restart inkypi
```

### UI Not Updated

Clear browser cache:
- Chrome/Edge: Ctrl+Shift+Delete
- Firefox: Ctrl+Shift+Delete
- Safari: Cmd+Option+E

Force reload:
- Chrome/Firefox: Ctrl+Shift+R
- Safari: Cmd+Shift+R

### Rollback to Previous Version

```bash
ssh admin@inky.local
sudo systemctl stop inkypi

# Restore old config
cp /usr/local/inkypi/src/config/device.json.pre-playlist-removal \
   /usr/local/inkypi/src/config/device.json

# Restore old code (if in git)
cd /home/admin/InkyPi
git checkout <previous-commit-hash>
sudo bash install/update.sh

sudo systemctl restart inkypi
```

## FAQ

**Q: Will my existing playlists be lost?**
A: No, the migration script converts them to loops automatically.

**Q: Can I still use time-based scheduling?**
A: Yes! Loops support time windows (e.g., 7am-5pm).

**Q: Can plugins have custom settings?**
A: Yes! Each plugin reference in a loop can have custom settings.

**Q: What happens to my plugin instances?**
A: They're converted to plugin references with the same settings.

**Q: Do I need to reconfigure everything?**
A: No, migration preserves your configuration.

**Q: Can I import new plugins?**
A: Yes, plugin import works exactly the same way.

**Q: What if I had multiple playlists?**
A: Each becomes a separate loop with its time window.

## Support

If you encounter issues:

1. Check logs: `sudo journalctl -u inkypi -n 100`
2. Verify config: `cat /usr/local/inkypi/src/config/device.json`
3. Check service: `sudo systemctl status inkypi`
4. Review migration backup: `device.json.backup`

## References

- Full migration details: `MIGRATION_SUMMARY.md`
- Original InkyPi docs: `README.md`
- Loop system docs: See web UI at http://inky.local
