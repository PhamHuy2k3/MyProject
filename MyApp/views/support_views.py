from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from MyApp.models import Order, OrderItem, ReturnRequest, ReturnItem, ProductVariation, Product

@login_required(login_url='login')
def request_return(request, order_number):
    """
    User requests a return or exchange for a delivered order.
    """
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    # Validation: Only delivered orders can be returned
    if order.status != 'delivered':
        messages.error(request, 'Bạn chỉ có thể yêu cầu trả hàng cho các đơn hàng đã giao thành công.')
        return redirect('order_detail', order_number=order_number)
    
    # Check if a return request already exists
    if order.return_requests.exclude(status='rejected').exists():
        messages.warning(request, 'Đơn hàng này đang có yêu cầu đổi trả đang được xử lý.')
        return redirect('order_detail', order_number=order_number)

    if request.method == 'POST':
        request_type = request.POST.get('request_type')
        reason = request.POST.get('reason')
        image = request.FILES.get('image')
        
        # Create the ReturnRequest
        return_req = ReturnRequest.objects.create(
            order=order,
            request_type=request_type,
            reason=reason,
            image=image,
            status='pending'
        )
        
        # Process items
        item_ids = request.POST.getlist('items')
        for item_id in item_ids:
            quantity = int(request.POST.get(f'quantity_{item_id}', 0))
            if quantity > 0:
                order_item = get_object_or_404(OrderItem, id=item_id, order=order)
                # Check quantity validity
                if quantity <= order_item.quantity:
                    ReturnItem.objects.create(
                        return_request=return_req,
                        order_item=order_item,
                        quantity=quantity
                    )
        
        # If no items were selected, delete the request and error out
        if not return_req.return_items.exists():
            return_req.delete()
            messages.error(request, 'Vui lòng chọn ít nhất một sản phẩm để đổi trả.')
            return redirect('request_return', order_number=order_number)
        
        # Update order status
        order.status = 'return_requested'
        order.save()
        
        messages.success(request, 'Yêu cầu đổi trả của bạn đã được gửi. Chúng tôi sẽ phản hồi sớm nhất.')
        return redirect('order_detail', order_number=order_number)

    return render(request, 'support/request_return.html', {'order': order})

@login_required(login_url='login')
def cancel_order(request, order_number):
    """
    Cancel an order if it's still pending.
    """
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    if order.status != 'pending':
        messages.error(request, 'Bạn không thể hủy đơn hàng này khi đã bắt đầu xử lý hoặc giao.')
        return redirect('order_detail', order_number=order_number)
    
    # Restore stock
    for item in order.items.all():
        if item.variation:
            item.variation.stock_quantity += item.quantity
            item.variation.save()
        elif item.product:
            item.product.stock_quantity += item.quantity
            item.product.save()
            
    order.status = 'cancelled'
    order.save()
    
    messages.success(request, f'Đơn hàng {order_number} đã được hủy thành công.')
    return redirect('order_list')
