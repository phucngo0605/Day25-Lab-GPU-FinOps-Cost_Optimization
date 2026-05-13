# GPU FinOps & Cost Optimization Lab Report

## Student Information

- Họ và tên: Ngô Quang Phúc
- MSSV: 2A202600477

## Mục tiêu

Bài lab mô phỏng quy trình GPU FinOps gồm giám sát GPU cluster, ghi nhận billing, tối ưu chi phí bằng spot instance, autoscaling, phát hiện waste, trực quan hóa chi phí và phân tích tối ưu nâng cao.

## Kết quả chính

- Local Docker Compose đã chạy đủ gateway và 5 service backend.
- Gateway được expose qua ngrok để notebook gọi API.
- Notebook đã chạy hoàn chỉnh và lưu output trong thư mục `notebook/`.
- Các biểu đồ bắt buộc đã được sinh trong `generated_charts/`.
- Screenshot từng phần đã được tạo trong `screenshots/`.

## Nhận xét FinOps

- Spot instance giúp giảm chi phí đáng kể nhưng cần checkpoint để giảm rủi ro preemption.
- Autoscaling giúp giảm idle GPU và giới hạn over-provisioning.
- Mixed precision/AMP giảm thời gian chạy và chi phí so với FP32.
- Phân tích multi-GPU cho thấy tăng số GPU không luôn tối ưu chi phí do hiệu suất scale giảm dần.
- Forecast và roadmap tối ưu giúp chọn các thay đổi có tỷ lệ savings/effort tốt trước.

## Ghi chú môi trường

Phần real GPU được chạy local trên Windows với NVIDIA GPU phát hiện qua `nvidia-smi`. Do PyTorch CUDA package quá lớn và tải không ổn định trong môi trường local, notebook sử dụng chế độ local telemetry và workload simulation để tạo kết quả FP32/AMP, cost report và biểu đồ.
