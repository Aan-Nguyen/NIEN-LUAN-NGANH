========================================================================
    ĐỒ ÁN NIÊN LUẬN NGÀNH AN TOÀN THÔNG TIN
    ĐỀ TÀI: NGHIÊN CỨU VÀ XÂY DỰNG ỨNG DỤNG KHÔI PHỤC DỮ LIỆU SỐ BỊ XÓA
========================================================================

I. THÔNG TIN CHUNG;
------------------
- Sinh viên thực hiện: Nguyễn Hữu Ân
- MSSV: B2203707
- Lớp: An Toàn Thông Tin - Khóa 48
- Giảng viên hướng dẫn: TS. Lâm Chí Nguyện
- Trường: Đại học Cần Thơ (CTU)
- Học kỳ: 1, Năm học: 2025-2026

II. GIỚI THIỆU
--------------
Digital Forensics Recovery Tool là ứng dụng hỗ trợ điều tra pháp y kỹ thuật số, 
cho phép tìm kiếm, xem trước và khôi phục các tập tin đã bị xóa trên thiết bị lưu trữ. 
Ứng dụng được viết bằng Python, sử dụng giao diện đồ họa PyQt5, hỗ trợ các hệ thống 
tập tin phổ biến như FAT32 và NTFS.

Các tính năng chính:
1. Thu thập thông tin thiết bị: Tự động nhận diện ổ cứng (HDD/SSD), USB, thẻ nhớ.
2. Quét nhanh (Quick Scan): Phân tích bảng MFT (NTFS) hoặc FAT (FAT32) để tìm file.
3. Quét sâu (Deep Scan/File Carving): Quét toàn bộ sector để tìm chữ ký file (Signature) 
   khi hệ thống tập tin bị hỏng hoặc bị Format.
4. Xem trước (Preview): Hỗ trợ xem trước nội dung file (Ảnh, Văn bản) và mã Hex.
5. Đánh giá toàn vẹn: Tự động tính toán mức độ phục hồi của file (Excellent, Good, Poor).
6. Quản lý phiên (Session): Lưu và mở lại kết quả quét để tiếp tục làm việc sau.
7. Thống kê (Dashboard): Biểu đồ trực quan về các loại dữ liệu tìm thấy.

III. YÊU CẦU HỆ THỐNG & CÀI ĐẶT
-------------------------------
1. Yêu cầu:
   - Hệ điều hành: Windows 10/11 (Bắt buộc để truy cập Physical Drive & WMI).
   - Python: Phiên bản 3.8 trở lên.
   - Quyền hạn: Phải chạy với quyền Quản trị viên (Run as Administrator).

2. Cài đặt thư viện:
   Mở Command Prompt (CMD) hoặc Terminal và chạy lệnh sau:
   
   pip install PyQt5 wmi psutil Pillow pywin32

IV. HƯỚNG DẪN SỬ DỤNG
---------------------
Bước 1: Khởi chạy ứng dụng
   - Mở CMD với quyền Admin (Right-click -> Run as Administrator).
   - Di chuyển đến thư mục chứa code: cd path/to/folder
   - Chạy lệnh: python main.py

Bước 2: Chọn thiết bị
   - Tại giao diện chính (Home), chọn ổ đĩa hoặc phân vùng cần quét từ danh sách.
   - Nhấn "Tiếp tục" để sang màn hình quét.

Bước 3: Chọn chế độ quét
   - Quét nhanh (Quick Scan): Khuyến nghị cho trường hợp vừa xóa nhầm (Shift+Delete).
   - Quét sâu (Deep Scan): Dùng khi bị Format hoặc quét nhanh không thấy.

Bước 4: Xem và Khôi phục
   - Sau khi quét xong, danh sách file sẽ hiện ra.
   - Bấm vào file để xem trước (Preview) hoặc xem Hex.
   - Chọn file cần cứu và nhấn "Khôi phục file".
   - Hoặc nhấn "Khôi phục tất cả" để cứu toàn bộ dữ liệu.

Bước 5: Quản lý phiên (Tùy chọn)
   - Nhấn "Lưu phiên" để lưu lại kết quả quét.
   - Tại màn hình Home, chọn tab "Sessions" để mở lại các phiên cũ.

V. CẤU TRÚC MÃ NGUỒN
--------------------
1. Core Logic (Xử lý chính):
   - main.py: Điểm khởi chạy ứng dụng, quản lý chuyển đổi giữa các màn hình.
   - quet_nhanh_fat.py: Thuật toán đọc bảng FAT và Directory Entry trên FAT32.
   - quet_nhanh_ntfs.py: Thuật toán đọc MFT Record trên NTFS.
   - quet_sau.py: Thuật toán File Carving (tìm kiếm theo Header/Footer).
   - check.py: Module kiểm tra độ toàn vẹn (Integrity Check) và Entropy.
   - disk_info.py: Module tương tác WMI để lấy thông tin phần cứng.

2. Giao diện (GUI):
   - giaodien1.py: Màn hình chọn ổ đĩa/thiết bị.
   - giaodien2.py: Màn hình chính (Tiến trình quét, Danh sách file, Preview).
   - giaodien3.py: Màn hình quản lý phiên làm việc và Log.
   - dashboard.py: Màn hình biểu đồ thống kê.

3. Tài nguyên & Cấu hình:
   - styles.py: Chứa CSS (QSS) cho giao diện đẹp.
   - config.py: Các biến cấu hình chung.
   - utils.py: Các hàm tiện ích (format size, convert date...).
   - assets/: Thư mục chứa hình ảnh, icon.

VI. LƯU Ý QUAN TRỌNG
--------------------
- KHÔNG bao giờ khôi phục file ngược lại vào chính ổ đĩa đang bị mất dữ liệu (để tránh ghi đè).
- Ứng dụng hoạt động tốt nhất trên HDD. Với SSD, khả năng khôi phục có thể bị hạn chế do lệnh TRIM.
- Nếu gặp lỗi "Access Denied", hãy chắc chắn bạn đã chạy chương trình bằng quyền Admin.

========================================================================
