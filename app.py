import streamlit as st
import numpy as np
import cv2
import os
import zxingcpp
from PIL import Image
from pyzbar.pyzbar import decode as pyzbar_decode
from docxtpl import DocxTemplate
from io import BytesIO

st.set_page_config(page_title="Tạo Sơ Yếu Lý Lịch từ CCCD", layout="centered")
st.title("Trích xuất CCCD & Xuất Sơ Yếu Lý Lịch")

# Khởi tạo session state
for key in ["cccd", "name", "dob", "gender", "address", "issue_date"]:
    if key not in st.session_state:
        st.session_state[key] = ""

# Hàm giải mã tiếng Việt chuẩn từ chuỗi byte
def decode_vietnamese(raw_bytes):
    try:
        return raw_bytes.decode('utf-8')
    except Exception:
        try:
            return raw_bytes.decode('latin1').encode('raw_unicode_escape').decode('utf-8')
        except Exception:
            return raw_bytes.decode('utf-8', errors='ignore')

# Hàm quét QR đa tầng (Thử nhiều thuật toán xử lý ảnh)
def scan_qr_code(img_np):
    # 1. Thử zxingcpp trên ảnh gốc
    results = zxingcpp.read_barcodes(img_np)
    if results:
        return results[0].text

    # 2. Thử pyzbar trên ảnh gốc
    pyz_res = pyzbar_decode(img_np)
    if pyz_res:
        return decode_vietnamese(pyz_res[0].data)

    # 3. Chuyển ảnh sang xám (Grayscale)
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    
    results = zxingcpp.read_barcodes(gray)
    if results:
        return results[0].text
    
    pyz_res = pyzbar_decode(gray)
    if pyz_res:
        return decode_vietnamese(pyz_res[0].data)

    # 4. Phóng to ảnh x2 để tăng chi tiết QR
    resized = cv2.resize(gray, (0, 0), fx=2, fy=2)
    results = zxingcpp.read_barcodes(resized)
    if results:
        return results[0].text

    pyz_res = pyzbar_decode(resized)
    if pyz_res:
        return decode_vietnamese(pyz_res[0].data)

    # 5. Tăng độ tương phản (Thresholding)
    _, thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY)
    results = zxingcpp.read_barcodes(thresh)
    if results:
        return results[0].text

    pyz_res = pyzbar_decode(thresh)
    if pyz_res:
        return decode_vietnamese(pyz_res[0].data)

    return None

# Chọn phương thức nhập ảnh
source_choice = st.radio("Chọn phương thức nhập ảnh:", ["Tải ảnh từ máy", "Chụp ảnh trực tiếp"], horizontal=True)

img_file = None
if source_choice == "Tải ảnh từ máy":
    img_file = st.file_uploader("Chọn ảnh CCCD từ thiết bị", type=["jpg", "jpeg", "png"])
else:
    img_file = st.camera_input("Chụp ảnh CCCD")

if img_file is not None:
    image = Image.open(img_file)
    img_array = np.array(image)

    # Quét QR bằng hàm xử lý đa tầng
    qr_text = scan_qr_code(img_array)

    if qr_text:
        fields = qr_text.split("|")
        
        if len(fields) >= 6:
            st.session_state["cccd"] = fields[0].strip()
            st.session_state["name"] = fields[2].strip()
            
            dob_raw = fields[3].strip()
            st.session_state["dob"] = f"{dob_raw[:2]}/{dob_raw[2:4]}/{dob_raw[4:]}" if len(dob_raw) == 8 else dob_raw
            
            st.session_state["gender"] = fields[4].strip()
            st.session_state["address"] = fields[5].strip()
            
            if len(fields) >= 7:
                issue_raw = fields[6].strip()
                st.session_state["issue_date"] = f"{issue_raw[:2]}/{issue_raw[2:4]}/{issue_raw[4:]}" if len(issue_raw) == 8 else issue_raw

            st.success("✅ Đã nhận diện thông tin tiếng Việt thành công!")
        else:
            st.warning("Đã quét thấy mã QR nhưng cấu trúc dữ liệu không đúng chuẩn CCCD.")
    else:
        st.error("Không tìm thấy mã QR trên ảnh. Vui lòng căn chụp rõ nét mã QR ở góc trên bên phải CCCD.")

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

# Xuất file Word mẫu
template_path = "mau_so_yeu_ly_lich.docx"

if not os.path.exists(template_path):
    st.error(f"⚠️ Không tìm thấy file mẫu `{template_path}` trên GitHub.")
else:
    context = {
        "HO_TEN": name,
        "SO_CCCD": cccd,
        "NGAY_SINH": dob,
        "GIOI_TINH": gender,
        "DIA_CHI": address,
        "NGAY_CAP": issue_date
    }

    doc = DocxTemplate(template_path)
    doc.render(context)
    
    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)

    st.download_button(
        label="🚀 Xuất file Sơ Yếu Lý Lịch (.docx)",
        data=bio,
        file_name=f"So_Yeu_Ly_Lich_{cccd if cccd else 'CCCD'}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
