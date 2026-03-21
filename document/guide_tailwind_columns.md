# Hướng dẫn: Chia cột trong Tailwind CSS (Grid & Flexbox)

Để chia trang web thành các cột (như 2 cột, 3 cột), Tailwind CSS cung cấp 2 cách mạnh mẽ nhất: **Grid** (Lưới) và **Flexbox**.

---

### 1. Cách dùng Grid (Khuyên dùng cho bố cục trang)
Grid giúp bạn xác định rõ có bao nhiêu cột một cách dễ dàng.

**Ví dụ: Chia 3 cột đều nhau**
```html
<div class="grid grid-cols-3 gap-4">
    <div class="bg-blue-200 p-4">Cột 1</div>
    <div class="bg-blue-300 p-4">Cột 2</div>
    <div class="bg-blue-400 p-4">Cột 3</div>
</div>
```

**Ví dụ: Chia cột theo tỉ lệ (Cột to, cột nhỏ)**
Dùng `col-span` để một cột chiếm nhiều chỗ hơn:
```html
<div class="grid grid-cols-4 gap-4">
    <div class="col-span-3 bg-green-200">Cột to (chiếm 3/4)</div>
    <div class="col-span-1 bg-green-300">Cột nhỏ (chiếm 1/4)</div>
</div>
```

---

### 2. Cách dùng Flexbox (Dùng cho thanh Menu hoặc các khối linh hoạt)
Flexbox giúp các cột co giãn theo nội dung bên trong.

```html
<div class="flex gap-4">
    <div class="flex-1 bg-red-200">Tự co giãn 1</div>
    <div class="flex-1 bg-red-300">Tự co giãn 2</div>
</div>
```

---

### 3. CỰC KỲ QUAN TRỌNG: Làm giao diện cho điện thoại (Responsive)
Thông thường, trên điện thoại (màn hình nhỏ) chúng ta muốn 1 cột, còn trên máy tính mới chia thành 2-3 cột.

**Công thức: `Lớp_Nhỏ md:Lớp_To`**
```html
<!-- Mặc định (điện thoại): 1 cột. Từ máy tính (md): 3 cột -->
<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
    <div>Nội dung 1</div>
    <div>Nội dung 2</div>
    <div>Nội dung 3</div>
</div>
```

---

### Mẹo nhanh:
- **`gap-4`**: Khoảng cách giữa các cột.
- **`items-center`**: Căn giữa các cột theo chiều dọc.
- **`justify-between`**: Đẩy các cột ra xa nhau nhất có thể.

Bạn có muốn tôi thử áp dụng **Grid** để tạo giao diện 2 cột cực đẹp (Bên trái nội dung - Bên phải hình ảnh) cho trang **About** sắp tới không?
