// --- THREE.JS: THE DIGITAL ZEN ARTIFACT ---
(function() {
    const container = document.getElementById('artifact-container');
    const canvas = document.getElementById('webgl-canvas');
    if (!container || !canvas || !window.THREE) return;
    const scene = new THREE.Scene();

    // Camera
    const camera = new THREE.PerspectiveCamera(45, container.offsetWidth / container.offsetHeight, 0.1, 100);
    camera.position.z = 25;

    // Renderer
    const renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
    renderer.setSize(container.offsetWidth, container.offsetHeight);
    renderer.setPixelRatio(window.devicePixelRatio);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);

    const pointLight = new THREE.PointLight(0x10b981, 2); // Emerald light
    pointLight.position.set(10, 10, 10);
    scene.add(pointLight);

    const pointLight2 = new THREE.PointLight(0x34d399, 1); // Teal light
    pointLight2.position.set(-10, -10, 10);
    scene.add(pointLight2);

    // The Artifact (Icosahedron -> Sphere Morph)
    const geometry = new THREE.IcosahedronGeometry(6, 4); // High detail sphere

    // Using MeshPhysicalMaterial for glass-like water effect
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

    // Original positions for morphing
    const originalPositions = geometry.attributes.position.array.slice();
    const count = geometry.attributes.position.count;

    // Mouse Interaction
    let mouseX = 0;
    let mouseY = 0;

    container.addEventListener('mousemove', (e) => {
        const rect = container.getBoundingClientRect();
        mouseX = (e.clientX - rect.left - rect.width / 2) * 0.005;
        mouseY = (e.clientY - rect.top - rect.height / 2) * 0.005;
    });

    // Particles
    const particlesGeometry = new THREE.BufferGeometry();
    const particlesCount = 300;
    const posArray = new Float32Array(particlesCount * 3);
    for (let i = 0; i < particlesCount * 3; i++) {
        posArray[i] = (Math.random() - 0.5) * 50;
    }
    particlesGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
    const particlesMaterial = new THREE.PointsMaterial({
        size: 0.1,
        color: 0x6ee7b7,
        transparent: true,
        opacity: 0.8
    });
    const particlesMesh = new THREE.Points(particlesGeometry, particlesMaterial);
    scene.add(particlesMesh);

    // Animation Loop
    const clock = new THREE.Clock();

    function animate() {
        const time = clock.getElapsedTime();

        // Rotate based on mouse
        sphere.rotation.y += 0.005;
        sphere.rotation.x += (mouseY - sphere.rotation.x) * 0.05;
        sphere.rotation.y += (mouseX - sphere.rotation.y) * 0.05;

        // Morphing Logic (Simplex Noise approximation using Sine waves)
        const positions = geometry.attributes.position.array;

        for (let i = 0; i < count; i++) {
            const ix = i * 3;
            const iy = i * 3 + 1;
            const iz = i * 3 + 2;

            const ox = originalPositions[ix];
            const oy = originalPositions[iy];
            const oz = originalPositions[iz];

            const distortion = Math.sin(ox * 0.5 + time) * Math.cos(oy * 0.5 + time) * Math.sin(oz * 0.5 + time);
            const scale = 1 + distortion * 0.2;

            positions[ix] = ox * scale;
            positions[iy] = oy * scale;
            positions[iz] = oz * scale;
        }
        geometry.attributes.position.needsUpdate = true;

        particlesMesh.rotation.y = -time * 0.1;
        particlesMesh.rotation.x = time * 0.05;

        renderer.render(scene, camera);
        requestAnimationFrame(animate);
    }

    animate();

    // Resize Handler
    window.addEventListener('resize', () => {
        camera.aspect = container.offsetWidth / container.offsetHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.offsetWidth, container.offsetHeight);
    });
})();

// --- ANIMATION OBSERVER ---
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('in-view');
        }
    });
}, { threshold: 0.1 });

function observeElements() {
    document.querySelectorAll('.reveal-text-container, .fade-up, .reveal-img-scale, .tree-node').forEach(el => observer.observe(el));
}

// --- NEW: HORIZONTAL SCROLL LOGIC ---
const hScrollSection = document.querySelector('.h-scroll-section');
const hScrollContainer = document.querySelector('.h-scroll-container');

window.addEventListener('scroll', () => {
    if (!hScrollSection || !hScrollContainer) return;
    const rect = hScrollSection.getBoundingClientRect();
    const offsetTop = rect.top;
    const sectionHeight = hScrollSection.offsetHeight;
    const windowHeight = window.innerHeight;

    let percentage = 0;
    if (offsetTop <= 0) {
        percentage = Math.abs(offsetTop) / (sectionHeight - windowHeight);
    }
    percentage = Math.min(Math.max(percentage, 0), 1);

    const x = -(hScrollContainer.scrollWidth - window.innerWidth) * percentage;
    hScrollContainer.style.transform = `translateX(${x}px)`;
});

// --- TREE LEAVES ---
function createTreeLeaves() {
    const container = document.getElementById('tree-leaves');
    if (!container) return;
    const leafSVG = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23064e3b' opacity='0.3' stroke='none'%3E%3Cpath d='M2 22s5-3 5-9c0-4.5-2.5-9-7-11 8 1 14 6 14 11 0 3.5-1.5 6-3.5 8'/%3E%3C/svg%3E";

    for (let i = 0; i < 10; i++) {
        const leaf = document.createElement('div');
        leaf.classList.add('falling-leaf');
        leaf.style.backgroundImage = `url("${leafSVG}")`;
        leaf.style.width = Math.random() * 15 + 10 + 'px';
        leaf.style.height = leaf.style.width;
        leaf.style.left = Math.random() * 100 + '%';
        leaf.style.animation = `leaf-fall ${Math.random() * 5 + 5}s linear infinite`;
        leaf.style.animationDelay = Math.random() * 5 + 's';
        container.appendChild(leaf);
    }
}
createTreeLeaves();

// --- NAVIGATION LOGIC ---
function navigateTo(pageId) {
    const home = document.getElementById('page-home');
    const story = document.getElementById('page-story');
    const target = document.getElementById(`page-${pageId}`);
    if (home && story) {
        home.classList.add('page-hidden');
        home.classList.remove('page-visible');
        story.classList.add('page-hidden');
        story.classList.remove('page-visible');
    }
    if (target) {
        target.classList.remove('page-hidden');
        target.classList.add('page-visible');
        window.scrollTo(0, 0);
    }
}

// --- INTRO ---
function createIntroLeaves() {
    const overlay = document.getElementById('intro-overlay');
    if (!overlay) return;
    const leafSVG = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%2310b981' stroke='%23065f46' stroke-width='1' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M2 22s5-3 5-9c0-4.5-2.5-9-7-11 8 1 14 6 14 11 0 3.5-1.5 6-3.5 8'/%3E%3Cpath d='M2 22c5-3 5-9'/%3E%3C/svg%3E";
    for (let i = 0; i < 15; i++) {
        const leaf = document.createElement('div');
        leaf.classList.add('falling-leaf');
        leaf.style.backgroundImage = `url("${leafSVG}")`;
        leaf.style.width = Math.random() * 20 + 20 + 'px';
        leaf.style.height = leaf.style.width;
        leaf.style.left = Math.random() * 100 + 'vw';
        leaf.style.animation = `leaf-fall ${Math.random() * 2 + 2}s linear forwards`;
        leaf.style.animationDelay = Math.random() * 1 + 's';
        overlay.appendChild(leaf);
    }
    setTimeout(() => {
        overlay.classList.add('fade-out');
        setTimeout(() => { overlay.style.display = 'none'; observeElements(); }, 1000);
    }, 3500);
}
window.addEventListener('load', createIntroLeaves);

// --- CURSOR ---
const cursor = document.getElementById('custom-cursor');
document.addEventListener('mousemove', (e) => {
    if (!cursor) return;
    cursor.style.left = e.clientX + 'px';
    cursor.style.top = e.clientY + 'px';
});
const addHoverListeners = () => {
    if (!cursor) return;
    document.querySelectorAll('.hover-trigger, .group').forEach(trigger => {
        trigger.addEventListener('mouseenter', () => cursor.classList.add('hovered'));
        trigger.addEventListener('mouseleave', () => cursor.classList.remove('hovered'));
    });
};

// --- SLIDER (Works with Django-rendered slides) ---
const sliderContainer = document.getElementById('parallax-slider-container');
const parallaxSection = document.getElementById('slider-section');
let currentIndex = 0;
let autoPlayTimer;

function updateSliderClasses() {
    if (!sliderContainer) return;
    const slides = sliderContainer.querySelectorAll('.slide-card');
    const len = slides.length;
    if (len === 0) return;
    
    const prevIndex = (currentIndex - 1 + len) % len;
    const nextIndex = (currentIndex + 1) % len;
    
    slides.forEach((slide, index) => {
        slide.classList.remove('active', 'prev', 'next', 'hidden-slide');
        if (index === currentIndex) slide.classList.add('active');
        else if (index === nextIndex) slide.classList.add('next');
        else if (index === prevIndex) slide.classList.add('prev');
        else slide.classList.add('hidden-slide');
    });
}

function moveSlider(dir) {
    if (!sliderContainer) return;
    const slides = sliderContainer.querySelectorAll('.slide-card');
    const len = slides.length;
    if (len === 0) return;
    currentIndex = dir === 'next' ? (currentIndex + 1) % len : (currentIndex - 1 + len) % len;
    updateSliderClasses();
}

function goToSlide(idx) { currentIndex = idx; updateSliderClasses(); }
function startAutoPlay() { stopAutoPlay(); autoPlayTimer = setInterval(() => moveSlider('next'), 4000); }
function stopAutoPlay() { clearInterval(autoPlayTimer); }

if (parallaxSection) {
    parallaxSection.addEventListener('mouseenter', stopAutoPlay);
    parallaxSection.addEventListener('mouseleave', startAutoPlay);
}
updateSliderClasses();
startAutoPlay();

// --- SCRAPBOOK (Works with Django-rendered items, adds spotlight effect) ---
const scrapbookContainer = document.getElementById('scrapbook-container');
const chaoticSection = document.getElementById('chaotic-section');
const chaoticTitle = document.getElementById('chaotic-title');
const chaoticSubtitle = document.getElementById('chaotic-subtitle');

function setupScrapbookEffects() {
    if (!scrapbookContainer) return;
    const items = scrapbookContainer.querySelectorAll('.scrapbook-item');
    if (items.length === 0) return;
    
    items.forEach(item => {
        item.addEventListener('mouseenter', () => {
            if (!chaoticSection || !chaoticTitle || !chaoticSubtitle) return;
            chaoticSection.classList.remove('bg-transparent');
            chaoticSection.classList.add('bg-[#0f291e]');
            chaoticTitle.classList.replace('text-emerald-950', 'text-emerald-50');
            chaoticSubtitle.classList.replace('text-stone-500', 'text-emerald-300');
            items.forEach(otherItem => {
                if (otherItem === item) {
                    otherItem.classList.add('z-50', 'scale-110', '-translate-y-4', '!rotate-0');
                    otherItem.style.boxShadow = '0 0 60px rgba(163, 230, 53, 0.6)';
                } else {
                    otherItem.classList.add('blur-[3px]', 'opacity-30', 'grayscale', 'scale-95');
                }
            });
        });
        item.addEventListener('mouseleave', () => {
            if (!chaoticSection || !chaoticTitle || !chaoticSubtitle) return;
            chaoticSection.classList.add('bg-transparent');
            chaoticSection.classList.remove('bg-[#0f291e]');
            chaoticTitle.classList.replace('text-emerald-50', 'text-emerald-950');
            chaoticSubtitle.classList.replace('text-emerald-300', 'text-stone-500');
            items.forEach(otherItem => {
                otherItem.classList.remove('z-50', 'scale-110', '-translate-y-4', '!rotate-0', 'blur-[3px]', 'opacity-30', 'grayscale', 'scale-95');
                otherItem.style.boxShadow = 'none';
            });
        });
    });
}
setupScrapbookEffects();

// --- CABINET (Works with Django-rendered items, adds accordion effect) ---
const cabinetContainer = document.getElementById('cabinet-container');

function setupCabinetEffects() {
    if (!cabinetContainer) return;
    const items = cabinetContainer.querySelectorAll('.cabinet-item');
    if (items.length === 0) return;
    
    items.forEach(item => {
        item.addEventListener('click', () => {
            const isActive = item.classList.contains('cabinet-active');
            items.forEach(i => {
                i.classList.remove('cabinet-active', 'flex-[4]');
                i.classList.add('flex-[1]');
            });
            if (!isActive) {
                item.classList.add('cabinet-active', 'flex-[4]');
                item.classList.remove('flex-[1]');
            }
        });
    });
}
setupCabinetEffects();

// --- PINTEREST (Works with Django-rendered items) ---
const pinterestContainer = document.getElementById('pinterest-scroll');

function scrollPinterest(direction) {
    if (!pinterestContainer) return;
    const amount = direction === 'left' ? -350 : 350;
    pinterestContainer.scrollBy({ left: amount, behavior: 'smooth' });
}

// Init
addHoverListeners();
if (window.lucide) lucide.createIcons();

setTimeout(observeElements, 500);
