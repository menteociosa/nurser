
# Nurser — Contributor Screen Functionality Prompts

App context: Nurser is a mobile-first PWA for caregiver teams. It lets caregivers log care events (medications, vitals, meals, etc.) for a shared patient, track shift start/end, see what teammates are doing in real time, and read pinned notes from the care coordinator. The UI is in Spanish and targets non-technical users on their personal phones. Max width 480 px, full-height layout.

---

## Main View (two tabs, visible simultaneously with header)

### Header (sticky, always visible)

The header shows the team name and a short description. The description is tappable and opens a modal with more details. On the right, the user's name is shown and there is a button to open the Teams Panel.

---

### Shift Banner (below header, collapsible)

A horizontal strip below the header shows the current shift status. If a shift is active, it displays the start time and a button to end the shift. If no shift is active, it shows a button to start a shift. Tapping the banner (not the button) expands a panel with the team status.

---

### Status Panel (collapsed by default, slides open from banner)

The status panel lists all team members. Each row shows a colored dot for shift status, the member's name, and their last activity time or status. Members are sorted by activity (active first).

---

### Pinned Note (always visible, below banner/status panel)

A card displays a pinned note for the team. There is a label and an edit button. The note content is shown, or a placeholder if empty. Editing opens a modal to update the note.

---

### Tabs (sticky, below pinned note)

There are two tabs: "Registrar" and "Línea de tiempo". The user can switch between them. The active tab is highlighted.

---

## "Registrar" Tab (Quick Event Grid)

This panel shows a grid of event type buttons (e.g., Medicamento, Comida, Baño, Glucosa). Each button represents an activity. Clicking a button opens a modal to log an event of that type. If no event types are configured, a message is shown. If the user has no teams, a message explains how to join or create one.

---

## "Línea de tiempo" Tab (Timeline)

This panel shows a chronological feed of the last 50 care events logged by any team member. Each item shows the event icon, event type name, time, value (if present), caregiver name, and an optional note. If there are no events, a message is shown.

---

## Event Logging Modal (Bottom Sheet)

When an event type is selected, a modal appears for logging the event. The modal includes:
- A title with the event icon and name, and a close button.
- A field for the event value, which can be one of: boolean toggle, dropdown, multi-select, numeric input, or text area, depending on the event type.
- A datetime field (always shown), pre-filled with the current time.
- An optional comment field (for all except text type).
- A save button to submit the event. The button is disabled while saving.

---

## End Shift Confirmation Modal (Bottom Sheet)

When ending a shift, a confirmation modal appears. It asks the user to confirm ending the shift and explains that this will be logged as an event. There is a confirm button to proceed.

---

## Pinned Note Editor Modal (Bottom Sheet)

This modal allows editing the pinned note. It includes a title, a hint that the note is visible to the whole team, a textarea pre-filled with the current note, and a save button.

---

## Teams Panel (Full-Screen Overlay)

The Teams Panel shows a list of all teams the user belongs to. Each team card shows the team name, role, description, and notification toggle. There are buttons to switch to a team or edit it (edit is only enabled for admins). There is also a button to create a new team. The panel footer has options for profile, contact, and logout.

---

## Create Team Modal (Bottom Sheet)

This modal allows the user to create a new team. It includes fields for the team name and an optional description/context, and a save button.

---

## Team Description Modal (Bottom Sheet)

This modal shows the full team description.

---

## Contact Modal (Centered Overlay)

This modal allows the user to contact support. It includes fields for phone, email, and comments, and a send button.

---

## Notification Popup (Top Banner)

A banner appears at the top of the screen to show notifications. It includes an icon, title, body text, time, and a dismiss button.

---

## Toast Notification

A floating message appears at the bottom center of the screen to provide feedback (e.g., success or error messages). It fades in and out automatically.

---

## Key UX Patterns to Preserve

- The header and tabs are sticky; content scrolls beneath them.
- Bottom sheets slide up from the bottom and use a dark overlay behind.
- The Teams Panel is a full-screen overlay with its own scroll context.
- Tap targets are large and finger-friendly.
- Navigation is through the gear panel and tabs only (no navigation bar).
- Toast messages are used for feedback instead of alert dialogs.
- Disabled states are visually distinct and not clickable.
