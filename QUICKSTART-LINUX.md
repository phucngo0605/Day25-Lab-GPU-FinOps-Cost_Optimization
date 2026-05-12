# Quick Start - Linux

> Dùng hệ điều hành khác? Xem [`QUICKSTART-MAC.md`](QUICKSTART-MAC.md) (macOS) hoặc [`QUICKSTART-WINDOWS.md`](QUICKSTART-WINDOWS.md) (Windows/WSL).

## Yêu cầu trước khi bắt đầu

| Thứ cần chuẩn bị | Chi tiết | Bắt buộc? |
|-------------------|----------|-----------|
| **Docker Engine** | `sudo apt install docker.io docker-compose-plugin` (Ubuntu/Debian) hoặc tương đương. Docker Desktop cũng được. | **Bắt buộc** |
| **Quyền docker (không cần sudo)** | `sudo usermod -aG docker $USER` rồi đăng xuất & đăng nhập lại | **Bắt buộc** |
| **Tài khoản Kaggle** | Đăng ký miễn phí tại https://www.kaggle.com để chạy notebook | **Bắt buộc** |
| Python local | **Không cần** — tất cả services chạy trong Docker, notebook chạy trên Kaggle/Colab | Không cần |
| Python packages local | **Không cần** — notebook tự cài `requests`, `pandas`, `matplotlib`, `plotly`, `torch`, `torchvision`, `pynvml` trên Kaggle/Colab | Không cần |

> **Lưu ý:** `cloudflared` (tunnel) **miễn phí, không cần đăng ký tài khoản**.

## Tổng quan các bước

```
Terminal 1: Docker services    Terminal 2: Tunnel    Browser: Kaggle notebook
     │                              │                        │
     ▼                              ▼                        ▼
./run-linux.sh start         ./run-linux.sh tunnel    Paste URL → Run cells
```

---

## Bước 1: Cài tunnel tool (1 lần duy nhất)

```bash
# Debian / Ubuntu
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o /tmp/cloudflared.deb
sudo dpkg -i /tmp/cloudflared.deb

# Fedora / RHEL / CentOS
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-x86_64.rpm -o /tmp/cloudflared.rpm
sudo rpm -i /tmp/cloudflared.rpm

# Arch / Manjaro
yay -S cloudflared
# hoặc: sudo pacman -S cloudflared-bin
```

> Miễn phí, không cần đăng ký tài khoản.

---

## Bước 2: Start Docker services

Mở Terminal và chạy:

```bash
cd ~/Day\ 25-Track02-/gpu-finops-lab
./run-linux.sh start
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
./run-linux.sh tunnel
```

Kết quả thực tế (log mẫu):
```
./run-linux.sh tunnel

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
2026-05-12T15:58:25Z INF GOOS: linux, GOVersion: go1.26.1, GoArch: amd64
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
./run-linux.sh test
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
| `./run-linux.sh start` | Khởi động tất cả services |
| `./run-linux.sh tunnel` | Mở tunnel cho Kaggle/Colab |
| `./run-linux.sh stop` | Tắt tất cả |
| `./run-linux.sh status` | Xem trạng thái |
| `./run-linux.sh logs` | Xem logs (tất cả services) |
| `./run-linux.sh logs gateway` | Xem logs gateway thôi |
| `./run-linux.sh test` | Test tất cả endpoints |

---

## Troubleshooting

### Docker không chạy
```bash
sudo systemctl status docker
sudo systemctl start docker
sudo usermod -aG docker $USER
# Đăng xuất và đăng nhập lại để group mới có hiệu lực
```

### Port đã bị chiếm
```bash
# Xem ai đang dùng port 8000
sudo ss -tlnp | grep :8000
# hoặc
sudo fuser 8000/tcp
# Kill process đó
sudo kill -9 <PID>
```

### Tunnel không hiện URL
```bash
# Xem log trực tiếp
cat .tunnel.log
# Hoặc chạy thủ công
cloudflared tunnel --url http://localhost:8000
```

### Kaggle/Colab không connect được
- Kiểm tra tunnel còn chạy: `./run-linux.sh status`
- Cloudflared URL thay đổi mỗi lần chạy → phải copy URL mới
- Nếu dùng ngrok free, chỉ 1 tunnel tại 1 thời điểm

### Firewall chặn port
```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 8000/tcp

# Fedora/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

### Rebuild sau khi sửa code
```bash
./run-linux.sh stop
./run-linux.sh start    # tự rebuild
```

---

## Cấu trúc project

```
gpu-finops-lab/
├── run-linux.sh                ← Script điều khiển chính (Linux)
├── docker-compose.yml          ← Orchestrate services
├── QUICKSTART-LINUX.md         ← File này
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
