import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import json

# Cấu hình trang
st.set_page_config(page_title="AI Ôn Tập Online", layout="wide", page_icon="🌐")

# --- QUẢN LÝ API KEY AN TOÀN TRÊN CLOUD ---
# Khi chạy trên máy cá nhân, nó sẽ tìm trong file .streamlit/secrets.toml
# Khi chạy trên Cloud, ta sẽ cấu hình trong phần cài đặt của web
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        # Nếu chạy local mà chưa cài secrets, hiện ô nhập tạm
        api_key = st.sidebar.text_input("Nhập Google API Key:", type="password")

    if api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error(f"Lỗi cấu hình: {e}")

# --- CÁC HÀM XỬ LÝ (Giữ nguyên logic cũ) ---
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

# --- GIAO DIỆN CHÍNH ---
st.title("🌐 Hệ Thống Ôn Tập Mọi Lúc Mọi Nơi")

with st.sidebar:
    st.header("📂 Nạp tài liệu")
    # Cho phép chọn NHIỀU FILE cùng lúc
    uploaded_files = st.file_uploader("Chọn tất cả file PDF của bạn:", type=['pdf'], accept_multiple_files=True)
    
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
        st.write("📄 **File đang học:**")
        for f in st.session_state['ds_file']:
            st.caption(f"- {f}")

# --- PHẦN CHỨC NĂNG (CHAT, QUIZ, CARD) ---
if 'noi_dung' in st.session_state:
    tab1, tab2, tab3 = st.tabs(["💬 Chat", "📝 Trắc Nghiệm", "🗂️ Flashcards"])

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
                    st.session_state.msg.append({"role": "assistant", "content": res.text})
                except: st.error("Chưa có API Key hoặc lỗi mạng.")

    # TAB 2: QUIZ
    with tab2:
        col1, col2 = st.columns([1,3])
        sl = col1.number_input("Số câu", 1, 50, 5)
        if col2.button("Tạo Đề"):
            with st.spinner("Đang tạo..."):
                try:
                    p = f"Tạo {sl} câu trắc nghiệm JSON list: [{{'question':'...','options':['A...'],'correct':'A','explain':'...'}}]"
                    res = model.generate_content(f"{p}\nNội dung: {st.session_state['noi_dung']}")
                    st.session_state['quiz'] = json.loads(lay_json(res.text))
                except: st.error("Thử lại nhé!")
        
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

    # TAB 3: FLASHCARDS
    with tab3:
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
else:
    st.info("👈 Tải file PDF lên để bắt đầu.")