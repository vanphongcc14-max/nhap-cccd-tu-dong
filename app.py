import streamlit as st
import cv2
import numpy as np
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

# Hàm giải mã chuỗi CCCD tránh lỗi font chữ Trung Quốc/ký tự lạ
def parse_cccd_raw(raw_bytes):
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = raw_bytes.decode("latin1").encode("latin1").decode("utf-8", errors="ignore")
        except Exception:
            text = raw_bytes.decode("utf-8", errors="ignore")
    return text

# Tùy chọn nguồn ảnh
source_choice = st.radio("Chọn phương thức nhập ảnh:", ["Tải ảnh từ máy", "Chụp ảnh trực tiếp"], horizontal=True)

img_file = None
if source_choice == "Tải ảnh từ máy":
    img_file = st.file_uploader("Chọn ảnh CCCD từ thiết bị", type=["jpg", "jpeg", "png"])
else:
    img_file = st.camera_input("Chụp ảnh CCCD")

if img_file is not None:
    image = Image.open(img_file)
    img_array = np.array(image)

    # Đọc mã QR
    decoded_objects = decode(img_array)
    if decoded_objects:
        raw_data = decoded_objects[0].data
        qr_text = parse_cccd_raw(raw_data)

        # Tách dữ liệu qua dấu |
        fields = qr_text.split("|")
        
        if len(fields) >= 6:
            st.session_state["cccd"] = fields[0].strip()
            st.session_state["name"] = fields[2].strip()
            
            # Xử lý Ngày sinh (DDMMYYYY -> DD/MM/YYYY)
            dob_raw = fields[3].strip()
            st.session_state["dob"] = f"{dob_raw[:2]}/{dob_raw[2:4]}/{dob_raw[4:]}" if len(dob_raw) == 8 else dob_raw
            
            st.session_state["gender"] = fields[4].strip()
            st.session_state["address"] = fields[5].strip()
            
            # Xử lý Ngày cấp (DDMMYYYY) nếu có
            if len(fields) >= 7:
                issue_raw = fields[6].strip()
                st.session_state["issue_date"] = f"{issue_raw[:2]}/{issue_raw[2:4]}/{issue_raw[4:]}" if len(issue_raw) == 8 else issue_raw

            st.success("✅ Đã nhận diện thông tin tiếng Việt thành công!")
        else:
            st.warning("Đã quét thấy mã QR nhưng cấu trúc dữ liệu không đúng chuẩn CCCD.")
    else:
        st.error("Không tìm thấy mã QR trên ảnh. Vui lòng căn chụp rõ nét hơn.")

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

# Thay thế các biến {{ ... }} trong file Word mẫu mau_so_yeu_ly_lich.docx
def fill_template(template_path, replacements):
    doc = Document(template_path)
    
    def replace_text_in_paragraph(p):
        for key, val in replacements.items():
            if key in p.text:
                for run in p.runs:
                    if key in run.text:
                        run.text = run.text.replace(key, str(val))
                if key in p.text:
                    p.text = p.text.replace(key, str(val))

    for p in doc.paragraphs:
        replace_text_in_paragraph(p)
        
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    replace_text_in_paragraph(p)

    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

replacements = {
    "{{ HO_TEN }}": name,
    "{{ SO_CCCD }}": cccd,
    "{{ NGAY_SINH }}": dob,
    "{{ GIOI_TINH }}": gender,
    "{{ DIA_CHI }}": address,
    "{{ NGAY_CAP }}": issue_date
}

try:
    docx_file = fill_template("mau_so_yeu_ly_lich.docx", replacements)
    st.download_button(
        label="🚀 Xuất file Sơ Yếu Lý Lịch (.docx)",
        data=docx_file,
        file_name=f"So_Yeu_Ly_Lich_{cccd if cccd else 'CCCD'}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
except Exception as e:
    st.error("Không tìm thấy file mẫu `mau_so_yeu_ly_lich.docx` trong thư mục. Vui lòng kiểm tra lại trên GitHub!")
