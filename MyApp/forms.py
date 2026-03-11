from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

from .models import Product, StoryboardItem, RawItem, CabinetItem, Category, UserProfile, Payment


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


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar', 'bio', 'phone', 'address']
        widgets = {
            'bio': forms.TextInput(attrs={'class': 'input-field', 'placeholder': ' '}),
            'phone': forms.TextInput(attrs={'class': 'input-field', 'placeholder': ' '}),
            'address': forms.Textarea(attrs={'class': 'input-field', 'rows': 3, 'placeholder': ' '}),
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
        fields = ['category', 'title', 'slug', 'excerpt', 'image', 'description', 'price', 'stock_quantity']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-input'}),
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Tên sản phẩm'}),
            'slug': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'slug-san-pham'}),
            'excerpt': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Mô tả ngắn'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 4, 'placeholder': 'Mô tả chi tiết'}),
            'price': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Giá (VNĐ)'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Số lượng tồn kho'}),
            'image': forms.FileInput(attrs={'class': 'form-file'}),
        }


class StoryboardItemForm(forms.ModelForm):
    class Meta:
        model = StoryboardItem
        fields = ['title', 'slug', 'image', 'excerpt']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Tiêu đề'}),
            'slug': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'slug-tieu-de'}),
            'excerpt': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Mô tả ngắn'}),
            'image': forms.FileInput(attrs={'class': 'form-file'}),
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
        fields = ['title', 'image', 'note']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Tiêu đề'}),
            'note': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ghi chú'}),
            'image': forms.FileInput(attrs={'class': 'form-file'}),
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
