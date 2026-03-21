# Hướng dẫn: Làm chủ Template và Hình ảnh (Media/Static)

Sau khi đã có dữ liệu từ Model, bạn cần biết cách "điều khiển" chúng hiển thị linh hoạt trên giao diện.

### 1. Logic trong Template (HTML)
Django cung cấp các thẻ (Tags) để bạn xử lý logic ngay trong file HTML:

- **Vòng lặp (for)**: Để hiển thị danh sách.
  ```html
  {% for product in products %}
      <p>{{ product.title }}</p>
  {% empty %}
      <p>Chưa có sản phẩm nào.</p>
  {% endfor %}
  ```

- **Điều kiện (if)**: Để ẩn/hiện nội dung.
  ```html
  {% if product.price < 50000 %}
      <span class="badge">Giá rẻ!</span>
  {% else %}
      <span>Giá cao cấp</span>
  {% endif %}
  ```

- **Bộ lọc (Filters)**: Để định dạng dữ liệu.
  - `{{ text|truncatechars:20 }}`: Cắt ngắn chuỗi.
  - `{{ price|floatformat:0 }}`: Định dạng số thập phân.
  - `{{ date|date:"d/m/Y" }}`: Định dạng ngày tháng.
  - `{{ content|safe }}`: Hiển thị mã HTML (dùng cho Rich Text).

---

### 2. Quản lý Hình ảnh và File tĩnh
Có 2 loại file bạn cần phân biệt:

- **Static Files** (CSS, JS, Logo): Những file không bao giờ đổi.
  - Gọi trong HTML: `{% load static %}` ở đầu file.
  - Sử dụng: `<link rel="stylesheet" href="{% static 'css/style.css' %}">`.

- **Media Files** (Ảnh sản phẩm, Ảnh Category): Những file do bạn tải lên qua Admin.
  - Cách gọi ảnh từ Model: `<img src="{{ product.image.url }}">`.
  - Luôn kiểm tra xem ảnh có tồn tại không để tránh lỗi:
    ```html
    {% if product.image %}
        <img src="{{ product.image.url }}">
    {% else %}
        <img src="{% static 'images/placeholder.png' %}">
    {% endif %}
    ```

---

### 3. "Mảnh ghép" giao diện (Include)
Nếu một đoạn code (như Navbar hoặc Footer) dùng ở nhiều trang, hãy tách nó ra file riêng và gọi vào:
```html
{% include 'shop/partials/product_card.html' %}
```

Bạn có muốn tôi giúp bạn tạo ra một **Trang Tin tức** hoặc hoàn thiện **Trang About** để thực hành ngay những kiến thức này không?
