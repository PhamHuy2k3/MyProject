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

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "minimax/minimax-m2.7"

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
        cleaned_content = re.sub(r'\[PRODUCTS:\s*[\d,\s]+\]', '', msg.content).strip()
        data.append({
            'sender': msg.sender,
            'content': cleaned_content,
            'created_at': msg.created_at.isoformat()
        })
    return JsonResponse({'messages': data})

@csrf_exempt
def api_chat_message(request):
    """Xử lý tin nhắn mới từ người dùng và gọi OpenRouter API (Claude)"""
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
    products = Product.objects.with_available_stock().filter(active_filter, available_stock_value__gt=0)[:20]
    product_context = "Sản phẩm hiện có tại TeaZen:\n"
    for p in products:
        price = f"{p.price:,.0f} VNĐ" if p.price else "Liên hệ"
        product_context += f"- [ID: {p.id}] {p.title}: {price}. {p.excerpt}\n"
        
    # Lấy lịch sử chat gần đây
    recent_messages = session.messages.order_by('-created_at')[:10]
    chat_history = []
    for m in reversed(recent_messages):
        role = "user" if m.sender == "user" else "assistant"
        # Gộp tin nhắn liên tiếp cùng role
        if chat_history and chat_history[-1]["role"] == role:
            chat_history[-1]["content"] += "\n" + m.content
        else:
            chat_history.append({"role": role, "content": m.content})
    
    # Đảm bảo tin nhắn đầu tiên là user
    if chat_history and chat_history[0]["role"] == "assistant":
        chat_history = chat_history[1:]
        
    system_prompt = f"""Bạn là một chuyên gia tư vấn trà đạo thanh lịch, làm việc cho thương hiệu TeaZen.
TeaZen là một website thương mại điện tử chuyên bán các loại trà cao cấp và ấm chén nghệ thuật.
Hãy trả lời khách hàng một cách lịch sự, tinh tế, mang hơi hướng cổ điển nhưng vẫn tự nhiên và thân thiện.
Dựa vào danh sách sản phẩm cửa hàng đang có để tư vấn phù hợp nhất. Nếu khách hỏi sản phẩm không có, hãy khéo léo giới thiệu sản phẩm tương tự.
Luôn dùng tiếng Việt chuẩn mực. Trực tiếp trả lời câu hỏi, không cần phải luôn luôn chào lại mỗi tin nhắn nếu đang trong cuộc hội thoại.

BẮT BUỘC - RẤT QUAN TRỌNG:
Mỗi khi bạn nhắc đến hoặc ĐỀ XUẤT bất kỳ sản phẩm nào từ danh sách bên dưới trong câu trả lời, bạn PHẢI thêm dòng cuối cùng là thẻ sản phẩm theo đúng định dạng sau:
[PRODUCTS: id1, id2, id3]
Trong đó id1, id2, id3 là các ID số nguyên của sản phẩm từ danh sách.
Ví dụ: Nếu bạn nhắc đến sản phẩm có ID 5 và ID 12, bạn PHẢI kết thúc tin nhắn bằng: [PRODUCTS: 5, 12]
Luôn luôn thêm thẻ này khi có nhắc đến sản phẩm cụ thể. KHÔNG BAO GIỜ quên thẻ này.

Context dữ liệu cửa hàng:
{product_context}"""
    
    # Xây dựng messages cho OpenRouter (OpenAI-compatible format)
    # Loại bỏ tin nhắn cuối (là tin nhắn user vừa gửi đã có trong history)
    openrouter_messages = [{"role": "system", "content": system_prompt}]
    
    # Thêm history (bỏ tin cuối vì sẽ thêm riêng với context)
    if len(chat_history) > 1:
        openrouter_messages.extend(chat_history[:-1])
    
    # Thêm tin nhắn hiện tại của user
    openrouter_messages.append({"role": "user", "content": user_content})

    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        error_msg = 'Hệ thống chưa được cấu hình API key. Vui lòng liên hệ quản trị viên.'
        AIChatMessage.objects.create(session=session, sender='ai', content=error_msg)
        return JsonResponse({'sender': 'ai', 'content': error_msg, 'recommended_products': []})
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
        'HTTP-Referer': 'http://localhost:8000',
        'X-Title': 'TeaZen Chatbot',
    }
    
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": openrouter_messages,
        "temperature": 0.7,
        "max_tokens": 2048,
    }
    
    ai_content = None
    last_error = None
    
    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        try:
            resp_data = response.json()
        except Exception:
            resp_data = {"error": "non_json_response", "text": response.text[:500]}
        
        if response.status_code == 200:
            try:
                ai_content = resp_data['choices'][0]['message']['content']
            except Exception:
                ai_content = None
                last_error = {"error": "invalid_response_shape", "response": resp_data}
        else:
            print(f"OpenRouter API Error - Status: {response.status_code}")
            print(f"OpenRouter API Error Response: {resp_data}")
            last_error = resp_data
    except requests.exceptions.Timeout:
        print("OpenRouter API timeout")
        last_error = {"error": "timeout"}
    except Exception as e:
        import traceback
        print(f"Exception calling OpenRouter API:")
        traceback.print_exc()
        last_error = {"error": "exception", "details": str(e)}
    
    if ai_content is None:
        error_detail = ''
        if settings.DEBUG and last_error:
            error_detail = f"\n\n[DEBUG] Chi tiết lỗi: {json.dumps(last_error, ensure_ascii=False, default=str)[:500]}"
        ai_content = f"Xin thứ lỗi, hiện tại tôi đang gặp chút vấn đề kỹ thuật. Quý khách vui lòng thử lại sau giây lát nhé.{error_detail}"
        print(f'[CHATBOT ERROR] OpenRouter API failed. Last error: {last_error}')
        
    # Xử lý parse [PRODUCTS: id1, id2]
    from django.urls import reverse
    recommended_products = []
    product_ids = []
    
    product_match = re.search(r'\[PRODUCTS:\s*([\d,\s]+)\]', ai_content)
    if product_match:
        id_strings = product_match.group(1).split(',')
        for pid in id_strings:
            pid = pid.strip()
            if pid.isdigit():
                product_ids.append(int(pid))
        # Remove the tag from the message so it doesn't show to user
        ai_content = re.sub(r'\[PRODUCTS:\s*[\d,\s]+\]', '', ai_content).strip()
    
    # Fallback: nếu AI không thêm tag, tìm sản phẩm theo tên được nhắc đến
    if not product_ids:
        active_filter = Q(category__isnull=True) | Q(category__is_active=True)
        all_products = Product.objects.filter(active_filter)
        for p in all_products:
            if p.title and p.title.lower() in ai_content.lower():
                product_ids.append(p.id)
        # Giới hạn tối đa 5 sản phẩm
        product_ids = product_ids[:5]
    
    if product_ids:
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

    # Lưu reply từ AI
    AIChatMessage.objects.create(session=session, sender='ai', content=ai_content)
    
    response_payload = {
        'sender': 'ai',
        'content': ai_content,
        'recommended_products': recommended_products
    }
    if settings.DEBUG and last_error:
        response_payload['debug'] = last_error
    return JsonResponse(response_payload)
