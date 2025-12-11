import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import json

# Cấu hình trang
st.set_page_config(page_title="AI Ôn Tập Online", layout="wide", page_icon="🧠")

# --- CẤU HÌNH API KEY ---
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
def doc_pdf(file_upload):
    try:
        reader = PdfReader(file_upload)
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
    """Làm sạch mã Graphviz DOT từ phản hồi của AI"""
    text = text.replace("```dot", "").replace("```graphviz", "").replace("```", "").strip()
    # Tìm điểm bắt đầu digraph
    s = text.find("digraph")
    if s != -1:
        return text[s:]
    return text

# --- GIAO DIỆN CHÍNH ---
st.title("🧠 Hệ Thống Ôn Tập Thông Minh")

with st.sidebar:
    st.header("📂 Nạp tài liệu")
    uploaded_files = st.file_uploader("Chọn file PDF:", type=['pdf'], accept_multiple_files=True)
    
    if uploaded_files:
        if st.button("🔄 Xử lý tài liệu"):
            with st.spinner("Đang đọc file..."):
                noi_dung_tong = ""
                ds_ten = []
                for uploaded_file in uploaded_files:
                    txt = doc_pdf(uploaded_file)
                    if txt:
                        noi_dung_tong += f"\n--- FILE: {uploaded_file.name} ---\n{txt}\n"
                        ds_ten.append(uploaded_file.name)
                
                st.session_state['noi_dung'] = noi_dung_tong
                st.session_state['ds_file'] = ds_ten
                st.success(f"Đã đọc xong {len(ds_ten)} file!")

    if 'ds_file' in st.session_state:
        st.write("---")
        st.caption("Đang học từ:")
        for f in st.session_state['ds_file']:
            st.write(f"- {f}")

# --- PHẦN CHỨC NĂNG ---
if 'noi_dung' in st.session_state:
    # Thêm Tab 4: Sơ Đồ Tư Duy
    tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat", "📝 Trắc Nghiệm", "🗂️ Flashcards", "🧠 Sơ Đồ Tư Duy"])

    # TAB 1: CHAT
    with tab1:
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
                    st.session_