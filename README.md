# RowletAI Reports

Paket otomatisasi laporan IDX untuk instalasi RowletAI yang sudah ada di PC Windows ARM64.

## Mulai

Ikuti [panduan pemasangan](PANDUAN_GITHUB.md). Daftarkan self-hosted runner dengan label `rowlet-idx` dan isi repository variable `ROWLET_APP_DIR` dengan path instalasi lokal. Aktifkan `ROWLET_ENABLED=true` setelah runner siap.

Jadwal: Senin–Jumat, 19.15 dan 21.15 WIB. PC dan runner harus aktif. Data sesi belum siap atau login Stockbit gagal tidak menggantikan PDF terakhir.

Repositori ini berisi paket otomatisasi, bukan seluruh aplikasi screening. Workflow menjalankan program di PC tanpa checkout; pembaruan kode perlu disalin ke instalasi lokal setelah ditinjau.

## Isi

- `.github/workflows/daily-report.yml`: jadwal dan pemicu manual.
- `automation/run_daily.py`: validasi, pembuatan, dan publikasi laporan.
- `automation/delivery.py`: penyimpanan lokal atau bucket privat S3.
- `automation/viewer.py`: pembaca PDF dengan login, opsional untuk hosting Python.
- `automation/test_automation.py`: pengujian lokal.

Tidak ada token, cookie Stockbit, atau cache akun dalam paket ini. Website dan runner belum aktif hanya dengan mengunggah berkas.

Created by RowletAI. Not a Recommendation to Buy or Sell. Just for research only.
