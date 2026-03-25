/**
 * TEAZEN - MAIN JAVASCRIPT
 * Tệp này chứa toàn bộ logic tương tác của website, được tập trung tại đây để dễ quản lý.
 */

// =============================================================================
// 0. INTRO OVERLAY - Ẩn màn hình chờ + Hiệu ứng lá trà rơi
// =============================================================================
(function() {
    const overlay = document.getElementById('intro-overlay');
    if (!overlay) return;

    // --- Tạo lá trà rơi ---
    var LEAF_COUNT = 25;
    var leafSVGs = [
        // Lá trà nhỏ gọn
        '<svg viewBox="0 0 40 50" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M20 2 C8 10, 2 25, 8 40 C12 48, 18 50, 20 50 C22 50, 28 48, 32 40 C38 25, 32 10, 20 2Z" fill="currentColor" opacity="0.7"/><path d="M20 8 L20 45" stroke="currentColor" stroke-width="0.8" opacity="0.4"/><path d="M20 18 L12 25" stroke="currentColor" stroke-width="0.5" opacity="0.3"/><path d="M20 25 L28 32" stroke="currentColor" stroke-width="0.5" opacity="0.3"/></svg>',
        // Lá trà tròn hơn
        '<svg viewBox="0 0 36 48" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M18 2 C6 12, 1 24, 6 38 C10 46, 16 48, 18 48 C20 48, 26 46, 30 38 C35 24, 30 12, 18 2Z" fill="currentColor" opacity="0.6"/><path d="M18 6 L18 42" stroke="currentColor" stroke-width="0.6" opacity="0.35"/></svg>',
        // Lá nhỏ
        '<svg viewBox="0 0 28 38" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M14 1 C5 8, 1 18, 5 30 C8 36, 12 38, 14 38 C16 38, 20 36, 23 30 C27 18, 23 8, 14 1Z" fill="currentColor" opacity="0.5"/></svg>'
    ];

    var leafColors = [
        '#86efac', '#6ee7b7', '#a7f3d0', '#bbf7d0',
        '#d1fae5', '#4ade80', '#34d399', '#ecfdf5'
    ];

    for (var i = 0; i < LEAF_COUNT; i++) {
        var leaf = document.createElement('div');
        leaf.className = 'falling-leaf';

        var size = 16 + Math.random() * 28;  // 16px - 44px
        var left = Math.random() * 100;       // vị trí ngang ngẫu nhiên
        var delay = Math.random() * 2;        // delay 0-2s
        var duration = 3 + Math.random() * 4; // thời gian rơi 3-7s
        var swayX = -30 + Math.random() * 60; // lắc ngang -30px đến 30px
        var rotateEnd = 180 + Math.random() * 360;
        var color = leafColors[Math.floor(Math.random() * leafColors.length)];
        var svgHtml = leafSVGs[Math.floor(Math.random() * leafSVGs.length)];

        leaf.innerHTML = svgHtml;
        leaf.style.cssText = [
            'position:absolute',
            'width:' + size + 'px',
            'height:' + size + 'px',
            'left:' + left + '%',
            'top:-60px',
            'color:' + color,
            'opacity:0',
            'pointer-events:none',
            'animation:leaf-fall ' + duration + 's ease-in ' + delay + 's forwards',
            '--sway-x:' + swayX + 'px',
            '--rotate-end:' + rotateEnd + 'deg',
            'filter:blur(' + (Math.random() < 0.3 ? '1px' : '0') + ')'
        ].join(';');

        overlay.appendChild(leaf);
    }

    // --- Ẩn intro overlay sau 3.5 giây (cho đủ thời gian xem lá rơi) ---
    window.addEventListener('load', function() {
        setTimeout(function() {
            overlay.classList.add('fade-out');
            setTimeout(function() {
                overlay.style.display = 'none';
            }, 1000);
        }, 3500);
    });
})();

// =============================================================================
// 0A. SCROLL ANIMATIONS - IntersectionObserver cho hiệu ứng cuộn
// =============================================================================
(function() {
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('in-view');
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

    // Quan sát tất cả các phần tử có hiệu ứng scroll
    document.addEventListener('DOMContentLoaded', function() {
        const selectors = [
            '.fade-up', '.reveal-text-container', '.scroll-section',
            '.tree-node', '.film-strip', '.branch-content'
        ];
        document.querySelectorAll(selectors.join(',')).forEach(function(el) {
            observer.observe(el);
        });
    });
})();

// =============================================================================
// 0B. SPA NAVIGATION - Chuyển trang nội bộ
// =============================================================================
window.navigateTo = function(pageId) {
    document.querySelectorAll('[id^="page-"]').forEach(function(page) {
        page.classList.remove('page-visible');
        page.classList.add('page-hidden');
    });
    var target = document.getElementById('page-' + pageId);
    if (target) {
        target.classList.remove('page-hidden');
        target.classList.add('page-visible');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
};

// =============================================================================
// 0C. PARALLAX SLIDER - Hệ thống slider sản phẩm
// =============================================================================
var currentSlideIndex = 0;
var totalSlides = 0;

(function() {
    var slides = document.querySelectorAll('.slide-card');
    totalSlides = slides.length;
})();

window.goToSlide = function(index) {
    var slides = document.querySelectorAll('.slide-card');
    if (slides.length === 0) return;

    currentSlideIndex = ((index % slides.length) + slides.length) % slides.length;

    slides.forEach(function(slide, i) {
        slide.classList.remove('active', 'next', 'prev', 'hidden-slide');
        if (i === currentSlideIndex) {
            slide.classList.add('active');
        } else if (i === (currentSlideIndex + 1) % slides.length) {
            slide.classList.add('next');
        } else if (i === (currentSlideIndex - 1 + slides.length) % slides.length) {
            slide.classList.add('prev');
        } else {
            slide.classList.add('hidden-slide');
        }
    });
};

window.moveSlider = function(direction) {
    var slides = document.querySelectorAll('.slide-card');
    if (slides.length === 0) return;

    if (direction === 'next') {
        goToSlide(currentSlideIndex + 1);
    } else {
        goToSlide(currentSlideIndex - 1);
    }
};

// =============================================================================
// 0D. SCROLL SECTION - Cuộn ngang các section sản phẩm
// =============================================================================
window.scrollSection = function(containerId, direction) {
    var container = document.getElementById(containerId);
    if (!container) return;
    var scrollAmount = 340;
    if (direction === 'left') {
        container.scrollBy({ left: -scrollAmount, behavior: 'smooth' });
    } else {
        container.scrollBy({ left: scrollAmount, behavior: 'smooth' });
    }
};

// =============================================================================
// 0E. HORIZONTAL SCROLL - The Ritual section
// =============================================================================
(function() {
    var section = document.querySelector('.h-scroll-section');
    var container = document.getElementById('ritual-container');
    if (!section || !container) return;

    window.addEventListener('scroll', function() {
        var rect = section.getBoundingClientRect();
        var sectionHeight = section.offsetHeight;
        var viewportHeight = window.innerHeight;

        if (rect.top < viewportHeight && rect.bottom > 0) {
            var scrollProgress = -rect.top / (sectionHeight - viewportHeight);
            scrollProgress = Math.max(0, Math.min(1, scrollProgress));
            var maxScroll = container.scrollWidth - window.innerWidth;
            container.style.transform = 'translateX(' + (-scrollProgress * maxScroll) + 'px)';
        }
    });
})();

// =============================================================================
// I. HIỆU ỨNG 3D (THREE.JS) - VẬT THỂ SỐ ZEN
// =============================================================================
(function() {
    const container = document.getElementById('artifact-container');
    const canvas = document.getElementById('webgl-canvas');
    if (!container || !canvas || !window.THREE) return;
    
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, container.offsetWidth / container.offsetHeight, 0.1, 100);
    camera.position.z = 25;

    const renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
    renderer.setSize(container.offsetWidth, container.offsetHeight);
    renderer.setPixelRatio(window.devicePixelRatio);

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);

    const pointLight = new THREE.PointLight(0x10b981, 2); 
    pointLight.position.set(10, 10, 10);
    scene.add(pointLight);

    const geometry = new THREE.IcosahedronGeometry(6, 4); 
    const material = new THREE.MeshPhysicalMaterial({
        color: 0x059669,
        roughness: 0.1,
        metalness: 0.1,
        transmission: 0.2,
        wireframe: true,
        emissive: 0x064e3b,
        emissiveIntensity: 0.2
    });

    const sphere = new THREE.Mesh(geometry, material);
    scene.add(sphere);

    const originalPositions = geometry.attributes.position.array.slice();
    const count = geometry.attributes.position.count;

    let mouseX = 0, mouseY = 0;
    container.addEventListener('mousemove', (e) => {
        const rect = container.getBoundingClientRect();
        mouseX = (e.clientX - rect.left - rect.width / 2) * 0.005;
        mouseY = (e.clientY - rect.top - rect.height / 2) * 0.005;
    });

    const clock = new THREE.Clock();
    function animate() {
        const time = clock.getElapsedTime();
        sphere.rotation.y += 0.005;
        sphere.rotation.x += (mouseY - sphere.rotation.x) * 0.05;
        sphere.rotation.y += (mouseX - sphere.rotation.y) * 0.05;

        const positions = geometry.attributes.position.array;
        for (let i = 0; i < count; i++) {
            const ix = i * 3, iy = i * 3 + 1, iz = i * 3 + 2;
            const ox = originalPositions[ix], oy = originalPositions[iy], oz = originalPositions[iz];
            const distortion = Math.sin(ox * 0.5 + time) * Math.cos(oy * 0.5 + time) * Math.sin(oz * 0.5 + time);
            const scale = 1 + distortion * 0.2;
            positions[ix] = ox * scale;
            positions[iy] = oy * scale;
            positions[iz] = oz * scale;
        }
        geometry.attributes.position.needsUpdate = true;
        renderer.render(scene, camera);
        requestAnimationFrame(animate);
    }
    animate();

    window.addEventListener('resize', () => {
        camera.aspect = container.offsetWidth / container.offsetHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.offsetWidth, container.offsetHeight);
    });
})();

// =============================================================================
// II. HỆ THỐNG TÌM KIẾM GỢI Ý (SEARCH SUGGESTIONS)
// =============================================================================
(function() {
    const searchInput = document.getElementById('search-input');
    const suggestionsBox = document.getElementById('search-suggestions');
    const suggestionsList = document.getElementById('suggestions-list');
    const resultsCountBadge = document.getElementById('results-count');
    const viewAllResults = document.getElementById('view-all-results');
    let searchTimeout = null;

    if (!searchInput || !suggestionsBox) return;

    // Hiển thị khung gợi ý với hiệu ứng animation
    const showSuggestions = () => {
        suggestionsBox.classList.remove('hidden');
        setTimeout(() => {
            suggestionsBox.style.opacity = '1';
            suggestionsBox.style.transform = 'translateY(0) scale(1)';
        }, 10);
    };

    // Ẩn khung gợi ý
    const hideSuggestions = () => {
        suggestionsBox.style.opacity = '0';
        suggestionsBox.style.transform = 'translateY(-10px) scale(0.95)';
        setTimeout(() => suggestionsBox.classList.add('hidden'), 300);
    };

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        clearTimeout(searchTimeout);

        if (query.length < 1) {
            hideSuggestions();
            return;
        }

        // Debounce: Chờ người dùng dừng gõ 150ms mới gửi yêu cầu AJAX
        searchTimeout = setTimeout(() => {
            fetch(`/api/search-suggestions/?q=${encodeURIComponent(query)}`)
                .then(r => r.json())
                .then(data => {
                    if (data.results && data.results.length > 0) {
                        if (resultsCountBadge) resultsCountBadge.textContent = `${data.results.length} kết quả`;

                        // Render danh sách sản phẩm gợi ý
                        suggestionsList.innerHTML = data.results.map(p => `
                            <a href="${p.url}" class="group flex flex-col bg-stone-50/50 rounded-xl overflow-hidden border border-transparent hover:border-emerald-200 hover:bg-white hover:shadow-lg transition-all duration-300">
                                <div class="aspect-[4/3] overflow-hidden relative">
                                    ${p.image_url 
                                        ? `<img src="${p.image_url}" class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500">`
                                        : `<div class="w-full h-full flex items-center justify-center bg-stone-100 text-stone-400 font-bold text-xs">TEA</div>`
                                    }
                                    <div class="absolute top-2 right-2 bg-white/90 backdrop-blur px-2 py-1 rounded-lg shadow-sm">
                                        <span class="text-[10px] font-bold text-emerald-700">${new Intl.NumberFormat('vi-VN').format(p.price)}đ</span>
                                    </div>
                                </div>
                                <div class="p-3">
                                    <div class="text-[9px] font-bold text-stone-400 uppercase tracking-widest mb-1">${p.category}</div>
                                    <div class="text-xs font-bold text-stone-800 line-clamp-1 group-hover:text-emerald-700 transition-colors">${p.title}</div>
                                </div>
                            </a>
                        `).join('');

                        showSuggestions();
                        
                        // Cập nhật link "Xem tất cả"
                        if (viewAllResults) {
                            const baseUrl = searchInput.dataset.searchUrl || '/shop/';
                            viewAllResults.href = `${baseUrl}?q=${encodeURIComponent(query)}`;
                        }
                        if (window.lucide) window.lucide.createIcons();
                    } else {
                        hideSuggestions();
                    }
                });
        }, 150);
    });

    // Đóng khi click ra ngoài
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !suggestionsBox.contains(e.target)) hideSuggestions();
    });
})();

// =============================================================================
// III. HỆ THỐNG THẺ THÔNG TIN (PRODUCT TOOLTIP)
// =============================================================================
(function() {
    const tooltip = document.getElementById('product-tooltip');
    if (!tooltip) return;

    const tImg = document.getElementById('tooltip-img');
    const tTitle = document.getElementById('tooltip-title');
    const tPrice = document.getElementById('tooltip-price');
    const tExcerpt = document.getElementById('tooltip-excerpt');
    const OFFSET = 15; // Khoảng cách từ con trỏ chuột đến tooltip

    // Khi di chuột vào sản phẩm
    function onEnter(e) {
        const el = e.currentTarget;
        const title = el.dataset.title || '';
        const image = el.dataset.image || '';
        if (!title) return;

        tTitle.textContent = title;
        tPrice.textContent = el.dataset.price || '';
        tExcerpt.textContent = el.dataset.excerpt || '';
        tImg.src = image;
        tImg.style.display = image ? '' : 'none';
        tooltip.style.opacity = '1';
    }

    // Khi di chuyển chuột bên trong sản phẩm (tooltip đi theo chuột)
    function onMove(e) {
        if (tooltip.style.opacity === '0') return;
        const rect = tooltip.getBoundingClientRect();
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        
        let x = e.clientX + OFFSET;
        let y = e.clientY + OFFSET;

        // Xử lý tràn màn hình
        if (x + rect.width > vw) x = e.clientX - rect.width - OFFSET;
        if (y + rect.height > vh) y = e.clientY - rect.height - OFFSET;
        
        tooltip.style.left = Math.max(4, x) + 'px';
        tooltip.style.top = Math.max(4, y) + 'px';
    }

    // Khi rời khỏi sản phẩm
    function onLeave() {
        tooltip.style.opacity = '0';
    }

    // Gán sự kiện cho các sản phẩm (hỗ trợ cả sản phẩm tải thêm bằng AJAX)
    function bindTooltips() {
        document.querySelectorAll('.product-hover-trigger').forEach(el => {
            if (el.dataset.tooltipBound) return;
            el.dataset.tooltipBound = '1';
            el.addEventListener('mouseenter', onEnter);
            el.addEventListener('mousemove', onMove);
            el.addEventListener('mouseleave', onLeave);
        });
    }

    document.addEventListener('DOMContentLoaded', bindTooltips);
    const observer = new MutationObserver(bindTooltips);
    observer.observe(document.body, { childList: true, subtree: true });
})();

// =============================================================================
// IV. HỆ THỐNG CHI TIẾT SẢN PHẨM (ZOOM, TABS, AJAX)
// =============================================================================

/**
 * Đổi ảnh chính khi click vào ảnh thu nhỏ
 */
window.switchImage = function(url) {
    const img = document.getElementById('main-product-img');
    if (!img) return;
    img.src = url;
    
    // Cập nhật trạng thái active cho ảnh thu nhỏ
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

/**
 * Hiệu ứng phóng to ảnh (Zoom)
 */
window.handleZoom = function(e) {
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

    // Giới hạn trong khung ảnh
    x = Math.max(lw, Math.min(x, rect.width - lw));
    y = Math.max(lh, Math.min(y, rect.height - lh));

    lens.style.left = (x - lw) + 'px';
    lens.style.top = (y - lh) + 'px';
    lens.classList.remove('hidden');

    // Cấu hình độ phóng to
    const zoomFactor = 2.5;
    preview.style.backgroundImage = `url(${img.src})`;
    preview.style.backgroundSize = `${rect.width * zoomFactor}px ${rect.height * zoomFactor}px`;
    preview.style.backgroundPosition = `-${(x - lw) * zoomFactor - preview.offsetWidth / 2 + lw * zoomFactor}px -${(y - lh) * zoomFactor - preview.offsetHeight / 2 + lh * zoomFactor}px`;
    preview.classList.remove('hidden');
};

window.hideZoom = function() {
    const lens = document.getElementById('zoom-lens');
    const preview = document.getElementById('zoom-preview');
    if (lens) lens.classList.add('hidden');
    if (preview) preview.classList.add('hidden');
};

/**
 * Chuyển đổi Tab (Mô tả, Đánh giá...)
 */
window.switchTab = function(tabId) {
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

/**
 * Thay đổi số lượng mua hàng
 */
window.changeQty = function(delta) {
    const input = document.getElementById('qty-input');
    if (!input) return;
    let val = parseInt(input.value) || 1;
    val = Math.max(1, Math.min(val + delta, parseInt(input.max) || 999));
    input.value = val;
};

// =============================================================================
// V. HỆ THỐNG ĐÁNH GIÁ (REVIEWS AJAX)
// =============================================================================
let currentReviewPage = 1;
let hasNextReviewPage = false;

window.fetchReviews = function(page = 1) {
    const productMeta = document.getElementById('product-meta');
    if (!productMeta) return;
    const slug = productMeta.dataset.slug;
    const sort = document.getElementById('review-sort')?.value || 'newest';
    const query = document.getElementById('review-search')?.value || '';
    const container = document.getElementById('reviews-list-container');
    
    if (!container) return;
    container.innerHTML = '<div class="flex justify-center py-12"><i data-lucide="loader-2" class="w-8 h-8 text-emerald-600 animate-spin"></i></div>';
    if (window.lucide) window.lucide.createIcons();
    
    fetch(`/product/${slug}/reviews-ajax/?page=${page}&sort=${sort}&q=${encodeURIComponent(query)}`)
        .then(r => r.json())
        .then(data => {
            container.innerHTML = data.html;
            if (window.lucide) window.lucide.createIcons();
            currentReviewPage = page;
            hasNextReviewPage = !!data.has_next;
            updateReviewNav();
        });
};

function updateReviewNav() {
    const moreBtn = document.getElementById('reviews-more-btn');
    const collapseBtn = document.getElementById('reviews-collapse-btn');
    if (moreBtn) moreBtn.classList.toggle('hidden', !hasNextReviewPage);
    if (collapseBtn) collapseBtn.classList.toggle('hidden', currentReviewPage <= 1);
}

// =============================================================================
// VI. HỆ THỐNG BÌNH LUẬN (COMMENTS AJAX)
// =============================================================================
let currentCommentPage = 1;
let hasNextCommentPage = false;

window.fetchComments = function(page = 1, append = false) {
    const productMeta = document.getElementById('product-meta');
    if (!productMeta) return;
    const slug = productMeta.dataset.slug;
    const sort = document.getElementById('comment-sort')?.value || 'newest';
    const container = document.getElementById('comments-list-container');
    
    if (!container) return;
    
    return fetch(`/product/${slug}/comments-ajax/?page=${page}&sort=${sort}`)
        .then(r => r.json())
        .then(data => {
            if (append) container.insertAdjacentHTML('beforeend', data.html);
            else container.innerHTML = data.html;
            
            currentCommentPage = page;
            hasNextCommentPage = data.has_next;
            if (window.lucide) window.lucide.createIcons();
            updateCommentsLoadControl();
        });
};

/**
 * Hiển thị thông báo Toast nhỏ cho bình luận
 */
window.showCommentToast = function(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `fixed top-24 right-4 z-[120] px-4 py-3 rounded-xl shadow-xl border text-sm font-semibold transition-all duration-300 translate-y-2 opacity-0 ${type === 'success' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' : 'bg-red-50 text-red-700 border-red-200'}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    requestAnimationFrame(() => toast.classList.remove('translate-y-2', 'opacity-0'));
    setTimeout(() => {
        toast.classList.add('translate-y-2', 'opacity-0');
        setTimeout(() => toast.remove(), 300);
    }, 2500);
};

// =============================================================================
// VII. TIỆN ÍCH CHUNG
// =============================================================================

// Hiệu ứng Spotlight cho Scrapbook
(function() {
    const scrapbook = document.getElementById('scrapbook-container');
    if (!scrapbook) return;
    const items = scrapbook.querySelectorAll('.scrapbook-item');
    items.forEach(item => {
        item.addEventListener('mouseenter', () => {
            items.forEach(other => {
                if (other !== item) other.classList.add('blur-[2px]', 'opacity-40');
                else item.classList.add('scale-105', 'z-10');
            });
        });
        item.addEventListener('mouseleave', () => {
            items.forEach(other => other.classList.remove('blur-[2px]', 'opacity-40', 'scale-105', 'z-10'));
        });
    });
})();

// Custom Cursor
(function() {
    const cursor = document.getElementById('custom-cursor');
    if (!cursor) return;
    document.addEventListener('mousemove', (e) => {
        cursor.style.left = e.clientX + 'px';
        cursor.style.top = e.clientY + 'px';
    });
    document.addEventListener('mouseover', (e) => {
        if (e.target.closest('.hover-trigger') || e.target.closest('button') || e.target.closest('a')) {
            cursor.classList.add('hovered');
        } else {
            cursor.classList.remove('hovered');
        }
    });
})();

// Khởi tạo icons Lucide
document.addEventListener('DOMContentLoaded', () => {
    if (window.lucide) lucide.createIcons();
});
