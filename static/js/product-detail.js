(function () {
    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta && meta.content) return meta.content;
        // Fallback to cookie
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : '';
    }

    function formatVnd(value) {
        const num = Number(value);
        if (Number.isNaN(num)) return value;
        return new Intl.NumberFormat('vi-VN').format(num) + '₫';
    }

    function ensureFallbackProductFns() {
        if (!window.switchImage) {
            window.switchImage = function (url) {
                const img = document.getElementById('main-product-img');
                if (!img) return;
                img.src = url;
                document.querySelectorAll('.gallery-thumb').forEach(t => {
                    const thumbImg = t.querySelector('img');
                    if (thumbImg && thumbImg.src === url) {
                        t.classList.add('border-emerald-600', 'opacity-100');
                        t.classList.remove('border-stone-200', 'opacity-70');
                    } else {
                        t.classList.remove('border-emerald-600', 'opacity-100');
                        t.classList.add('border-stone-200', 'opacity-70');
                    }
                });
            };
        }

        if (!window.handleZoom) {
            window.handleZoom = function (e) {
                const container = document.getElementById('zoom-container');
                const img = document.getElementById('main-product-img');
                const lens = document.getElementById('zoom-lens');
                const preview = document.getElementById('zoom-preview');
                if (!container || !img || !lens || !preview || window.innerWidth < 1024) return;

                const rect = container.getBoundingClientRect();
                let x = e.clientX - rect.left;
                let y = e.clientY - rect.top;
                const lw = lens.offsetWidth / 2;
                const lh = lens.offsetHeight / 2;

                x = Math.max(lw, Math.min(x, rect.width - lw));
                y = Math.max(lh, Math.min(y, rect.height - lh));

                lens.style.left = (x - lw) + 'px';
                lens.style.top = (y - lh) + 'px';
                lens.classList.remove('hidden');

                const zoomFactor = 2.5;
                preview.style.backgroundImage = `url(${img.src})`;
                preview.style.backgroundSize = `${rect.width * zoomFactor}px ${rect.height * zoomFactor}px`;
                preview.style.backgroundPosition = `-${(x - lw) * zoomFactor - preview.offsetWidth / 2 + lw * zoomFactor}px -${(y - lh) * zoomFactor - preview.offsetHeight / 2 + lh * zoomFactor}px`;
                preview.classList.remove('hidden');
            };
        }

        if (!window.hideZoom) {
            window.hideZoom = function () {
                const lens = document.getElementById('zoom-lens');
                const preview = document.getElementById('zoom-preview');
                if (lens) lens.classList.add('hidden');
                if (preview) preview.classList.add('hidden');
            };
        }

        if (!window.switchTab) {
            window.switchTab = function (tabId) {
                document.querySelectorAll('.product-tab-content').forEach(c => c.classList.add('hidden'));
                document.querySelectorAll('.product-tab-btn').forEach(b => {
                    b.classList.remove('text-emerald-900', 'border-emerald-700', 'bg-white');
                    b.classList.add('text-stone-500', 'border-transparent');
                });
                const tab = document.getElementById(tabId);
                const btn = document.getElementById('btn-' + tabId);
                if (tab) tab.classList.remove('hidden');
                if (btn) {
                    btn.classList.add('text-emerald-900', 'border-emerald-700', 'bg-white');
                    btn.classList.remove('text-stone-500', 'border-transparent');
                }
            };
        }

        if (!window.changeQty) {
            window.changeQty = function (delta) {
                const input = document.getElementById('qty-input');
                if (!input) return;
                let val = parseInt(input.value) || 1;
                val = Math.max(1, Math.min(val + delta, parseInt(input.max) || 999));
                input.value = val;
            };
        }
    }

    function ensureFallbackTooltip() {
        const tooltip = document.getElementById('product-tooltip');
        if (!tooltip) return;

        const tImg = document.getElementById('tooltip-img');
        const tTitle = document.getElementById('tooltip-title');
        const tPrice = document.getElementById('tooltip-price');
        const tExcerpt = document.getElementById('tooltip-excerpt');
        const OFFSET = 15;

        function onEnter(e) {
            const el = e.currentTarget;
            const title = el.dataset.title || '';
            const image = el.dataset.image || '';
            if (!title) return;

            if (tTitle) tTitle.textContent = title;
            if (tPrice) tPrice.textContent = el.dataset.price || '';
            if (tExcerpt) tExcerpt.textContent = el.dataset.excerpt || '';
            if (tImg) {
                tImg.src = image;
                tImg.style.display = image ? '' : 'none';
            }
            tooltip.style.opacity = '1';
        }

        function onMove(e) {
            if (tooltip.style.opacity === '0') return;
            const rect = tooltip.getBoundingClientRect();
            const vw = window.innerWidth;
            const vh = window.innerHeight;

            let x = e.clientX + OFFSET;
            let y = e.clientY + OFFSET;
            if (x + rect.width > vw) x = e.clientX - rect.width - OFFSET;
            if (y + rect.height > vh) y = e.clientY - rect.height - OFFSET;

            tooltip.style.left = Math.max(4, x) + 'px';
            tooltip.style.top = Math.max(4, y) + 'px';
        }

        function onLeave() {
            tooltip.style.opacity = '0';
        }

        function bindTooltips() {
            document.querySelectorAll('.product-hover-trigger').forEach(el => {
                if (el.dataset.tooltipBound) return;
                el.dataset.tooltipBound = '1';
                el.addEventListener('mouseenter', onEnter);
                el.addEventListener('mousemove', onMove);
                el.addEventListener('mouseleave', onLeave);
            });
        }

        bindTooltips();
        const observer = new MutationObserver(bindTooltips);
        observer.observe(document.body, { childList: true, subtree: true });
    }

    function updateVariationUI(input) {
        if (!input) return;
        const price = input.dataset.price;
        const stock = parseInt(input.dataset.stock || '0', 10);

        const priceDisplay = document.getElementById('product-price-display');
        if (priceDisplay && price) priceDisplay.textContent = formatVnd(price);

        const stickyPrice = document.querySelector('#sticky-cta .font-art');
        if (stickyPrice && price) stickyPrice.textContent = formatVnd(price);

        const qtyInput = document.getElementById('qty-input');
        if (qtyInput) {
            qtyInput.max = stock > 0 ? String(stock) : '0';
            if (parseInt(qtyInput.value || '1', 10) > stock && stock > 0) {
                qtyInput.value = String(stock);
            }
        }

        const variationInput = document.getElementById('variation-input');
        if (variationInput) variationInput.value = input.value;

        const form = document.getElementById('add-to-cart-form');
        if (form) form.dataset.productStock = stock;

        const addBtn = document.querySelector('#add-to-cart-form button[type="submit"]');
        const stickyBtn = document.querySelector('#sticky-cta button');
        const inStock = stock > 0;
        if (addBtn) {
            addBtn.disabled = !inStock;
            addBtn.innerText = inStock ? 'Thêm vào giỏ' : 'Hết hàng';
        }
        if (stickyBtn) stickyBtn.disabled = !inStock;
    }

    function initVariationUI() {
        const container = document.getElementById('variation-container');
        if (!container) return;
        const inputs = container.querySelectorAll('input[name="variation_radio"]');
        if (!inputs.length) return;

        container.addEventListener('change', (e) => {
            const target = e.target;
            if (target && target.name === 'variation_radio') {
                updateVariationUI(target);
            }
        });

        const checked = container.querySelector('input[name="variation_radio"]:checked') || inputs[0];
        updateVariationUI(checked);
    }

    function updateCommentCount(count) {
        document.querySelectorAll('[data-comment-count]').forEach(el => {
            el.textContent = count;
        });
        const text = document.getElementById('comment-count-text');
        if (text) text.textContent = `${count} bình luận`;
        const inline = document.getElementById('comment-count-inline');
        if (inline) inline.textContent = `(${count})`;
    }

    function bindCommentEvents() {
        document.querySelectorAll('.auto-resize-textarea').forEach(el => {
            if (el.dataset.autoresizeBound) return;
            el.dataset.autoresizeBound = '1';
            const resize = () => {
                el.style.height = 'auto';
                el.style.height = el.scrollHeight + 'px';
            };
            el.addEventListener('input', resize);
            resize();
        });

        document.querySelectorAll('.comment-form').forEach(form => {
            if (form.dataset.counterBound) return;
            form.dataset.counterBound = '1';
            const textarea = form.querySelector('textarea[name="content"]');
            const counter = form.querySelector('.char-counter');
            if (textarea && counter) {
                const update = () => {
                    const max = parseInt(textarea.getAttribute('maxlength') || '1000', 10);
                    counter.textContent = `${textarea.value.length}/${max}`;
                };
                textarea.addEventListener('input', update);
                update();
            }

            const fileInput = form.querySelector('.media-upload-input');
            const preview = form.querySelector('.media-preview-container');
            if (fileInput && preview) {
                fileInput.addEventListener('change', () => {
                    preview.innerHTML = '';
                    const files = Array.from(fileInput.files || []);
                    if (!files.length) {
                        preview.classList.add('hidden');
                        return;
                    }
                    preview.classList.remove('hidden');
                    files.forEach(file => {
                        const url = URL.createObjectURL(file);
                        const item = document.createElement(file.type.startsWith('video') ? 'video' : 'img');
                        item.src = url;
                        item.className = 'w-16 h-16 object-cover rounded-lg border border-stone-200';
                        if (item.tagName === 'VIDEO') {
                            item.controls = true;
                        }
                        preview.appendChild(item);
                    });
                });
            }
        });
    }

    function showCommentToast(message, type = 'success') {
        if (window.showCommentToast) {
            window.showCommentToast(message, type);
            return;
        }
        if (type === 'error') {
            alert(message);
        }
    }

    window.submitComment = function (event, productId, parentId = null) {
        event.preventDefault();
        const form = event.target;
        const textarea = form.querySelector('textarea[name="content"]');
        if (!textarea || !textarea.value.trim()) return;

        const btn = form.querySelector('.submit-btn') || form.querySelector('button[type="submit"]');
        const originalBtnHtml = btn ? btn.innerHTML : '';
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="opacity-70">Đang gửi...</span>';
        }

        const slug = document.getElementById('product-meta')?.dataset.slug;
        if (!slug) {
            showCommentToast('Không tìm thấy sản phẩm.', 'error');
            if (btn) {
                btn.innerHTML = originalBtnHtml;
                btn.disabled = false;
            }
            return;
        }

        const formData = new FormData(form);
        if (parentId) formData.append('parent_id', parentId);

        fetch(`/product/${slug}/comment/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
            body: formData
        })
            .then(r => r.json())
            .then(data => {
                if (!data.success) throw new Error(data.error || 'submit_failed');

                if (data.parent_id) {
                    const repliesList = document.getElementById(`replies-list-${data.parent_id}`);
                    if (repliesList) {
                        repliesList.insertAdjacentHTML('beforeend', data.html || '');
                    }
                    showReplyWindow(data.parent_id);
                } else {
                    const container = document.getElementById('comments-list-container');
                    if (container) {
                        if (container.innerText.includes('Chưa có bình luận nào')) container.innerHTML = '';
                        container.insertAdjacentHTML('afterbegin', data.html || '');
                    }
                }

                textarea.value = '';
                const preview = form.querySelector('.media-preview-container');
                if (preview) {
                    preview.innerHTML = '';
                    preview.classList.add('hidden');
                }

                if (typeof data.total_count === 'number') {
                    updateCommentCount(data.total_count);
                }

                if (window.lucide) window.lucide.createIcons();
                bindCommentEvents();
                showCommentToast(parentId ? 'Đã gửi trả lời.' : 'Đã gửi bình luận.');
            })
            .catch((err) => {
                console.error('submitComment error:', err);
                showCommentToast('Không thể gửi bình luận. Vui lòng thử lại.', 'error');
            })
            .finally(() => {
                if (btn) {
                    btn.innerHTML = originalBtnHtml;
                    btn.disabled = false;
                    if (window.lucide) window.lucide.createIcons();
                }
            });
    };

    window.interactComment = function (commentId, action) {
        const likeBtn = document.getElementById(`btn-like-${commentId}`);
        const dislikeBtn = document.getElementById(`btn-dislike-${commentId}`);
        const likeCount = document.getElementById(`like-count-${commentId}`);

        if (!likeBtn || !dislikeBtn || !likeCount) return;

        const prevLikeClass = likeBtn.className;
        const prevDislikeClass = dislikeBtn.className;
        const prevCount = parseInt(likeCount.textContent) || 0;

        const isCurrentlyLiked = likeBtn.className.includes('text-emerald-600');
        const isCurrentlyDisliked = dislikeBtn.className.includes('text-red-500');

        let newCount = prevCount;

        if (action === 'like') {
            if (isCurrentlyLiked) {
                likeBtn.className = 'flex items-center gap-1.5 font-bold text-sm transition-colors text-stone-500 hover:text-emerald-600';
                const icon = likeBtn.querySelector('svg') || likeBtn.querySelector('i');
                if (icon) icon.classList.remove('fill-current');
                newCount = Math.max(0, prevCount - 1);
            } else {
                likeBtn.className = 'flex items-center gap-1.5 font-bold text-sm transition-colors text-emerald-600';
                const icon = likeBtn.querySelector('svg') || likeBtn.querySelector('i');
                if (icon) icon.classList.add('fill-current');
                if (isCurrentlyDisliked) {
                    dislikeBtn.className = 'flex items-center gap-1.5 font-bold text-sm transition-colors text-stone-500 hover:text-red-500';
                    const dIcon = dislikeBtn.querySelector('svg') || dislikeBtn.querySelector('i');
                    if (dIcon) dIcon.classList.remove('fill-current');
                }
                newCount = prevCount + 1;
            }
        } else if (action === 'dislike') {
            if (isCurrentlyDisliked) {
                dislikeBtn.className = 'flex items-center gap-1.5 font-bold text-sm transition-colors text-stone-500 hover:text-red-500';
                const dIcon = dislikeBtn.querySelector('svg') || dislikeBtn.querySelector('i');
                if (dIcon) dIcon.classList.remove('fill-current');
            } else {
                dislikeBtn.className = 'flex items-center gap-1.5 font-bold text-sm transition-colors text-red-500';
                const dIcon = dislikeBtn.querySelector('svg') || dislikeBtn.querySelector('i');
                if (dIcon) dIcon.classList.add('fill-current');
                if (isCurrentlyLiked) {
                    likeBtn.className = 'flex items-center gap-1.5 font-bold text-sm transition-colors text-stone-500 hover:text-emerald-600';
                    const icon = likeBtn.querySelector('svg') || likeBtn.querySelector('i');
                    if (icon) icon.classList.remove('fill-current');
                    newCount = Math.max(0, prevCount - 1);
                }
            }
        }

        likeCount.textContent = newCount;

        const formData = new FormData();
        formData.append('action', action);

        fetch(`/comment/${commentId}/interact/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
            body: formData
        })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    likeCount.textContent = data.likes;
                    likeBtn.className = `flex items-center gap-1.5 font-bold text-sm transition-colors ${data.state === 'like' ? 'text-emerald-600' : 'text-stone-500 hover:text-emerald-600'}`;
                    const icon = likeBtn.querySelector('svg') || likeBtn.querySelector('i');
                    if (icon) icon.classList.toggle('fill-current', data.state === 'like');

                    dislikeBtn.className = `flex items-center gap-1.5 font-bold text-sm transition-colors ${data.state === 'dislike' ? 'text-red-500' : 'text-stone-500 hover:text-red-500'}`;
                    const dIcon = dislikeBtn.querySelector('svg') || dislikeBtn.querySelector('i');
                    if (dIcon) dIcon.classList.toggle('fill-current', data.state === 'dislike');
                } else {
                    throw new Error('Not authenticated');
                }
            })
            .catch(err => {
                likeBtn.className = prevLikeClass;
                dislikeBtn.className = prevDislikeClass;

                const prevLiked = prevLikeClass.includes('text-emerald-600');
                const prevDisliked = prevDislikeClass.includes('text-red-500');

                const icon = likeBtn.querySelector('svg') || likeBtn.querySelector('i');
                if (icon) icon.classList.toggle('fill-current', prevLiked);

                const dIcon = dislikeBtn.querySelector('svg') || dislikeBtn.querySelector('i');
                if (dIcon) dIcon.classList.toggle('fill-current', prevDisliked);

                likeCount.textContent = prevCount;

                if (err.message === 'Not authenticated') {
                    window.location.href = `/login/?next=${encodeURIComponent(window.location.pathname)}`;
                } else {
                    alert('Mất kết nối mạng. Đã hoàn tác thao tác.');
                }
            });
    };

    window.deleteComment = function (commentId) {
        if (!confirm('Bạn có chắc chắn muốn xóa bình luận này?')) return;
        fetch(`/comment/${commentId}/delete/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() }
        })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    const el = document.getElementById('comment-' + commentId);
                    if (el) {
                        el.style.opacity = '0';
                        setTimeout(() => el.remove(), 300);
                    }
                    if (typeof data.total_count === 'number') {
                        updateCommentCount(data.total_count);
                    }
                    if (window.fetchComments) {
                        window.fetchComments(1, false);
                    }
                    showCommentToast('Đã xóa bình luận.');
                }
            });
    };

    window.toggleCommentReply = function (commentId, username) {
        const container = document.getElementById('reply-container-' + commentId);
        if (!container) return;
        container.classList.toggle('hidden');
        if (!container.classList.contains('hidden')) {
            const textarea = container.querySelector('textarea[name="content"]');
            if (textarea) {
                if (username && !textarea.value.trim()) textarea.value = `@${username} `;
                textarea.focus();
            }
        }
    };

    window.showReplyWindow = function (commentId) {
        document.querySelectorAll(`.reply-item-${commentId}`).forEach(el => el.classList.remove('hidden'));
        const showBtn = document.getElementById('show-replies-btn-' + commentId);
        const hideBtn = document.getElementById('hide-replies-btn-' + commentId);
        if (showBtn) showBtn.classList.add('hidden');
        if (hideBtn) hideBtn.classList.remove('hidden');
    };

    window.collapseReplies = function (commentId) {
        document.querySelectorAll(`.reply-item-${commentId}`).forEach(el => el.classList.add('hidden'));
        const showBtn = document.getElementById('show-replies-btn-' + commentId);
        const hideBtn = document.getElementById('hide-replies-btn-' + commentId);
        if (showBtn) showBtn.classList.remove('hidden');
        if (hideBtn) hideBtn.classList.add('hidden');
    };

    window.openLightbox = function (url) {
        if (!url) return;
        let overlay = document.getElementById('lightbox-overlay');
        let img;
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'lightbox-overlay';
            overlay.className = 'fixed inset-0 z-[9999] bg-black/70 flex items-center justify-center p-6';
            overlay.addEventListener('click', () => overlay.classList.add('hidden'));
            img = document.createElement('img');
            img.id = 'lightbox-image';
            img.className = 'max-h-[90vh] max-w-[90vw] rounded-2xl shadow-2xl border border-white/10';
            overlay.appendChild(img);
            document.body.appendChild(overlay);
        } else {
            img = document.getElementById('lightbox-image');
            overlay.classList.remove('hidden');
        }
        if (img) img.src = url;
    };

    window.voteReviewHelpful = function (reviewId) {
        if (!reviewId) return;
        const btn = document.getElementById(`helpful-btn-${reviewId}`);
        fetch(`/review/${reviewId}/helpful/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() }
        })
            .then(r => r.json())
            .then(data => {
                if (!data.success) return;
                const count = document.getElementById(`helpful-count-${reviewId}`);
                if (count) count.textContent = data.helpful_votes;
                if (btn) btn.classList.add('text-emerald-700');
            })
            .catch(() => {});
    };

    window.showUserPopup = function (event, username, userId) {
        event.preventDefault();
        const existing = document.getElementById('user-popup');
        if (existing) existing.remove();

        const popup = document.createElement('div');
        popup.id = 'user-popup';
        popup.className = 'fixed z-[9999] bg-white border border-stone-200 rounded-xl shadow-xl px-4 py-3 text-sm text-stone-700';
        popup.textContent = username || 'User';
        document.body.appendChild(popup);

        const x = event.clientX + 12;
        const y = event.clientY + 12;
        popup.style.left = x + 'px';
        popup.style.top = y + 'px';

        const remove = () => popup.remove();
        setTimeout(() => {
            document.addEventListener('click', remove, { once: true });
        }, 0);
    };

    function initReviewControls() {
        const search = document.getElementById('review-search');
        const sort = document.getElementById('review-sort');
        let debounce = null;
        if (search && window.fetchReviews) {
            search.addEventListener('input', () => {
                clearTimeout(debounce);
                debounce = setTimeout(() => window.fetchReviews(1), 300);
            });
        }
        if (sort && window.fetchReviews) {
            sort.addEventListener('change', () => window.fetchReviews(1));
        }

        const moreBtn = document.getElementById('reviews-more-btn');
        if (moreBtn && window.fetchReviews) {
            moreBtn.addEventListener('click', () => window.fetchReviews((window.currentReviewPage || 1) + 1));
        }
        const collapseBtn = document.getElementById('reviews-collapse-btn');
        if (collapseBtn && window.fetchReviews) {
            collapseBtn.addEventListener('click', () => window.fetchReviews(1));
        }

        if (document.getElementById('reviews-list-container') && window.fetchReviews) {
            window.fetchReviews(1);
        }
    }

    function initCommentControls() {
        const sort = document.getElementById('comment-sort');
        if (sort && window.fetchComments) {
            sort.addEventListener('change', () => window.fetchComments(1, false));
        }
        const moreBtn = document.getElementById('comments-more-btn');
        if (moreBtn && window.fetchComments) {
            moreBtn.addEventListener('click', () => window.fetchComments((window.currentCommentPage || 1) + 1, true));
        }
        const collapseBtn = document.getElementById('comments-collapse-btn');
        if (collapseBtn && window.fetchComments) {
            collapseBtn.addEventListener('click', () => window.fetchComments(1, false));
        }

        if (document.getElementById('comments-list-container') && window.fetchComments) {
            window.fetchComments(1, false);
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        ensureFallbackProductFns();
        ensureFallbackTooltip();
        initVariationUI();
        bindCommentEvents();
        initReviewControls();
        initCommentControls();
    });

    // Expose some helpers
    window.getCsrfToken = window.getCsrfToken || getCsrfToken;
    window.bindCommentEvents = window.bindCommentEvents || bindCommentEvents;
    window.updateCommentCount = window.updateCommentCount || updateCommentCount;

    /* ===== AJAX FETCH: Reviews ===== */
    window.currentReviewPage = 0;

    window.fetchReviews = function (page) {
        const slug = document.getElementById('product-meta')?.dataset.slug;
        const container = document.getElementById('reviews-list-container');
        if (!slug || !container) return;

        const search = document.getElementById('review-search');
        const sort = document.getElementById('review-sort');
        const params = new URLSearchParams();
        params.set('page', page);
        if (search && search.value.trim()) params.set('q', search.value.trim());
        if (sort) params.set('sort', sort.value);

        fetch(`/product/${slug}/reviews-ajax/?${params}`)
            .then(r => r.json())
            .then(data => {
                if (page === 1) {
                    container.innerHTML = data.html || '';
                } else {
                    container.insertAdjacentHTML('beforeend', data.html || '');
                }
                window.currentReviewPage = page;

                const moreBtn = document.getElementById('reviews-more-btn');
                const collapseBtn = document.getElementById('reviews-collapse-btn');
                if (moreBtn) moreBtn.classList.toggle('hidden', !data.has_next);
                if (collapseBtn) collapseBtn.classList.toggle('hidden', page <= 1);

                // Update counts
                if (typeof data.review_count === 'number') {
                    const countText = document.getElementById('review-count-text');
                    if (countText) countText.textContent = `${data.review_count} bài đánh giá`;
                    const countInline = document.getElementById('review-count-inline');
                    if (countInline) countInline.textContent = `(${data.review_count} đánh giá)`;
                }

                if (window.lucide) window.lucide.createIcons();
            })
            .catch(err => console.error('fetchReviews error:', err));
    };

    /* ===== AJAX FETCH: Comments ===== */
    window.currentCommentPage = 0;

    window.fetchComments = function (page, append) {
        const slug = document.getElementById('product-meta')?.dataset.slug;
        const container = document.getElementById('comments-list-container');
        if (!slug || !container) return;

        const sort = document.getElementById('comment-sort');
        const params = new URLSearchParams();
        params.set('page', page);
        if (sort) params.set('sort', sort.value);

        fetch(`/product/${slug}/comments-ajax/?${params}`)
            .then(r => r.json())
            .then(data => {
                if (append && page > 1) {
                    container.insertAdjacentHTML('beforeend', data.html || '');
                } else {
                    container.innerHTML = data.html || '';
                }
                window.currentCommentPage = page;

                const moreBtn = document.getElementById('comments-more-btn');
                const collapseBtn = document.getElementById('comments-collapse-btn');
                if (moreBtn) moreBtn.classList.toggle('hidden', !data.has_next);
                if (collapseBtn) collapseBtn.classList.toggle('hidden', page <= 1);

                if (typeof data.total_count === 'number') {
                    updateCommentCount(data.total_count);
                }

                if (window.lucide) window.lucide.createIcons();
                bindCommentEvents();
            })
            .catch(err => console.error('fetchComments error:', err));
    };
})();
