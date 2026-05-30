# FreeCAD Imparator 🚀

> **A robust Blender addon for importing FreeCAD (.fcstd) files — preserving full assembly hierarchy, materials, hidden objects, and real-world scale.**

[![Version](https://img.shields.io/badge/version-2026.5.35-blue)](https://github.com/gurkanerol/freecad-imparator/releases)
[![Blender](https://img.shields.io/badge/Blender-4.2%2B-orange)](https://www.blender.org)
[![FreeCAD](https://img.shields.io/badge/FreeCAD-0.21%2B-red)](https://www.freecad.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## ✨ Features

| Feature | Description |
|---|---|
| 🗂 **Full Assembly Hierarchy** | Folders and groups from FreeCAD are reconstructed as Empty (Locator) objects in Blender |
| 📐 **Accurate Coordinates** | Absolute global placements are computed — no broken offsets or scattered parts |
| 🙈 **Hidden Object Support** | Objects hidden in FreeCAD are imported into a separate `Hidden Geometry` collection, untouched |
| 📏 **Scale Selector** | Choose from 1:1, 1:10, 1:50, 1:100 or 1:1000 (Real Metric) via a clean dropdown |
| 🔢 **Auto Scene Units** | Blender scene units are automatically set to Millimeters on first import |
| 🔵 **BMesh N-Gon Cleanup** | Coplanar triangles are dissolved into clean flat N-gons |
| 🎨 **Materials & Transparency** | FreeCAD ShapeColor values are mapped to Principled BSDF materials automatically |
| 🔄 **Per-File Reload** | Reload any imported file individually without losing your Blender scene setup |
| 🎛 **Compact Sidebar UI** | Icon-only action buttons, Quality and Scale side-by-side in the N-Panel |
| 📍 **Small Locators** | Pivot (Empty) display size is 0.5 — no giant axes cluttering the viewport |

---

## 📦 Installation

1. Download the latest `.zip` from [Releases](https://github.com/gurkanerol/freecad-imparator/releases)
2. Open Blender → `Edit > Preferences > Add-ons`
3. Click **Install from Disk** and select the downloaded `.zip`
4. Enable **Import-Export: FreeCAD Imparator** from the list

---

## ⚙️ Configuration (Required)

After enabling the addon, set your **FreeCAD executable path** in the Addon Preferences:

| OS | Typical Path |
|---|---|
| **macOS** | `/Applications/FreeCAD.app/Contents/Resources/bin/python` |
| **Windows** | `C:\Program Files\FreeCAD 0.21\bin\python.exe` |
| **Linux** | `freecadcmd` or `/usr/lib/freecad/bin/python` |

> The addon spawns FreeCAD as a headless subprocess to parse geometry. The path must point to FreeCAD's bundled Python executable.

---

## 🚀 Usage

**Via File Menu:**
```
File > Import > FreeCAD (.fcstd)
```

**Via Sidebar (N-Panel):**
Press `N` in the 3D Viewport → open the **FreeCAD** tab

### Import Options

| Option | Description | Default |
|---|---|---|
| **Quality (Deflection)** | Mesh tessellation precision in mm. Lower = smoother, heavier | `0.1` |
| **Scale** | Mapping ratio from FreeCAD mm to Blender units | `1:1000 (Real Metric)` |
| **BMesh** | Dissolve coplanar triangles into clean N-gons | `✓ On` |

### Sidebar Panel (after import)

Each imported file gets its own entry with:
- **BMesh** toggle + **Select** and **Reload** icon buttons in the top row
- **Quality** and **Scale** selectors in the bottom row
- **Delete** button to remove the import record

---

## 🏗 How It Works

```
FreeCAD (.fcstd)
     │
     ▼  [Headless subprocess: fcstd_to_obj.py]
     │   • Parses GuiDocument.xml for visibility & colors
     │   • Computes absolute global placements
     │   • Exports geometry as .obj + companion .json
     │
     ▼  [Blender: __init__.py]
     │   • Imports .obj mesh objects
     │   • Reads .json hierarchy descriptor
     │   • Builds Empty (Locator) tree matching FreeCAD folders
     │   • Parents meshes to their correct containers
     │   • Assigns Principled BSDF materials
     │   • Routes hidden objects to "Hidden Geometry" collection
     │   • Auto-sets scene units to Millimeters
     ▼
Blender Scene ✓
```

---

## 📋 Requirements

- **Blender 4.2** or newer
- **FreeCAD 0.21** or newer (must be installed on the system)

---

## 🗂 Project Structure

```
freecad-imparator/
├── freecad_imparator/
│   ├── __init__.py          # Blender addon (UI + import logic)
│   └── fcstd_to_obj.py      # FreeCAD headless geometry exporter
├── releases/
│   └── freecad_imparator_v2026.5.35.zip
├── .gitignore
└── README.md
```

---

## 📜 Changelog

### v2026.5.35 *(Latest)*
- ✅ Hidden objects imported into `Hidden Geometry` collection (folder visibility untouched)
- ✅ Hidden object parent hierarchy preserved in `needed_containers`
- ✅ Blender scene units auto-set to Millimeters on import
- ✅ Scale dropdown: 1:1 / 1:10 / 1:50 / 1:100 / 1:1000
- ✅ Compact sidebar UI — icon-only buttons, BMesh + actions on top row
- ✅ Quality and Scale side-by-side on bottom row
- ✅ Path label removed from sidebar (name already shown in header)

### v2026.5.33–34
- Locator display size reduced to 0.5
- Empty group pruning (no orphan container folders)
- Double-transformation bug fixed via `parent_gp.Matrix` approach

---

## 👤 Author

**gurkanerol** — [gurkanerol@gmail.com](mailto:gurkanerol@gmail.com)

---

*Built with ❤️ for the FreeCAD + Blender community.*
