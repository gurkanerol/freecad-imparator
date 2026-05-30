# FreeCAD Imparator 🚀

**FreeCAD Imparator**, FreeCAD (.fcstd) montaj ve parça dosyalarını, geometri hiyerarşisini, koordinatları ve materyalleri koruyarak doğrudan Blender içerisine aktarmanızı sağlayan güçlü bir Blender Eklentisidir (Addon).

Bu proje, orijinal CAD dosyası içindeki "Gizli/İşlem Gören" (Intermediate) eskizleri yoksayarak yalnızca ana geometrileri (Mesh ve Part özelliklerini) akıllıca tarar, onları Blender'ın metrik ve "Z-Up" sistemine milimi milimine çevirir ve mükemmel ağ yapılarıyla (BMesh/N-Gon) sahnenize dâhil eder.

---

## 🌟 Temel Özellikler

1. **Akıllı Hiyerarşi Koruması:**
   FreeCAD'deki karmaşık klasörleme ve gruplama (Assembly) sisteminiz Blender'a boş (Empty) objeler yardımıyla birebir aktarılır.

2. **Kusursuz Koordinat Eşlemesi:**
   Parçaların FreeCAD içerisindeki "Mutlak Global (Dünya) Koordinatları" (Absolute Global Placements) hesaplanır. Lokal (Parent) kaynaklı kaymalar/offset'ler kusursuz bir matematikle çözülerek objelerin Blender'da parçalanması/dağılması önlenir.

3. **Otomatik Ölçü (Scale) ve Yön (Z-Up) Dönüşümü:**
   FreeCAD standartlarında *Milimetre (mm)* olan ölçek, dönüşüm esnasında arka planda `0.001` ile çarpılarak Blender'ın standart *Metre (m)* ölçeğine devasa büyüme olmadan yansıtılır. Yönelim olarak standart `Y-Forward, Z-Up` eksen yapısı uygulanır.

4. **BMesh ile Pürüzsüz N-Gon Yüzeyler:**
   Çoğu CAD dönüştürücüsünün yarattığı "üçgen kirliliği" (triangulation) çözülür. Blender'a gelen parçalar BMesh modülü sayesinde açı toleranslarına göre filtrelenir; aynı düzlemdeki gereksiz üçgen bağları eritilir ve temiz (N-Gon) yapılı, yumuşatılmış pürüzsüz yüzeyler elde edilir.

5. **Materyal ve Şeffaflık Desteği:**
   Standart FreeCAD "ShapeColor" değerleri okunarak otomatik olarak `Principled BSDF` materyalleri şeklinde atanır. Şeffaflık desteklenir. (Not: İleri seviye mimari "BIM/Arch - ShapeAppearance37" gibi ikili (binary) materyaller şu anda GUI gereksinimi sebebiyle doğrudan okunamaz, ancak parça geometrileri ve konumları güvenle aktarılır).

6. **Kolay Yenileme (Reload) Modülü:**
   Blender üzerinden FreeCAD dosyanızı bir kez içeri aktardıktan sonra, FreeCAD'de yapacağınız bir değişikliği "Reload" (Yenile) butonuna tıklayarak saniyeler içinde Blender'a çekebilirsiniz. 

---

## 🛠 Sistem Gereksinimleri ve Bağımlılıklar

* **Blender 4.0 veya üzeri:** (Eklenti en güncel özellikler ve modern `obj_import` fonksiyonu için optimize edilmiştir).
* **FreeCAD (0.20, 0.21 veya 0.22):** Sisteminizde kurulu olmalıdır. Dönüştürme işlemini kendi arka plan Python motorunu kullanarak yapar.

---

## 📥 Kurulum (Installation)

1. Bu deponun `releases` klasöründeki güncel `.zip` dosyasını indirin (Örn: `freecad_imparator_v2026.5.32.zip`).
2. Blender'ı açın. `Edit > Preferences > Add-ons` yolunu izleyin.
3. Sağ üst köşedeki aşağı bakan ok simgesine (veya **Install** butonuna) tıklayarak indirdiğiniz `.zip` dosyasını seçin.
4. Çıkan listeden `Import-Export: FreeCAD Imparator` eklentisini bularak yanındaki kutucuğu işaretleyip aktifleştirin.

---

## ⚙️ Yapılandırma (ÇOK ÖNEMLİ!)

Eklentiyi kurup aktif ettikten hemen sonra eklentinin ayar menüsüne girmeli ve sisteminizdeki **FreeCAD çalıştırılabilir (executable)** yolunu göstermelisiniz:

* **macOS için (Genellikle):** `/Applications/FreeCAD.app/Contents/Resources/bin/python` veya `/Applications/FreeCAD.app/Contents/MacOS/FreeCAD`
* **Windows için (Genellikle):** `C:\Program Files\FreeCAD 0.21\bin\python.exe`
* **Linux için:** `freecadcmd` veya `python3` (FreeCAD kütüphanelerine erişimi olan bir Python sürümü)

> Bu yol ayarlandığında, eklenti içindeki FreeCAD Python modüllerine otomatik olarak erişim sağlayacaktır.

---

## 🚀 Kullanım

* **Dosya Menüsünden:** `File > Import > FreeCAD (.fcstd)`
* **Yan Menüden (Sidebar):** 3D Görüntüleme ekranında (Viewport) klavyeden `N` tuşuna basın. Açılan sağ menüden **FreeCAD** sekmesine geçin.

### Seçenekler
* **Mesh Quality (Deflection):** FreeCAD parçasının yüzey kalitesidir. Değer küçüldükçe pürüzsüzlük artar ama obje ağırlaşır (Varsayılan: `0.1` mm).
* **Clean N-Gons:** Yüzeylerdeki fazlalık üçgen çizgisini (edge) eriterek yüzeyin temiz bir çokgene dönüşmesini sağlar. Seçili kalması tavsiye edilir.

---

*(gurkanerol tarafından geliştirilmiştir - 2026)*
