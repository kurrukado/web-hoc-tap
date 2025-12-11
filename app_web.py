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
                    st.session_state.msg.append({"role": "assistant", "content": res.text})
                except: st.error("Lỗi API.")

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

    # TAB 4: SƠ ĐỒ TƯ DUY (TÍNH NĂNG MỚI)
    with tab4:
        st.subheader("Hệ thống hóa kiến thức bằng hình ảnh")
        st.info("Mẹo: Nếu sơ đồ quá rối, hãy yêu cầu AI vẽ lại đơn giản hơn.")
        
        col_map1, col_map2 = st.columns([1, 4])
        with col_map1:
            style = st.selectbox("Chọn kiểu:", ["Top-Down (Trên xuống)", "Left-Right (Trái qua phải)"])
        
        with col_map2:
            if st.button("🎨 Vẽ Sơ Đồ Ngay"):
                with st.spinner("Đang phân tích và vẽ sơ đồ..."):
                    rankdir = "TB" if style == "Top-Down (Trên xuống)" else "LR"
                    
                    # Prompt đặc biệt để tạo mã Graphviz
                    prompt_map = f"""
                    Hãy tóm tắt nội dung bài học thành một Sơ đồ tư duy (Mind Map).
                    Yêu cầu Output: Chỉ trả về mã Graphviz DOT (nằm trong ```dot ... ```).
                    
                    Cấu hình Graphviz:
                    - Sử dụng `digraph G {{ ... }}`
                    - Thêm thuộc tính: `rankdir="{rankdir}"; node [shape=box, style=filled, fillcolor="#E8F5E9", fontname="Arial"];`
                    - Nội dung phải Tiếng Việt.
                    - Root node là chủ đề chính của tài liệu.
                    - Các nhánh con là các ý chính.
                    - Giữ cấu trúc đơn giản, dễ nhìn.
                    """
                    
                    try:
                        res = model.generate_content(f"{prompt_map}\n\nNội dung: {st.session_state['noi_dung']}")
                        dot_code = lay_dot_code(res.text)
                        
                        # Lưu vào session để không bị mất khi đổi tab
                        st.session_state['mindmap_code'] = dot_code
                    except Exception as e:
                        st.error(f"Không vẽ được sơ đồ: {e}")

        # Hiển thị sơ đồ
        if 'mindmap_code' in st.session_state:
            try:
                st.graphviz_chart(st.session_state['mindmap_code'])
            except Exception as e:
                st.error("Lỗi hiển thị hình ảnh. AI đã tạo mã lỗi.")
                with st.expander("Xem mã lỗi"):
                    st.code(st.session_state['mindmap_code'])

else:
    st.info("👈 Tải file PDF lên để bắt đầu.")