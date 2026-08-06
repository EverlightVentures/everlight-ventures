# Samsung DeX Look on KDE Plasma 6 (Arch) -- AceMagician Handoff

**Target:** AceMagician PC (Garuda/Arch, KDE Plasma 6, user `richgee`).
**Owner of execution:** the Claude session running on the PC. The phone cannot do this; it needs a live KDE session.
**Added to handoff:** 2026-08-06, alongside the terminal-look upgrade.

**Objective:** make KDE Plasma + KWin visually and functionally replicate Samsung DeX:
- Bottom panel with centered app icons (DeX taskbar style)
- App folders that expand to show grouped apps (DeX folder widgets)
- Full app drawer with categorized apps
- **Preserve all existing transparency settings** (panel, Kvantum, blur)
- DeX-like extras: system tray right-aligned, minimize-all, clean minimal chrome

---

## READ THIS BEFORE PHASE 1: two collisions specific to this machine

**1. KDE global shortcuts were rebound on this PC today at 13:24 PT.** That work is recorded in `_state/DECISION_LOG.md` as *"Rebind KDE global shortcuts to match Rich's cheatsheet (not the reverse)."* This document touches `~/.config/kglobalshortcutsrc`. **Do not overwrite it.** Back it up, and when modifying, edit only the specific keys you need. Losing that rebind means losing a deliberate decision made the same day.

**2. The shell/terminal look was merged onto this PC today.** `~/everlight_brand.zsh` is sourced as the last line of `~/.zshrc`, running after oh-my-zsh and powerlevel10k. Backup at `~/.zshrc.bak.20260806`. The DeX work here is the *desktop* layer; it sits alongside that, not on top of it. If a theme change alters terminal colors, verify the Everlight gold/navy/turquoise palette still renders before calling the phase done.

**3. Transparency is the hard constraint.** Rich has explicitly said the current transparency must survive. Treat any step that resets it as a failure, not a side effect. Phase 5 exists for this reason. Verify, do not assume.

---

## Phase 1: Backup current configuration

Do this first. No exceptions.

```bash
cp ~/.config/plasma-org.kde.plasma.desktop-appletsrc \
   ~/.config/plasma-org.kde.plasma.desktop-appletsrc.backup.$(date +%Y%m%d)

cp ~/.config/kwinrc ~/.config/kwinrc.backup.$(date +%Y%m%d)

cp ~/.config/kglobalshortcutsrc ~/.config/kglobalshortcutsrc.backup.$(date +%Y%m%d)

cp ~/.config/Kvantum/kvantum.kvconfig \
   ~/.config/Kvantum/kvantum.kvconfig.backup.$(date +%Y%m%d) 2>/dev/null || true
```

**Critical:** do NOT overwrite these backups later in the process. Per standing workspace doctrine, verify before delete, and nothing gets reclaimed without a manifest.

---

## Phase 2: Install packages and widgets

### A. Arch repos

```bash
sudo pacman -S --needed \
    papirus-icon-theme \
    tela-icon-theme \
    plasma-workspace \
    kwin \
    kdeplasma-addons
```

### B. AUR

```bash
sudo pacman -S --needed yay

yay -S --needed \
    whitesur-kde-theme-git \
    orchis-kde-theme-git \
    panel-colorizer-plasma6-git
```

### C. KDE Store widgets (installed through the Plasma widget installer)

1. **Plasma Drawer** -- full-screen app drawer with folders/categories. Closest match to the DeX app drawer.
   Right-click desktop, Add Widgets, Get New Widgets, Download New Plasma Widgets, search `Plasma Drawer`.
2. **Popup Tile Launcher** -- grid popup launcher for app folders on the panel. May need a native helper; follow its README.
3. **Panel Colorizer** -- advanced transparency/blur control without touching theme files.

> Note: `sudo` on this box requires a password, so package installs are operator-gated. If a prompt blocks an unattended run, stop and report rather than working around it.

---

## Phase 3: Panel layout (DeX bottom bar)

**Create or modify the bottom panel.** If one exists, edit it rather than adding a second.

**Position and size:**
1. Right-click panel, Edit Panel
2. Drag to bottom screen edge
3. Height 48 to 56 px (DeX uses chunky icons)
4. Length Mode: `Fill`

**Widget arrangement, left to right:**

*Left:*
- Application Launcher (Kickoff) **or** Plasma Drawer for the app grid button. If using Plasma Drawer, right-click, Configure, set the icon to a grid/dots icon.
- Pager (virtual desktop switcher), optional

*Center:*
- **Icons-Only Task Manager**, the DeX dock itself
  - Configure, Behavior tab: pin favourites (Firefox/Brave, terminal, Dolphin)
  - Appearance tab: icon size `Scale with panel height`
  - Behavior tab: disable Group for individual icons per window (DeX style)

**To force dead-center:**
1. Add a Spacer to the left of the task manager
2. Add a Spacer to the right of it
3. Configure each spacer and **uncheck Flexible size**

*Right:*
- Margins Separator
- System Tray
- Digital Clock
- Minimize All Windows (DeX "show desktop")

Remove leftover default widgets, especially the standard Task Manager if Icons-Only replaced it.

---

## Phase 4: App folders (the DeX folder-widget feature)

KDE has no native equivalent. Four approaches, best first.

### Option A: Plasma Drawer (recommended)

Replicates the DeX App Tray: a full-screen grid with categorized folders.

1. Add Plasma Drawer to the panel
2. Right-click, Edit Applications
3. New Menu, name it (`Office`, `Dev Tools`, `Media`)
4. Drag apps into folders
5. Root-level apps show on the main page; folder contents open on click
6. Configure grid columns, icon size, search plugins

### Option B: Popup Tile Launcher (panel folders)

Each panel icon behaves like a DeX folder: click, get a popup grid.

1. Add Popup Tile Launcher
2. Configure with a category name and icon
3. Display mode: Grid
4. Add apps
5. Repeat for one instance per category

### Option C: Quicklaunch with popup (built-in, no third party)

1. Add Quicklaunch
2. Configure, check **Enable Popup**
3. Add apps

Less polished than A or B.

### Option D: Folder View on panel (simplest)

1. Add Folder View widget
2. Create `~/Desktop/Office Apps/`
3. Point the widget's Location there
4. Copy `.desktop` files in:

```bash
cp /usr/share/applications/libreoffice-*.desktop ~/Desktop/Office\ Apps/
cp /usr/share/applications/org.kde.kwrite.desktop ~/Desktop/Office\ Apps/
```

Shows as a folder icon on the panel; click reveals contents.

---

## Phase 5: Preserve transparency (the critical section)

### Rule 1: do NOT change the Global Theme

Changing it overrides panel transparency, Kvantum settings and colour schemes in one move. Change only:
- Icon Theme
- Cursor Theme
- Window Decorations (if desired)

### Rule 2: panel transparency

Controlled by the Plasma Style, panel background settings, and Desktop Effects blur.

**Method A: native panel settings (safest)**
1. Right-click panel, Edit Panel
2. Configure the panel background
3. Set Opacity: `Adaptive`, `Translucent`, `Opaque`, or custom
4. If the options are missing, the current Plasma Style does not support them. Switch temporarily to Breeze, set opacity, switch back.

**Method B: Panel Colorizer widget (most control)**
1. Add Panel Colorizer
2. Panel Background, Opacity: set value (e.g. 0.6)
3. Check **Hide native panel background**
4. Enable/disable blur as desired
5. Save as a preset for easy toggling

**Method C: KWin window rule (the hammer)**
1. System Settings, Window Management, Window Rules, New
2. Window Types: **Dock** only
3. Appearance & Fixes tab
4. Opacity: Force, `65%`
5. OK, Apply

**Method D: theme file editing (last resort, not recommended)**

```bash
mkdir -p ~/.local/share/plasma/desktoptheme/YOUR-THEME-NAME/translucent
cp /usr/share/plasma/desktoptheme/default/translucent/panel-background.svgz \
   ~/.local/share/plasma/desktoptheme/YOUR-THEME-NAME/translucent/ 2>/dev/null || true
```

Then edit the SVG alpha channel. Use Panel Colorizer instead.

### Rule 3: Kvantum / application transparency

- Do NOT reinstall or reconfigure Kvantum unless explicitly asked
- Leave `kvantum.kvconfig` untouched
- If the application style must change, pick a Kvantum variant matching the new icons and **verify transparency survived**

### Rule 4: shortcuts

Preserve these files:
- `~/.config/kglobalshortcutsrc` -- keyboard shortcuts. **See the collision warning at the top: this was rebound today.**
- `~/.config/kwinrc` -- KWin settings
- The `launchers=` line in `plasma-org.kde.plasma.desktop-appletsrc` -- pinned panel apps

When modifying the panel, edit only the `launchers=` line. Never replace the whole file.

---

## Phase 6: DeX visual polish

**Icons:** Papirus or Tela. System Settings, Appearance, Icons.

**Colour scheme:** DeX is light blue/white with blue accents. Breeze Light with accent `#0073E6` (Samsung blue), or WhiteSur.

> Everlight note: the terminal keeps the Everlight palette (gold `#D4AF37`, dark `#0A0A0A`, light text `#E8E8E8`). DeX blue is the *desktop* accent. Do not push Samsung blue into the terminal theme or branded output; the Everlight palette has a single source of truth in `content_tools/report_template.py`.

**Window decorations:** Breeze or WhiteSur. Configure, enable "No side borders when maximized."

**Fonts:** General `Noto Sans` or `Inter` 10pt. Fixed width `JetBrains Mono` or `Noto Sans Mono`.

**Cursor:** Breeze Snow or any clean white cursor.

---

## Phase 7: Additional DeX features

1. **Minimize All / Show Desktop** -- widget added in Phase 3, or bind a screen corner: System Settings, Workspace Behavior, Screen Edges.
2. **Notification centre** -- System Tray already covers it. Add the Notifications widget for a closer match.
3. **Quick settings** -- the Plasma 6 tray popup is already close. Ensure Media Player, Volume, Network, Bluetooth, Battery are visible.
4. **Touch/gestures** (if convertible) -- System Settings, Workspace Behavior, Touchscreen; and Input Devices, Touchpad.
5. **Always-visible panel** -- DeX does not auto-hide. Edit Panel, Visibility: `Always Visible`.

---

## Phase 8: Verification and rollback

**Verify transparency survived.** This is the acceptance test, not an afterthought:
1. Panel: right-click, Edit Panel, Background, confirm opacity is still the preferred value
2. Kvantum: open Dolphin and a browser, confirm menus/dialogs kept their transparency
3. Blur: System Settings, Workspace Behavior, Desktop Effects, Blur still enabled at the previous strength
4. **Terminal:** open a shell, confirm the Everlight brand layer still renders and p10k still drives the prompt
5. **Shortcuts:** confirm the 13:24 KDE rebind still works

**Rollback:**

```bash
cp ~/.config/plasma-org.kde.plasma.desktop-appletsrc.backup.YYYYMMDD \
   ~/.config/plasma-org.kde.plasma.desktop-appletsrc
systemctl restart --user plasma-plasmashell

cp ~/.config/kwinrc.backup.YYYYMMDD ~/.config/kwinrc
systemctl restart --user plasma-kwin_wayland   # or plasma-kwin_x11

cp ~/.config/kglobalshortcutsrc.backup.YYYYMMDD ~/.config/kglobalshortcutsrc
```

---

## Key files

| File | Purpose | Backup |
|---|---|---|
| `~/.config/plasma-org.kde.plasma.desktop-appletsrc` | Panel layout, widgets, pinned apps (`launchers=`) | YES |
| `~/.config/kwinrc` | KWin effects, blur, transparency rules | YES |
| `~/.config/Kvantum/kvantum.kvconfig` | Application transparency | YES |
| `~/.config/kglobalshortcutsrc` | Keyboard shortcuts (**rebound 2026-08-06**) | YES |

---

## Agent checklist

- [ ] Backed up all four config files
- [ ] Confirmed the 13:24 KDE shortcut rebind is preserved, not clobbered
- [ ] Installed Plasma Drawer and/or Popup Tile Launcher
- [ ] Installed Panel Colorizer if native transparency options are insufficient
- [ ] Bottom panel created with Icons-Only Task Manager centered via fixed spacers
- [ ] App folder widgets added (Plasma Drawer for the full grid, Popup Tile for panel folders)
- [ ] Icon theme set to Papirus or Tela
- [ ] **Panel transparency verified preserved, not reset to opaque**
- [ ] **Kvantum / app transparency verified untouched**
- [ ] Panel set to Always Visible
- [ ] System Tray, Clock, Minimize All on the right
- [ ] Terminal still renders the Everlight brand layer with p10k prompt
- [ ] `systemctl restart --user plasma-plasmashell` retains all settings

---

*Execution belongs to the PC session. Report results back through `_state/AGENT_MAILBOX.md`, which is the coordination surface between the two devices. Remember the two machines commit to different repos by design (`aa-my-drive.git` on the PC, `everlight-ventures.git` on the phone), so this file reaches the phone via Syncthing/rsync, not by push.*
