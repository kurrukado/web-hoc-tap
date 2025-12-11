import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import json
import zipfile
import io

# Cấu hình trang
st.set_page_config(page_title="AI Ôn Tập (Hỗ trợ ZIP)", layout="wide", page_icon="📦")

# --- CẤU HÌNH API ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        api_key = st.sidebar.text_input("Nhập Google API Key:", type="password")

    if api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error(f"Lỗi cấu hình: {e}")

# --- CÁC HÀM XỬ LÝ ---
def doc_pdf_tu_bytes(file_bytes):
    """Đọc PDF từ dữ liệu thô (dùng cho cả file lẻ và file trong zip)"""
    try:
        reader = PdfReader(file_bytes)
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t: text += t + "\n"
        return text
    except: return ""

def lay_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("[")
    e = text.rfind("]") + 1
    return text[s:e] if s != -1 and e != -1 else text

def lay_dot_code(text):
    text = text.replace("```dot", "").replace("```graphviz", "").replace("```", "").strip()
    s = text.find("digraph")
    if s != -1: return text[s:]
    return text

# --- GIAO DIỆN CHÍNH ---
st.title("📦 Hệ Thống Ôn Tập (Hỗ trợ file nén ZIP)")

with st.sidebar:
    st.header("📂 Nạp tài liệu")
    st.info("Mẹo: Nén cả thư mục thành file .zip để tải lên 1 lần!")
    
    # Cho phép chọn cả file PDF và file ZIP
    uploaded_files = st.file_uploader("Tải file PDF hoặc ZIP:", type=['pdf', 'zip'], accept_multiple_files=True)
    
    if uploaded_files:
        if st.button("🔄 Xử lý tài liệu"):
            with st.spinner("Đang giải nén và đọc file..."):
                noi_dung_tong = ""
                ds_ten = []
                
                # Thanh tiến trình
                bar = st.progress(0)
                total_files = len(uploaded_files)
                
                for i, file in enumerate(uploaded_files):
                    # TRƯỜNG HỢP 1: LÀ FILE ZIP
                    if file.name.lower().endswith('.zip'):
                        try:
                            with zipfile.ZipFile(file) as z:
                                # Lọc lấy các file PDF trong zip
                                pdf_files = [f for f in z.namelist() if f.lower().endswith('.pdf') and not f.startswith('__MACOSX')]
                                
                                for pdf_name in pdf_files:
                                    with z.open(pdf_name) as pdf_data:
                                        # Đọc nội dung PDF từ trong zip
                                        txt = doc_pdf_tu_bytes(pdf_data)
                                        if txt:
                                            noi_dung_tong += f"\n--- FILE ZIP/{pdf_name} ---\n{txt}\n"
                                            ds_ten.append(f"📦 {pdf_name}")
                        except Exception as e:
                            st.error(f"Lỗi đọc zip {file.name}: {e}")

                    # TRƯỜNG HỢP 2: LÀ FILE PDF THƯỜNG
                    elif file.name.lower().endswith('.pdf'):
                        txt = doc_pdf_tu_bytes(file)
                        if txt:
                            noi_dung_tong += f"\n--- FILE: {file.name} ---\n{txt}\n"
                            ds_ten.append(file.name)
                    
                    # Cập nhật tiến trình
                    bar.progress((i + 1) / total_files)
                
                bar.empty()
                
                if ds_ten:
                    st.session_state['noi_dung'] = noi_dung_tong
                    st.session_state['ds_file'] = ds_ten
                    st.success(f"✅ Đã đọc xong {len(ds_ten)} tài liệu!")
                else:
                    st.warning("Không tìm thấy nội dung PDF nào.")

    if 'ds_file' in st.session_state:
        st.write("---")
        st.caption("Danh sách file đã nạp:")
        for f in st.session_state['ds_file']:
            st.code(f, language="text")

# --- PHẦN CHỨC NĂNG (CHAT, QUIZ, FLASHCARDS, MINDMAP) ---
# (Phần này giữ nguyên logic cũ, chỉ copy lại để code hoàn chỉnh)

if 'noi_dung' in st.session_state:
    t1, t2, t3, t4 = st.tabs(["💬 Chat", "📝 Trắc Nghiệm", "🗂️ Flashcards", "🧠 Sơ Đồ Tư Duy"])

    # 1. CHAT
    with t1:
        if "msg" not in st.session_state: st.session_state.msg = []
        for m in st.session_state.msg: 
            with st.chat_message(m["role"]): st.markdown(m["content"])
        if p := st.chat_input("Hỏi gì đó..."):
            st.session_state.msg.append({"role": "user", "content": p})
            with st.chat_message("user"): st.markdown(p)
            with st.chat_message("assistant"):
                try:
                    res = model.generate_content(f"Dựa vào tài liệu:\n{st.session_state['noi_dung']}\nTrả lời: {p}")
                    st.markdown(res.text)
                    st.session_state.msg.append({"role": "assistant", "content": res.text})
                except: st.error("Lỗi API.")

    # 2. QUIZ
    with t2:
        c1, c2 = st.columns([1,3])
        sl = c1.number_input("Số câu", 1, 50, 5)
        if c2.button("🚀 Tạo Đề"):
            with st.spinner("Đang tạo..."):
                try:
                    p = f"Tạo {sl} câu trắc nghiệm JSON list: [{{'question':'...','options':['A...'],'correct':'A','explain':'...'}}]"
                    res = model.generate_content(f"{p}\nNội dung: {st.session_state['noi_dung']}")
                    st.session_state['quiz'] = json.loads(lay_json(res.text))
                except: st.error("Lỗi định dạng.")
        if 'quiz' in st.session_state:
            score = 0
            for i, q in enumerate(st.session_state['quiz']):
                st.divider()
                st.markdown(f"**{i+1}.** {q['question']}")
                ch = st.radio("Chọn:", q['options'], key=f"q{i}", index=None)
                if ch:
                    if ch[0] == q['correct'][0]:
                        st.success("Đúng!")
                        score+=1
                    else: st.error(f"Sai. Đáp án: {q['correct']}")
                    with st.expander("Giải thích"): st.write(q['explain'])
            st.info(f"Điểm: {score}/{len(st.session_state['quiz'])}")

    # 3. FLASHCARDS
    with t3:
        if st.button("Tạo Flashcards"):
            with st.spinner("Đang tạo..."):
                try:
                    p = "Tạo 10 thẻ JSON list: [{'q':'...','a':'...'}]"
                    res = model.generate_content(f"{p}\nNội dung: {st.session_state['noi_dung']}")
                    st.session_state['fc'] = json.loads(lay_json(res.text))
                except: st.error("Lỗi tạo thẻ.")
        if 'fc' in st.session_state:
            for c in st.session_state['fc']:
                with st.expander(c.get('q','?')): st.info(c.get('a','!'))

    # 4. MINDMAP
    with t4:
        st.subheader("Bản đồ kiến thức")
        if st.button("🎨 Vẽ Sơ Đồ"):
            with st.spinner("Đang vẽ..."):
                try:
                    p = """
                    Tóm tắt thành Sơ đồ tư duy (Mind Map).
                    Output format: chỉ mã Graphviz DOT (trong ```dot ... ```).
                    Dùng digraph G { rankdir="LR"; node [shape=box, style=filled, fillcolor="#E8F5E9", fontname="Arial"]; ... }
                    """
                    res = model.generate_content(f"{p}\nNội dung: {st.session_state['noi_dung']}")
                    st.session_state['map'] = lay_dot_code(res.text)
                except: st.error("Lỗi vẽ hình.")
        if 'map' in st.session_state:
            try: st.graphviz_chart(st.session_state['map'])
            except: st.error("Mã hình lỗi.")
else:
    st.info("👈 Nén tài liệu thành file ZIP rồi tải lên.")