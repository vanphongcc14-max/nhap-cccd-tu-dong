import streamlit as st
import numpy as np
import cv2
import zxingcpp
import pandas as pd
from PIL import Image
from pyzbar.pyzbar import decode as pyzbar_decode

# Thiết lập trang web chuẩn mobile & desktop
st.set_page_config(page_title="Tra cứu thông tin CCCD", page_icon="🪪", layout="centered")

# CSS giao diện tùy chỉnh cho bảng hiển thị đẹp trên mobile/desktop
st.markdown("""
    <style>
    .main-header {
        text-align: center;
        color: #1E3A8A;
        font-weight: 700;
        margin-bottom: 20px;
    }
    .stDataFrame {
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h2 class='main-header'>🪪 TRÁCH XUẤT THÔNG TIN CCCD</h2>", unsafe_allow_html=True)

# Khởi tạo thông tin lưu trữ
if "info_dict" not in st.session_state:
    st.session_state["info_dict"] = {
        "Họ và tên": "",
        "Số CCCD": "",
        "Nơi thường trú / Địa chỉ": ""
    }

# Hàm giải mã tiếng Việt từ QR CCCD
def decode_vietnamese(raw_bytes):
    try:
        return raw_bytes.decode('utf-8')
    except Exception:
        try:
            return raw_bytes.decode('latin1').encode('raw_unicode_escape').decode('utf-8')
        except Exception:
            return raw_bytes.decode('utf-8', errors='ignore')

# Hàm quét QR đa tầng hỗ trợ đọc tiếng Việt chuẩn
def scan_qr_code(img_np):
    # 1. Quét bằng zxingcpp ảnh gốc
    results = zxingcpp.read_barcodes(img_np)
    if results:
        return results[0].text

    # 2. Quét bằng pyzbar ảnh gốc
    pyz_res = pyzbar_decode(img_np)
    if pyz_res:
        return decode_vietnamese(pyz_res[0].data)

    # 3. Chuyển ảnh xám
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    results = zxingcpp.read_barcodes(gray)
    if results:
        return results[0].text
    
    pyz_res = pyzbar_decode(gray)
    if pyz_res:
        return decode_vietnamese(pyz_res[0].data)

    # 4. Phóng to ảnh x2
    resized = cv2.resize(gray, (0, 0), fx=2, fy=2)
    results = zxingcpp.read_barcodes(resized)
    if results:
        return results[0].text

    pyz_res = pyzbar_decode(resized)
    if pyz_res:
        return decode_vietnamese(pyz_res[0].data)

    return None

# Tải hoặc chụp ảnh
source_choice = st.radio("Phương thức nhập ảnh:", ["📷 Chụp ảnh trực tiếp", "📁 Tải ảnh từ máy"], horizontal=True)

img_file = None
if source_choice == "📷 Chụp ảnh trực tiếp":
    img_file = st.camera_input("Chụp ảnh mặt trước CCCD")
else:
    img_file = st.file_uploader("Chọn ảnh CCCD từ thư viện", type=["jpg", "jpeg", "png"])

if img_file is not None:
    image = Image.open(img_file)
    img_array = np.array(image)

    with st.spinner("Đang quét mã QR..."):
        qr_text = scan_qr_code(img_array)

    if qr_text:
        fields = qr_text.split("|")
        
        if len(fields) >= 6:
            st.session_state["info_dict"] = {
                "Họ và tên": fields[2].strip(),
                "Số CCCD": fields[0].strip(),
                "Nơi thường trú / Địa chỉ": fields[5].strip()
            }
            st.success("✅ Đã trích xuất thông tin thành công!")
        else:
            st.warning("Đã quét thấy mã QR nhưng cấu trúc dữ liệu không chuẩn CCCD.")
    else:
        st.error("Không tìm thấy mã QR trên ảnh. Vui lòng căn chụp rõ nét góc trên bên phải CCCD.")

# ---------------- HIỂN THỊ BẢNG THÔNG TIN ----------------
st.write("---")
st.subheader("📋 BẢNG THÔNG TIN CÁ NHÂN")

# Chuyển đổi dữ liệu thành Bảng (DataFrame)
df = pd.DataFrame(
    list(st.session_state["info_dict"].items()), 
    columns=["Mục thông tin", "Nội dung chi tiết"]
)

# Hiển thị dạng Bảng dữ liệu tương thích mobile & PC
st.table(df)
