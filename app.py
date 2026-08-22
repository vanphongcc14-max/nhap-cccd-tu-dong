import streamlit as st
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from docxtpl import DocxTemplate
import io

st.set_page_config(page_title="Chuyển Đổi QR CCCD Sang Sơ Yếu Lý Lịch", layout="wide")

st.title("📇 Chuyển Đổi QR CCCD Sang Sơ Yếu Lý Lịch")

st.subheader("Bước 1: Tải ảnh CCCD (Mặt trước có chứa mã QR)")

# Chọn tệp ảnh đã chụp sẵn từ thiết bị
uploaded_file = st.file_uploader("Chọn tệp ảnh CCCD (JPG, PNG, JPEG)...", type=["jpg", "png", "jpeg"])

extracted_data = {}

if uploaded_file is not None:
    # Đọc dữ liệu ảnh
    file_bytes = np.frombuffer(uploaded_file.read(), np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    # Hiển thị ảnh đã tải lên
    st.image(image, caption="Ảnh CCCD đã tải lên", width=350)

    # --- THUẬT TOÁN XỬ LÝ MÃ QR ---
    # 1. Thử giải mã trực tiếp trên ảnh gốc
    barcodes = decode(image)

    # 2. Nếu chưa đọc được, chuyển sang ảnh xám để tăng khả năng nhận diện
    if not barcodes:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        barcodes = decode(gray)

    # 3. Nếu vẫn chưa đọc được, tăng độ tương phản (Thresholding)
    if not barcodes:
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        barcodes = decode(thresh)

    if barcodes:
        try:
            # Lấy chuỗi dữ liệu mã QR (định dạng UTF-8)
            data_string = barcodes[0].data.decode("utf-8")
            parts = data_string.split('|')

            if len(parts) >= 6:
                extracted_data['SO_CCCD'] = parts[0].strip()
                extracted_data['HO_TEN'] = parts[2].strip()

                # Định dạng ngày sinh (DDMMYYYY -> DD/MM/YYYY)
                dob_raw = parts[3].strip()
                if len(dob_raw) == 8:
                    extracted_data['NGAY_SINH'] = f"{dob_raw[:2]}/{dob_raw[2:4]}/{dob_raw[4:]}"
                else:
                    extracted_data['NGAY_SINH'] = dob_raw

                extracted_data['GIOI_TINH'] = parts[4].strip()
                extracted_data['DIA_CHI'] = parts[5].strip()

                # Định dạng ngày cấp nếu có trong mã QR (phần tử thứ 7)
                if len(parts) >= 7:
                    issue_raw = parts[6].strip()
                    if len(issue_raw) == 8:
                        extracted_data['NGAY_CAP'] = f"{issue_raw[:2]}/{issue_raw[2:4]}/{issue_raw[4:]}"
                    else:
                        extracted_data['NGAY_CAP'] = issue_raw
                else:
                    extracted_data['NGAY_CAP'] = ""

                st.success("🎉 Đã quét và bóc tách thành công thông tin từ mã QR!")
            else:
                st.warning("⚠️ Đã đọc được mã QR nhưng cấu trúc dữ liệu không chính xác định dạng CCCD.")
        except Exception as e:
            st.error(f"❌ Lỗi khi bóc tách dữ liệu: {e}")
    else:
        st.error("❌ Không thể đọc được mã QR trong ảnh. Vui lòng kiểm tra lại ảnh (chụp rõ nét, đủ ánh sáng) hoặc nhập tay bên dưới.")

st.markdown("---")
st.subheader("Bước 2: Xác nhận và bổ sung thông tin")

with st.form("info_form"):
    col1, col2 = st.columns(2)

    with col1:
        ho_ten = st.text_input("Họ và Tên (Từ QR)", value=extracted_data.get('HO_TEN', ''))
        so_cccd = st.text_input("Số Căn Cước Công Dân (Từ QR)", value=extracted_data.get('SO_CCCD', ''))
        ngay_sinh = st.text_input("Ngày Sinh (DD/MM/YYYY)", value=extracted_data.get('NGAY_SINH', ''))
        ngay_cap = st.text_input("Ngày Cấp CCCD", value=extracted_data.get('NGAY_CAP', ''))

    with col2:
        # Chọn giới tính
        gioi_tinh_default = extracted_data.get('GIOI_TINH', 'Nam')
        index_gt = 0 if gioi_tinh_default == 'Nam' else 1
        gioi_tinh = st.selectbox("Giới Tính (Từ QR)", ["Nam", "Nữ"], index=index_gt)

        dia_chi = st.text_area("Hộ Khẩu Thường Trú / Địa Chỉ (Từ QR)", value=extracted_data.get('DIA_CHI', ''), height=108)

    submitted = st.form_submit_button("🚀 Xuất File Sơ Yếu Lý Lịch (.docx)")

if submitted:
    if not ho_ten or not so_cccd:
        st.warning("⚠️ Vui lòng điền tối thiểu Họ tên và Số CCCD.")
    else:
        try:
            doc = DocxTemplate("mau_so_yeu_ly_lich.docx")
            context = {
                'HO_TEN': ho_ten,
                'SO_CCCD': so_cccd,
                'NGAY_SINH': ngay_sinh,
                'GIOI_TINH': gioi_tinh,
                'DIA_CHI': dia_chi,
                'NGAY_CAP': ngay_cap
            }

            doc.render(context)

            output_file = io.BytesIO()
            doc.save(output_file)
            output_file.seek(0)

            st.download_button(
                label="📥 Tải file DOCX đã điền về máy",
                data=output_file,
                file_name=f"So_Yeu_Ly_Lich_{ho_ten}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            st.error(f"❌ Lỗi khi tạo file Word: {e}")
