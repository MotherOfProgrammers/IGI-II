<div align="center">

# ⚡ IGI-RAMPAGE

### Project IGI 2 — Reimagined for Multiplayer

**Built and maintained by [GenIGI](#-team)**

Modern multiplayer enhancements. Fresh content. Classic IGI action.

[Overview](#-overview) · [Features](#-features) · [Requirements](#-requirements) · [Installation](#-installation) · [Project Structure](#-project-structure) · [Important Notes](#-important-notes)

</div>

---

## 🎯 Overview

**IGI-Rampage** is a GenIGI project focused on bringing a modernized multiplayer experience to **Project IGI 2**.

The goal is to expand the multiplayer side of the game with new content and gameplay options while preserving the original single-player campaign.

> 🛡️ **The original story and single-player campaign are not the target of this project.** IGI-Rampage focuses on multiplayer enhancements; it is not intended to rewrite the original storyline.

## ✨ Features

- 🌐 **Modernized Multiplayer** — work toward a more flexible online multiplayer experience.
- 🗺️ **New Maps** — additional environments for multiplayer matches.
- 🔫 **New Weapons and Weapon Skins** — expanded weapon variety and visual customization.
- 🪖 **New Characters and Character Skins** — more options for player appearance.
- 🎨 **Enhanced Graphics** — visual improvements aimed at multiplayer.
- 🏃 **New Movements and Combat Tactics** — additional ways to move and engage.
- 🧰 **Development Tools** — project utilities for inspecting, preparing, and working with game data.

*Feature availability depends on the current development and release version.*

## 💻 Requirements

Before getting started, make sure you have:

- **Operating system:** Windows
- **Python:** 3.13 or newer
- **Game:** A working copy of Project IGI 2
- **Project files and tools:** The required directory structure shown below

## 🚀 Installation

These steps prepare the development environment. They do **not** describe a player-facing game installation.

1. **Open a terminal** in the IGI-Rampage project directory.
2. **Install the Python dependencies:**

   ```bash
   python -m pip install -r requirements.txt
   ```

3. **Run the preparation script:**

   ```bash
   python prep.py
   ```

4. **Check the result.** If the script reports **`Preparation Successful`** and **`Ready To Go!`**, the preparation step has completed successfully.

5. **Continue development** using the project's scripts and tools.

> **Troubleshooting:** If preparation fails, verify that Python is installed and available on your `PATH`, dependencies installed without errors, and the required folders and converter files are in the expected locations.

## 🗂️ Project Structure

The project expects the following directory layout. Some folders contain generated or collected game data and may need to be prepared before running the tools.

```text
IGI-Rampage/
├── igi2_collected/
├── igi2_converted/
├── igi2conv-windows-x86_64-qt-r9/
│   └── igi2conv/
│       └── igi2conv.exe
├── out/
│   ├── weapon_data/
│   │   └── {WEAPON_ID}/
│   │       ├── {WEAPON_ID}.json
│   │       ├── {WEAPON_ID}.qsc
│   │       └── {MOD_VERSION}/
│   │           └── {WEAPON_ID}.qsc
│   └── weapon_textures/
│       └── {WEAPON_ID}/
│           ├── {WEAPON_ID}.0.tga
│           ├── {WEAPON_ID}_pickup.0.tga
│           ├── {WEAPON_ID}.png
│           ├── {WEAPON_ID}_pickup.png
│           └── {MOD_VERSION}/
│               ├── {WEAPON_ID}.0.tga
│               ├── {WEAPON_ID}_pickup.0.tga
│               ├── {WEAPON_ID}.png
│               └── {WEAPON_ID}_pickup.png
├── src/
│   ├── core/
│   │   ├── weapon_parsers/
│   │   │   ├── decode_weapon_textures.py
│   │   │   └── diff_weapon_data.py
│   │   ├── player_parsers/
│   │   ├── world_parsers/
│   │   ├── multiplayer/
│   │   └── utils/
│   ├── debugs/
│   │   └── debug_symbols.py
│   └── banners/
│       └── banner.py
├── drit/                         # Data Route Index Tree
│   ├── weapons_drit.txt
│   ├── player_drip.txt
│   ├── world_drit.txt
│   └── multiplayer_drit.txt
├── igipy.json
├── prep.py
├── main.py
├── weapon_data_info.txt
├── requirements.txt
└── README.md
```

### 📁 Directory guide

| Path | Purpose |
|---|---|
| `igi2_collected/` | Collected source game data used by the project tools. |
| `igi2_converted/` | Converted game data used during development. |
| `igi2conv-windows-x86_64-qt-r9/` | IGI 2 conversion utility and its executable. |
| `out/weapon_data/` | Weapon data files and versioned QSC files. |
| `out/weapon_textures/` | Weapon textures, pickup textures, and versioned assets. |
| `src/core/` | Core parsing and multiplayer-related development modules. |
| `src/debugs/` | Debugging utilities. |
| `src/banners/` | Terminal banner utilities. |
| `drit/` | Data Route Index Tree files for weapons, players, worlds, and multiplayer. |
| `prep.py` | Prepares the development environment. |
| `main.py` | Main project entry point. |
| `requirements.txt` | Python dependency list. |

> **Note:** The tree documents the intended layout. Empty or unfinished directories may not contain implementation files yet. Keep folder and file names consistent with the scripts in your checkout.

## 🛡️ Important Notes

- **Multiplayer-focused:** IGI-Rampage is intended to enhance multiplayer. The original single-player story and campaign are not intended to be changed by these multiplayer-focused features.
- **Developer repository:** This repository is intended for developers and contributors who understand Project IGI 2's file formats, assets, and technical workflow. It is **not** the recommended route for ordinary players who simply want to play.
- **Players:** Use the project's official published releases, when available, and follow their included installation instructions instead of running development scripts.
- **Back up your files:** Keep a clean backup of your game installation before testing modifications.
- **Respect ownership and permissions:** Project IGI 2 is a third-party game. This project is not a claim of ownership over the original game, its trademarks, or its assets. Use game files only where you have the right to do so, and follow the game's applicable terms and local law.
- **No guarantee of compatibility:** Compatibility can vary by game version, configuration, and mod release. Check the notes provided with each release.
- **No unsupported promises:** Features listed here describe the project's goals and development areas; they do not guarantee that every feature is complete in every build.

## 🤝 Contributing

Contributions, testing, bug reports, and practical suggestions can help improve IGI-Rampage.

1. Review the project structure and current scripts.
2. Test changes against a backed-up game installation.
3. Keep changes focused and document any new setup requirements.
4. Report reproducible issues with the steps, expected behavior, and actual behavior.

## 👥 Team

**IGI-Rampage is handled by GenIGI.**

Built for the community of Project IGI 2 fans who want to explore new possibilities for multiplayer.

---

<div align="center">

**⚡ IGI-RAMPAGE · Multiplayer evolves. The original mission remains.**

</div>
