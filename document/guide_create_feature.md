# Hướng dẫn: Tạo tính năng mới từ A-Z (Ví dụ: Tin tức - News)

Để tạo ra một trang mới hiển thị dữ liệu từ Cơ sở dữ liệu, bạn cần đi qua quy trình 5 bước "Thần thánh" sau đây:

### Bước 1: Tạo Model (Nơi chứa dữ liệu)
Trong [models.py](file:///c:/ITC_Subjects_HKV/Django/MyProject%20-%20Copy%20-%20Copy/MyApp/models.py), hãy thêm class mới:
```python
class NewsItem(models.Model):
    title = models.CharField(max_length=200, verbose_name="Tiêu đề")
    content = models.TextField(verbose_name="Nội dung")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
```
*Đừng quên chạy `makemigrations` và `migrate` sau bước này!*

### Bước 2: Hiển thị trong Admin (Để bạn nhập liệu)
Trong [admin.py](file:///c:/ITC_Subjects_HKV/Django/MyProject%20-%20Copy%20-%20Copy/MyApp/admin.py), đăng ký model mới:
```python
admin.site.register(NewsItem)
```

### Bước 3: Viết View (Cửa ngõ xử lý dữ liệu)
Trong [views/product_views.py](file:///c:/ITC_Subjects_HKV/Django/MyProject%20-%20Copy%20-%20Copy/MyApp/views/product_views.py) (hoặc view tương ứng), viết hàm để lấy dữ liệu:
```python
def news_list(request):
    # Lấy toàn bộ tin tức từ Database
    items = NewsItem.objects.all().order_by('-created_at') 
    return render(request, 'shop/news_list.html', {'news_items': items})
```

### Bước 4: Đăng ký URL (Đường dẫn trang)
Trong [urls.py](file:///c:/ITC_Subjects_HKV/Django/MyProject%20-%20Copy%20-%20Copy/MyApp/urls.py), thêm đường dẫn:
```python
path('news/', views.news_list, name='news_list'),
```

### Bước 5: Tạo Template (Giao diện hiển thị)
Tạo file `templates/shop/news_list.html`:
```html
{% extends 'base.html' %}
{% block content %}
<div class="container mx-auto py-10">
    <h1 class="text-3xl font-bold mb-6">Tin tức TeaZen</h1>
    <div class="grid gap-6">
        {% for item in news_items %}
            <div class="p-4 border rounded-xl shadow-sm bg-white">
                <h2 class="text-xl font-bold">{{ item.title }}</h2>
                <p class="text-gray-600 mt-2">{{ item.content }}</p>
                <small class="text-gray-400">{{ item.created_at|date:"d/m/Y" }}</small>
            </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
```

---

> [!IMPORTANT]
> **Mockup dữ liệu**: Sau khi xong Bước 2, bạn có thể vào trang Admin (`/admin`) để thêm vài mẫu tin tức. Lúc đó, trang `/news/` sẽ tự động hiển thị những gì bạn vừa nhập!

Bạn có muốn tôi áp dụng quy trình này để tạo ra một tính năng thực tế nào đó cho website ngay bây giờ không? (Ví dụ: Một trang **Blog** hoặc **Feedback khách hàng**?)
