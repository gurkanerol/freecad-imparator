# FreeCAD Imparator 🚀

[![Version](https://img.shields.io/badge/version-2026.5.35-blue)](https://github.com/gurkanerol/freecad-imparator/releases)
[![Blender](https://img.shields.io/badge/Blender-4.2%2B-orange)](https://www.blender.org)
[![FreeCAD](https://img.shields.io/badge/FreeCAD-0.21%2B-red)](https://www.freecad.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

🇬🇧 [English](#english) &nbsp;|&nbsp; 🇹🇷 [Türkçe](#turkce)

---

<a name="english"></a>
## 🇬🇧 English

> **A robust Blender addon for importing FreeCAD (.fcstd) files — preserving full assembly hierarchy, materials, hidden objects, and real-world scale.**

### ✨ Features

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

### 📦 Installation

1. Download the latest `.zip` from [Releases](https://github.com/gurkanerol/freecad-imparator/releases)
2. Open Blender → `Edit > Preferences > Add-ons`
3. Click **Install from Disk** and select the downloaded `.zip`
4. Enable **Import-Export: FreeCAD Imparator** from the list

### ⚙️ Configuration (Required)

Set your **FreeCAD executable path** in the Addon Preferences:

| OS | Typical Path |
|---|---|
| **macOS** | `/Applications/FreeCAD.app/Contents/Resources/bin/python` |
| **Windows** | `C:\Program Files\FreeCAD 0.21\bin\python.exe` |
| **Linux** | `freecadcmd` or `/usr/lib/freecad/bin/python` |

### 🚀 Usage

**Via File Menu:** `File > Import > FreeCAD (.fcstd)`

**Via Sidebar:** Press `N` in the 3D Viewport → open the **FreeCAD** tab

| Option | Description | Default |
|---|---|---|
| **Quality (Deflection)** | Mesh tessellation precision in mm. Lower = smoother | `0.1` |
| **Scale** | Mapping ratio from FreeCAD mm to Blender units | `1:1000 (Real Metric)` |
| **BMesh** | Dissolve coplanar triangles into clean N-gons | `✓ On` |

### 🏗 How It Works

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
     │   • Routes hidden objects → "Hidden Geometry" collection
     │   • Assigns Principled BSDF materials
     │   • Auto-sets scene units to Millimeters
     ▼
Blender Scene ✓
```

### 📜 Changelog

**v2026.5.35** *(Latest)*
- Hidden objects → `Hidden Geometry` collection (viewport visibility untouched)
- Hidden object parent hierarchy preserved
- Blender scene units auto-set to Millimeters on import
- Scale dropdown: 1:1 / 1:10 / 1:50 / 1:100 / 1:1000
- Compact sidebar UI with icon-only buttons
- Path label removed from sidebar

---

<a name="turkce"></a>
## 🇹🇷 Türkçe

> **FreeCAD (.fcstd) dosyalarını tam montaj hiyerarşisi, materyaller, gizli objeler ve gerçek dünya ölçeğiyle Blender'a aktaran güçlü bir eklenti.**

### ✨ Özellikler

| Özellik | Açıklama |
|---|---|
| 🗂 **Tam Hiyerarşi Koruması** | FreeCAD'deki klasör ve grup yapısı Blender'a Empty (Locator) objeler olarak aktarılır |
| 📐 **Doğru Koordinatlar** | Mutlak global konumlar hesaplanır — parçalar dağılmaz veya kayaya kaçmaz |
| 🙈 **Gizli Obje Desteği** | FreeCAD'de gizli objeler silinmez, `Hidden Geometry` koleksiyonuna alınır; görünürlük senin elinde |
| 📏 **Ölçek Seçici** | Açılır menüden 1:1, 1:10, 1:50, 1:100 veya 1:1000 (Gerçek Metrik) seçimi |
| 🔢 **Otomatik Sahne Birimi** | İlk import sonrası Blender sahne birimi otomatik olarak Milimetreye ayarlanır |
| 🔵 **BMesh N-Gon Temizliği** | Aynı düzlemdeki gereksiz üçgenler eritilerek temiz N-gon yüzeyler elde edilir |
| 🎨 **Materyal ve Şeffaflık** | FreeCAD ShapeColor değerleri otomatik olarak Principled BSDF materyallerine dönüştürülür |
| 🔄 **Tekil Yenileme (Reload)** | Sahneyi bozmadan her dosyayı ayrı ayrı yeniden yükle |
| 🎛 **Kompakt Sidebar** | İkon bazlı butonlar; BMesh ve işlemler üst satırda, Quality ve Scale alt satırda |
| 📍 **Küçük Locator Boyutu** | Pivot (Empty) boyutu 0.5 — ekranı kapatan devasa eksenler yok |

### 📦 Kurulum

1. [Releases](https://github.com/gurkanerol/freecad-imparator/releases) sayfasından güncel `.zip` dosyasını indir
2. Blender → `Edit > Preferences > Add-ons` yolunu izle
3. **Install from Disk** butonuna tıkla ve indirdiğin `.zip` dosyasını seç
4. Listeden **Import-Export: FreeCAD Imparator** eklentisini bulup aktifleştir

### ⚙️ Yapılandırma (Zorunlu)

Eklentiyi aktif ettikten sonra **FreeCAD çalıştırılabilir dosya yolunu** Addon Preferences içinde ayarla:

| İşletim Sistemi | Tipik Yol |
|---|---|
| **macOS** | `/Applications/FreeCAD.app/Contents/Resources/bin/python` |
| **Windows** | `C:\Program Files\FreeCAD 0.21\bin\python.exe` |
| **Linux** | `freecadcmd` veya `/usr/lib/freecad/bin/python` |

### 🚀 Kullanım

**Dosya Menüsünden:** `File > Import > FreeCAD (.fcstd)`

**Yan Menüden (Sidebar):** 3D Viewport'ta `N` tuşuna bas → **FreeCAD** sekmesine geç

| Seçenek | Açıklama | Varsayılan |
|---|---|---|
| **Quality (Deflection)** | Yüzey kalitesi (mm). Küçüldükçe pürüzsüzlük artar | `0.1` |
| **Scale** | FreeCAD mm → Blender birimi dönüşüm oranı | `1:1000 (Gerçek Metrik)` |
| **BMesh** | Üçgenleri temiz N-gon yüzeylere dönüştür | `✓ Açık` |

### 📜 Sürüm Notları

**v2026.5.35** *(Son Sürüm)*
- Gizli objeler → `Hidden Geometry` koleksiyonu (görünürlük ayarına dokunulmaz)
- Gizli objelerin parent klasör hiyerarşisi korunuyor
- Import sonrası Blender sahne birimi otomatik Milimetre oluyor
- Scale açılır menüsü: 1:1 / 1:10 / 1:50 / 1:100 / 1:1000
- Kompakt sidebar — ikon bazlı butonlar
- Sidebar'dan gereksiz Path yazısı kaldırıldı

---

## 👤 Author / Geliştirici

**gurkanerol** — [gurkanerol@gmail.com](mailto:gurkanerol@gmail.com)

---

*Built with ❤️ for the FreeCAD + Blender community.*
