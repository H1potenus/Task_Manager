# Verimlilik Merkezi

Python + customtkinter ile yazılmış görev yönetimi ve Pomodoro/süreölçer uygulaması.
Tüm veriler yerel SQLite veritabanında (`veriler/verimlilik.db`) saklanır.

## Kurulum ve çalıştırma

```bash
pip install -r requirements.txt
python main.py
```

## Dosya yapısı

```
main.py                  Giriş noktası
app/
  database.py            SQLite katmanı (Categories, Tasks, TimeLogs, Settings)
  timer_logic.py         Arayüzden bağımsız zamanlayıcı motoru
  sound.py               Uyarı melodileri (winsound, ayrı iş parçacığında)
  utils.py               Türkçe harf/sıralama, tarih ve süre yardımcıları
  ui/
    main_window.py       Ana pencere (üst çubuk + iki panel)
    task_panel.py        Sol panel: görevler / alt görevler
    timer_panel.py       Sağ panel: kategoriler + zamanlayıcı
    stats_window.py      İstatistik penceresi (matplotlib)
    settings_window.py   Ayarlar penceresi
    dialogs.py           Türkçe butonlu diyaloglar
    theme.py             Renkler ve yazı tipleri
```

## Kullanım

- **Görev ekleme:** Görev adını yaz, istersen son tarihi gir (`15.10.2026`, `bugün`, `yarın`), Enter veya **+ Ekle**.
- **Tamamlama:** Görevin adına ya da kutucuğuna tıkla. Tamamlanan görev üzeri çizili olarak en alta iner;
  ana görev tamamlanınca alt görevleri de tamamlanır.
- **Son tarih uyarısı:** Süresi geçen ya da yaklaşan (varsayılan 2 gün) görevler kırmızı ve `!` ile gösterilir.
- **Zamanlayıcı:** Kategori seç → **Başlat** → **Duraklat** → **Devam Et**. **Bitir ve Kaydet** geçen süreyi
  seçili kategoriye bugünün tarihiyle kaydeder. Pomodoro'da çalışma süresi bitince süre otomatik kaydedilir,
  melodi çalar ve mola başlar.
- Oturum sürerken uygulamayı kapatırsan geçen çalışma süresi yine kaydedilir.
