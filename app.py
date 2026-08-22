import streamlit as st
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from docx import Document
import io

st.set_page_config(page_title="Nhập CCCD Tự Động", page_icon="📜", layout="centered")

st.title("📜 Quét CCCD & Xuất Sơ Yếu Lý Lịch")
st.write("Đưa mã QR trên CCCD vào camera hoặc chụp ảnh để tự động điền thông tin.")

# Khởi tạo dữ liệu
extracted_data = {
    'SO_CCCD': '',
    'HO_TEN': '',
    'NGAY_SINH': '',
    'GIOI_TINH': '',
    'DIA_CHI': '',
    'NGAY_CAP': ''
}

# Chụp ảnh từ camera
img_file_buffer = st.camera_input("Chụp ảnh mặt trước CCCD (chứa mã QR)")

if img_file_buffer is not None:
    bytes_data = img_file_buffer.getvalue()
    cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)

    # Giải mã QR
    barcodes = decode(cv2_img)
    if not barcodes:
        gray = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2GRAY)
        barcodes = decode(gray)

    if barcodes:
        try:
            # Giải mã chuẩn tiếng Việt cho CCCD Việt Nam
            raw_bytes = barcodes[0].data
            data_string = raw_bytes.decode('latin1').encode('latin1').decode('utf-8', errors='ignore')

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
        st.warning("Chưa tìm thấy mã QR trong ảnh. Vui lòng thử chụp lại rõ hơn.")

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

if st.button("🚀 Xuất file Sơ Yếu Lý Lịch (.docx)"):
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
            file_name=f"So_Yeu_Ly_Lich_{ho_ten}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    except Exception as e:
        st.error(f"Lỗi khi xuất file: {e}")
