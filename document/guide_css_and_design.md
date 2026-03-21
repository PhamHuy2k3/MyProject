# Hướng dẫn: Làm chủ CSS và Ngôn ngữ thiết kế TeaZen

Website TeaZen của bạn sử dụng sự kết hợp giữa **Tailwind CSS** (tiện lợi, nhanh) và **Custom CSS** (nghệ thuật, đặc thù).

---

### 1. Hệ thống màu sắc và Font chữ
Các biến cốt lõi được định nghĩa trong [static/css/styles.css](file:///c:/ITC_Subjects_HKV/Django/MyProject%20-%20Copy%20-%20Copy/static/css/styles.css):
- **Font chữ chính**: `Space Grotesk` (Hiện đại).
- **Font nghệ thuật**: `Syne` (Dùng cho tiêu đề lớn, class `.font-art`).
- **Màu nền chủ đạo**: `--color-bg: #34eb80` (Xanh trà).
- **Màu nhấn**: `--color-accent: #b8d418` (Xanh lá mạ).

### 2. Cách sử dụng Tailwind CSS
Bạn có thể thêm các lớp trực tiếp vào HTML mà không cần viết CSS:
- `text-emerald-900`: Màu chữ xanh đậm.
- `bg-white/80`: Nền trắng mờ (80% opacity).
- `backdrop-blur-md`: Hiệu ứng kính mờ cho nền.
- `rounded-2xl`: Bo góc cực lớn (kiểu hiện đại).
- `shadow-xl`: Đổ bóng sâu.

### 3. Các thành phần nghệ thuật đặc trưng (Custom Classes)
Trong [styles.css](file:///c:/ITC_Subjects_HKV/Django/MyProject%20-%20Copy%20-%20Copy/static/css/styles.css) và [shop.css](file:///c:/ITC_Subjects_HKV/Django/MyProject%20-%20Copy%20-%20Copy/static/css/shop.css), có những lớp giúp tạo nên "vibe" của TeaZen:

- **Hiệu ứng Băng dính (`.tape`)**: Tạo cảm giác như ảnh được dán bằng băng keo mờ.
- **Khung ảnh (`.image-frame`)**: Giống như ảnh chụp lấy ngay (Polaroid).
- **Lớp quầng nhiễu (`.noise-overlay`)**: Tạo bề mặt hơi hạt hạt, trông cao cấp và có chiều sâu hơn.
- **Con trỏ chuột (`#custom-cursor`)**: Vòng tròn chạy theo chuột (được điều khiển bằng JS kết hợp CSS).

### 4. Quy trình tạo một thành phần mới đẹp mắt
Nếu bạn muốn tạo một khối nội dung mới, hãy kết hợp như sau:
```html
<div class="product-card bg-white p-6 rounded-[2rem] shadow-xl">
    <div class="image-frame floating-item mb-4">
        <!-- Ảnh của bạn ở đây -->
        <div class="tape top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 rotate-3"></div>
    </div>
    <h3 class="font-art text-xl font-bold">Tiêu đề nghệ thuật</h3>
    <p class="text-gray-600 text-sm">Mô tả sản phẩm...</p>
</div>
```

---

### Mẹo nhỏ:
- Để thay đổi màu nền toàn bộ trang web: Hãy sửa `--color-bg` trong `:root` của file [styles.css](file:///c:/ITC_Subjects_HKV/Django/MyProject%20-%20Copy%20-%20Copy/static/css/styles.css).
- Để tìm các Icon đẹp: Sử dụng [Lucide Icons](https://lucide.dev/). Bạn chỉ cần viết `<i data-lucide="tên-icon"></i>`.

Bạn có muốn tôi thử áp dụng những phong cách này để thiết kế demo một **Section** cụ thể nào đó (ví dụ: Team Members hoặc Testimonials) không?
