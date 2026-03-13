from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

from .models import Product, StoryboardItem, RawItem, CabinetItem, Category, UserProfile, Payment, Coupon


# ==================== AUTH FORMS ====================

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': ' '})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'input-field', 'placeholder': ' '})
    )


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': ' '})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': ' '})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'input-field', 'placeholder': ' '})
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'input-field', 'placeholder': ' '})
        self.fields['password2'].widget.attrs.update({'class': 'input-field', 'placeholder': ' '})

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            username = email.split('@')[0]
            if User.objects.filter(username=username).exists():
                raise forms.ValidationError("Tên người dùng được tạo từ email này (phần trước @) đã tồn tại. Vui lòng sử dụng email khác.")
            if User.objects.filter(email=email).exists():
                raise forms.ValidationError("Email này đã được đăng ký.")
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        # Tạo username từ email (phần trước @)
        user.username = self.cleaned_data['email'].split('@')[0]
        if commit:
            user.save()
        return user


class AdminUserForm(forms.ModelForm):
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-input'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input'}), required=False, help_text="Để trống nếu không muốn đổi mật khẩu.")

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-emerald-600 rounded border-stone-300 focus:ring-emerald-500'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['role'].initial = self.instance.profile.role
            self.fields['password'].required = False
        else:
            self.fields['password'].required = True

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
            # Cập nhật role trong profile
            role = self.cleaned_data.get('role')
            user.profile.role = role
            user.profile.save()
        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar', 'bio', 'phone', 'street_address', 'province', 'province_code', 'district', 'district_code', 'ward', 'ward_code']
        widgets = {
            'bio': forms.TextInput(attrs={'class': 'input-field', 'placeholder': ' '}),
            'phone': forms.TextInput(attrs={'class': 'input-field', 'placeholder': ' '}),
            'street_address': forms.TextInput(attrs={'class': 'input-field', 'placeholder': ' '}),
            'province': forms.HiddenInput(),
            'province_code': forms.HiddenInput(),
            'district': forms.HiddenInput(),
            'district_code': forms.HiddenInput(),
            'ward': forms.HiddenInput(),
            'ward_code': forms.HiddenInput(),
            'avatar': forms.FileInput(attrs={'class': 'form-file'}),
        }


# ==================== MODEL FORMS ====================

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'slug', 'description', 'image', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Tên danh mục'}),
            'slug': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'slug-danh-muc'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Mô tả danh mục'}),
            'image': forms.FileInput(attrs={'class': 'form-file'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-emerald-600 rounded border-stone-300 focus:ring-emerald-500'}),
        }


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'title', 'slug', 'excerpt', 'image', 'description', 'ingredients', 'brewing_guide', 'price', 'physical_stock']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-input'}),
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Tên sản phẩm'}),
            'slug': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'slug-san-pham'}),
            'excerpt': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Mô tả ngắn gọn về sản phẩm'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 5, 'placeholder': 'Mô tả chi tiết về sản phẩm...'}),
            'ingredients': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Thành phần, nguyên liệu...'}),
            'brewing_guide': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Hướng dẫn pha chế, sử dụng...'}),
            'price': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '0'}),
            'physical_stock': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '0'}),
            'image': forms.FileInput(attrs={'class': 'form-file', 'accept': 'image/*'}),
        }


class StoryboardItemForm(forms.ModelForm):
    class Meta:
        model = StoryboardItem
        fields = ['title', 'slug', 'image', 'excerpt', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Tiêu đề'}),
            'slug': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'slug-tieu-de'}),
            'excerpt': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Mô tả ngắn'}),
            'content': forms.Textarea(attrs={'class': 'form-input', 'rows': 8, 'placeholder': 'Nội dung bài viết...'}),
            'image': forms.FileInput(attrs={'class': 'form-file', 'accept': 'image/*'}),
        }


class RawItemForm(forms.ModelForm):
    class Meta:
        model = RawItem
        fields = ['title', 'image', 'caption']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Tiêu đề'}),
            'caption': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Caption (VD: @username)'}),
            'image': forms.FileInput(attrs={'class': 'form-file'}),
        }


class CabinetItemForm(forms.ModelForm):
    class Meta:
        model = CabinetItem
        fields = ['title', 'image', 'note', 'link_url']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Tiêu đề'}),
            'note': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ghi chú'}),
            'link_url': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://...'}),
            'image': forms.FileInput(attrs={'class': 'form-file', 'accept': 'image/*'}),
        }


# ==================== COUPON FORMS ====================

class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = ['code', 'discount_type', 'discount_value', 'min_purchase', 'active', 'valid_from', 'valid_to', 'usage_limit']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'VD: SALE20'}),
            'discount_type': forms.Select(attrs={'class': 'form-select'}),
            'discount_value': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '20'}),
            'min_purchase': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '100000'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'valid_from': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'valid_to': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'usage_limit': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '100'}),
        }


# ==================== PAYMENT FORMS ====================

class PaymentForm(forms.ModelForm):
    """
    Form để xử lý thanh toán
    """
    class Meta:
        model = Payment
        fields = ['payment_method', 'notes']
        widgets = {
            'payment_method': forms.Select(attrs={'class': 'form-control form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ghi chú (tuỳ chọn)'}),
        }
        labels = {
            'payment_method': 'Phương thức thanh toán',
            'notes': 'Ghi chú',
        }


class CheckoutForm(forms.Form):
    """
    Form cho trang checkout
    """
    note = forms.CharField(
        label='Ghi chú đơn hàng',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Nhập ghi chú (tuỳ chọn)...'
        })
    )
    
    # Chấp nhận điều khoản
    agree_terms = forms.BooleanField(
        label='Tôi đồng ý với điều khoản và điều kiện',
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class QRPaymentForm(forms.Form):
    """
    Form cho thanh toán QR
    """
    PAYMENT_METHOD_CHOICES = [
        ('bank', 'Thanh toán qua ngân hàng'),
        ('vietqr', 'VietQR'),
        ('custom', 'Tùy chỉnh'),
    ]
    
    payment_method = forms.ChoiceField(
        label='Phương thức QR',
        choices=PAYMENT_METHOD_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='bank'
    )
    
    transaction_id = forms.CharField(
        label='Mã giao dịch (nếu có)',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nhập mã giao dịch từ ngân hàng'
        })
    )
    
    confirm_payment = forms.BooleanField(
        label='Tôi xác nhận đã thanh toán',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
