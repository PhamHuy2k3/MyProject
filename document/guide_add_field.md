# Hướng dẫn: Thêm trường dữ liệu mới cho Product

Để thêm một trường mới (ví dụ: **Xuất xứ - origin**) vào sản phẩm, bạn cần thực hiện 4 bước sau:

### Bước 1: Khai báo trong [models.py](file:///c:/ITC_Subjects_HKV/Django/MyProject%20-%20Copy%20-%20Copy/MyApp/models.py)
Tìm đến class [Product](file:///c:/ITC_Subjects_HKV/Django/MyProject%20-%20Copy%20-%20Copy/MyApp/models.py#32-63) và thêm trường mới.
```python
class Product(models.Model):
    # ... các trường cũ ...
    origin = models.CharField(max_length=100, blank=True, verbose_name="Xuất xứ")
```

### Bước 2: Chạy Migration (Cực kỳ quan trọng)
Mở terminal và chạy 2 lệnh sau để cập nhật cơ sở dữ liệu:
1. `python manage.py makemigrations` (Để Django tạo ra "bản vẽ" thay đổi).
2. `python manage.py migrate` (Để áp dụng "bản vẽ" đó vào thực tế).

### Bước 3: Cập nhật Form nhập liệu ([forms.py](file:///c:/ITC_Subjects_HKV/Django/MyProject%20-%20Copy%20-%20Copy/MyApp/forms.py))
Nếu bạn có trang thêm/sửa sản phẩm, hãy thêm tên trường vào danh sách `fields`:
```python
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['title', 'category', 'origin', 'price', ...] # Thêm 'origin' vào đây
```

### Bước 4: Hiển thị ra giao diện (`templates/`)
Mở file HTML của trang chi tiết sản phẩm (ví dụ [product_detail.html](file:///c:/ITC_Subjects_HKV/Django/MyProject%20-%20Copy%20-%20Copy/templates/shop/product_detail.html)) và gọi dữ liệu:
```html
<p><strong>Xuất xứ:</strong> {{ product.origin }}</p>
```

---

> [!TIP]
> **Lưu ý về `null=True` và `blank=True`**:
> - `blank=True`: Cho phép để trống khi nhập trên giao diện (Admin/Form).
> - `null=True`: Cho phép cơ sở dữ liệu lưu giá trị Rỗng (thường dùng cho các trường số hoặc liên kết ForeignKey).
> - Với `CharField` (chuỗi), thường chỉ cần `blank=True` là đủ.

Nếu bạn muốn tôi thực hiện trực tiếp một trường cụ thể nào đó (ví dụ như để phục vụ trang About), hãy cho tôi biết tên trường nhé!
