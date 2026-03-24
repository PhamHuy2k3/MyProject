# Kế hoạch triển khai Trang Giới thiệu (About Page)

Trang này sẽ giới thiệu về câu chuyện thương hiệu TeaZen, giá trị tinh thần và cam kết chất lượng của cửa hàng.

## Thay đổi dự kiến

### MyApp/views/product_views.py
#### [MODIFY] [product_views.py](file:///c:/ITC_Subjects_HKV/Django/MyProject - Copy - Copy/MyApp/views/product_views.py)
- Thêm function `about_view` đơn giản để render template.

### MyApp/urls.py
#### [MODIFY] [urls.py](file:///c:/ITC_Subjects_HKV/Django/MyProject - Copy - Copy/MyApp/urls.py)
- Thêm path `'about/'` trỏ tới `about_view`.

### templates/shop/about.html [NEW]
#### [NEW] [about.html](file:///c:/ITC_Subjects_HKV/Django/MyProject - Copy - Copy/templates/shop/about.html)
- Thiết kế giao diện với các section: Hero, Our Story, Quality Commitment, và Visual Assets.

### templates/base.html
#### [MODIFY] [base.html](file:///c:/ITC_Subjects_HKV/Django/MyProject - Copy - Copy/templates/base.html)
- Cập nhật link "Giới thiệu" trong Navbar để trỏ tới `{% url 'about' %}`.

## Kế hoạch kiểm thử
1. Truy cập `/about/` để kiểm tra giao diện.
2. Kiểm tra tính phản hồi (Mobile/Desktop).
3. Xác minh link từ Navbar hoạt động đúng.
