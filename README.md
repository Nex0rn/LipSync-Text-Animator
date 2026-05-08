# LipSync Text Animator

A Blender 4.1 add-on that converts plain text into mouth animations on a bone-based armature — no shape keys, no manual keyframing. Type your text, assign a pose to each letter, and let the add-on write every keyframe for you.

---

## Features

- **Bone-based** — works directly on armature pose bones, no shape key setup required
- **Per-character pose mapping** — record the exact bone positions for every letter with a single button click
- **Vowel / Consonant / Space timing** — set independent frame durations for each character class, plus a global speed multiplier
- **Direct FCurve writing** — bypasses Blender's animation evaluator entirely, so every character gets its own unique keyframe without interference
- **Latin + Turkish alphabet** — full support for Turkish characters (ğ, ü, ş, ı, ö, ç) alongside standard English
- **Pose library** — export all saved poses to a JSON file and import them into any other project

---

## Requirements

- Blender **4.1** or newer

---

## Installation

1. Download `lipsync_addon.py`
2. Open Blender and go to `Edit → Preferences → Add-ons`
3. Click **Install**, select the downloaded file, and confirm
4. Enable the add-on by checking the box next to **LipSync Text Animator**
5. The panel appears in the **3D Viewport → N (Sidebar) → LipSync** tab

---

## How to Use

### Step 1 — Select your armature

Click on your character's armature in the viewport. The panel header will confirm the selected armature name. The **Generate Animation** button stays disabled until an armature is active.

### Step 2 — Record a pose for each letter

1. Switch to **Pose Mode** and shape your character's mouth for a given letter
2. In the LipSync panel, type the letter into the **Char** field (use `_` for a space/pause)
3. Click **Save Current Pose**
4. Repeat for every character you want to animate

A small grid at the bottom of the mapping section shows all characters that have a pose recorded. You can click the eye icon next to the Char field at any time to preview a saved pose in the viewport.

### Step 3 — Set frame durations

| Setting | Default | Description |
|---|---|---|
| Vowel (frames) | 4 | Duration held for vowel characters |
| Consonant (frames) | 2 | Duration held for consonant characters |
| Space (frames) | 6 | Duration held for space/pause |
| Speed Multiplier | 1.0 | Scales all durations (0.5 = 2× faster, 2.0 = 2× slower) |

### Step 4 — Generate the animation

1. Type your text into the **Text** field
2. Move the timeline cursor to the frame where you want the animation to start
3. Click **Generate Animation**

The add-on writes a keyframe for each character's pose at the correct frame, advances by the appropriate duration, and moves on to the next character. Characters with no saved pose are skipped (you'll see a warning listing which ones were missed).

---

## Pose Library

Poses are stored inside the Blender scene, but you can export and re-use them across projects.

| Button | Action |
|---|---|
| **Export** | Saves all recorded poses to a `.json` file |
| **Import** | Loads poses from a `.json` file into the current scene |

This lets you build a reusable mouth-pose library for a character rig and share it with collaborators or use it in future projects without re-recording everything.

---

## Tips

- **Record poses in Pose Mode** — the add-on reads the live bone transforms, so make sure your rig is in Pose Mode when you click Save Current Pose
- **All bones are saved** — every bone in the armature is included in each pose snapshot. If you only want mouth bones to move, set all other bones to their rest position before saving
- **Undo support** — Generate Animation is fully undoable with `Ctrl+Z`
- **Non-letter characters** — punctuation, numbers, and any character outside the supported alphabet are silently skipped; the timeline simply advances past them without writing a keyframe
- **Existing actions** — if the armature already has an action, keyframes are added to it rather than creating a new one. You can rename or manage actions in the NLA Editor as usual

---

## Supported Characters

The add-on recognises the following characters:

**Vowels** (longer default duration)
`a e ı i o  u ` and their uppercase variants

**Consonants** (shorter default duration)
`b c  d f g h j k l m n p r s t v y z` and their uppercase variants

**Space** — use a literal space in your text, or `_` in the Char field when recording the rest pose

---

## License

MIT — free to use, modify, and distribute.
