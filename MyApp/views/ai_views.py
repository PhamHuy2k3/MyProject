from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils import timezone
from django.template.loader import render_to_string
from django.db.models import Count, Sum, Avg, F, Q, DecimalField, IntegerField
from django.db.models.functions import Coalesce
from decimal import Decimal
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt

from django.conf import settings
from MyApp.models import *
from MyApp.forms import *
import requests
import json
import re
from .utils import *

# ==================== AI CHATBOT VIEWS ====================

def get_or_create_ai_session(request):
    if request.user.is_authenticated:
        session, _ = AIChatSession.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        session, _ = AIChatSession.objects.get_or_create(session_key=session_key)
    return session

@csrf_exempt
def api_chat_history(request):
    """Trả về lịch sử chat của session hiện tại"""
    from django.http import JsonResponse
    session = get_or_create_ai_session(request)
    messages = session.messages.all().order_by('created_at')
    data = []
    for msg in messages:
        # Xóa thẻ [PRODUCTS: ...] nếu còn sót trong DB cũ
        cleaned_content = re.sub(r'\[PRODUCTS:\s*[\d,\s]+\]', '', msg.content).strip()
        data.append({
            'sender': msg.sender,
            'content': cleaned_content,
            'created_at': msg.created_at.isoformat()
        })
    return JsonResponse({'messages': data})

@csrf_exempt
def api_chat_message(request):
    """Xử lý tin nhắn mới từ người dùng và gọi Gemini API"""
    from django.http import JsonResponse
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    try:
        body = json.loads(request.body)
        user_content = body.get('message', '').strip()
    except:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        
    if not user_content:
        return JsonResponse({'error': 'Message cannot be empty'}, status=400)
        
    session = get_or_create_ai_session(request)
    
    # Lưu tin nhắn của user
    AIChatMessage.objects.create(session=session, sender='user', content=user_content)
    
    # Xây dựng Context lấy từ database (Sản phẩm)
    active_filter = Q(category__isnull=True) | Q(category__is_active=True)
    products = Product.objects.with_available_stock().filter(active_filter, available_stock_value__gt=0)[:20] # Lấy 20 SP còn hàng
    product_context = "Sản phẩm hiện có tại TeaZen:\n"
    for p in products:
        price = f"{p.price:,.0f} VNĐ" if p.price else "Liên hệ"
        product_context += f"- [ID: {p.id}] {p.title}: {price}. {p.excerpt}\n"
        
    # Lấy lịch sử chat (đảm bảo role xen kẽ đúng user/model cho Gemini API)
    recent_messages = session.messages.order_by('-created_at')[:10]
    history_context = []
    for m in reversed(recent_messages):
        role = "user" if m.sender == "user" else "model"
        # Gemini yêu cầu role phải xen kẽ, gộp các tin nhắn liên tiếp cùng role
        if history_context and history_context[-1]["role"] == role:
            history_context[-1]["parts"][0]["text"] += "\n" + m.content
        else:
            history_context.append({
                "role": role,
                "parts": [{"text": m.content}]
            })
    # Đảm bảo tin nhắn đầu tiên luôn là user (Gemini API yêu cầu)
    if history_context and history_context[0]["role"] == "model":
        history_context = history_context[1:]
        
    system_instruction = """
    Bạn là một chuyên gia tư vấn trà đạo thanh lịch, làm việc cho thương hiệu TeaZen.
    TeaZen là một website thương mại điện tử chuyên bán các loại trà cao cấp và ấm chén nghệ thuật.
    Hãy trả lời khách hàng một cách lịch sự, tinh tế, mang hơi hướng cổ điển nhưng vẫn tự nhiên và thân thiện.
    Dựa vào danh sách sản phẩm cửa hàng đang có để tư vấn phù hợp nhất. Nếu khách hỏi sản phẩm không có, hãy khéo léo giới thiệu sản phẩm tương tự.
    Luôn dùng tiếng Việt chuẩn mực. Trực tiếp trả lời câu hỏi, không cần phải luôn luôn chào lại mỗi tin nhắn nếu đang trong cuộc hội thoại.
    
    QUAN TRỌNG: 
    Nếu trong câu trả lời bạn quyết định ĐỀ XUẤT cụ thể 1 hoặc nhiều sản phẩm nào đó từ danh sách, bạn BẮT BUỘC phải thêm một thẻ ở cuối cùng của tin nhắn với định dạng: [PRODUCTS: id1, id2, ...]
    Ví dụ: [PRODUCTS: 5, 12, 8]
    Nếu không đề xuất sản phẩm cụ thể nào, đừng thêm thẻ này.
    """
    
    # Loại bỏ tin nhắn cuối cùng của user ra khỏi history vì API Gemini v1beta yêu cầu payload contents phải theo thứ tự
    gemini_contents = history_context[:-1] 
    gemini_contents.append({
        "role": "user",
        "parts": [{"text": f"Context dữ liệu cửa hàng:\n{product_context}\n\nTin nhắn người dùng:\n{user_content}"}]
    })

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        AIChatMessage.objects.create(session=session, sender='ai', content='Hệ thống chưa được cấu hình API key. Vui lòng liên hệ quản trị viên.')
        return JsonResponse({'sender': 'ai', 'content': 'Hệ thống chưa được cấu hình API key. Vui lòng liên hệ quản trị viên.', 'recommended_products': []})
    
    # Thử lần lượt các model Gemini (phòng trường hợp quota hết ở model chính)
    gemini_models = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-2.0-flash-lite']
    
    def build_payload(use_snake_case: bool):
        if use_snake_case:
            return {
                "system_instruction": {
                    "parts": [{"text": system_instruction}]
                },
                "contents": gemini_contents,
                "generation_config": {
                    "temperature": 0.7,
                    "max_output_tokens": 2048,
                }
            }
        return {
            "systemInstruction": {
                "parts": [{"text": system_instruction}]
            },
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048,
            }
        }

    def should_retry_with_snake_case(resp_data):
        try:
            text = json.dumps(resp_data, ensure_ascii=False)
        except Exception:
            text = str(resp_data)
        return (
            'Unknown name "systemInstruction"' in text or
            'Unknown name "generationConfig"' in text or
            ('Unknown name' in text and 'systemInstruction' in text) or
            ('Unknown name' in text and 'generationConfig' in text)
        )

    payload = build_payload(use_snake_case=False)
    payload_snake = build_payload(use_snake_case=True)
    
    headers = {'Content-Type': 'application/json'}
    
    ai_content = None
    last_error = None
    import time
    for model_name in gemini_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        for attempt in range(2):
            current_payload = payload if attempt == 0 else payload_snake
            try:
                response = requests.post(url, headers=headers, json=current_payload, timeout=30)
                try:
                    resp_data = response.json()
                except Exception:
                    resp_data = {"error": "non_json_response", "text": response.text}
                
                if response.status_code == 200:
                    try:
                        ai_content = resp_data['candidates'][0]['content']['parts'][0]['text']
                    except Exception:
                        ai_content = None
                        last_error = {"error": "invalid_response_shape", "response": resp_data}
                    if ai_content:
                        break
                elif response.status_code == 429:
                    print(f"Gemini API 429 (quota exceeded) for model {model_name}, trying next model...")
                    last_error = resp_data
                    break
                elif response.status_code == 400 and attempt == 0 and should_retry_with_snake_case(resp_data):
                    print("Retrying Gemini payload with snake_case fields...")
                    last_error = resp_data
                    continue
                else:
                    print(f"Gemini API Error ({model_name}) Status: {response.status_code}")
                    print(f"Gemini API Error Response: {resp_data}")
                    last_error = resp_data
                    break
            except requests.exceptions.Timeout:
                print(f"Gemini API timeout for model {model_name}")
                last_error = {"error": "timeout"}
                break
            except Exception as e:
                import traceback
                print(f"Exception calling Gemini API ({model_name}):")
                traceback.print_exc()
                last_error = {"error": "exception", "details": str(e)}
                break
        if ai_content:
            break
    
    if ai_content is None:
        ai_content = "Xin thứ lỗi, hiện tại tôi đang gặp chút vấn đề kỹ thuật. Quý khách vui lòng thử lại sau giây lát nhé."
        
    # Xử lý parse [PRODUCTS: id1, id2]
    recommended_products = []
    product_match = re.search(r'\[PRODUCTS:\s*([\d,\s]+)\]', ai_content)
    if product_match:
        id_strings = product_match.group(1).split(',')
        product_ids = []
        for pid in id_strings:
            pid = pid.strip()
            if pid.isdigit():
                product_ids.append(int(pid))
        
        if product_ids:
            # Query the database for these specific products
            from django.urls import reverse
            active_filter = Q(category__isnull=True) | Q(category__is_active=True)
            recs = Product.objects.filter(active_filter, id__in=product_ids)
            for p in recs:
                recommended_products.append({
                    'id': p.id,
                    'title': p.title,
                    'price': float(p.price) if p.price else 0,
                    'image_url': p.image.url if p.image else '',
                    'detail_url': reverse('product_detail', kwargs={'slug': p.slug})
                })
        
        # Remove the tag from the message so it doesn't show to user
        ai_content = re.sub(r'\[PRODUCTS:\s*[\d,\s]+\]', '', ai_content).strip()

    # Lưu reply từ AI (lưu text đã xóa raw tag)
    AIChatMessage.objects.create(session=session, sender='ai', content=ai_content)
    
    response_payload = {
        'sender': 'ai',
        'content': ai_content,
        'recommended_products': recommended_products
    }
    if settings.DEBUG and last_error:
        response_payload['debug'] = last_error
    return JsonResponse(response_payload)
