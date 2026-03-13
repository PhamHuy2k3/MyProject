/**
 * Voice Search Implementation for TeaZen
 * Uses Web Speech API to provide voice-to-text search functionality.
 */

document.addEventListener('DOMContentLoaded', () => {
    const voiceSearchBtn = document.getElementById('voice-search-btn');
    const searchInput = document.getElementById('search-input');
    const searchForm = searchInput ? searchInput.closest('form') : null;
    const voiceIndicator = document.getElementById('voice-indicator');

    if (!voiceSearchBtn || !searchInput || !searchForm) return;

    // Check for browser support
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
        voiceSearchBtn.style.display = 'none';
        console.warn('Speech Recognition API not supported in this browser.');
        return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'vi-VN'; // Set language to Vietnamese
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    let isListening = false;

    const startListening = () => {
        try {
            recognition.start();
            isListening = true;
            voiceSearchBtn.classList.add('text-emerald-600', 'bg-emerald-50', 'ring-2', 'ring-emerald-500');
            voiceIndicator.classList.remove('hidden');
            searchInput.placeholder = 'Đang lắng nghe...';
        } catch (e) {
            console.error('Speech recognition error:', e);
        }
    };

    const stopListening = () => {
        recognition.stop();
        isListening = false;
        voiceSearchBtn.classList.remove('text-emerald-600', 'bg-emerald-50', 'ring-2', 'ring-emerald-500');
        voiceIndicator.classList.add('hidden');
        searchInput.placeholder = 'Tìm kiếm trà, ấm chén...';
    };

    voiceSearchBtn.addEventListener('click', (e) => {
        e.preventDefault();
        if (isListening) {
            stopListening();
        } else {
            startListening();
        }
    });

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        searchInput.value = transcript;
        
        // Visual feedback
        voiceSearchBtn.innerHTML = '<i data-lucide="check" class="w-4 h-4 text-emerald-600"></i>';
        if (typeof lucide !== 'undefined') lucide.createIcons();

        // Submit form after a short delay
        setTimeout(() => {
            searchForm.submit();
        }, 800);
    };

    recognition.onspeechend = () => {
        stopListening();
    };

    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        stopListening();
        
        // Visual feedback for error
        voiceSearchBtn.innerHTML = '<i data-lucide="mic-off" class="w-4 h-4 text-red-500"></i>';
        if (typeof lucide !== 'undefined') lucide.createIcons();
        
        setTimeout(() => {
            voiceSearchBtn.innerHTML = '<i data-lucide="mic" class="w-4 h-4"></i>';
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }, 2000);
    };

    recognition.onend = () => {
        isListening = false;
    };
});
