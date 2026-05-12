# Quick Start - macOS

> Dùng hệ điều hành khác? Xem [`QUICKSTART-WINDOWS.md`](QUICKSTART-WINDOWS.md) (Windows/WSL) hoặc [`QUICKSTART-LINUX.md`](QUICKSTART-LINUX.md) (Linux).

## Yêu cầu trước khi bắt đầu

| Thứ cần chuẩn bị | Chi tiết | Bắt buộc? |
|-------------------|----------|-----------|
| **Docker Desktop** | Cài từ https://docs.docker.com/desktop/setup/install/mac-install/ | **Bắt buộc** |
| **Tài khoản Kaggle** | Đăng ký miễn phí tại https://www.kaggle.com để chạy notebook | **Bắt buộc** |
| Homebrew | Để cài `cloudflared` ở Bước 1. Nếu chưa có: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"` | Khuyến nghị |
| Python local | **Không cần** — tất cả services chạy trong Docker | Không cần |
| Python packages local | **Không cần** — notebook tự cài `requests`, `pandas`, `matplotlib`, `plotly`, `torch`, `torchvision`, `pynvml` trên Kaggle/Colab | Không cần |

> **Lưu ý:** `cloudflared` (tunnel) **miễn phí, không cần đăng ký tài khoản**.

## Tổng quan các bước

```
Terminal 1: Docker services    Terminal 2: Tunnel    Browser: Kaggle notebook
     │                              │                        │
     ▼                              ▼                        ▼
./run.sh start              ./run.sh tunnel          Paste URL → Run cells
```

---

## Bước 1: Cài tunnel tool (1 lần duy nhất)

```bash
brew install cloudflare/cloudflare/cloudflared
```

> Miễn phí, không cần đăng ký tài khoản.

---

## Bước 2: Start Docker services

Mở Terminal và chạy:

```bash
cd ~/Day\ 25-Track02-/gpu-finops-lab
./run.sh start
```

Kết quả mong đợi:
```
[STEP] 1/3 - Checking Docker...
  Docker is running
[STEP] 2/3 - Building and starting services...
[STEP] 3/3 - Waiting for services to be healthy...
  Gateway is UP at http://localhost:8000

==========================================
 ALL SERVICES RUNNING
==========================================
```

> Lần đầu build sẽ mất ~2-3 phút. Lần sau chỉ ~5 giây.

---

## Bước 3: Mở tunnel

Trong **cùng terminal** hoặc terminal mới:

```bash
cd ~/Day\ 25-Track02-/gpu-finops-lab
./run.sh tunnel
```

Kết quả thực tế (log mẫu):
```
./run.sh tunnel

[STEP] Starting tunnel to expose gateway...
[INFO] Using cloudflared (free, no account needed)
  Starting tunnel...
2026-05-12T15:58:22Z INF Thank you for trying Cloudflare Tunnel. Doing so, without a Cloudflare account,
  is a quick way to experiment and try it out. However, be aware that these account-less Tunnels have
  no uptime guarantee...
2026-05-12T15:58:22Z INF Requesting new quick Tunnel on trycloudflare.com...

2026-05-12T15:58:25Z INF +--------------------------------------------------------------------------------------------+
2026-05-12T15:58:25Z INF |  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |
2026-05-12T15:58:25Z INF |  https://<your-random-subdomain>.trycloudflare.com                            |
2026-05-12T15:58:25Z INF +--------------------------------------------------------------------------------------------+

2026-05-12T15:58:25Z INF Version 2026.3.0
2026-05-12T15:58:25Z INF GOOS: darwin, GOVersion: go1.26.1, GoArch: arm64
2026-05-12T15:58:25Z INF Settings: map[ha-connections:1 protocol:quic url:http://localhost:8000]
2026-05-12T15:58:35Z INF Initial protocol quic
2026-05-12T15:58:45Z INF Registered tunnel connection connIndex=0 location=hkg01 protocol=quic
```

> **URL nằm ở dòng có `trycloudflare.com`** — copy URL đó paste vào notebook.
>
> Các dòng `ERR Failed to refresh DNS` ở cuối là bình thường, **không ảnh hưởng** tunnel.

Nếu script hiện URL thành công:
```
==========================================
 TUNNEL ACTIVE
==========================================

  URL: https://<your-random-subdomain>.trycloudflare.com

  Copy this URL into your Kaggle/Colab notebook:
  GATEWAY_URL = "https://<your-random-subdomain>.trycloudflare.com"
```

---

## Bước 4: Test nhanh (optional)

```bash
./run.sh test
```

```
  [OK] GET /
  [OK] GET /cluster/nodes
  [OK] GET /cluster/metrics
  [OK] GET /billing/pricing
  [OK] GET /spot/pricing
  [OK] GET /autoscaler/policy
  [OK] GET /cost/dashboard
```

---

## Bước 5: Upload & chạy notebook trên Kaggle

1. Vào https://www.kaggle.com → **New Notebook**
2. Upload file `notebook/gpu_finops_lab.ipynb`
3. Settings → **Accelerator** → **GPU T4 x2** (hoặc P100)
4. Trong **Cell 2**, thay URL:
   ```python
   GATEWAY_URL = "https://abc-xyz-123.trycloudflare.com"  # URL từ bước 3
   ```
5. **Run All Cells**

---

## Các lệnh hữu ích

| Lệnh | Mô tả |
|-------|--------|
| `./run.sh start` | Khởi động tất cả services |
| `./run.sh tunnel` | Mở tunnel cho Kaggle/Colab |
| `./run.sh stop` | Tắt tất cả |
| `./run.sh status` | Xem trạng thái |
| `./run.sh logs` | Xem logs (tất cả services) |
| `./run.sh logs gateway` | Xem logs gateway thôi |
| `./run.sh test` | Test tất cả endpoints |

---

## Troubleshooting

### Docker không chạy
```bash
open -a Docker    # Mở Docker Desktop
# Đợi 10-20s rồi chạy lại ./run.sh start
```

### Port đã bị chiếm
```bash
# Xem ai đang dùng port 8000
lsof -i :8000
# Kill process đó
kill -9 <PID>
```

### Tunnel không hiện URL
```bash
# Xem log trực tiếp
cat .tunnel.log
# Hoặc chạy thủ công
cloudflared tunnel --url http://localhost:8000
```

### Kaggle/Colab không connect được
- Kiểm tra tunnel còn chạy: `./run.sh status`
- Cloudflared URL thay đổi mỗi lần chạy → phải copy URL mới
- Nếu dùng ngrok free, chỉ 1 tunnel tại 1 thời điểm

### Rebuild sau khi sửa code
```bash
./run.sh stop
./run.sh start    # tự rebuild
```

---

## Cấu trúc project

```
gpu-finops-lab/
├── run.sh                      ← Script điều khiển chính
├── docker-compose.yml          ← Orchestrate services
├── QUICKSTART-MAC.md           ← File này
├── README.md                   ← Tài liệu đầy đủ
├── notebook/
│   └── gpu_finops_lab.ipynb    ← Upload lên Kaggle/Colab
└── services/
    ├── gateway/                ← API Gateway (port 8000)
    ├── gpu-node-manager/       ← Mock GPU cluster (port 8001)
    ├── billing-api/            ← Mock billing (port 8002)
    ├── spot-manager/           ← Spot instances (port 8003)
    ├── autoscaler/             ← KEDA-like (port 8004)
    └── cost-tracker/           ← OpenCost-like (port 8005)
```
