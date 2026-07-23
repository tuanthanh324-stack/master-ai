import gradio as gr
import os
import sys
import json
from core_processor import (
    load_config, save_config, get_gemini_key, set_gemini_key,
    process_transcription, process_gemini
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")

# ==================== CONFIG HELPER ====================
def luu_api_key(api_key):
    api_key = (api_key or "").strip()
    if not api_key:
        return "Chưa nhập API Key!"
    if set_gemini_key(api_key):
        return f"Đã lưu thành công ({len(api_key)} ký tự)"
    return "Lỗi khi lưu API Key!"

def xoa_api_key():
    set_gemini_key("")
    return "Đã xóa API Key!"

def lay_api_key_da_luu():
    return get_gemini_key()

# ==================== PROCESSORS ====================
def chuyen_doi(url, ngon_ngu, model_type, lay_sub, dung_ocr, auto_gemini, progress=gr.Progress()):
    try:
        url = (url or "").strip()
        if not url:
            return "Chưa nhập link video!", "ERROR", "", ""

        progress(0.2, "Đang tải video & trích xuất audio...")

        result = process_transcription(
            url=url,
            language=ngon_ngu,
            model_type=model_type,
            use_sub=lay_sub,
            auto_gemini=auto_gemini
        )

        if "error" in result:
            return result["error"], "ERROR", "", ""

        raw_text = result.get("raw_text", "")
        method_info = f"{result.get('method', 'Whisper AI')} | {result.get('word_count', 0)} từ"
        gemini_text = result.get("gemini_text", "")
        gemini_status = result.get("gemini_status", "")

        progress(1.0, "Hoàn tất!")
        return raw_text, method_info, gemini_text, gemini_status

    except Exception as e:
        return f"Lỗi: {str(e)}", "ERROR", "", ""

def chuan_hoa_gemini(api_key, input_text, ngon_ngu, prompt_custom, progress=gr.Progress()):
    progress(0.4, "Đang gọi Gemini AI...")
    output, status = process_gemini(input_text, ngon_ngu, prompt_custom, api_key)
    progress(1.0, "Xong!")
    return output, status

# ==================== GRADIO CSS ====================
custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
* { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Inter', sans-serif; }
body { background: #fafaf9; }
.header { padding: 16px 0 12px 0; background: #fafaf9; text-align: center; }
.header h1 { font-size: 1.15rem; font-weight: 800; color: #37352f; letter-spacing: 0.15em; }
.main-row { display: flex; background: #fafaf9; padding: 8px 16px 16px 16px; gap: 12px; }
.panel { background: #fff; border: 1px solid #e5e3df; border-radius: 6px; padding: 18px; display: flex; flex-direction: column; }
.panel-title { font-size: 0.95rem; font-weight: 800; color: #37352f; margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid #e5e3df; }
.badge { background: #5645d4; color: #fff; font-size: 0.7rem; font-weight: 700; padding: 3px 8px; border-radius: 3px; }
.lb { color: #37352f; font-size: 0.72rem; font-weight: 800; text-transform: uppercase; margin: 10px 0 5px; }
.btn-save { background: #1aae39; color: #fff; }
.btn-del { background: #e03131; color: #fff; }
.btn-main { background: linear-gradient(180deg, #5645d4, #4534b3); color: #fff; font-size: 1rem; font-weight: 800; padding: 16px; border-radius: 6px; }
"""

# ==================== UI BLOCKS ====================
with gr.Blocks(title="MASTER AI", css=custom_css) as demo:
    gr.HTML('<div class="header"><h1>MASTER AI PRO</h1></div>')

    with gr.Row(elem_classes="main-row"):
        # SIDEBAR
        with gr.Column(scale=2, elem_classes="panel sidebar", min_width=260):
            gr.HTML('<div class="panel-title">CẤU HÌNH SIDEBAR</div>')

            gr.HTML('<div class="lb">LINK VIDEO</div>')
            url = gr.Textbox(placeholder="Dán link TikTok, YouTube, Facebook...", show_label=False, container=False)

            gr.HTML('<div class="lb">NGÔN NGỮ</div>')
            lang = gr.Dropdown(choices=["Vietnamese", "English", "Spanish", "French", "German"],
                             value="Vietnamese", show_label=False, container=False)

            gr.HTML('<div class="lb">MODEL WHISPER</div>')
            model_type = gr.Dropdown(choices=["Standard", "Draft", "Professional", "Premium"],
                                   value="Standard", show_label=False, container=False)

            gr.HTML('<div class="lb">TÙY CHỌN</div>')
            with gr.Row():
                lay_sub = gr.Checkbox(label="Phụ đề", value=True)
                dung_ocr = gr.Checkbox(label="Ưu tiên Sub", value=True)
            with gr.Row():
                auto_gemini = gr.Checkbox(label="Auto Gemini AI", value=True)

            gr.HTML('<div class="lb">GEMINI API KEY</div>')
            api_key = gr.Textbox(placeholder="AIzaSy...", type="password",
                                value=lay_api_key_da_luu(), show_label=False, container=False)

            with gr.Row():
                btn_save = gr.Button("LƯU KEY", elem_classes="btn-save")
                btn_del = gr.Button("XÓA KEY", elem_classes="btn-del")
                gr.HTML('<a href="https://aistudio.google.com/apikey" target="_blank" class="btn-link">GET KEY</a>')

            api_msg = gr.Textbox(value="Sẵn sàng", interactive=False, show_label=False, container=False)

            btn = gr.Button("XỬ LÝ NGAY", elem_classes="btn-main")
            status = gr.Textbox(value="", interactive=False, show_label=False, container=False)

        # ARROW 1
        gr.HTML('<div class="arrow-mid"><div class="icon">▶</div></div>')

        # WHISPER
        with gr.Column(scale=3, elem_classes="panel ws-panel", min_width=320):
            gr.HTML('<div class="panel-title">WHISPER <span class="badge">NỘI DUNG THÔ</span></div>')
            result = gr.Textbox(lines=12, show_label=False, placeholder="Kết quả trích xuất văn bản từ video...", container=False)
            with gr.Row():
                gr.Button("Copy", elem_classes="btn-ws").click(
                    fn=None, inputs=[result], outputs=[status],
                    js="(t)=>{navigator.clipboard.writeText(t||'');return'Đã copy văn bản thô'}"
                )
                gr.Button("Clear", elem_classes="btn-ws").click(
                    fn=lambda:("",""), inputs=[], outputs=[result, status]
                )

        # ARROW 2
        gr.HTML('<div class="arrow-mid"><div class="icon">▶</div></div>')

        # GEMINI
        with gr.Column(scale=3, elem_classes="panel ws-panel", min_width=320):
            gr.HTML('<div class="panel-title">GEMINI AI <span class="badge">CHUẨN HÓA</span></div>')
            prompt_text = gr.Textbox(placeholder="Prompt tùy chỉnh (VD: Chỉnh sửa chính tả, viết lại mượt mà)...", show_label=False, container=False)
            with gr.Row():
                btn_gemini = gr.Button("CHUẨN HÓA LẠI", elem_classes="btn-gemini", scale=3)
                gemini_st = gr.Textbox(value="", interactive=False, show_label=False, container=False, scale=1)

            result_gemini = gr.Textbox(lines=12, show_label=False, placeholder="Kết quả chuẩn hóa...", container=False)
            with gr.Row():
                gr.Button("Copy", elem_classes="btn-ws").click(
                    fn=None, inputs=[result_gemini], outputs=[gemini_st],
                    js="(t)=>{navigator.clipboard.writeText(t||'');return'Đã copy văn bản Gemini'}"
                )
                gr.Button("Clear", elem_classes="btn-ws").click(
                    fn=lambda:"", inputs=[], outputs=[result_gemini]
                )

    # EVENTS
    btn_save.click(fn=luu_api_key, inputs=[api_key], outputs=[api_msg])
    btn_del.click(fn=xoa_api_key, inputs=[], outputs=[api_msg])

    btn.click(fn=chuyen_doi,
              inputs=[url, lang, model_type, lay_sub, dung_ocr, auto_gemini],
              outputs=[result, status, result_gemini, gemini_st])

    btn_gemini.click(fn=chuan_hoa_gemini,
                     inputs=[api_key, result, lang, prompt_text],
                     outputs=[result_gemini, gemini_st])

if __name__ == "__main__":
    port = 7860
    demo.launch(server_name="0.0.0.0", server_port=port, inbrowser=True)
