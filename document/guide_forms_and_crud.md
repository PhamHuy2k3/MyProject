# Hướng dẫn: Xử lý Form và Phản hồi người dùng (CRUD)

Đây là kỹ năng giúp khách hàng "nói chuyện" với website của bạn (ví dụ: Gửi liên hệ, Đóng góp ý kiến).

### 1. Tạo Form trong [forms.py](file:///c:/ITC_Subjects_HKV/Django/MyProject%20-%20Copy%20-%20Copy/MyApp/forms.py)
Django có class `ModelForm` giúp tạo form từ Model cực kỳ nhanh:
```python
from django import forms
from .models import Feedback

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['user_name', 'email', 'message']
```

### 2. Xử lý trong View (Nhận dữ liệu)
Bạn cần xử lý 2 trường hợp: Khách xem trang (GET) và Khách bấm Gửi (POST).
```python
def contact_view(request):
    if request.method == 'POST':
        form = FeedbackForm(request.POST) # Nhận dữ liệu từ user
        if form.is_valid():
            form.save() # Lưu trực tiếp vào Database!
            messages.success(request, 'Cảm ơn bạn đã gửi phản hồi.')
            return redirect('index')
    else:
        form = FeedbackForm() # Tạo form trống cho khách điền
    
    return render(request, 'shop/contact.html', {'form': form})
```

### 3. Hiển thị trong Template
Chỉ cần gọi biến `{{ form }}` và thêm thẻ `<form>`:
```html
<form method="POST">
    {% csrf_token %} <!-- Cực kỳ quan trọng để bảo mật! -->
    {{ form.as_p }}  <!-- Hiển thị các ô nhập liệu dạng đoạn văn -->
    <button type="submit">Gửi ngay</button>
</form>
```

---

### Bảng các loại trường (Fields) hay dùng:
| Loại trường | Mã Code chuẩn | Dùng cho |
| :--- | :--- | :--- |
| Văn bản ngắn | `models.CharField` | Tên, Tiêu đề, Số điện thoại |
| Văn bản dài | `models.TextField` | Nội dung, Mô tả, Ý kiến |
| Con số | `models.IntegerField` | Số lượng, Tuổi, Thứ tự |
| Ngày tháng | `models.DateTimeField` | Thời gian tạo, Ngày sinh |
| Liên kết | `models.ForeignKey` | Liên kết sang mục khác (như Danh mục) |

Bạn đã sẵn sàng để thực hành tạo ra một trang **Feedback khách hàng** hoặc **Blog tin tức** thực sự với những hướng dẫn này chưa? Hãy chọn một cái, tôi sẽ đồng hành cùng bạn làm "thật" luôn!
