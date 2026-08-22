import streamlit as st
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from docxtpl import DocxTemplate
import io

st.set_page_config(page_title="Tự động tạo hồ sơ từ CCCD", layout="centered")

st.title("📄 Ứng dụng Tạo Sơ Yếu Lý Lịch & Đơn Xin Việc")
st.caption("Chụp ảnh mặt trước CCCD để tự động trích xuất thông tin")

# Chụp ảnh mặt trước CCCD
img_file_buffer = st.camera_input("Chụp mặt trước CCCD (chứa mã QR)")

so_cccd, cmnd_cu, ho_ten, ngay_sinh, gioi_tinh, dia_chi, ngay_cap, que_quan = "", "", "", "", "", "", "", ""
quoc_tich = "Việt Nam"

if img_file_buffer is not None:
    bytes_data = img_file_buffer.getvalue()
    cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)

    barcodes = decode(cv2_img)
    
    if barcodes:
        qr_data = barcodes[0].data.decode('utf-8')
        info = qr_data.split('|')
        
        if len(info) >= 6:
            so_cccd = info[0]
            cmnd_cu = info[1] if info[1] else "Không"
            ho_ten = info[2]
            
            raw_ns = info[3]
            ngay_sinh = f"{raw_ns[:2]}/{raw_ns[2:4]}/{raw_ns[4:]}" if len(raw_ns) == 8 else raw_ns
            
            gioi_tinh = info[4]
            dia_chi = info[5]
            
            if len(info) >= 7 and info[6]:
                raw_nc = info[6]
                ngay_cap = f"{raw_nc[:2]}/{raw_nc[2:4]}/{raw_nc[4:]}" if len(raw_nc) == 8 else raw_nc
                
            st.success("✅ Đã trích xuất thành công dữ liệu từ mã QR!")
    else:
        st.warning("⚠️ Không tìm thấy mã QR trên ảnh. Bạn có thể tự nhập tay các trường bên dưới.")

st.subheader("📌 Kiểm tra & Bổ sung thông tin")

col1, col2 = st.columns(2)

with col1:
    ho_ten_val = st.text_input("Họ và tên", value=ho_ten)
    so_cccd_val = st.text_input("Số CCCD", value=so_cccd)
    cmnd_cu_val = st.text_input("Số CMND cũ (nếu có)", value=cmnd_cu)
    ngay_sinh_val = st.text_input("Ngày sinh (DD/MM/YYYY)", value=ngay_sinh)
    gioi_tinh_val = st.selectbox("Giới tính", ["Nam", "Nữ"], index=0 if gioi_tinh == "Nam" else 1)

with col2:
    quoc_tich_val = st.text_input("Quốc tịch", value=quoc_tich)
    que_quan_val = st.text_input("Quê quán", value=que_quan)
    dia_chi_val = st.text_input("Nơi thường trú / Địa chỉ", value=dia_chi)
    ngay_cap_val = st.text_input("Ngày cấp CCCD/CMND", value=ngay_cap)

st.divider()

if st.button("🚀 Xuất file Sơ Yếu Lý Lịch (.docx)", type="primary"):
    try:
        doc = DocxTemplate("mau_so_yeu_ly_lich.docx")
        
        context = {
            'HO_TEN': ho_ten_val,
            'SO_CCCD': so_cccd_val,
            'CMND_CU': cmnd_cu_val,
            'NGAY_SINH': ngay_sinh_val,
            'GIOI_TINH': gioi_tinh_val,
            'QUOC_TICH': quoc_tich_val,
            'QUE_QUAN': que_quan_val,
            'DIA_CHI': dia_chi_val,
            'NGAY_CAP': ngay_cap_val
        }
        
        doc.render(context)
        
        target_stream = io.BytesIO()
        doc.save(target_stream)
        
        st.download_button(
            label="📥 Bấm vào đây để tải file Word về máy",
            data=target_stream.getvalue(),
            file_name=f"So_Yeu_Ly_Lich_{ho_ten_val}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    except Exception as e:
        st.error(f"Lỗi: Không tìm thấy file 'mau_so_yeu_ly_lich.docx'. Chi tiết: {e}")
