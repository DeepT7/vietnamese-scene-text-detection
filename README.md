# vietnamese-scene-text-detection
Quick start:

Bước 1: Tải thư viện PaddleOCR và giải nén theo đường dẫn sau: https://github.com/PaddlePaddle/PaddleOCR

Bước 2: Tải trained model the đường dẫn sau: https://drive.google.com/drive/folders/1G0ai7ivYfUiJcWppayDlWC9QZv-8PcQy?usp=sharing

Bước 3: Tạo lập file dẫn đến trained model như trong file utility_vn.py 

Detection text model : './PaddleOCR/inference/SAST/'

Recognition text model: './PaddleOCR/inference/SRN/'

Để xác định vị trí chữ trong ảnh hãy chạy file predict_det_vn.py

Để nhận diện chữ chạy file predict_rec_vn.py

Để xác định và detect đồng thời chuyển chữ trong ảnh thành giọng nói chạy file: predict_system_vn.py

Mình rất biết ơn đến bạn Cao Hùng đã giúp đõ mình rất nhiều để hoàn thành project này. 

Link bài viết của bạn: http://tutorials.aiclub.cs.uit.edu.vn/index.php/2022/04/20/nhan-dang-chu-tieng-viet-trong-anh-ngoai-canh/
