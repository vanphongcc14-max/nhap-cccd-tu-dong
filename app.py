import streamlit as st
import numpy as np
import cv2
from PIL import Image
from pyzbar.pyzbar import decode
from docx import Document
from io import BytesIO

st.set_page_config(page_title="Tạo Sơ Yếu Lý Lịch từ CCCD", layout="centered")
st.title("Trích xuất CCCD & Xuất Sơ Yếu Lý Lịch")

# Khởi tạo session state
for key in ["cccd", "name", "dob", "gender", "address", "issue_date"]:
    if key not in st.session_state:
        st.session_state[key] = ""

# Hàm giải mã chuỗi CCCD tránh lỗi font chữ
def parse_cccd_raw(raw_bytes):
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = raw_bytes.decode("latin1").encode("latin1").decode("utf-8", errors="ignore")
        except Exception:
            text = raw_bytes.decode("utf-8", errors="ignore")
    return text

# Hàm hỗ trợ xử lý ảnh để quét QR tốt hơn
def scan_qr_advanced(img_array):
    # 1. Thử đọc ảnh gốc
    decoded = decode(img_array)
    if decoded:
        return decoded
    
    # 2. Chuyển sang ảnh xám (Grayscale)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    decoded = decode(gray)
    if decoded:
        return decoded
        
    # 3. Tăng độ tương phản (Thresholding)
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    decoded = decode(thresh)
    if decoded:
        return decoded

    # 4. Phóng to ảnh (nếu mã QR quá nhỏ)
    resized = cv2.resize(gray, (0, 0), fx=2, fy=2)
    decoded = decode(resized)
    return decoded

# Chọn nguồn ảnh
source_choice = st.radio("Chọn phương thức nhập ảnh:", ["Tải ảnh từ máy", "Chụp ảnh trực tiếp"], horizontal=True)

img_file = None
if source_choice == "Tải ảnh từ máy":
    img_file = st.file_uploader("Chọn ảnh CCCD từ thiết bị", type=["jpg", "jpeg", "png"])
else:
    img_file = st.camera_input("Chụp ảnh CCCD")

if img_file is not None:
    image = Image.open(img_file)
    img_array = np.array(image)

    # Đọc mã QR với hàm xử lý nâng cao
    decoded_objects = scan_qr_advanced(img_array)
    if decoded_objects:
        raw_data = decoded_objects[0].data
        qr_text = parse_cccd_raw(raw_data)

        # Tách dữ liệu qua dấu |
        fields = qr_text.split("|")
        
        if len(fields) >= 6:
            st.session_state["cccd"] = fields[0].strip()
            st.session_state["name"] = fields[2].strip()
            
            # Xử lý Ngày sinh (DDMMYYYY)
            dob_raw = fields[3].strip()
            st.session_state["dob"] = f"{dob_raw[:2]}/{dob_raw[2:4]}/{dob_raw[4:]}" if len(dob_raw) == 8 else dob_raw
            
            st.session_state["gender"] = fields[4].strip()
            st.session_state["address"] = fields[5].strip()
            
            # Xử lý Ngày cấp (DDMMYYYY)
            if len(fields) >= 7:
                issue_raw = fields[6].strip()
                st.session_state["issue_date"] = f"{issue_raw[:2]}/{issue_raw[2:4]}/{issue_raw[4:]}" if len(issue_raw) == 8 else issue_raw

            st.success("✅ Đã nhận diện thông tin tiếng Việt thành công!")
        else:
            st.warning("Đã quét thấy mã QR nhưng cấu trúc dữ liệu không đúng chuẩn CCCD.")
    else:
        st.error("Không tìm thấy mã QR trên ảnh. Vui lòng di chuyển camera lại gần mã QR ở góc trên bên phải CCCD hoặc tải ảnh rõ nét hơn.")

# Form hiển thị và chỉnh sửa thông tin
st.subheader("Thông tin chi tiết")
with st.form("cccd_form"):
    cccd = st.text_input("Số CCCD", value=st.session_state["cccd"])
    name = st.text_input("Họ và tên", value=st.session_state["name"])
    dob = st.text_input("Ngày sinh (DD/MM/YYYY)", value=st.session_state["dob"])
    
    gender_options = ["Nam", "Nữ", "Khác"]
    curr_gender = st.session_state["gender"]
    g_idx = gender_options.index(curr_gender) if curr_gender in gender_options else 0
    gender = st.selectbox("Giới tính", options=gender_options, index=g_idx)
    
    address = st.text_input("Nơi thường trú / Địa chỉ", value=st.session_state["address"])
    issue_date = st.text_input("Ngày cấp CCCD", value=st.session_state["issue_date"])
    
    st.form_submit_button("Cập nhật lại form")

# Hàm tạo trực tiếp file Word .docx chuẩn
def create_docx(data):
    doc = Document()
    doc.add_heading("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", level=2)
    doc.add_paragraph("Độc lập - Tự do - Hạnh phúc").alignment = 1
    doc.add_heading("SƠ YẾU LÝ LỊCH", level=1)
    
    doc.add_paragraph(f"Họ và tên: {data['name']}")
    doc.add_paragraph(f"Ngày, tháng, năm sinh: {data['dob']}")
    doc.add_paragraph(f"Giới tính: {data['gender']}")
    doc.add_paragraph(f"Căn cước công dân số: {data['cccd']}")
    doc.add_paragraph(f"Cấp ngày: {data['issue_date']}, tại Cục Cảnh sát quản lý hành chính về trật tự xã hội")
    doc.add_paragraph(f"Thường trú: {data['address']}")
    
    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

user_data = {
    "cccd": cccd,
    "name": name,
    "dob": dob,
    "gender": gender,
    "address": address,
    "issue_date": issue_date
}

st.download_button(
    label="🚀 Xuất file Sơ Yếu Lý Lịch (.docx)",
    data=create_docx(user_data),
    file_name=f"So_Yeu_Ly_Lich_{cccd if cccd else 'CCCD'}.docx",
    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
