import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import json
import zipfile
import pandas as pd
from docx import Document
from pptx import Presentation
import io

# Cấu hình trang
st.set_page_config(page_title="Hệ Thống Hỗ Trợ Học Tập", layout="wide", page_icon="📚")

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

# ======================================================
# CÁC HÀM ĐỌC FILE (Word, Excel, PPT, PDF)
# ======================================================

def doc_pdf(file_bytes):
    try:
        reader = PdfReader(file_bytes)
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t: text += t + "\n"
        return text
    except: return ""

def doc_word(file_bytes):
    """Đọc file .docx"""
    try:
        doc = Document(file_bytes)
        text = []
        for para in doc.paragraphs:
            text.append(para.text)
        return "\n".join(text)
    except: return ""

def doc_pptx(file_bytes):
    """Đọc file .pptx (PowerPoint)"""
    try:
        prs = Presentation(file_bytes)
        text = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text.append(shape.text)
        return "\n".join(text)
    except: return ""

def doc_excel(file_bytes):
    """Đọc file .xlsx (Excel) - Chuyển toàn bộ bảng thành text"""
    try:
        df = pd.read_excel(file_bytes)
        return df.to_string() # Chuyển bảng số liệu thành dạng chữ để AI đọc
    except: return ""

def xu_ly_file_upload(file_obj, ten_file):
    """Hàm điều phối: Nhìn đuôi file để gọi hàm đọc đúng"""
    ten_file = ten_file.lower()
    noi_dung = ""
    
    if ten_file.endswith('.pdf'):
        noi_dung = doc_pdf(file_obj)
    elif ten_file.endswith('.docx'):
        noi_dung = doc_word(file_obj)
    elif ten_file.endswith('.pptx'):
        noi_dung = doc_pptx(file_obj)
    elif ten_file.endswith('.xlsx') or ten_file.endswith('.xls'):
        noi_dung = doc_excel(file_obj)
        
    return noi_dung

# --- CÁC HÀM PHỤ TRỢ ---
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

# ======================================================
# GIAO DIỆN CHÍNH
# ======================================================
st.title("📚 Hệ Thống Học Tập Tích Hợp Gemini 2.0 Flash")

with st.sidebar:
    st.header("📂 Nạp tài liệu")
    st.caption("Hỗ trợ: PDF, Word, Excel, PowerPoint và ZIP")
    
    # Cho phép chọn nhiều loại file
    uploaded_files = st.file_uploader("Tải file lên:", 
                                      type=['pdf', 'docx', 'pptx', 'xlsx', 'zip'], 
                                      accept_multiple_files=True)
    
    if uploaded_files:
        if st.button("🔄 Xử lý tài liệu"):
            with st.spinner("Đang đọc và phân tích đa định dạng..."):
                noi_dung_tong = ""
                ds_ten = []
                
                bar = st.progress(0)
                total_files = len(uploaded_files)
                
                for i, file in enumerate(uploaded_files):
                    # TRƯỜNG HỢP 1: LÀ FILE ZIP
                    if file.name.lower().endswith('.zip'):
                        try:
                            with zipfile.ZipFile(file) as z:
                                # Lấy danh sách file trong zip
                                all_files = z.namelist()
                                for sub_file in all_files:
                                    # Bỏ qua file hệ thống rác của Mac/Windows
                                    if not sub_file.startswith('__') and '.' in sub_file:
                                        with z.open(sub_file) as f_data:
                                            # Đọc dữ liệu binary vào bộ nhớ đệm
                                            bytes_io = io.BytesIO(f_data.read())
                                            txt = xu_ly_file_upload(bytes_io, sub_file)
                                            if txt:
                                                noi_dung_tong += f"\n--- FILE ZIP/{sub_file} ---\n{txt}\n"
                                                ds_ten.append(f"📦 {sub_file}")
                        except Exception as e:
                            st.error(f"Lỗi zip {file.name}: {e}")

                    # TRƯỜNG HỢP 2: LÀ FILE THƯỜNG (PDF, DOCX, PPTX...)
                    else:
                        txt = xu_ly_file_upload(file, file.name)
                        if txt:
                            noi_dung_tong += f"\n--- FILE: {file.name} ---\n{txt}\n"
                            ds_ten.append(file.name)
                    
                    bar.progress((i + 1) / total_files)
                
                bar.empty()
                
                if ds_ten:
                    st.session_state['noi_dung'] = noi_dung_tong
                    st.session_state['ds_file'] = ds_ten
                    st.success(f"✅ Đã xử lý xong {len(ds_ten)} tài liệu!")
                else:
                    st.warning("Không tìm thấy file nào.")

    if 'ds_file' in st.session_state:
        st.write("---")
        st.caption("Danh sách file đã nạp:")
        for f in st.session_state['ds_file']:
            st.code(f, language="text")

# --- PHẦN CHỨC NĂNG (GIỮ NGUYÊN NHƯ CŨ) ---
if 'noi_dung' in st.session_state:
    t1, t2, t3, t4 = st.tabs(["💬 Chat", "📝 Trắc Nghiệm", "🗂️ Flashcards", "🧠 Sơ Đồ Tư Duy"])

    # 1. CHAT
    with t1:
        if "msg" not in st.session_state: st.session_state.msg = []
        # -- Hiển thị lịch sử chat 
        for m in st.session_state.msg: 
            with st.chat_message(m["role"]): st.markdown(m["content"])
        st.caption("⚠️ **Lưu ý:** AI không biết thông tin ngoài lề, chỉ cố định trong file.")
        # -- Xử lý nhập liệu
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
    st.info("👈 Tải file PDF, Word, Excel, PowerPoint hoặc ZIP lên để học!")