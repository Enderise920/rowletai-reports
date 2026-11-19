# RowletAI — pemasangan GitHub dan laporan terjadwal

Status: paket konfigurasi lokal. Belum ada repositori, runner GitHub, bucket, atau website yang diaktifkan. Paket ini menggunakan program yang sudah terpasang di PC; bukan installer program dari nol.

## 1. Buat repositori privat

Buat akun GitHub bila belum ada, kemudian repositori **Private**, misalnya `rowletai-reports`. Ekstrak ZIP paket ini dan unggah isinya ke branch utama, mempertahankan folder `.github/workflows` dan `automation`. Jangan hanya mengunggah ZIP. Jangan unggah seluruh folder kerja: cache, `.stockbit`, token, konfigurasi Telegram, dan data akun tetap lokal.

Workflow hanya menjalankan instalasi lokal yang sudah ditinjau, tanpa checkout kode pull request. Perubahan Python yang diunggah ke GitHub **tidak otomatis memperbarui program di PC**; salin perubahan yang sudah ditinjau ke instalasi PC sebelum menjalankan ulang.

## 2. Persiapkan PC yang saat ini memiliki akses Stockbit

Gunakan Windows ARM64 dan akun Windows yang sama dengan instalasi Stockbit saat ini. Pertahankan struktur folder saudara `idx_trader_improved`, `stockbit-mcp`, dan `stockbit_runtime`. Jangan memindahkan atau menghapus cache.

Dari PowerShell di folder `idx_trader_improved`:

```powershell
& .webvenv/Scripts/python.exe -m pip install -r automation/requirements.txt
& .webvenv/Scripts/python.exe automation/run_daily.py --app-dir . --check
```

`--check` memeriksa berkas dan dependensi; tidak membuktikan sesi Stockbit masih berlaku. Gunakan `CEK_STOCKBIT.cmd` dan, bila diminta, `LOGIN_STOCKBIT.cmd` pada PC tersebut. Jangan memasukkan token Stockbit ke GitHub.

Di GitHub: Settings → Actions → Runners → New self-hosted runner. Pilih Windows ARM64 dan ikuti perintah resmi yang ditampilkan GitHub. Pasang runner di folder terpisah dari program. Tambahkan label **rowlet-idx** selain label bawaan `self-hosted`, `Windows`, `ARM64`. Jalankan runner sebagai pengguna Windows yang sama; untuk awal, gunakan proses interaktif yang tetap menyala. Jangan membagikan token pendaftaran runner.

## 3. Konfigurasikan Actions

Settings → Secrets and variables → Actions → Variables:

| Nama | Isi |
|---|---|
| ROWLET_APP_DIR | Path absolut folder `idx_trader_improved` pada PC |
| ROWLET_ENABLED | `true`, setelah instalasi dan runner siap |

Workflow menjalankan pemeriksaan dan laporan setiap Senin–Jumat pukul **19.15 dan 21.15 WIB**. PC harus menyala, terhubung internet, dan runner aktif. Jadwal GitHub bisa terlambat; bukan jaminan waktu tepat. Run workflow manual juga tersedia, tetapi proses melewati akhir pekan dan jam sebelum 19.00 WIB.

Tanggal data IHSG harus sama dengan tanggal Jakarta saat proses dimulai. Minimal 75% cakupan saham harus berada pada tanggal itu; semua NEW BUY harus bertanggal sama dan umur nol. Hari libur bursa atau data belum siap menghasilkan `data_not_ready`, tanpa mengubah PDF terakhir. Tidak ada label tanggal baru untuk data lama.

Hasil lokal:
- `output/daily/YYYY-MM-DD.pdf`: laporan.
- `output/daily/status.json`: status percobaan terbaru.
- `output/daily/published/latest.json`: penunjuk laporan terakhir yang berhasil diterbitkan.

Jika status `stockbit_login_required`, login kembali secara lokal lalu jalankan ulang. Sesi tidak dijamin berlaku selamanya. Data tambahan yang tidak tersedia tetap diberi keterangan oleh pembuat laporan. Program tidak mengirim pesan Telegram.

## 4. Opsional: penyimpanan privat untuk akses online

Tanpa langkah ini, PDF tersimpan di PC saja. Untuk website terpisah, gunakan bucket S3 atau kompatibel S3 yang **privat**. Penyedia, akun, dan biaya belum dipilih/disetujui.

Variables tambahan pada repo:
- `ROWLET_S3_BUCKET`: nama bucket.
- `ROWLET_S3_ENDPOINT`: URL endpoint penyedia; kosong untuk AWS S3.
- `ROWLET_S3_PREFIX`: misalnya `rowlet`.
- `AWS_DEFAULT_REGION`: region penyedia, misalnya region bucket AWS atau `auto` bila penyedia mewajibkannya.

Secrets pada repo:
- `ROWLET_STORAGE_ACCESS_KEY`
- `ROWLET_STORAGE_SECRET_KEY`

Batasi kredensial runner pada penulisan object di prefix tersebut. Hanya PDF, ringkasan laporan, dan status yang dikirim. Cache mentah dan kredensial Stockbit tidak dikirim. PDF menggunakan nama object unik, lalu `latest.json` baru diganti setelah seluruh unggahan berhasil. Terapkan lifecycle untuk object lama bila diperlukan.

## 5. Opsional: website pembaca laporan

`automation/viewer.py` adalah aplikasi FastAPI terpisah yang hanya membaca PDF. Jangan membuka server aplikasi lokal lama ke internet.

Pada hosting Python pilihan, pasang `automation/requirements-viewer.txt`. Konfigurasikan environment server:
- `ROWLET_VIEW_USER` dan `ROWLET_VIEW_PASSWORD` (minimal 16 karakter, simpan sebagai secret).
- Variabel bucket/endpoint/prefix/region seperti di atas.
- `AWS_ACCESS_KEY_ID` dan `AWS_SECRET_ACCESS_KEY`: kredensial **baca saja**, terpisah dari runner.

Perintah start dari folder induk `automation`:

```text
python -m uvicorn automation.viewer:app --host 0.0.0.0 --port 8000
```

Gunakan HTTPS dari hosting/reverse proxy sebelum akses internet, karena login memakai HTTP Basic. Jangan gunakan GitHub Pages untuk menjalankan backend Python ini. Website tidak menyimpan login Stockbit dan tidak memicu screening.

Untuk pemeriksaan lokal tanpa bucket, set `ROWLET_REPORT_DIR` ke path absolut `output/daily/published`, set akun viewer, dan jalankan uvicorn dengan `--host 127.0.0.1`. Jangan mengunggah folder ini ke repo.

## Pengujian dan batas

Pengujian lokal mencakup publikasi, checksum, penolakan path berbahaya, tanggal/cakupan data, serta akses viewer. Pengujian tidak membuktikan konektivitas GitHub, bucket, hosting, atau login Stockbit aktif. Integrasi penuh perlu dijalankan setelah layanan tersebut tersedia.

```powershell
& .webvenv/Scripts/python.exe -m unittest automation.test_automation -v
```

## Referensi resmi

- https://docs.github.com/en/actions/reference/runners/self-hosted-runners
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
- https://docs.github.com/en/actions/reference/security/secure-use
- https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html
