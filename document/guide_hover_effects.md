# Giải thích: Vị trí mã nguồn các hiệu ứng Hover

Dưới đây là vị trí chính xác của hai hiệu ứng bạn đang quan tâm:

### 1. Hiệu ứng phóng to ảnh (Product Zoom)
Hiệu ứng này được viết trực tiếp trong trang chi tiết sản phẩm để đảm bảo tốc độ xử lý nhanh.

- **Vị trí HTML**: [templates/shop/product_detail.html](file:///c:/ITC_Subjects_HKV/Django/MyProject%20-%20Copy%20-%20Copy/templates/shop/product_detail.html) (Khoảng dòng 34-45). Bạn sẽ thấy các ID như `#zoom-container`, `#zoom-lens`, và `#zoom-preview`.
- **Vị trí Javascript**: Cũng trong file [product_detail.html](file:///c:/ITC_Subjects_HKV/Django/MyProject%20-%20Copy%20-%20Copy/templates/shop/product_detail.html), tìm thẻ `<script>` có hàm [handleZoom(e)](file:///c:/ITC_Subjects_HKV/Django/MyProject%20-%20Copy%20-%20Copy/templates/shop/product_detail.html#588-620) và [hideZoom()](file:///c:/ITC_Subjects_HKV/Django/MyProject%20-%20Copy%20-%20Copy/templates/shop/product_detail.html#621-627).
- **Cơ chế**: Khi bạn di chuột (`onmousemove`), hàm JS sẽ tính toán tọa độ chuột so với khung ảnh, sau đó di chuyển "kính lúp" (`zoom-lens`) và thay đổi thuộc tính `background-position` của khung xem thử (`zoom-preview`) để tạo cảm giác phóng to.

---

### 2. Thẻ thông tin khi di chuột vào sản phẩm (Product Tooltip)
Vì hiệu ứng này xuất hiện ở nhiều trang (Trang chủ, Danh sách sản phẩm, Sản phẩm liên quan), nên nó được đặt ở file dùng chung.

- **Vị trí mã nguồn**: [templates/base.html](file:///c:/ITC_Subjects_HKV/Django/MyProject%20-%20Copy%20-%20Copy/templates/base.html) (Nằm ở cuối file, trước thẻ đóng `</body>`).
- **Thành phần**:
    - **HTML**: Một khối `<div id="product-tooltip">` được đặt cố định (`position: fixed`).
    - **Javascript**: Một đoạn mã tự động tìm tất cả các phần tử có class `.product-hover-trigger` để lắng nghe sự kiện di chuột.
- **Cơ chế**: Khi bạn hover vào một sản phẩm, JS sẽ lấy dữ liệu từ các thuộc tính `data-title`, `data-price`, `data-image` của sản phẩm đó để đổ vào cái "thẻ thông tin" chung kia và hiển thị nó ngay tại vị trí con trỏ chuột.

---

> [!TIP]
> **Cách tùy chỉnh**:
> - Nếu bạn muốn thay đổi màu sắc của thẻ thông tin, hãy vào [base.html](file:///c:/ITC_Subjects_HKV/Django/MyProject%20-%20Copy%20-%20Copy/templates/base.html) và sửa CSS trong thẻ `#product-tooltip`.
> - Nếu bạn muốn chỉnh độ phóng to của ảnh, hãy vào [product_detail.html](file:///c:/ITC_Subjects_HKV/Django/MyProject%20-%20Copy%20-%20Copy/templates/shop/product_detail.html) và chỉnh biến `bgSize` trong hàm [handleZoom](file:///c:/ITC_Subjects_HKV/Django/MyProject%20-%20Copy%20-%20Copy/templates/shop/product_detail.html#588-620).

Bạn có muốn tôi giúp bạn thay đổi hoặc nâng cấp thêm tính năng nào cho các hiệu ứng này không?
