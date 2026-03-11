"""
VietQR Service - Tích hợp API VietQR để tạo mã QR thanh toán động
"""
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class VietQRService:
    """Service để gọi VietQR API và tạo mã QR thanh toán"""
    
    # VietQR API endpoints
    VIETQR_API_BASE = "https://api.vietqr.io"  # Production
    VIETQR_API_DEV = "https://api.vietqr.io"  # Development (Use same base URL)
    
    QR_GENERATE_ENDPOINT = "/v2/generate"
    
    def __init__(self):
        """Khởi tạo VietQR service"""
        self.vietqr_config = getattr(settings, 'VIETQR_CONFIG', {})
        self.use_dev = self.vietqr_config.get('use_dev', False)
        self.api_base = self.VIETQR_API_DEV if self.use_dev else self.VIETQR_API_BASE
        self.client_id = self.vietqr_config.get('client_id', '')
        self.api_key = self.vietqr_config.get('api_key', '')
    
    def get_bin_code(self, bank_code):
        """
        Chuyển đổi mã ngân hàng (string) sang BIN code (acqId) 6 số
        """
        bank_map = {
            'BIDV': '970418',
            'MB': '970422', 'MBBANK': '970422',
            'VCB': '970436', 'VIETCOMBANK': '970436',
            'CTG': '970415', 'VIETINBANK': '970415',
            'TCB': '970407', 'TECHCOMBANK': '970407',
            'ACB': '970416',
            'VPB': '970432', 'VPBANK': '970432',
            'TPB': '970423', 'TPBANK': '970423',
            'STB': '970403', 'SACOMBANK': '970403',
            'VIB': '970441',
            'HDB': '970437', 'HDBANK': '970437',
        }
        
        code_str = str(bank_code).strip().upper()
        # Nếu là số 6 chữ số thì trả về luôn
        if code_str.isdigit() and len(code_str) == 6:
            return code_str
            
        return bank_map.get(code_str, code_str)

    def generate_qr_code(self, order, qr_type=0):
        """
        Tạo mã QR thanh toán từ VietQR API
        
        Args:
            order: Order object
            qr_type: Loại QR (0=động, 1=tĩnh, 3=bán động)
                    Mặc định: 0 (động)
        
        Returns:
            dict: Response từ VietQR API chứa qrCode, imgId, qrLink, v.v.
        """
        try:
            # Lấy thông tin ngân hàng từ settings
            bank_config = getattr(settings, 'BANK_ACCOUNT', {})
            
            url = f"{self.api_base}{self.QR_GENERATE_ENDPOINT}"
            headers = {
                'Content-Type': 'application/json',
                'x-client-id': self.client_id,
                'x-api-key': self.api_key,
            }
            content = f"TeaZen{order.order_number[-6:]}".replace("-", "")[:23]
            bank_code = bank_config.get('code', '970422')
            acq_id = self.get_bin_code(bank_code)
            logger.info(f"VietQR processing: Bank={bank_code} -> BIN={acq_id}")
            
            payload = {
                'accountNo': bank_config.get('account_number', ''),
                'accountName': bank_config.get('account_name', ''),
                'acqId': acq_id,
                'amount': int(order.total_amount),
                'addInfo': content,
                'format': 'text',
                'template': 'compact'
            }
            
            logger.info(f"Creating VietQR for order {order.order_number}")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('code') != '00':
                raise Exception(f"VietQR API Error: {data.get('desc')}")
            
            result_data = data.get('data', {})
            result = {
                'qrCode': result_data.get('qrCode'),
                'qrLink': result_data.get('qrDataURL'),
                'imgId': result_data.get('qrDataURL'),
            }
            
            logger.info(f"VietQR created successfully: {result.get('qrLink')}")
            return result
            
        except requests.RequestException as e:
            logger.error(f"VietQR QR generation error: {str(e)}")
            raise Exception(f"Lỗi tạo mã QR: {str(e)}")
        except Exception as e:
            logger.error(f"VietQR unexpected error: {str(e)}")
            raise
    
    def get_qr_image(self, qr_link):
        try:
            response = requests.get(qr_link, timeout=30)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Error fetching QR image: {str(e)}")
            return None


def create_vietqr_payment(order):
    service = VietQRService()
    return service.generate_qr_code(order, qr_type=0)
