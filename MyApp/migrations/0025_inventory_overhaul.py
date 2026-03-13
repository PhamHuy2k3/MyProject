from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ('MyApp', '0024_userprofile_role'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Rename stock_quantity to physical_stock in Product
        migrations.RenameField(
            model_name='product',
            old_name='stock_quantity',
            new_name='physical_stock',
        ),
        # 2. Add reserved_stock to Product
        migrations.AddField(
            model_name='product',
            name='reserved_stock',
            field=models.PositiveIntegerField(default=0, verbose_name='Số lượng tạm giữ'),
        ),
        # 3. Rename stock_quantity to physical_stock in ProductVariation
        migrations.RenameField(
            model_name='productvariation',
            old_name='stock_quantity',
            new_name='physical_stock',
        ),
        # 4. Add reserved_stock to ProductVariation
        migrations.AddField(
            model_name='productvariation',
            name='reserved_stock',
            field=models.PositiveIntegerField(default=0, verbose_name='Số lượng tạm giữ biến thể'),
        ),
        # 5. Create InventoryTransaction
        migrations.CreateModel(
            name='InventoryTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transaction_type', models.CharField(choices=[('IN', 'Nhập kho'), ('OUT', 'Xuất kho'), ('ADJUST', 'Điều chỉnh (Kiểm kê)'), ('RESERVE', 'Tạm giữ (Đặt hàng)'), ('RELEASE', 'Giải phóng (Hủy đơn)')], max_length=10)),
                ('quantity', models.IntegerField(verbose_name='Số lượng thay đổi')),
                ('is_physical', models.BooleanField(default=True, verbose_name='Biến động vật lý')),
                ('reference_id', models.CharField(blank=True, max_length=100, verbose_name='Mã tham chiếu (Đơn hàng/Phiếu nhập)')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='inventory_transactions', to='MyApp.product')),
                ('variation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='inventory_transactions', to='MyApp.productvariation')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
        # 6. Create InventoryReceipt
        migrations.CreateModel(
            name='InventoryReceipt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('receipt_number', models.CharField(max_length=50, unique=True)),
                ('supplier', models.CharField(blank=True, max_length=200, verbose_name='Nhà cung cấp')),
                ('status', models.CharField(choices=[('draft', 'Nháp'), ('completed', 'Hoàn tất')], default='draft', max_length=20)),
                ('note', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        # 7. Create InventoryReceiptItem
        migrations.CreateModel(
            name='InventoryReceiptItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField()),
                ('unit_price', models.DecimalField(decimal_places=0, default=0, max_digits=12)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='MyApp.product')),
                ('receipt', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='MyApp.inventoryreceipt')),
                ('variation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='MyApp.productvariation')),
            ],
        ),
    ]
