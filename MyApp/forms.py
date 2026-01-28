from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

from .models import Product, StoryboardItem, RawItem, CabinetItem, UserProfile


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

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['title', 'slug', 'excerpt', 'image', 'description', 'price']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Tên sản phẩm'}),
            'slug': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'slug-san-pham'}),
            'excerpt': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Mô tả ngắn'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 4, 'placeholder': 'Mô tả chi tiết'}),
            'price': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Giá (VNĐ)'}),
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
