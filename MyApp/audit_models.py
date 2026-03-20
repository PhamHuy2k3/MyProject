import uuid
import json
from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet
from django.core.exceptions import ValidationError

class EncryptedTextField(models.TextField):
    """Custom TextField that encrypts data before saving and decrypts when reading."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_fernet(self):
        key = getattr(settings, 'AUDIT_LOG_ENCRYPTION_KEY', None)
        if not key:
            raise ValueError("AUDIT_LOG_ENCRYPTION_KEY must be set in settings.")
        return Fernet(key)

    def get_prep_value(self, value):
        if value is None or value == '':
            return value
        if not isinstance(value, str):
            value = json.dumps(value)
        cipher = self.get_fernet()
        encrypted_value = cipher.encrypt(value.encode('utf-8'))
        return encrypted_value.decode('utf-8')

    def from_db_value(self, value, expression, connection):
        if value is None or value == '':
            return value
        try:
            cipher = self.get_fernet()
            decrypted_value = cipher.decrypt(value.encode('utf-8'))
            return decrypted_value.decode('utf-8')
        except Exception:
            return value  # If decryption fails (e.g. data was not encrypted)


class AuditLog(models.Model):
    SEVERITY_CHOICES = [
        ('INFO', 'Thông tin'),
        ('WARNING', 'Cảnh báo'),
        ('ERROR', 'Lỗi'),
        ('CRITICAL', 'Nghiêm trọng'),
    ]

    log_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="Log ID")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Thời gian")
    event_type = models.CharField(max_length=100, db_index=True, verbose_name="Loại sự kiện")
    severity_level = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='INFO', verbose_name="Mức độ")
    
    actor_id = models.IntegerField(null=True, blank=True, verbose_name="User/Account ID")
    actor_role = models.CharField(max_length=50, blank=True, verbose_name="Vai trò")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Địa chỉ IP")
    user_agent = models.CharField(max_length=255, blank=True, verbose_name="User Agent")
    
    resource_type = models.CharField(max_length=100, blank=True, verbose_name="Loại tài nguyên")
    resource_id = models.CharField(max_length=100, blank=True, verbose_name="ID Tài nguyên")
    
    before_state = EncryptedTextField(blank=True, verbose_name="Dữ liệu Cũ")
    after_state = EncryptedTextField(blank=True, verbose_name="Dữ liệu Mới")
    
    status = models.CharField(max_length=20, default='SUCCESS', verbose_name="Trạng thái")
    reason = models.TextField(blank=True, verbose_name="Lý do chi tiết")
    
    previous_hash = models.CharField(max_length=64, blank=True, verbose_name="Mã băm liền trước")
    current_hash = models.CharField(max_length=64, blank=True, verbose_name="Mã băm hiện tại")

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"

    def __str__(self):
        return f"{self.timestamp} - {self.event_type} ({self.actor_id})"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Audit Logs are append-only. Modification is not allowed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit Logs are append-only. Deletion is not allowed.")
