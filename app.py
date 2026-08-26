import streamlit as st
import numpy as np
import cv2
import pandas as pd
import re
import os
import json
from PIL import Image, ImageOps

st.set_page_config(page_title="Đọc & Lưu Văn Bản Giấy Tờ", page_icon="📄", layout="wide")

DB_FILE = "data_list.json"

# Hàm đọc/lưu dữ liệu dùng chung cho Mobile & PC
def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data_list = load_data()

# Dùng Tesseract OCR đọc chữ từ ảnh
try:
    import pytesseract
except ImportError:
    pytesseract = None

def extract_text_from_image(img):
    # Tự động xoay ảnh đúng chiều nếu ảnh bị ngược từ điện thoại
    img = ImageOps.exif_transpose(img)
    img_gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    
    # Tăng độ tương phản
    _, thresh = cv2.threshold(img_gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    if pytesseract:
        try:
            text = pytesseract.image_to_string(thresh, lang='vie+eng')
            return text
        except Exception:
            text = pytesseract.image_to_string(thresh)
            return text
    return ""

st.title("📄 CHỤP & BÓC TÁCH THÔNG TIN VĂN BẢN HÀNG LOẠT")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📸 1. Chụp văn bản / Hợp đồng")
    
    # Cho phép xoay ảnh nếu ảnh chụp bị ngược
    rotate_angle = st.selectbox("Xoay chiều ảnh (nếu bị ngược):", [0, 90, 180, 270], index=0)
    
    source_choice = st.radio("Nguồn ảnh:", ["📷 Chụp trực tiếp", "📁 Tải ảnh"], horizontal=True)

    img_file = None
    if source_choice == "📷 Chụp trực tiếp":
        img_file = st.camera_input("Chụp trang văn bản")
    else:
        img_file = st.file_uploader("Chọn ảnh văn bản từ thiết bị", type=["jpg", "jpeg", "png"])

    if img_file is not None:
        image = Image.open(img_file)
        
        # Xoay ảnh theo góc người dùng chọn nếu ảnh bị ngược
        if rotate_angle != 0:
            image = image.rotate(-rotate_angle, expand=True)

        st.image(image, caption="Ảnh xem trước (Đã căn chỉnh)", use_column_width=True)

        # Bóc tách thủ công / tự động
        st.write("---")
        st.markdown("**Trích xuất / Nhập thông tin từ văn bản:**")
        
        # Thử đọc tự động bằng OCR
        raw_text = ""
        if st.button("🔍 Đọc chữ tự động từ văn bản (OCR)"):
            with st.spinner("Đang xử lý đọc chữ..."):
                raw_text = extract_text_from_image(image)
                st.success("Đã đọc xong văn bản!")

        # Tìm các số CCCD/CMND có trong đoạn văn bản
        found_cccds = re.findall(r'\b\d{9,12}\b', raw_text)
        default_cccd = found_cccds[0] if found_cccds else ""

        with st.form("add_form"):
            ten = st.text_input("Họ và tên (Bên A / Bên B / Người liên quan):")
            cccd = st.text_input("Số CCCD / CMND:", value=default_cccd)
            diachi = st.text_area("Nơi cư trú / Địa chỉ:")
            noidung = st.text_area("Ghi chú / Trích yếu văn bản:", value=raw_text[:200] if raw_text else "")

            submit = st.form_submit_button("➕ Thêm vào danh sách tổng hợp", type="primary")

            if submit:
                if ten or cccd or diachi:
                    item = {
                        "Họ và tên": ten if ten else "Không ghi",
                        "Số CCCD": cccd if cccd else "Không ghi",
                        "Địa chỉ": diachi if diachi else "Không ghi",
                        "Nội dung văn bản": noidung
                    }
                    data_list.append(item)
                    save_data(data_list)
                    st.success(f"✅ Đã lưu hồ sơ của: {item['Họ và tên']}")
                    st.rerun()
                else:
                    st.warning("Vui lòng nhập ít nhất Họ tên hoặc Số CCCD.")

with col2:
    st.subheader(f"📋 2. Danh sách tổng hợp ({len(data_list)} văn bản)")
    
    if st.button("🔄 Cập nhật danh sách (Xem từ PC)"):
        st.rerun()

    if data_list:
        df = pd.DataFrame(data_list)
        st.dataframe(df[["Họ và tên", "Số CCCD", "Địa chỉ"]], use_container_width=True)

        st.write("---")
        st.write("🔍 **Xem chi tiết từng văn bản đã chụp:**")
        
        options = [f"{i+1}. {item['Họ và tên']} - CCCD: {item['Số CCCD']}" for i, item in enumerate(data_list)]
        selected_option = st.selectbox("Chọn hồ sơ muốn xem:", options)

        if selected_option:
            idx = int(selected_option.split(".")[0]) - 1
            selected_person = data_list[idx]

            st.info(f"**Chi tiết văn bản của: {selected_person['Họ và tên']}**")
            detail_df = pd.DataFrame(list(selected_person.items()), columns=["Mục thông tin", "Nội dung"])
            st.table(detail_df)

        if st.button("🗑️ Xóa toàn bộ danh sách"):
            save_data([])
            st.rerun()
    else:
        st.info("Chưa có dữ liệu. Hãy chụp văn bản từ điện thoại để lưu vào bảng.")
