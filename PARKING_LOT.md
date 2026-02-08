# Parking Lot - Items to Test/Address

**Last Updated:** February 8, 2026
**Status:** Post-Deployment of Playlist Removal

---

## ✅ Completed & Verified

- [x] Service starts cleanly
- [x] Main page loads correctly
- [x] Loop toggle works (enable/disable)
- [x] Countdown timer displays
- [x] Loops page loads with modern styling
- [x] Plugin pages load without errors
- [x] "Add to Loop" functionality works
- [x] Dark mode toggle functions
- [x] Config backup created (device.json.20260208-102003.backup)

---

## ⏳ Pending Testing (Playlist Removal Features)

### High Priority - Core Functionality
1. **Actual loop rotation** (waiting for 60 minute interval)
   - Current: clock → wpotd → weather
   - Need to wait for rotation_interval_seconds (3600s = 1 hour)
   - Expected: Display should change from clock to wpotd after 1 hour

2. **Plugin refresh intervals**
   - Clock: 60 seconds (should update every minute)
   - WPOTD: 24 hours (should fetch new Wikipedia picture daily)
   - Weather: 30 minutes (should update weather data)
   - **How to test:** Watch logs for "Refreshing plugin data (interval elapsed)"

3. **Time-based loop activation**
   - Current loop: 07:00-18:00 (Day Loop)
   - Need to test: What happens outside this window?
   - Expected: Display should stop rotating or show nothing

### Medium Priority - User Actions
4. **Adding new plugins to loop**
   - Test: Click any plugin → "Add to Loop" → Select loop → Set interval → Save
   - Verify: Plugin appears in loop on Loops page
   - Verify: Plugin appears in rotation cycle

5. **Editing plugin settings within loop**
   - Test: Go to Loops page → Click plugin in loop → Edit settings → Save
   - Verify: Settings persist after save
   - Verify: Display updates with new settings

6. **Drag-and-drop reordering on Loops page**
   - Test: Go to Loops page → Drag plugins to reorder
   - Verify: Order saves and affects rotation sequence

---

## 🐛 Known Issues (Unrelated to Playlist Removal)

### ai_image Plugin - Unicode Encoding Bug
**Priority:** Low (doesn't affect core functionality)
**Status:** Pre-existing bug, not caused by playlist removal

**Error:**
```
ERROR - plugins.ai_image.ai_image - Failed to make OpenAI request:
'ascii' codec can't encode character '\u2014' in position 9:
ordinal not in range(128)
```

**Impact:** AI image plugin fails when trying to generate images
**Root Cause:** Unicode em dash (—) character in prompt/response
**Fix:** Plugin needs to handle UTF-8 encoding properly
**Owner:** Original InkyPi maintainer (not our issue)

**Note:** This error appears in logs but doesn't affect the core loop rotation or other plugins.

---

## 📋 Monitoring Tasks

### Next 24 Hours
- [ ] Monitor logs for any new errors: `ssh admin@inky.local "sudo journalctl -u inkypi -f"`
- [ ] Verify first loop rotation completes successfully (after 1 hour)
- [ ] Check that countdown timer updates correctly
- [ ] Verify loop_enabled toggle persists after reboot

### Next Week
- [ ] Test outside Day Loop hours (before 7am or after 6pm)
- [ ] Add a new plugin to loop and verify it works
- [ ] Test editing plugin settings in existing loop
- [ ] Monitor plugin refresh intervals (especially 24hr WPOTD)

---

## 🎯 Future Enhancements (Not Urgent)

1. **Multiple Loops:** User might want different loops for different times of day
2. **Loop Priorities:** If loops overlap, which takes precedence?
3. **Manual Refresh Button:** Quick way to force immediate refresh
4. **Plugin Status Indicators:** Show last refresh time for each plugin
5. **Loop Preview:** Preview what the loop will look like before activating

---

## 📊 Current System State

**Service:** ✅ Active (running)
**Web UI:** ✅ http://inky.local
**Configuration:** ✅ Restored from backup
**Loops:** 1 (Day Loop, 07:00-18:00)
**Plugins in Loop:** 3 (clock, wpotd, weather)
**Rotation Interval:** 60 minutes
**Loop Enabled:** Yes

**Config Backups:**
- `/usr/local/inkypi/src/config/device.json.20260208-102003.backup` (current working)
- `/home/admin/InkyPi/src/config/device.json.backup` (pre-deployment)

---

## 🔧 Quick Commands

```bash
# Check service status
ssh admin@inky.local "sudo systemctl status inkypi"

# Watch logs in real-time
ssh admin@inky.local "sudo journalctl -u inkypi -f"

# Check for errors
ssh admin@inky.local "sudo journalctl -u inkypi -n 100 | grep ERROR"

# Restart service
ssh admin@inky.local "sudo systemctl restart inkypi"

# View current config
ssh admin@inky.local "cat /usr/local/inkypi/src/config/device.json | python3 -m json.tool"
```

---

**Note:** Most items in this parking lot are routine testing that should happen naturally over the next few days of normal use. No urgent action required unless errors appear in logs.
