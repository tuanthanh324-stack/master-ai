document.addEventListener('DOMContentLoaded', () => {
    async function safeFetch(url, options = {}, retries = 2) {
        for (let i = 0; i <= retries; i++) {
            try {
                const res = await fetch(url, options);
                if (res.ok || res.status < 500) return res;
            } catch (err) {
                if (i === retries) throw err;
                await new Promise(r => setTimeout(r, 800));
            }
        }
        return fetch(url, options);
    }

    // ===== DOM ELEMENTS =====
    const body = document.body;
    const btnThemeToggle = document.getElementById('btnThemeToggle');
    const btnSettings = document.getElementById('btnSettings');
    const settingsModal = document.getElementById('settingsModal');
    const btnCloseModal = document.getElementById('btnCloseModal');

    // Hero Inputs
    const videoUrlInput = document.getElementById('videoUrl');
    const btnClearUrl = document.getElementById('btnClearUrl');
    const btnProcess = document.getElementById('btnProcess');
    const processSpinner = document.getElementById('processSpinner');

    // Progress Elements
    const statusDot = document.getElementById('statusDot');
    const statusMessage = document.getElementById('statusMessage');
    const timerText = document.getElementById('timerText');
    const progressPercent = document.getElementById('progressPercent');
    const progressBarFill = document.getElementById('progressBarFill');

    // Toolbars
    const selLang = document.getElementById('selLang');
    const selModel = document.getElementById('selModel');
    const selMode = document.getElementById('selMode');
    const chkAutoGemini = document.getElementById('chkAutoGemini');
    const chkUseSub = document.getElementById('chkUseSub');

    // Stage 1
    const txtWhisper = document.getElementById('txtWhisper');
    const whisperWordCount = document.getElementById('whisperWordCount');
    const btnCopyWhisper = document.getElementById('btnCopyWhisper');
    const btnDownloadWhisper = document.getElementById('btnDownloadWhisper');
    const btnClearWhisper = document.getElementById('btnClearWhisper');

    // Stage 2
    const txtGemini = document.getElementById('txtGemini');
    const geminiWordCount = document.getElementById('geminiWordCount');
    const customPrompt = document.getElementById('customPrompt');
    const btnRunGemini = document.getElementById('btnRunGemini');
    const btnCopyGemini = document.getElementById('btnCopyGemini');
    const btnDownloadGemini = document.getElementById('btnDownloadGemini');
    const btnClearGemini = document.getElementById('btnClearGemini');

    // Stage 3 (TTS & Speaker Preview)
    const selVoice = document.getElementById('selVoice');
    const btnPreviewSelectedVoice = document.getElementById('btnPreviewSelectedVoice');
    const selBgm = document.getElementById('selBgm');
    const selRate = document.getElementById('selRate');
    const btnRunTTS = document.getElementById('btnRunTTS');
    const ttsSpinner = document.getElementById('ttsSpinner');
    const audioPlayerWrapper = document.getElementById('audioPlayerWrapper');
    const ttsAudioPlayer = document.getElementById('ttsAudioPlayer');
    const btnDownloadAudio = document.getElementById('btnDownloadAudio');

    // Stage 4 (Voice Clone & Miner)
    const btnChooseFile = document.getElementById('btnChooseFile');
    const refAudioFile = document.getElementById('refAudioFile');
    const refVoiceName = document.getElementById('refVoiceName');
    const btnUploadRefVoice = document.getElementById('btnUploadRefVoice');

    const selCategory = document.getElementById('selCategory');
    const btnStartMining = document.getElementById('btnStartMining');
    const minerSpinner = document.getElementById('minerSpinner');
    const minerProgress = document.getElementById('minerProgress');
    const minerStatusText = document.getElementById('minerStatusText');
    const minerPercentText = document.getElementById('minerPercentText');
    const minerProgressFill = document.getElementById('minerProgressFill');
    const refVoiceGallery = document.getElementById('refVoiceGallery');

    // Modal
    const apiKeyInput = document.getElementById('apiKeyInput');
    const btnToggleKeyVis = document.getElementById('btnToggleKeyVis');
    const btnSaveKey = document.getElementById('btnSaveKey');
    const btnDeleteKey = document.getElementById('btnDeleteKey');
    const saveKeyMsg = document.getElementById('saveKeyMsg');

    // State Variables
    let currentAudioUrl = '';
    let selectedRefFile = null;
    let minerPollInterval = null;

    let currentPreviewAudio = null;
    let activePreviewBtn = null;

    // Load initial data
    fetchConfig();
    loadVoiceDropdownAndGallery();

    // Theme Toggle
    const savedTheme = localStorage.getItem('theme') || 'light';
    if (savedTheme === 'dark') {
        body.classList.add('dark-theme');
        btnThemeToggle.textContent = '☀️';
    }
    btnThemeToggle.addEventListener('click', () => {
        body.classList.toggle('dark-theme');
        const isDark = body.classList.contains('dark-theme');
        btnThemeToggle.textContent = isDark ? '☀️' : '🌙';
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    });

    // URL Clear Input
    videoUrlInput.addEventListener('input', () => {
        btnClearUrl.style.display = videoUrlInput.value ? 'block' : 'none';
    });
    btnClearUrl.addEventListener('click', () => {
        videoUrlInput.value = '';
        btnClearUrl.style.display = 'none';
        videoUrlInput.focus();
    });
    videoUrlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') triggerProcess();
    });

    const elevenLabsKeyInput = document.getElementById('elevenLabsKeyInput');
    const btnToggleElKeyVis = document.getElementById('btnToggleElKeyVis');

    async function fetchConfig() {
        try {
            const res = await fetch('/api/config');
            const data = await res.json();
            if (data.api_key) apiKeyInput.value = data.api_key;
            if (data.elevenlabs_api_key && elevenLabsKeyInput) elevenLabsKeyInput.value = data.elevenlabs_api_key;
        } catch (err) {
            console.error('Lỗi nạp config:', err);
        }
    }

    // Modal Control
    btnSettings.addEventListener('click', () => settingsModal.classList.add('active'));
    btnCloseModal.addEventListener('click', () => settingsModal.classList.remove('active'));
    settingsModal.addEventListener('click', (e) => {
        if (e.target === settingsModal) settingsModal.classList.remove('active');
    });

    btnToggleKeyVis.addEventListener('click', () => {
        apiKeyInput.type = apiKeyInput.type === 'password' ? 'text' : 'password';
    });

    if (btnToggleElKeyVis && elevenLabsKeyInput) {
        btnToggleElKeyVis.addEventListener('click', () => {
            elevenLabsKeyInput.type = elevenLabsKeyInput.type === 'password' ? 'text' : 'password';
        });
    }

    btnSaveKey.addEventListener('click', async () => {
        const origText = btnSaveKey.textContent;
        btnSaveKey.disabled = true;
        btnSaveKey.textContent = '⏳ Đang kiểm tra Key...';
        
        const key = apiKeyInput.value.trim();
        const elKey = elevenLabsKeyInput ? elevenLabsKeyInput.value.trim() : '';
        try {
            const res = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: key, elevenlabs_api_key: elKey })
            });
            const data = await res.json();
            showMsg(data.message, data.success ? 'success' : 'error');
        } catch (err) {
            showMsg('Lỗi kết nối lưu API key: ' + err.message, 'error');
        } finally {
            btnSaveKey.disabled = false;
            btnSaveKey.textContent = origText;
        }
    });

    btnDeleteKey.addEventListener('click', async () => {
        apiKeyInput.value = '';
        if (elevenLabsKeyInput) elevenLabsKeyInput.value = '';
        try {
            await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: '', elevenlabs_api_key: '' })
            });
            showMsg('Đã xóa tất cả API Key!', 'success');
        } catch (err) {
            showMsg('Lỗi xóa Key!', 'error');
        }
    });

    function showMsg(text, type) {
        if (!saveKeyMsg) return;
        saveKeyMsg.style.display = 'block';
        saveKeyMsg.textContent = text;
        saveKeyMsg.className = `msg-alert ${type}`;
        setTimeout(() => { saveKeyMsg.style.display = 'none'; }, 6000);
    }

    // Slim Progress & Timer Controller
    let progressTimer = null;
    let clockTimer = null;
    let startTime = 0;

    function resetTimers() {
        if (progressTimer) { clearInterval(progressTimer); progressTimer = null; }
        if (clockTimer) { clearInterval(clockTimer); clockTimer = null; }
    }

    function updateProgress(percent, text, state = 'info') {
        statusMessage.textContent = text;
        progressPercent.textContent = `${percent}%`;
        progressBarFill.style.width = `${percent}%`;

        statusDot.className = 'pulse-dot';
        if (state === 'success') statusDot.classList.add('success');
        if (state === 'error') statusDot.classList.add('error');
    }

    function startLiveTimer(estimatedSeconds = 5) {
        resetTimers();
        startTime = Date.now();
        clockTimer = setInterval(() => {
            const sec = ((Date.now() - startTime) / 1000).toFixed(1);
            timerText.textContent = `⏱️ ${sec}s (Dự kiến ~${estimatedSeconds}s)`;
        }, 100);
    }

    function stopLiveTimer(isSuccess = true) {
        resetTimers();
        const totalSec = ((Date.now() - startTime) / 1000).toFixed(1);
        timerText.textContent = isSuccess ? `⏱️ Đã xong: ${totalSec}s` : `⏱️ Hủy: ${totalSec}s`;
    }

    // Word Counter Helper
    function updateWordCount(textarea, tag) {
        const text = textarea.value.trim();
        const words = text ? text.split(/\s+/).length : 0;
        tag.textContent = `${words} từ`;
    }

    txtWhisper.addEventListener('input', () => updateWordCount(txtWhisper, whisperWordCount));
    txtGemini.addEventListener('input', () => updateWordCount(txtGemini, geminiWordCount));

    // ===== STAGE 1 & STAGE 2 PROCESS =====
    btnProcess.addEventListener('click', triggerProcess);

    async function triggerProcess() {
        const url = videoUrlInput.value.trim();
        if (!url) {
            updateProgress(0, '⚠️ Vui lòng dán link video trước khi xử lý!', 'error');
            videoUrlInput.focus();
            return;
        }

        btnProcess.disabled = true;
        processSpinner.style.display = 'inline-block';
        txtWhisper.value = '';
        txtGemini.value = '';
        updateWordCount(txtWhisper, whisperWordCount);
        updateWordCount(txtGemini, geminiWordCount);

        const modelEstMap = { 'Draft': 4, 'Standard': 10, 'Professional': 25, 'Premium': 45 };
        const estSec = modelEstMap[selModel.value] || 10;
        startLiveTimer(estSec);

        let currentPercent = 10;
        updateProgress(currentPercent, '⚡ STAGE 1: [1/3] Đang kết nối server & tải audio...', 'info');

        progressTimer = setInterval(() => {
            const elapsed = (Date.now() - startTime) / 1000;
            if (elapsed < 3) {
                currentPercent = Math.min(35, currentPercent + 5);
                updateProgress(currentPercent, '⚡ STAGE 1: [1/3] Đang tải audio stream...', 'info');
            } else if (elapsed < estSec) {
                currentPercent = Math.min(80, currentPercent + 3);
                updateProgress(currentPercent, `⚡ STAGE 1: [2/3] Whisper AI (${selModel.value}) đang nhận dạng giọng nói...`, 'info');
            } else if (currentPercent < 92) {
                currentPercent += 1;
                updateProgress(currentPercent, `⚡ STAGE 1: [3/3] Đang hoàn thiện trích xuất...`, 'info');
            }
        }, 600);

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 75000);

            let res;
            try {
                res = await fetch('/api/process', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    signal: controller.signal,
                    body: JSON.stringify({
                        url: url,
                        language: selLang.value,
                        model_type: selModel.value,
                        use_sub: chkUseSub.checked,
                        auto_gemini: false,
                        prompt_custom: customPrompt.value.trim(),
                        prompt_mode: selMode.value
                    })
                });
            } finally {
                clearTimeout(timeoutId);
            }

            if (!res.ok) throw new Error(`Server phản hồi lỗi HTTP ${res.status}`);
            const data = await res.json();
            resetTimers();

            if (data.error) {
                stopLiveTimer(false);
                updateProgress(0, `❌ Lỗi: ${data.error}`, 'error');
                btnProcess.disabled = false;
                processSpinner.style.display = 'none';
                return;
            }

            txtWhisper.value = data.raw_text || '';
            updateWordCount(txtWhisper, whisperWordCount);

            const isAutoGemini = chkAutoGemini.checked;
            if (!isAutoGemini || !data.raw_text) {
                stopLiveTimer(true);
                updateProgress(100, `🎉 Hoàn thành Stage 1! (${data.method} | ${data.word_count} từ)`, 'success');
                btnProcess.disabled = false;
                processSpinner.style.display = 'none';
                return;
            }

            updateProgress(85, `🤖 STAGE 2: Gemini AI đang chuẩn hóa bài viết...`, 'info');
            const gemController = new AbortController();
            const gemTimeoutId = setTimeout(() => gemController.abort(), 45000);

            let gemRes;
            try {
                gemRes = await fetch('/api/gemini', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    signal: gemController.signal,
                    body: JSON.stringify({
                        input_text: data.raw_text,
                        language: selLang.value,
                        prompt_custom: customPrompt.value.trim(),
                        api_key: apiKeyInput.value.trim(),
                        prompt_mode: selMode.value
                    })
                });
            } finally {
                clearTimeout(gemTimeoutId);
            }

            const gemData = await gemRes.json();
            stopLiveTimer(true);

            if (gemData.status === 'ERROR') {
                updateProgress(85, `⚠️ Stage 1 Hoàn thành! Lỗi Gemini Stage 2: ${gemData.text}`, 'error');
            } else {
                txtGemini.value = gemData.text || '';
                updateWordCount(txtGemini, geminiWordCount);
                const stageStatus = gemData.status || data.method || 'Thành công';
                if (stageStatus.includes("CHƯA NẠP") || stageStatus.includes("Offline") || stageStatus.includes("Nội bộ")) {
                    updateProgress(100, `⚠️ CHƯA NẠP GEMINI API KEY (Đang chạy Offline không có AI). Vui lòng bấm nút ⚙️ Cài đặt và dán Key để AI tóm tắt / viết lại bài!`, 'error');
                } else {
                    updateProgress(100, `🎉 Gemini AI đã chuẩn hóa xong bài viết! (${stageStatus})`, 'success');
                }
            }
        } catch (err) {
            resetTimers();
            stopLiveTimer(false);
            const isAbort = err.name === 'AbortError';
            const errMsg = isAbort 
                ? 'Quá thời gian chờ server (Timeout 75s). Vui lòng thử lại hoặc dán Gemini API Key trong Cài đặt!' 
                : err.message;
            updateProgress(0, `❌ Lỗi: ${errMsg}`, 'error');
        } finally {
            btnProcess.disabled = false;
            processSpinner.style.display = 'none';
        }
    }

    // Manual Gemini Run
    btnRunGemini.addEventListener('click', async () => {
        const rawText = txtWhisper.value.trim();
        if (!rawText) {
            updateProgress(0, '⚠️ Chưa có nội dung thô để Gemini chuẩn hóa!', 'error');
            return;
        }

        btnRunGemini.disabled = true;
        startLiveTimer(3);
        updateProgress(85, '⚡ Gemini AI đang chuẩn hóa và biên tập bài viết...', 'info');

        try {
            const res = await fetch('/api/gemini', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    input_text: rawText,
                    language: selLang.value,
                    prompt_custom: customPrompt.value.trim(),
                    api_key: apiKeyInput.value.trim(),
                    prompt_mode: selMode.value
                })
            });

            if (!res.ok) throw new Error(`Server phản hồi lỗi HTTP ${res.status}`);
            const data = await res.json();
            stopLiveTimer(true);

            if (data.status === 'ERROR') {
                updateProgress(50, `❌ Lỗi Gemini: ${data.text}`, 'error');
            } else {
                txtGemini.value = data.text;
                updateWordCount(txtGemini, geminiWordCount);
                updateProgress(100, `🎉 Gemini AI đã chuẩn hóa xong bài viết! (${data.status})`, 'success');
                const stage2 = document.getElementById('txtGemini') || document.getElementById('stage2Card');
                if (stage2) {
                    stage2.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    stage2.classList.add('highlight-flash');
                    setTimeout(() => stage2.classList.remove('highlight-flash'), 1500);
                }
            }
        } catch (err) {
            stopLiveTimer(false);
            updateProgress(50, `❌ Lỗi kết nối Gemini: ${err.message}`, 'error');
        } finally {
            btnRunGemini.disabled = false;
        }
    });

    // ===== STAGE 3: TTS & SPEAKER PREVIEW =====
    btnPreviewSelectedVoice.addEventListener('click', async () => {
        const selectedVoiceVal = selVoice.value;

        // Toggle Stop Preview if playing
        if (currentPreviewAudio && activePreviewBtn === btnPreviewSelectedVoice) {
            currentPreviewAudio.pause();
            currentPreviewAudio = null;
            btnPreviewSelectedVoice.classList.remove('playing');
            btnPreviewSelectedVoice.textContent = '🔊';
            activePreviewBtn = null;
            return;
        }

        if (currentPreviewAudio) {
            currentPreviewAudio.pause();
            if (activePreviewBtn) {
                activePreviewBtn.classList.remove('playing');
                activePreviewBtn.textContent = '🔊';
            }
        }

        btnPreviewSelectedVoice.textContent = '⏳';
        btnPreviewSelectedVoice.classList.add('playing');
        activePreviewBtn = btnPreviewSelectedVoice;

        try {
            let previewUrl = '';

            // 1. Original Video Audio
            if (selectedVoiceVal === 'original') {
                previewUrl = '/temp/input_audio.mp3';
            }
            // 2. Custom Ref Voice
            else if (selectedVoiceVal.startsWith('ref:')) {
                const filename = selectedVoiceVal.substring(4);
                previewUrl = `/temp/ref_voices/${filename}`;
            }
            // 3. Preset Voice (Edge-TTS / Google) -> Generate quick 2s sample
            else {
                const res = await fetch('/api/tts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: "Xin chào, đây là giọng đọc thử nghiệm MASTER AI PRO.",
                        voice: selectedVoiceVal,
                        rate: "+0%",
                        bgm_type: "none"
                    })
                });
                const data = await res.json();
                if (data.success) {
                    previewUrl = data.audio_url;
                } else {
                    throw new Error(data.error || "Không thể tạo thử giọng");
                }
            }

            const testAudio = new Audio();
            testAudio.onerror = () => {
                btnPreviewSelectedVoice.classList.remove('playing');
                btnPreviewSelectedVoice.textContent = '🔊';
                currentPreviewAudio = null;
                activePreviewBtn = null;
                if (selectedVoiceVal === 'original') {
                    alert('📌 Vui lòng dán link video & bấm "XỬ LÝ NGAY" ở Stage 1 để bóc tách giọng video gốc trước khi nghe thử!');
                } else {
                    alert('Mẫu âm thanh thử nghiệm chưa sẵn sàng hoặc đã bị xóa!');
                }
            };

            testAudio.oncanplay = () => {
                testAudio.play().catch(() => {});
            };

            testAudio.onended = () => {
                btnPreviewSelectedVoice.classList.remove('playing');
                btnPreviewSelectedVoice.textContent = '🔊';
                currentPreviewAudio = null;
                activePreviewBtn = null;
            };

            currentPreviewAudio = testAudio;
            btnPreviewSelectedVoice.textContent = '⏸️';
            testAudio.src = previewUrl;

        } catch (err) {
            alert('Lỗi thử giọng: ' + err.message);
            btnPreviewSelectedVoice.classList.remove('playing');
            btnPreviewSelectedVoice.textContent = '🔊';
            currentPreviewAudio = null;
            activePreviewBtn = null;
        }
    });

    // Voice Filter & Deletion System
    function applyHiddenVoicesFilter() {
        const hiddenVoices = JSON.parse(localStorage.getItem('hidden_voices') || '[]');
        Array.from(selVoice.options).forEach(opt => {
            if (hiddenVoices.includes(opt.value)) {
                opt.style.display = 'none';
                opt.disabled = true;
            } else {
                opt.style.display = '';
                opt.disabled = false;
            }
        });
    }

    const btnDeleteSelectedVoice = document.getElementById('btnDeleteSelectedVoice');
    if (btnDeleteSelectedVoice) {
        btnDeleteSelectedVoice.addEventListener('click', () => {
            const val = selVoice.value;
            const opt = selVoice.selectedOptions[0];
            if (!val || val === 'vi-VN-NamMinhNeural' || val === 'vi-VN-HoaiMyNeural') {
                alert('⚠️ Giọng [Studio] Nam Minh và Hoài Mỹ là giọng chính Tiếng Việt tiêu chuẩn, không thể ẩn!');
                return;
            }
            const voiceName = opt ? opt.textContent.trim() : val;
            if (confirm(`Bạn có chắc chắn muốn xóa/ẩn giọng "${voiceName}" khỏi danh sách chọn không?`)) {
                let hiddenVoices = JSON.parse(localStorage.getItem('hidden_voices') || '[]');
                if (!hiddenVoices.includes(val)) {
                    hiddenVoices.push(val);
                    localStorage.setItem('hidden_voices', JSON.stringify(hiddenVoices));
                }
                applyHiddenVoicesFilter();
                selVoice.value = 'vi-VN-NamMinhNeural';
                selVoice.dispatchEvent(new Event('change'));
                alert(`Đã xóa giọng "${voiceName}" khỏi danh sách!`);
            }
        });
    }

    applyHiddenVoicesFilter();

    // Voice Frequency & Pitch Meter Analyzer
    const btnAnalyzeVoice = document.getElementById('btnAnalyzeVoice');
    const freqMeterResults = document.getElementById('freqMeterResults');
    const meterF0 = document.getElementById('meterF0');
    const meterRange = document.getElementById('meterRange');
    const meterTone = document.getElementById('meterTone');
    const meterCentroid = document.getElementById('meterCentroid');
    const pitchContourWrapper = document.getElementById('pitchContourWrapper');
    const pitchGraphBars = document.getElementById('pitchGraphBars');

    if (btnAnalyzeVoice) {
        btnAnalyzeVoice.addEventListener('click', async () => {
            const voiceVal = selVoice.value;
            if (!voiceVal || voiceVal === 'original') {
                alert('Vui lòng chọn một mẫu giọng (Ví dụ: ⭐ ADAM Các vợ) để phân tích tần số!');
                return;
            }

            btnAnalyzeVoice.disabled = true;
            btnAnalyzeVoice.textContent = '⏳ Đang đo tần số F0 & Formant...';

            try {
                const res = await fetch(`/api/voice/analyze?file=${encodeURIComponent(voiceVal)}`);
                const data = await res.json();

                if (data.error) {
                    alert('Lỗi phân tích: ' + data.error);
                } else {
                    freqMeterResults.style.display = 'grid';
                    pitchContourWrapper.style.display = 'flex';

                    meterF0.textContent = `${data.mean_f0} Hz`;
                    meterRange.textContent = `${data.min_f0} - ${data.max_f0} Hz`;
                    meterTone.textContent = data.tone_type;
                    meterCentroid.textContent = `${data.spectral_centroid} Hz`;

                    if (data.contour && data.contour.length > 0 && pitchGraphBars) {
                        const maxVal = Math.max(...data.contour, 250);
                        const minVal = Math.min(...data.contour, 50);
                        const range = (maxVal - minVal) || 1;

                        pitchGraphBars.innerHTML = data.contour.map(val => {
                            const pct = Math.max(12, Math.min(100, ((val - minVal) / range) * 100));
                            return `<div class="pitch-bar" style="height: ${pct}%;" title="F0: ${val} Hz"></div>`;
                        }).join('');
                    }
                }
            } catch (err) {
                alert('Lỗi kết nối máy đo tần số: ' + err.message);
            } finally {
                btnAnalyzeVoice.disabled = false;
                btnAnalyzeVoice.textContent = '🔍 Phân tích Tần số Giọng Mẫu';
            }
        });
    }

    const selVoiceEl = document.getElementById('selVoice');
    const customVoiceIdWrapperEl = document.getElementById('customVoiceIdWrapper');
    if (selVoiceEl && customVoiceIdWrapperEl) {
        selVoiceEl.addEventListener('change', () => {
            if (selVoiceEl.value === 'el-custom') {
                customVoiceIdWrapperEl.style.display = 'block';
            } else {
                customVoiceIdWrapperEl.style.display = 'none';
            }
        });
    }

    btnRunTTS.addEventListener('click', async () => {
        const text = txtGemini.value.trim() || txtWhisper.value.trim();
        if (!text && selVoice.value !== 'original') {
            alert('Vui lòng tạo nội dung văn bản ở Stage 1 hoặc Stage 2 trước!');
            return;
        }

        btnRunTTS.disabled = true;
        ttsSpinner.style.display = 'inline-block';
        updateProgress(85, '🎙️ STAGE 3: Đang tạo giọng đọc AI & ghép nhạc nền...', 'info');

        const ttsProgContainer = document.getElementById('ttsProgressContainer');
        const ttsProgFill = document.getElementById('ttsProgressBarFill');
        const ttsProgText = document.getElementById('ttsProgressText');
        const ttsProgPercent = document.getElementById('ttsProgressPercent');

        let pStep = 5;
        let ttsStartTime = Date.now();
        if (ttsProgContainer) ttsProgContainer.style.display = 'block';
        const ttsTimer = setInterval(() => {
            const elapsedSec = ((Date.now() - ttsStartTime) / 1000).toFixed(1);
            if (pStep < 35) {
                pStep += 5;
                if (ttsProgText) ttsProgText.textContent = `🎙️ 1/3: Đang trích xuất & tổng hợp giọng đọc AI... (⏱️ ${elapsedSec}s)`;
            } else if (pStep < 80) {
                pStep += 6;
                if (ttsProgText) ttsProgText.textContent = `🎛️ 2/3: Đang điều chỉnh tần số âm sắc Voice Clone Timbre... (⏱️ ${elapsedSec}s)`;
            } else if (pStep < 95) {
                pStep += 2;
                const isBgm = selBgm && selBgm.value !== 'none';
                const bgmMsg = isBgm ? '🎼 3/3: Đang hòa trộn Nhạc nền BGM & kết xuất file MP3...' : '🎧 3/3: Đang kết xuất file MP3 âm thanh lồng tiếng...';
                if (ttsProgText) ttsProgText.textContent = `${bgmMsg} (⏱️ ${elapsedSec}s)`;
            }
            if (ttsProgFill) ttsProgFill.style.width = `${pStep}%`;
            if (ttsProgPercent) ttsProgPercent.textContent = `⏱️ ${elapsedSec}s | ${pStep}%`;
        }, 100);

        try {
            const customVoiceIdInput = document.getElementById('inputCustomVoiceId');
            const customVoiceId = customVoiceIdInput ? customVoiceIdInput.value.trim() : '';

            const res = await safeFetch('/api/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: text,
                    voice: selVoice.value,
                    rate: selRate.value,
                    bgm_type: selBgm.value,
                    custom_voice_id: customVoiceId
                })
            });

            clearInterval(ttsTimer);
            const finalSec = ((Date.now() - ttsStartTime) / 1000).toFixed(1);
            if (ttsProgFill) ttsProgFill.style.width = '100%';
            if (ttsProgPercent) ttsProgPercent.textContent = `⏱️ ${finalSec}s | 100%`;
            if (ttsProgText) ttsProgText.textContent = `🎉 Hoàn tất lồng tiếng trong ${finalSec} giây!`;
            setTimeout(() => { if (ttsProgContainer) ttsProgContainer.style.display = 'none'; }, 3000);

            const data = await res.json();
            if (data.success) {
                currentAudioUrl = data.audio_url;
                ttsAudioPlayer.src = data.audio_url;
                audioPlayerWrapper.style.display = 'flex';
                ttsAudioPlayer.play().catch(() => {});
                updateProgress(100, `🎉 STAGE 3 Hoàn thành! Đã lồng tiếng và ghép nhạc nền thành công tệp: ${data.filename}`, 'success');
                loadHistory();
            } else {
                alert('Lỗi tạo giọng đọc: ' + (data.error || 'Thất bại'));
                updateProgress(0, '❌ Lỗi STAGE 3', 'error');
            }
        } catch (err) {
            clearInterval(ttsTimer);
            if (ttsProgContainer) ttsProgContainer.style.display = 'none';
            alert('Lỗi kết nối TTS: ' + err.message);
            updateProgress(0, '❌ Lỗi kết nối TTS', 'error');
        } finally {
            btnRunTTS.disabled = false;
            ttsSpinner.style.display = 'none';
        }
    });

    btnDownloadAudio.addEventListener('click', () => {
        if (!currentAudioUrl) return;
        const a = document.createElement('a');
        a.href = currentAudioUrl;
        a.download = 'voice_speech.mp3';
        a.click();
    });

    // ===== STAGE 4: VOICE CLONE & MINER VAULT =====
    btnChooseFile.addEventListener('click', () => refAudioFile.click());
    refAudioFile.addEventListener('change', () => {
        if (refAudioFile.files.length > 0) {
            selectedRefFile = refAudioFile.files[0];
            btnChooseFile.textContent = `🎵 ${selectedRefFile.name.substring(0, 15)}...`;
        }
    });

    btnUploadRefVoice.addEventListener('click', async () => {
        if (!selectedRefFile) {
            alert('Vui lòng chọn file âm thanh trước!');
            return;
        }

        const name = refVoiceName.value.trim() || selectedRefFile.name;
        btnUploadRefVoice.disabled = true;

        const reader = new FileReader();
        reader.onload = async (e) => {
            const base64Data = e.target.result.split(',')[1];
            try {
                const res = await fetch('/api/clone-voice/upload', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        file_b64: base64Data,
                        filename: selectedRefFile.name,
                        voice_name: name
                    })
                });

                const data = await res.json();
                if (data.success) {
                    selectedRefFile = null;
                    refAudioFile.value = '';
                    refVoiceName.value = '';
                    btnChooseFile.textContent = '📁 Chọn mẫu audio 5s';
                    loadVoiceDropdownAndGallery();
                } else {
                    alert('Lỗi: ' + data.error);
                }
            } catch (err) {
                alert('Lỗi tải file: ' + err.message);
            } finally {
                btnUploadRefVoice.disabled = false;
            }
        };
        reader.readAsDataURL(selectedRefFile);
    });

    // Auto Miner Trigger & Polling
    btnStartMining.addEventListener('click', async () => {
        btnStartMining.disabled = true;
        minerSpinner.style.display = 'inline-block';
        minerProgress.style.display = 'flex';

        try {
            const res = await fetch('/api/mine-voice', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    category: selCategory.value,
                    count: 6
                })
            });

            const data = await res.json();
            if (data.success) {
                startMinerPolling();
            } else {
                alert('Lỗi: ' + data.message);
                btnStartMining.disabled = false;
                minerSpinner.style.display = 'none';
            }
        } catch (err) {
            alert('Lỗi kết nối Miner: ' + err.message);
            btnStartMining.disabled = false;
            minerSpinner.style.display = 'none';
        }
    });

    function startMinerPolling() {
        if (minerPollInterval) clearInterval(minerPollInterval);

        minerPollInterval = setInterval(async () => {
            try {
                const res = await fetch('/api/mine-voice/status');
                const st = await res.json();

                minerStatusText.textContent = `${st.current_category}: ${st.current_action}`;
                minerPercentText.textContent = `${st.progress_percent}%`;
                minerProgressFill.style.width = `${st.progress_percent}%`;

                if (!st.is_running && st.progress_percent >= 100) {
                    clearInterval(minerPollInterval);
                    minerPollInterval = null;
                    btnStartMining.disabled = false;
                    minerSpinner.style.display = 'none';
                    setTimeout(() => minerProgress.style.display = 'none', 3000);
                    loadVoiceDropdownAndGallery();
                }
            } catch (e) {
                console.error('Lỗi poll status:', e);
            }
        }, 1200);
    }

    async function loadVoiceDropdownAndGallery(retryCount = 0) {
        try {
            const refRes = await fetch('/api/ref-voices');
            const refData = await refRes.json();
            renderVaultChips(refData.voices || []);
            applyHiddenVoicesFilter();
        } catch (err) {
            console.error('Lỗi nạp kho giọng mẫu:', err);
            if (retryCount < 3) {
                setTimeout(() => loadVoiceDropdownAndGallery(retryCount + 1), 1500);
            } else {
                if (refVoiceGallery) {
                    refVoiceGallery.innerHTML = '<p class="empty-gallery">❌ Chưa kết nối máy chủ. Vui lòng kiểm tra server hoặc bấm F5!</p>';
                }
            }
        }
    }

    function renderVaultChips(voices) {
        if (!voices || voices.length === 0) {
            refVoiceGallery.innerHTML = '<p class="empty-gallery">Chưa có giọng mẫu. Hãy cào hoặc upload file 5s!</p>';
            return;
        }

        // Anti-duplication guard: Filter unique voices by display name
        const uniqueVoices = [];
        const seenNames = new Set();
        for (const v of voices) {
            const key = (v.name || v.filename || '').trim().toLowerCase();
            if (!seenNames.has(key)) {
                seenNames.add(key);
                uniqueVoices.push(v);
            }
        }

        refVoiceGallery.innerHTML = uniqueVoices.map(v => `
            <div class="voice-chip ${v.is_saved ? 'saved' : ''}" data-filename="${v.filename}" data-url="${v.url}">
                <button class="btn-chip-icon btn-chip-star" title="${v.is_saved ? 'Đã lưu vĩnh viễn (Bấm để bỏ lưu)' : 'Bấm ⭐ để lưu vĩnh viễn không bị xóa sau 24h'}">${v.is_saved ? '⭐' : '☆'}</button>
                <button class="btn-chip-icon btn-chip-play" title="Nghe thử giọng mẫu">🔊</button>
                <span class="chip-name" title="${v.name}">${v.name}</span>
                <button class="btn-chip-icon btn-chip-edit" title="Sửa tên giọng">✏️</button>
                <button class="btn-chip-icon btn-chip-del" title="Xóa giọng mẫu">🗑️</button>
            </div>
        `).join('');

        document.querySelectorAll('.voice-chip').forEach(chip => {
            const filename = chip.dataset.filename;
            const url = chip.dataset.url;
            const starBtn = chip.querySelector('.btn-chip-star');
            const playBtn = chip.querySelector('.btn-chip-play');
            const editBtn = chip.querySelector('.btn-chip-edit');
            const delBtn = chip.querySelector('.btn-chip-del');
            const nameSpan = chip.querySelector('.chip-name');

            // Click chip to select voice for TTS lồng tiếng
            chip.addEventListener('click', (e) => {
                if (e.target.closest('.btn-chip-icon')) return;

                const voiceId = `ref:${filename}`;
                const optExists = Array.from(selVoice.options).some(opt => opt.value === voiceId);
                if (!optExists) {
                    const opt = document.createElement('option');
                    opt.value = voiceId;
                    opt.textContent = `🎙️ ${nameSpan.textContent}`;
                    selVoice.appendChild(opt);
                }
                selVoice.value = voiceId;

                document.querySelectorAll('.voice-chip').forEach(c => c.classList.remove('selected-active'));
                chip.classList.add('selected-active');

                updateProgress(100, `🎯 Đã chọn giọng lồng tiếng: ${nameSpan.textContent}`, 'success');

                const stage3 = document.getElementById('stage3Card') || document.getElementById('selVoice');
                if (stage3) {
                    stage3.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    stage3.classList.add('highlight-flash');
                    setTimeout(() => stage3.classList.remove('highlight-flash'), 1500);
                }
            });

            // Star / Toggle Favorite Save
            starBtn.addEventListener('click', async () => {
                try {
                    const res = await fetch('/api/ref-voices/toggle-save', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ filename: filename })
                    });
                    const data = await res.json();
                    if (data.success) {
                        loadVoiceDropdownAndGallery();
                    } else {
                        alert('Lỗi lưu giọng: ' + data.error);
                    }
                } catch (err) {
                    alert('Lỗi kết nối: ' + err.message);
                }
            });

            // Play / Stop Preview
            playBtn.addEventListener('click', () => {
                if (currentPreviewAudio && activePreviewBtn === playBtn) {
                    currentPreviewAudio.pause();
                    currentPreviewAudio = null;
                    playBtn.classList.remove('playing');
                    playBtn.textContent = '🔊';
                    activePreviewBtn = null;
                    return;
                }

                if (currentPreviewAudio) {
                    currentPreviewAudio.pause();
                    if (activePreviewBtn) {
                        activePreviewBtn.classList.remove('playing');
                        activePreviewBtn.textContent = '🔊';
                    }
                }

                const testAudio = new Audio();
                testAudio.onerror = () => {
                    alert('Không thể tải file âm thanh thử nghiệm này!');
                    playBtn.classList.remove('playing');
                    playBtn.textContent = '🔊';
                    currentPreviewAudio = null;
                    activePreviewBtn = null;
                };

                testAudio.onended = () => {
                    playBtn.classList.remove('playing');
                    playBtn.textContent = '🔊';
                    currentPreviewAudio = null;
                    activePreviewBtn = null;
                };

                playBtn.classList.add('playing');
                playBtn.textContent = '⏸️';
                activePreviewBtn = playBtn;
                currentPreviewAudio = testAudio;
                testAudio.src = url;
                testAudio.play().catch(() => {});
            });

            // Edit / Rename Voice
            editBtn.addEventListener('click', async () => {
                const newName = prompt('Nhập tên mới cho mẫu giọng:', nameSpan.textContent);
                if (!newName || newName.trim() === nameSpan.textContent) return;

                try {
                    const res = await fetch('/api/ref-voices/rename', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ filename: filename, new_name: newName.trim() })
                    });
                    const data = await res.json();
                    if (data.success) {
                        loadVoiceDropdownAndGallery();
                    } else {
                        alert('Lỗi đổi tên: ' + data.error);
                    }
                } catch (err) {
                    alert('Lỗi: ' + err.message);
                }
            });

            // Delete Voice
            delBtn.addEventListener('click', async () => {
                if (!confirm(`Bạn có chắc muốn xóa mẫu giọng "${nameSpan.textContent}"?`)) return;

                try {
                    const res = await fetch('/api/ref-voices/delete', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ filename: filename })
                    });
                    const data = await res.json();
                    if (data.success) {
                        if (currentPreviewAudio && activePreviewBtn === playBtn) {
                            currentPreviewAudio.pause();
                            currentPreviewAudio = null;
                        }
                        loadVoiceDropdownAndGallery();
                    } else {
                        alert('Lỗi xóa: ' + data.error);
                    }
                } catch (err) {
                    alert('Lỗi: ' + err.message);
                }
            });
        });
    }

    // Helper Copy, Download, Clear Functions
    function copyText(textarea, btn) {
        const text = textarea.value.trim();
        if (!text) return;
        navigator.clipboard.writeText(text);
        const originalText = btn.textContent;
        btn.textContent = '✅ Đã copy!';
        setTimeout(() => { btn.textContent = originalText; }, 2000);
    }

    function downloadText(textarea, defaultFilename) {
        const text = textarea.value.trim();
        if (!text) return;
        const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = defaultFilename;
        a.click();
        URL.revokeObjectURL(a.href);
    }

    btnCopyWhisper.addEventListener('click', () => copyText(txtWhisper, btnCopyWhisper));
    btnCopyGemini.addEventListener('click', () => copyText(txtGemini, btnCopyGemini));

    btnDownloadWhisper.addEventListener('click', () => downloadText(txtWhisper, 'whisper_raw_transcript.txt'));
    btnDownloadGemini.addEventListener('click', () => downloadText(txtGemini, 'gemini_normalized_transcript.txt'));

    btnClearWhisper.addEventListener('click', () => {
        txtWhisper.value = '';
        updateWordCount(txtWhisper, whisperWordCount);
    });
    btnClearGemini.addEventListener('click', () => {
        txtGemini.value = '';
        updateWordCount(txtWhisper, geminiWordCount);
    });

    // ===== STAGE 5: HISTORY ARCHIVE =====
    const chkSelectAllHistory = document.getElementById('chkSelectAllHistory');
    const btnBulkDownloadHistory = document.getElementById('btnBulkDownloadHistory');
    const btnBulkDeleteHistory = document.getElementById('btnBulkDeleteHistory');

    async function loadHistory() {
        try {
            const res = await fetch('/api/history');
            const data = await res.json();
            const listEl = document.getElementById('historyList');
            if (!listEl) return;

            if (chkSelectAllHistory) chkSelectAllHistory.checked = false;

            if (data.history && data.history.length > 0) {
                listEl.innerHTML = data.history.map((item, idx) => `
                    <div class="history-card" data-filename="${item.filename}">
                        <div class="history-info">
                            <input type="checkbox" class="chk-history-item" data-filename="${item.filename}" data-url="${item.url}" style="width:18px; height:18px; cursor:pointer;">
                            <span class="history-idx" style="font-weight:700; color:var(--primary); font-size:13px; min-width:26px;">#${idx + 1}</span>
                            <span class="history-icon">🎵</span>
                            <div class="history-meta">
                                <span class="history-name" title="${item.filename}">${item.filename}</span>
                                <span class="history-time">⏱️ ${item.time_str} • 💾 ${item.size_kb} KB</span>
                            </div>
                        </div>
                        <audio controls src="${item.url}" class="history-audio"></audio>
                        <div class="history-actions">
                            <button class="btn-sub sm btn-rename-history" data-filename="${item.filename}">✏️ Đổi Tên</button>
                            <a href="${item.url}" download="${item.filename}" class="btn-sub primary sm">💾 Tải MP3</a>
                            <button class="btn-sub danger sm btn-delete-history" data-filename="${item.filename}">🗑️ Xóa</button>
                        </div>
                    </div>
                `).join('');

                // Single Item Delete
                document.querySelectorAll('.btn-delete-history').forEach(btn => {
                    btn.addEventListener('click', async (e) => {
                        const fn = e.target.getAttribute('data-filename');
                        if (confirm(`Bạn có chắc muốn xóa file ${fn}?`)) {
                            await fetch('/api/history/delete', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ filename: fn })
                            });
                            loadHistory();
                        }
                    });
                });

                // Single Item Rename
                document.querySelectorAll('.btn-rename-history').forEach(btn => {
                    btn.addEventListener('click', async (e) => {
                        const fn = e.target.getAttribute('data-filename');
                        const newName = prompt('Nhập tên mới cho file audio (không cần nhập .mp3):', fn.replace('.mp3', ''));
                        if (!newName || !newName.trim()) return;
                        
                        try {
                            const r = await fetch('/api/history/rename', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ filename: fn, new_name: newName.trim() })
                            });
                            const resData = await r.json();
                            if (resData.success) {
                                loadHistory();
                            } else {
                                alert('Lỗi đổi tên: ' + resData.error);
                            }
                        } catch (err) {
                            alert('Lỗi đổi tên file: ' + err.message);
                        }
                    });
                });

            } else {
                listEl.innerHTML = '<div class="history-empty">Chưa có lịch sử tạo âm thanh nào.</div>';
            }
        } catch (e) {
            console.error('Lỗi nạp lịch sử:', e);
        }
    }

    // Select All Checkbox Handler
    if (chkSelectAllHistory) {
        chkSelectAllHistory.addEventListener('change', () => {
            const isChecked = chkSelectAllHistory.checked;
            document.querySelectorAll('.chk-history-item').forEach(chk => {
                chk.checked = isChecked;
            });
        });
    }

    // Bulk Delete Handler
    if (btnBulkDeleteHistory) {
        btnBulkDeleteHistory.addEventListener('click', async () => {
            const checkedBoxes = document.querySelectorAll('.chk-history-item:checked');
            if (checkedBoxes.length === 0) {
                alert('📌 Vui lòng tích chọn ít nhất 1 file để xóa!');
                return;
            }
            const filenames = Array.from(checkedBoxes).map(chk => chk.getAttribute('data-filename'));
            if (confirm(`Bạn có chắc muốn XÓA ĐỒNG LOẠT ${filenames.length} file đã chọn?`)) {
                try {
                    const r = await fetch('/api/history/bulk-delete', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ filenames: filenames })
                    });
                    const resData = await r.json();
                    if (resData.success) {
                        loadHistory();
                    } else {
                        alert('Lỗi xóa đồng loạt: ' + resData.error);
                    }
                } catch (err) {
                    alert('Lỗi kết nối: ' + err.message);
                }
            }
        });
    }

    // Bulk Download Handler
    if (btnBulkDownloadHistory) {
        btnBulkDownloadHistory.addEventListener('click', () => {
            const checkedBoxes = document.querySelectorAll('.chk-history-item:checked');
            if (checkedBoxes.length === 0) {
                alert('📌 Vui lòng tích chọn ít nhất 1 file để tải về đồng loạt!');
                return;
            }
            checkedBoxes.forEach((chk, idx) => {
                const url = chk.getAttribute('data-url');
                const fn = chk.getAttribute('data-filename');
                setTimeout(() => {
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = fn;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                }, idx * 300);
            });
        });
    }

    const btnRefreshHistory = document.getElementById('btnRefreshHistory');
    if (btnRefreshHistory) btnRefreshHistory.addEventListener('click', loadHistory);

    const btnToggleVault = document.getElementById('btnToggleVault');
    if (btnToggleVault && refVoiceGallery) {
        btnToggleVault.addEventListener('click', () => {
            if (refVoiceGallery.style.display === 'none') {
                refVoiceGallery.style.display = 'grid';
                btnToggleVault.textContent = '▲ Thu gọn Kho Giọng Mẫu';
            } else {
                refVoiceGallery.style.display = 'none';
                btnToggleVault.textContent = '▼ Mở rộng Kho Giọng Mẫu';
            }
        });
    }

    // Initial Load History
    loadHistory();
});
