import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MyProject.settings')
django.setup()

from MyApp.models import Product, StoryboardItem, RawItem, CabinetItem

# Xóa dữ liệu cũ (nếu có)
Product.objects.all().delete()
StoryboardItem.objects.all().delete()
RawItem.objects.all().delete()
CabinetItem.objects.all().delete()

# Tạo Products (6 sản phẩm)
products_data = [
    {'title': 'Trà Shan Tuyết Cổ Thụ', 'slug': 'tra-shan-tuyet-co-thu', 'excerpt': 'Hương vị nguyên bản từ núi rừng Tây Bắc', 'description': 'Trà Shan Tuyết được hái từ những cây chè cổ thụ hàng trăm năm tuổi, mọc tự nhiên trên độ cao 1500m.', 'price': 350000},
    {'title': 'Trà Ô Long Thượng Hạng', 'slug': 'tra-o-long-thuong-hang', 'excerpt': 'Bán lên men tinh tế, hương hoa quả', 'description': 'Ô Long cao cấp với quy trình lên men 30-40%, tạo nên hương vị độc đáo.', 'price': 420000},
    {'title': 'Trà Thái Nguyên Đặc Sản', 'slug': 'tra-thai-nguyen-dac-san', 'excerpt': 'Búp non một tôm hai lá', 'description': 'Trà xanh Thái Nguyên hái sớm, màu nước xanh trong, vị chát nhẹ.', 'price': 280000},
    {'title': 'Trà Hoa Nhài Premium', 'slug': 'tra-hoa-nhai-premium', 'excerpt': 'Ướp hương nhài tự nhiên 7 lần', 'description': 'Trà xanh được ướp cùng hoa nhài tươi theo phương pháp truyền thống.', 'price': 320000},
    {'title': 'Trà Phổ Nhĩ Chín 10 Năm', 'slug': 'tra-pho-nhi-chin-10-nam', 'excerpt': 'Lên men tự nhiên, vị đậm đà', 'description': 'Phổ Nhĩ chín được ủ trong điều kiện đặc biệt suốt 10 năm.', 'price': 580000},
    {'title': 'Trà Matcha Nhật Bản', 'slug': 'tra-matcha-nhat-ban', 'excerpt': 'Bột trà xanh nguyên chất Grade A', 'description': 'Matcha cao cấp nhập khẩu từ Uji, Nhật Bản.', 'price': 450000},
]

for data in products_data:
    Product.objects.create(**data)
print(f'Created {Product.objects.count()} products')

# Tạo StoryboardItems (6 items)
storyboard_data = [
    {'title': 'Thu Hoạch Sớm Mai', 'slug': 'thu-hoach-som-mai', 'excerpt': 'Búp trà được hái lúc bình minh'},
    {'title': 'Nghệ Nhân Sao Chè', 'slug': 'nghe-nhan-sao-che', 'excerpt': 'Kỹ thuật sao chè thủ công truyền đời'},
    {'title': 'Hương Trà Lan Tỏa', 'slug': 'huong-tra-lan-toa', 'excerpt': 'Mùi hương quyến rũ trong không gian thiền'},
    {'title': 'Đồi Chè Mờ Sương', 'slug': 'doi-che-mo-suong', 'excerpt': 'Đồi chè xanh mướt ẩn trong sương sớm'},
    {'title': 'Ấm Đất Nung Cổ', 'slug': 'am-dat-nung-co', 'excerpt': 'Ấm trà đất nung theo lối cổ truyền'},
    {'title': 'Thưởng Trà Chiều', 'slug': 'thuong-tra-chieu', 'excerpt': 'Khoảnh khắc tĩnh lặng bên chén trà'},
]

for data in storyboard_data:
    StoryboardItem.objects.create(**data)
print(f'Created {StoryboardItem.objects.count()} storyboard items')

# Tạo RawItems (8 items)
raw_data = [
    {'title': 'Bình Minh Đồi Chè', 'caption': '@teazen_daily'},
    {'title': 'Chén Trà Thiền', 'caption': '@mindful_tea'},
    {'title': 'Lá Trà Phơi Nắng', 'caption': '@organic_life'},
    {'title': 'Góc Trà Vintage', 'caption': '@cozy_corner'},
    {'title': 'Trà Đá Mùa Hè', 'caption': '@summer_vibes'},
    {'title': 'Ấm Trà Gốm Sứ', 'caption': '@ceramic_art'},
    {'title': 'Khoảnh Khắc Yên Bình', 'caption': '@peaceful_moment'},
    {'title': 'Trà Và Sách', 'caption': '@book_tea_lover'},
]

for data in raw_data:
    RawItem.objects.create(**data)
print(f'Created {RawItem.objects.count()} raw items')

# Tạo CabinetItems (6 items)
cabinet_data = [
    {'title': 'Bộ Sưu Tập Shan Tuyết', 'note': 'Trà quý từ vùng núi cao Hà Giang'},
    {'title': 'Ô Long Đài Loan', 'note': 'Nhập khẩu từ Ali Mountain'},
    {'title': 'Bạch Trà Phúc Kiến', 'note': 'White tea hiếm, sản xuất giới hạn'},
    {'title': 'Hồng Trà Assam', 'note': 'Vị mạnh mẽ từ Đông Bắc Ấn Độ'},
    {'title': 'Trà Hoàng Kim', 'note': 'Golden tea - Đỉnh cao nghệ thuật'},
    {'title': 'Lục Trà Long Tỉnh', 'note': 'Trà xanh nổi tiếng nhất Trung Quốc'},
]

for data in cabinet_data:
    CabinetItem.objects.create(**data)
print(f'Created {CabinetItem.objects.count()} cabinet items')

print('\n=== DONE! Sample data created successfully ===')
print('Vao Admin de upload hinh anh cho tung item.')
