import random
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from MyApp.models import Category, Product, ProductVariation


class Command(BaseCommand):
    help = 'Seed sample products into the database'

    def handle(self, *args, **kwargs):
        # Ensure categories exist first
        categories_map = {}
        categories_data = [
            {'name': 'Trà Xanh', 'description': 'Các loại trà xanh truyền thống và hiện đại.'},
            {'name': 'Trà Đen', 'description': 'Trà đen đậm đà, lên men hoàn toàn.'},
            {'name': 'Ô Long', 'description': 'Dòng trà ô long cao cấp với hương vị đa dạng.'},
            {'name': 'Trà Thảo Mộc', 'description': 'Các loại trà từ hoa, quả và thảo mộc tự nhiên.'},
            {'name': 'Phụ Kiện Pha Trà', 'description': 'Ấm chén, dụng cụ pha trà tinh tế.'},
        ]
        for item in categories_data:
            cat, _ = Category.objects.get_or_create(
                slug=slugify(item['name']),
                defaults={'name': item['name'], 'description': item['description']}
            )
            categories_map[item['name']] = cat

        products_data = [
            # ── Trà Xanh ──
            {
                'category': 'Trà Xanh',
                'title': 'Trà Xanh Thái Nguyên',
                'slug': 'tra-xanh-thai-nguyen',
                'excerpt': 'Trà xanh đặc sản vùng Thái Nguyên, vị chát nhẹ, hậu ngọt.',
                'description': 'Trà xanh Thái Nguyên được hái từ những búp non trên đồi chè vùng cao. Lá trà xanh tươi, sao suốt thủ công, giữ nguyên hương vị tự nhiên. Nước trà xanh trong, vị chát dịu, hậu ngọt thanh kéo dài.',
                'ingredients': 'Lá trà xanh Thái Nguyên 100% tự nhiên, không chất bảo quản.',
                'brewing_guide': 'Dùng nước 80-85°C, cho 3-5g trà vào ấm 200ml. Hãm lần đầu 30 giây rồi đổ bỏ nước tráng. Hãm lần 2 khoảng 1-2 phút, thưởng thức.',
                'price': 150000,
                'stock_quantity': 120,
                'variations': [('Gói 100g', 150000), ('Gói 250g', 350000), ('Gói 500g', 650000)],
            },
            {
                'category': 'Trà Xanh',
                'title': 'Trà Matcha Nhật Bản',
                'slug': 'tra-matcha-nhat-ban',
                'excerpt': 'Bột trà matcha nguyên chất nhập khẩu từ Uji, Kyoto.',
                'description': 'Matcha cao cấp từ vùng Uji, Kyoto — thủ phủ matcha Nhật Bản. Lá trà được che nắng 3 tuần trước khi thu hoạch, xay bằng cối đá truyền thống. Bột mịn màu xanh ngọc, vị umami đặc trưng, thích hợp pha trà đạo hoặc pha latte.',
                'ingredients': 'Bột trà xanh matcha 100%, xuất xứ Uji, Kyoto, Nhật Bản.',
                'brewing_guide': 'Cho 2g matcha vào chawan (chén trà), thêm 70ml nước 75°C. Dùng chasen (chổi tre) đánh theo hình chữ W cho đến khi tạo bọt mịn. Thưởng thức ngay.',
                'price': 320000,
                'stock_quantity': 80,
                'variations': [('Hộp 30g', 320000), ('Hộp 100g', 950000)],
            },
            {
                'category': 'Trà Xanh',
                'title': 'Trà Xanh Tân Cương',
                'slug': 'tra-xanh-tan-cuong',
                'excerpt': 'Trà xanh Tân Cương hảo hạng, hương cốm non đặc trưng.',
                'description': 'Đến từ vùng đất Tân Cương nổi tiếng của Thái Nguyên, loại trà này được chế biến từ búp trà một tôm hai lá non. Hương cốm thoảng nhẹ khi mở gói, nước pha xanh vàng đẹp mắt, vị đậm đà mà thanh tao.',
                'ingredients': 'Trà xanh Tân Cương nguyên chất, thu hái thủ công.',
                'brewing_guide': 'Tráng ấm bằng nước sôi. Cho 5g trà, đổ nước 85°C, hãm 2-3 phút. Có thể hãm 3-4 lần, mỗi lần tăng thêm 30 giây.',
                'price': 200000,
                'stock_quantity': 95,
                'variations': [('Gói 100g', 200000), ('Gói 200g', 380000)],
            },
            # ── Trà Đen ──
            {
                'category': 'Trà Đen',
                'title': 'Hồng Trà Lâm Đồng',
                'slug': 'hong-tra-lam-dong',
                'excerpt': 'Hồng trà đặc sản Lâm Đồng, vị mạnh mẽ, thơm nồng.',
                'description': 'Hồng trà (trà đen) từ vùng cao nguyên Lâm Đồng, lên men hoàn toàn theo phương pháp truyền thống. Lá trà cuộn chặt, khi pha cho nước màu đỏ hổ phách đẹp mắt. Hương thơm mạnh mẽ pha chút mật ong, vị đầy đặn, thích hợp uống nóng hoặc pha trà sữa.',
                'ingredients': 'Trà đen Lâm Đồng 100%, lên men tự nhiên.',
                'brewing_guide': 'Dùng nước sôi 95-100°C, cho 3-4g trà vào ấm 250ml. Hãm 3-5 phút tùy khẩu vị. Có thể thêm sữa hoặc mật ong.',
                'price': 130000,
                'stock_quantity': 150,
                'variations': [('Gói 100g', 130000), ('Gói 250g', 300000), ('Gói 500g', 550000)],
            },
            {
                'category': 'Trà Đen',
                'title': 'Earl Grey Classic',
                'slug': 'earl-grey-classic',
                'excerpt': 'Trà đen hảo hạng ướp tinh dầu bergamot tự nhiên.',
                'description': 'Earl Grey kinh điển với nền trà đen Ceylon cao cấp, ướp tinh dầu bergamot Ý. Hương cam bergamot thơm thanh nhã hòa quyện với vị trà đen đậm đà. Lý tưởng cho buổi chiều trà kiểu Anh, uống kèm bánh ngọt.',
                'ingredients': 'Trà đen Ceylon, tinh dầu bergamot tự nhiên.',
                'brewing_guide': 'Nước sôi 100°C, cho 1 túi lọc hoặc 3g trà lá vào cốc 200ml. Hãm 3-4 phút, thêm một lát chanh tươi nếu thích.',
                'price': 180000,
                'stock_quantity': 100,
                'variations': [('Hộp 20 túi lọc', 180000), ('Gói lá 100g', 220000)],
            },
            {
                'category': 'Trà Đen',
                'title': 'Trà Đen Assam TGFOP',
                'slug': 'tra-den-assam-tgfop',
                'excerpt': 'Trà đen Assam hạng Tippy Golden Flowery, đậm đà mạnh mẽ.',
                'description': 'Assam TGFOP là dòng trà đen cao cấp từ thung lũng Assam, Ấn Độ. Lá trà chứa nhiều búp vàng (golden tips), cho nước pha màu đỏ sẫm, hương mạch nha đặc trưng. Vị rất đậm, thích hợp pha trà sữa chai hoặc uống đen nguyên chất.',
                'ingredients': 'Trà đen Assam TGFOP nguyên lá, xuất xứ Ấn Độ.',
                'brewing_guide': 'Nước 95-100°C, 4g trà cho 200ml. Hãm 4-5 phút. Pha masala chai: đun sôi trà cùng sữa, gừng, quế, cardamom trong 5 phút.',
                'price': 250000,
                'stock_quantity': 65,
                'variations': [('Gói 50g', 250000), ('Gói 100g', 450000)],
            },
            # ── Ô Long ──
            {
                'category': 'Ô Long',
                'title': 'Trà Ô Long Đà Lạt',
                'slug': 'tra-o-long-da-lat',
                'excerpt': 'Ô long Đà Lạt thanh nhẹ, hương hoa lan thoảng.',
                'description': 'Ô long trồng tại Cầu Đất, Đà Lạt ở độ cao 1.500m. Khí hậu mát lạnh quanh năm tạo nên hương vị tinh tế riêng biệt. Trà bán lên men (30-40%), nước pha vàng nhạt, hương hoa lan và bơ thoang thoảng, vị ngọt tự nhiên nơi cuống họng.',
                'ingredients': 'Trà ô long Cầu Đất, Đà Lạt, chế biến bán lên men.',
                'brewing_guide': 'Nước 90-95°C, 5g trà cho ấm 150ml. Tráng trà lần đầu, bỏ nước. Hãm từ lần 2, mỗi lần 30-45 giây. Có thể hãm 5-7 lần.',
                'price': 220000,
                'stock_quantity': 85,
                'variations': [('Gói 100g', 220000), ('Gói 250g', 500000)],
            },
            {
                'category': 'Ô Long',
                'title': 'Thiết Quan Âm',
                'slug': 'thiet-quan-am',
                'excerpt': 'Thiết Quan Âm truyền thống, hương hoa đậm, vị thanh.',
                'description': 'Thiết Quan Âm (Tieguanyin) là dòng ô long nổi tiếng nhất Trung Quốc, xuất xứ An Khê, Phúc Kiến. Lá trà cuộn viên chặt, khi hãm nở ra lá nguyên vẹn. Hương hoa lan đậm đà, vị ngọt pha chút kem, nước xanh vàng sáng.',
                'ingredients': 'Trà ô long Thiết Quan Âm, xuất xứ Phúc Kiến, Trung Quốc.',
                'brewing_guide': 'Dùng ấm tử sa hoặc gaiwan. Nước 95°C, 7g trà cho 120ml. Tráng trà nhanh, hãm lần 1 khoảng 15 giây, tăng dần mỗi lần. Hãm được 7-10 lần.',
                'price': 350000,
                'stock_quantity': 50,
                'variations': [('Gói 50g', 350000), ('Gói 100g', 650000), ('Gói 250g', 1500000)],
            },
            {
                'category': 'Ô Long',
                'title': 'Đông Phương Mỹ Nhân',
                'slug': 'dong-phuong-my-nhan',
                'excerpt': 'Ô long lên men nặng, hương mật ong và trái cây chín.',
                'description': 'Đông Phương Mỹ Nhân (Oriental Beauty) là loại ô long đặc biệt, lên men 60-70%. Lá trà bị rầy xanh cắn tạo nên hương mật ong và trái cây chín đặc trưng không thể nhân tạo. Nước pha màu hổ phách, hương ngọt ngào tự nhiên, vị mượt mà.',
                'ingredients': 'Trà ô long Đông Phương Mỹ Nhân, lên men tự nhiên 60-70%.',
                'brewing_guide': 'Nước 85-90°C, 5g trà cho 200ml. Hãm 2-3 phút. Không cần tráng trà. Uống chậm rãi để cảm nhận hương vị thay đổi.',
                'price': 450000,
                'stock_quantity': 35,
                'variations': [('Gói 50g', 450000), ('Gói 100g', 850000)],
            },
            # ── Trà Thảo Mộc ──
            {
                'category': 'Trà Thảo Mộc',
                'title': 'Trà Hoa Cúc Mật Ong',
                'slug': 'tra-hoa-cuc-mat-ong',
                'excerpt': 'Trà hoa cúc vàng kết hợp mật ong, thanh mát dễ uống.',
                'description': 'Hoa cúc vàng sấy khô kết hợp cùng mật ong nguyên chất. Trà không chứa caffeine, thích hợp uống buổi tối để thư giãn và ngủ ngon. Nước pha vàng nhạt, hương hoa nhẹ nhàng, vị ngọt thanh tự nhiên.',
                'ingredients': 'Hoa cúc vàng sấy khô, mật ong hoa nhãn nguyên chất.',
                'brewing_guide': 'Cho 5-7 bông cúc vào cốc, đổ nước 90°C, hãm 5 phút. Thêm 1 thìa mật ong khi nước nguội bớt (dưới 60°C). Khuấy đều, thưởng thức.',
                'price': 95000,
                'stock_quantity': 200,
                'variations': [('Hộp 20 túi', 95000), ('Gói hoa khô 100g', 120000)],
            },
            {
                'category': 'Trà Thảo Mộc',
                'title': 'Trà Atiso Đà Lạt',
                'slug': 'tra-atiso-da-lat',
                'excerpt': 'Trà atiso mát gan, thanh lọc cơ thể từ Đà Lạt.',
                'description': 'Trà atiso từ vùng Đà Lạt, được sấy khô tự nhiên giữ nguyên dưỡng chất. Có tác dụng thanh nhiệt, mát gan, hỗ trợ tiêu hóa và giảm cholesterol. Không caffeine, thích hợp cho mọi lứa tuổi.',
                'ingredients': 'Lá và hoa atiso Đà Lạt sấy khô 100% tự nhiên.',
                'brewing_guide': 'Cho 10g atiso vào 500ml nước, đun sôi nhỏ lửa 10-15 phút. Lọc, thêm đường phèn nếu thích. Có thể uống nóng hoặc lạnh.',
                'price': 75000,
                'stock_quantity': 180,
                'variations': [('Gói 100g', 75000), ('Gói 250g', 170000), ('Gói 500g', 300000)],
            },
            {
                'category': 'Trà Thảo Mộc',
                'title': 'Trà Gừng Nghệ',
                'slug': 'tra-gung-nghe',
                'excerpt': 'Trà gừng nghệ ấm bụng, tăng đề kháng, chống viêm.',
                'description': 'Hỗn hợp gừng tươi và nghệ vàng sấy lạnh, giữ nguyên hoạt chất curcumin và gingerol. Thức uống ấm bụng, hỗ trợ tiêu hóa, tăng cường hệ miễn dịch. Vị cay nồng tự nhiên, hương thơm ấm áp.',
                'ingredients': 'Gừng sấy lạnh 60%, nghệ vàng sấy lạnh 40%. Không chất phụ gia.',
                'brewing_guide': 'Cho 1 túi lọc hoặc 5g bột vào cốc 200ml nước sôi. Hãm 5-7 phút. Thêm mật ong và chanh tùy thích.',
                'price': 85000,
                'stock_quantity': 160,
                'variations': [('Hộp 20 túi lọc', 85000), ('Bột nghệ gừng 200g', 145000)],
            },
            {
                'category': 'Trà Thảo Mộc',
                'title': 'Trà Hoa Hồng',
                'slug': 'tra-hoa-hong',
                'excerpt': 'Trà hoa hồng thơm ngát, làm đẹp da, an thần nhẹ.',
                'description': 'Nụ hoa hồng Đà Lạt sấy khô ở nhiệt độ thấp, giữ nguyên màu sắc và tinh dầu. Trà có tác dụng làm đẹp da, điều hòa kinh nguyệt, giảm stress. Nước pha hồng nhạt, hương hoa hồng quyến rũ.',
                'ingredients': 'Nụ hoa hồng Đà Lạt sấy khô 100%.',
                'brewing_guide': 'Cho 5-8 nụ hồng vào cốc, đổ nước 85°C, hãm 5 phút. Có thể kết hợp cùng trà xanh hoặc mật ong.',
                'price': 110000,
                'stock_quantity': 140,
                'variations': [('Hộp 50g', 110000), ('Hộp 100g', 200000)],
            },
            # ── Phụ Kiện Pha Trà ──
            {
                'category': 'Phụ Kiện Pha Trà',
                'title': 'Ấm Tử Sa Nghi Hưng',
                'slug': 'am-tu-sa-nghi-hung',
                'excerpt': 'Ấm tử sa chính hiệu Nghi Hưng, dung tích 200ml.',
                'description': 'Ấm tử sa làm từ đất sét Nghi Hưng (Yixing) chính hiệu, dung tích 200ml. Đất tử sa có cấu trúc vi lỗ giúp "hít thở", giữ nhiệt tốt và tăng hương vị trà theo thời gian sử dụng. Mỗi ấm chỉ nên dùng cho một loại trà.',
                'ingredients': 'Đất sét tử sa Nghi Hưng tự nhiên, nung thủ công ở 1100-1200°C.',
                'brewing_guide': 'Trước khi dùng lần đầu: rửa sạch, đun sôi ấm trong nước trà loãng 30 phút. Sau mỗi lần dùng, rửa bằng nước nóng, không dùng xà phòng.',
                'price': 850000,
                'stock_quantity': 25,
                'variations': [('200ml - Tròn', 850000), ('150ml - Bẹt', 780000), ('300ml - Cao', 950000)],
            },
            {
                'category': 'Phụ Kiện Pha Trà',
                'title': 'Bộ Chén Trà Gốm Bát Tràng',
                'slug': 'bo-chen-tra-gom-bat-trang',
                'excerpt': 'Bộ 6 chén trà gốm Bát Tràng men lam cổ điển.',
                'description': 'Bộ 6 chén trà gốm Bát Tràng với men lam cổ điển, hoa văn truyền thống Việt Nam. Dung tích mỗi chén 50ml, kích thước vừa tay. Gốm giữ nhiệt tốt, an toàn thực phẩm, phù hợp thưởng trà kiểu Việt.',
                'ingredients': 'Gốm Bát Tràng men lam, nung ở nhiệt độ cao, an toàn thực phẩm.',
                'brewing_guide': 'Tráng chén bằng nước nóng trước khi rót trà. Rửa sạch sau khi dùng, tránh thay đổi nhiệt độ đột ngột.',
                'price': 280000,
                'stock_quantity': 40,
                'variations': [('Bộ 6 chén', 280000), ('Bộ 6 chén kèm khay tre', 420000)],
            },
            {
                'category': 'Phụ Kiện Pha Trà',
                'title': 'Chasen - Chổi Tre Đánh Matcha',
                'slug': 'chasen-choi-tre-danh-matcha',
                'excerpt': 'Chổi tre 80 nan truyền thống cho matcha mịn hoàn hảo.',
                'description': 'Chasen (chổi tre đánh matcha) 80 nan, làm thủ công từ tre già tự nhiên. Dụng cụ không thể thiếu trong trà đạo Nhật Bản, giúp đánh matcha tạo bọt mịn đều. Kèm đế giữ chasen để bảo quản đúng cách.',
                'ingredients': 'Tre già tự nhiên, chế tác thủ công truyền thống Nhật Bản.',
                'brewing_guide': 'Ngâm chasen trong nước ấm 1 phút trước khi dùng. Đánh matcha theo hình chữ W. Sau khi dùng, rửa sạch bằng nước ấm, đặt lên đế giữ chasen.',
                'price': 195000,
                'stock_quantity': 55,
                'variations': [('Chasen 80 nan', 195000), ('Chasen 80 nan + đế', 260000), ('Bộ Matcha (chasen + chashaku + chawan)', 550000)],
            },
        ]

        created_count = 0
        skipped_count = 0

        for item in products_data:
            category = categories_map.get(item['category'])
            variations = item.pop('variations', [])
            cat_name = item.pop('category')

            product, created = Product.objects.get_or_create(
                slug=item['slug'],
                defaults={
                    'category': category,
                    'title': item['title'],
                    'excerpt': item['excerpt'],
                    'description': item['description'],
                    'ingredients': item['ingredients'],
                    'brewing_guide': item['brewing_guide'],
                    'price': item['price'],
                    'stock_quantity': item['stock_quantity'],
                }
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  + {item["title"]}'))

                # Create variations
                for var_title, var_price in variations:
                    ProductVariation.objects.get_or_create(
                        product=product,
                        title=var_title,
                        defaults={
                            'price': var_price,
                            'stock_quantity': random.randint(10, 50),
                        }
                    )
            else:
                skipped_count += 1
                self.stdout.write(self.style.WARNING(f'  ~ {item["title"]} (đã tồn tại)'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Hoàn tất: Tạo {created_count} sản phẩm mới, bỏ qua {skipped_count} sản phẩm đã có.'
        ))
        self.stdout.write(self.style.NOTICE(
            'Lưu ý: Hãy vào Admin để thêm hình ảnh cho từng sản phẩm.'
        ))
