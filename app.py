import streamlit as st
import numpy as np
import cv2
import zxingcpp
import pandas as pd
import os
import json
from PIL import Image
from pyzbar.pyzbar import decode as pyzbar_decode

st.set_page_config(page_title="Quét CCCD Hàng Loạt", page_icon="🪪", layout="wide")

DB_FILE = "data_list.json"

# Hàm đọc danh sách dữ liệu dùng chung
def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

# Hàm lưu danh sách dữ liệu dùng chung
def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Khởi tạo dữ liệu
data_list = load_data()

# Hàm giải mã tiếng Việt chuẩn từ QR CCCD
def decode_vietnamese(raw_bytes):
    try:
        return raw_bytes.decode('utf-8')
    except Exception:
        try:
            return raw_bytes.decode('latin1').encode('raw_unicode_escape').decode('utf-8')
        except Exception:
            return raw_bytes.decode('utf-8', errors='ignore')

# Hàm quét QR
def scan_qr_code(img_np):
    results = zxingcpp.read_barcodes(img_np)
    if results:
        return results[0].text

    pyz_res = pyzbar_decode(img_np)
    if pyz_res:
        return decode_vietnamese(pyz_res[0].data)

    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    results = zxingcpp.read_barcodes(gray)
    if results:
        return results[0].text
    
    pyz_res = pyzbar_decode(gray)
    if pyz_res:
        return decode_vietnamese(pyz_res[0].data)

    resized = cv2.resize(gray, (0, 0), fx=2, fy=2)
    results = zxingcpp.read_barcodes(resized)
    if results:
        return results[0].text

    pyz_res = pyzbar_decode(resized)
    if pyz_res:
        return decode_vietnamese(pyz_res[0].data)

    return None

st.title("🪪 QUÉT CCCD HÀNG LOẠT (LƯU DANH SÁCH)")

# Tạo 2 Cột giao diện (Cột 1: Chụp/Tải - Cột 2: Danh sách)
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📸 1. Chụp / Tải ảnh CCCD")
    source_choice = st.radio("Nguồn ảnh:", ["📷 Chụp trực tiếp", "📁 Tải ảnh"], horizontal=True)

    img_file = None
    if source_choice == "📷 Chụp trực tiếp":
        img_file = st.camera_input("Chụp mặt trước CCCD")
    else:
        img_file = st.file_uploader("Chọn ảnh CCCD", type=["jpg", "jpeg", "png"])

    if img_file is not None:
        image = Image.open(img_file)
        img_array = np.array(image)

        if st.button("➕ Thêm vào danh sách", type="primary"):
            qr_text = scan_qr_code(img_array)
            if qr_text:
                fields = qr_text.split("|")
                if len(fields) >= 6:
                    item = {
                        "Số CCCD": fields[0].strip(),
                        "Họ và tên": fields[2].strip(),
                        "Ngày sinh": f"{fields[3][:2]}/{fields[3][2:4]}/{fields[3][4:]}" if len(fields[3])==8 else fields[3],
                        "Giới tính": fields[4].strip(),
                        "Địa chỉ": fields[5].strip()
                    }
                    
                    # Kiểm tra trùng lặp
                    if not any(d['Số CCCD'] == item['Số CCCD'] for d in data_list):
                        data_list.append(item)
                        save_data(data_list)
                        st.success(f"✅ Đã thêm: {item['Họ và tên']}")
                        st.rerun()
                    else:
                        st.warning("⚠️ CCCD này đã có trong danh sách!")
                else:
                    st.error("QR không đúng định dạng CCCD.")
            else:
                st.error("Không tìm thấy mã QR trên ảnh.")

with col2:
    st.subheader(f"📋 2. Danh sách đã quét ({len(data_list)} hồ sơ)")
    
    if st.button("🔄 Cập nhật danh sách mới nhất"):
        st.rerun()

    if data_list:
        # Bảng tổng hợp tất cả hồ sơ
        df = pd.DataFrame(data_list)
        st.dataframe(df[["Số CCCD", "Họ và tên", "Địa chỉ"]], use_container_width=True)

        st.write("---")
        st.write("🔍 **Xem chi tiết / Chọn hồ sơ:**")
        
        # Menu chọn từng người trong danh sách để xem chi tiết
        options = [f"{i+1}. {item['Họ và tên']} - {item['Số CCCD']}" for i, item in enumerate(data_list)]
        selected_option = st.selectbox("Chọn người muốn xem:", options)

        if selected_option:
            idx = int(selected_option.split(".")[0]) - 1
            selected_person = data_list[idx]

            # Hiển thị thông tin chi tiết dưới dạng bảng
            st.info(f"**Thông tin chi tiết của: {selected_person['Họ và tên']}**")
            detail_df = pd.DataFrame(list(selected_person.items()), columns=["Mục", "Nội dung"])
            st.table(detail_df)

        # Nút xóa tất cả nếu muốn làm lại từ đầu
        if st.button("🗑️ Xóa toàn bộ danh sách", type="secondary"):
            save_data([])
            st.rerun()
    else:
        st.info("Chưa có dữ liệu nào. Hãy chụp ảnh từ điện thoại để thêm vào danh sách.")
