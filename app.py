import streamlit as st
import numpy as np
import pandas as pd
import re
import easyocr
from PIL import Image

# Thiết lập trang web chuẩn mobile & desktop
st.set_page_config(page_title="Đọc văn bản & Trích xuất thông tin", page_icon="📝", layout="centered")

st.markdown("""
    <style>
    .main-header {
        text-align: center;
        color: #1E3A8A;
        font-weight: 700;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h2 class='main-header'>📝 TRÍCH XUẤT CHỮ TỪ VĂN BẢN (OCR)</h2>", unsafe_allow_html=True)

# Khởi tạo EasyOCR cho tiếng Việt (chỉ tải mô hình 1 lần)
@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['vi', 'en'], gpu=False)

reader = load_ocr_reader()

# Khởi tạo thông tin mặc định
if "info_dict" not in st.session_state:
    st.session_state["info_dict"] = {
        "Họ và tên": "",
        "Số CCCD": "",
        "Nơi thường trú / Địa chỉ": ""
    }
if "full_raw_text" not in st.session_state:
    st.session_state["full_raw_text"] = ""

# Hàm bóc tách thông tin bằng biểu thức chính quy (Regex) từ đoạn chữ quét được
def parse_text_info(text_list):
    full_text = " ".join(text_list)
    st.session_state["full_raw_text"] = "\n".join(text_list)
    
    # 1. Tìm số CCCD / CMND (chuỗi 9 hoặc 12 chữ số)
    cccd_match = re.search(r'\b\d{12}\b|\b\d{9}\b', full_text)
    cccd = cccd_match.group(0) if cccd_match else ""

    # 2. Tìm Họ và tên (Thường đứng sau từ khóa Họ tên / Name)
    name = ""
    for i, line in enumerate(text_list):
        if re.search(r'(họ\s*và\s*tên|họ\s*tên|full\s*name)', line, re.IGNORECASE):
            # Lấy dòng kế tiếp hoặc cùng dòng
            if i + 1 < len(text_list):
                name = text_list[i+1].strip()
            else:
                name = re.sub(r'.*?(họ\s*và\s*tên|họ\s*tên|full\s*name)[:\s]*', '', line, flags=re.IGNORECASE).strip()
            break

    # 3. Tìm Địa chỉ / Nơi thường trú
    address = ""
    for i, line in enumerate(text_list):
        if re.search(r'(nơi\s*thường\s*trú|địa\s*chỉ|thường\s*trú|address)', line, re.IGNORECASE):
            addr_parts = text_list[i+1:i+3] if i + 1 < len(text_list) else [line]
            address = " ".join(addr_parts).strip()
            break

    return {
        "Họ và tên": name if name else "Không xác định",
        "Số CCCD": cccd if cccd else "Không xác định",
        "Nơi thường trú / Địa chỉ": address if address else "Không xác định"
    }

# Chọn nguồn ảnh
source_choice = st.radio("Chọn phương thức nhập ảnh:", ["📷 Chụp ảnh trực tiếp", "📁 Tải ảnh từ máy"], horizontal=True)

img_file = None
if source_choice == "📷 Chụp ảnh trực tiếp":
    img_file = st.camera_input("Chụp ảnh văn bản/giấy tờ")
else:
    img_file = st.file_uploader("Chọn ảnh văn bản từ thiết bị", type=["jpg", "jpeg", "png"])

if img_file is not None:
    image = Image.open(img_file)
    img_np = np.array(image)

    with st.spinner("Đang quét và đọc chữ từ ảnh (OCR)..."):
        # Đọc chữ từ ảnh
        ocr_results = reader.readtext(img_np, detail=0)
        
        if ocr_results:
            st.session_state["info_dict"] = parse_text_info(ocr_results)
            st.success("✅ Đã nhận diện chữ và trích xuất thông tin thành công!")
        else:
            st.warning("Không tìm thấy ký tự chữ nào trên hình ảnh.")

# ---------------- HIỂN THỊ BẢNG THÔNG TIN ----------------
st.write("---")
st.subheader("📋 BẢNG THÔNG TIN TRÍCH XUẤT")

# Chuyển đổi thành Bảng dữ liệu
df = pd.DataFrame(
    list(st.session_state["info_dict"].items()), 
    columns=["Mục thông tin", "Nội dung chi tiết"]
)

# Hiển thị dạng bảng tương thích Mobile & PC
st.table(df)

# Mở rộng: Hiển thị toàn bộ đoạn chữ thô đọc được từ ảnh
with st.expander("🔍 Xem toàn bộ chữ đọc được từ ảnh"):
    st.text_area("Nội dung chữ thô (OCR):", value=st.session_state["full_raw_text"], height=200)
