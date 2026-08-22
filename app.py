import streamlit as st
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from docx import Document
import io

st.set_page_config(page_title="Nhập CCCD Tự Động", page_icon="📜", layout="centered")

st.title("📜 Quét CCCD & Xuất Sơ Yếu Lý Lịch")
st.write("Dùng camera chụp trực tiếp hoặc tải lên ảnh mặt trước CCCD có mã QR.")

# Khởi tạo dữ liệu
extracted_data = {
    'SO_CCCD': '',
    'HO_TEN': '',
    'NGAY_SINH': '',
    'GIOI_TINH': '',
    'DIA_CHI': '',
    'NGAY_CAP': ''
}

# --- PHẦN 1: LẤY ĐẦU VÀO ẢNH ---
input_method = st.radio("Chọn cách nhập ảnh:", ("Chụp ảnh trực tiếp", "Tải ảnh từ máy"))
final_img_bytes = None

if input_method == "Chụp ảnh trực tiếp":
    img_camera = st.camera_input("Chụp ảnh mặt trước CCCD")
    if img_camera is not None:
        final_img_bytes = img_camera.getvalue()
else:
    img_upload = st.file_uploader("Chọn ảnh CCCD từ thiết bị", type=['jpg', 'jpeg', 'png'])
    if img_upload is not None:
        final_img_bytes = img_upload.getvalue()

# --- PHẦN 2: XỬ LÝ ẢNH & GIẢI MÃ QR ---
if final_img_bytes is not None:
    cv2_img = cv2.imdecode(np.frombuffer(final_img_bytes, np.uint8), cv2.IMREAD_COLOR)

    # Thử quét trên ảnh gốc
    barcodes = decode(cv2_img)
    
    # Nếu chưa tìm thấy, thử quét trên ảnh xám
    if not barcodes:
        gray = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2GRAY)
        barcodes = decode(gray)

    if barcodes:
        try:
            # Lấy mảng byte thô từ pyzbar
            raw_bytes = bytes(barcodes[0].data)
            
            # Giải mã UTF-8 trực tiếp từ byte thô để khắc phục triệt để chữ Hán/ký tự lạ
            try:
                data_string = raw_bytes.decode('utf-8')
            except UnicodeDecodeError:
                data_string = raw_bytes.decode('utf-8', errors='ignore')

            # Tách chuỗi bằng dấu gạch đứng '|'
            parts = data_string.split('|')

            if len(parts) >= 6:
                extracted_data['SO_CCCD'] = parts[0].strip()
                extracted_data['HO_TEN'] = parts[2].strip()

                dob_raw = parts[3].strip()
                if len(dob_raw) == 8:
                    extracted_data['NGAY_SINH'] = f"{dob_raw[:2]}/{dob_raw[2:4]}/{dob_raw[4:]}"
                else:
                    extracted_data['NGAY_SINH'] = dob_raw

                extracted_data['GIOI_TINH'] = parts[4].strip()
                extracted_data['DIA_CHI'] = parts[5].strip()

            if len(parts) >= 7:
                issue_raw = parts[6].strip()
                if len(issue_raw) == 8:
                    extracted_data['NGAY_CAP'] = f"{issue_raw[:2]}/{issue_raw[2:4]}/{issue_raw[4:]}"
                else:
                    extracted_data['NGAY_CAP'] = issue_raw

            st.success("🎉 Đã quét và bóc tách thành công thông tin từ mã QR!")
        except Exception as e:
            st.error("Không thể đọc định dạng mã QR này.")
    else:
        st.warning("Chưa tìm thấy mã QR trong ảnh. Vui lòng thử chọn/chụp ảnh rõ hơn.")

# --- PHẦN 3: HIỂN THỊ VÀ CHỈNH SỬA THÔNG TIN ---
st.subheader("📌 Kiểm tra & Bổ sung thông tin")

col1, col2 = st.columns(2)
with col1:
    ho_ten = st.text_input("Họ và tên", value=extracted_data['HO_TEN'])
    so_cccd = st.text_input("Số CCCD", value=extracted_data['SO_CCCD'])
    ngay_sinh = st.text_input("Ngày sinh (DD/MM/YYYY)", value=extracted_data['NGAY_SINH'])
    gioi_tinh = st.selectbox("Giới tính", ["Nam", "Nữ"], index=0 if extracted_data['GIOI_TINH'] == "Nam" else 1)

with col2:
    dia_chi = st.text_input("Nơi thường trú / Địa chỉ", value=extracted_data['DIA_CHI'])
    ngay_cap = st.text_input("Ngày cấp CCCD", value=extracted_data['NGAY_CAP'])

# --- PHẦN 4: XUẤT FILE WORD ---
if st.button("🚀 Xuất file Sơ Yếu Lý Lịch (.docx)"):
    if not ho_ten:
        st.error("Vui lòng nhập Họ và tên trước khi xuất file.")
    else:
        try:
            doc = Document("mau_so_yeu_ly_lich.docx")

            replacements = {
                "{{ HO_TEN }}": ho_ten,
                "{{ SO_CCCD }}": so_cccd,
                "{{ NGAY_SINH }}": ngay_sinh,
                "{{ GIOI_TINH }}": gioi_tinh,
                "{{ DIA_CHI }}": dia_chi,
                "{{ NGAY_CAP }}": ngay_cap,
            }

            for p in doc.paragraphs:
                for key, val in replacements.items():
                    if key in p.text:
                        p.text = p.text.replace(key, val)

            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for p in cell.paragraphs:
                            for key, val in replacements.items():
                                if key in p.text:
                                    p.text = p.text.replace(key, val)

            bio = io.BytesIO()
            doc.save(bio)
            bio.seek(0)

            st.download_button(
                label="📥 Tải file Word về máy",
                data=bio,
                file_name=f"So_Yeu_Ly_Lich_{ho_ten.replace(' ', '_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            st.error(f"Lỗi khi xuất file: {e}")
