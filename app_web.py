import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# 1. ĐIỀN URL WEB APP APPS SCRIPT CỦA BẠN VÀO ĐÂY
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbx3dXuQdWLEH_BTogMnF6O-H0x-w4QHHakUgZevcQYT2DyDS8jHhzanZnaCDWf3lwWeg/exec"

st.set_page_config(page_title="Quản Lý Chi Tiêu Đa Nền Tảng", page_icon="💰", layout="縱向" if 'layout' not in st.session_state else "wide")

# Hàm lấy toàn bộ dữ liệu (doGet)
@st.cache_data(ttl=10)  # Lưu bộ nhớ đệm 10 giây để ứng dụng mượt mà hơn
def fetch_all_data():
    try:
        res = requests.get(WEB_APP_URL, timeout=10)
        if res.status_code == 200:
            return res.json()
        return None
    except Exception as e:
        return None

# Hàm gửi dữ liệu lên Sheets (doPost)
def send_data_to_sheets(payload):
    try:
        res = requests.post(WEB_APP_URL, json=payload, timeout=15)
        if res.status_code == 200:
            # Nhận phản hồi dạng Text ("Success") giúp tránh hoàn toàn lỗi Expecting Value JSON
            return res.text 
        return f"Lỗi kết nối Server: mã lỗi {res.status_code}"
    except Exception as e:
        return f"Lỗi hệ thống: {str(e)}"

# Tải dữ liệu từ Google Sheets về
data_sheets = fetch_all_data()

st.title("💰 Quản Lý Chi Tiêu Đa Nền Tảng")

# Tạo 4 Tabs chức năng chuẩn ban đầu
tab1, tab2, tab3, tab4 = st.tabs(["📋 Danh sách & Lịch sử", "📥 Nạp tiền / Tạo ví", "📤 Ghi nhận Chi tiêu", "⚙️ Quản lý Ví"])

# --- TAB 1: DANH SÁCH & LỊCH SỬ ---
with tab1:
    st.header("📋 Lịch sử giao dịch dữ liệu")
    if data_sheets:
        st.success("🟢 Kết nối đồng bộ dữ liệu thành công!")
        for sheet_name, rows in data_sheets.items():
            st.subheader(f"Dữ liệu bảng: {sheet_name}")
            if len(rows) > 0:
                df = pd.DataFrame(rows[1:], columns=rows[0])
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Bảng này hiện tại chưa có dòng dữ liệu nào.")
    else:
        st.error("❌ Không thể tải dữ liệu. Vui lòng kiểm tra lại cấu hình hoặc đường truyền URL Web App.")

# --- TAB 2: NẠP TIỀN / TẠO VÍ (Bản trực tiếp - Không Modal) ---
with tab2:
    st.header("📥 Thêm ví hoặc Nạp thêm tiền")
    
    vi_to = st.selectbox("Chọn Ví To (Ví dụ: Thẻ ngân hàng, Tiền mặt...):", ["Tiền mặt", "Thẻ ngân hàng", "Ví điện tử"], key="txt_vi_to")
    vi_nho = st.selectbox("Chọn Ví Nhỏ (Ví dụ: Tiền ăn, Tiền sinh hoạt...):", ["Tiền sinh hoạt", "Tiền ăn", "Tiền nhà", "Tiết kiệm"], key="txt_vi_nho")
    so_tien_nap = st.number_input("Số tiền nạp (VNĐ):", min_value=0, step=1000, value=50000)
    
    # Nút bấm xử lý trực tiếp không qua trung gian câu hỏi
    if st.button("XÁC NHẬN NẠP TIỀN / TẠO VÍ", type="primary"):
        if so_tien_nap <= 0:
            st.warning("⚠️ Số tiền nạp vào bắt buộc phải lớn hơn 0 VNĐ.")
        else:
            with st.spinner("Đang gửi dữ liệu trực tiếp lên Google Sheets..."):
                thoi_gian_hien_tai = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                payload = {
                    "sheetName": "NapTien",  # Dữ liệu sẽ đẩy vào sheet có tên 'NapTien'
                    "action": "append",
                    "row": [thoi_gian_hien_tai, vi_to, vi_nho, so_tien_nap]
                }
                
                ket_qua = send_data_to_sheets(payload)
                if ket_qua == "Success":
                    st.success(f"🎉 Thành công! Đã nạp xong {so_tien_nap:,} VNĐ vào ví [{vi_to} -> {vi_nho}].")
                    st.cache_data.clear() # Xóa cache để tab lịch sử cập nhật mới luôn
                    st.rerun()
                else:
                    st.error(f"❌ Đồng bộ thất bại. Chi tiết: {ket_qua}")

# --- TAB 3: GHI NHẬN CHI TIÊU ---
with tab3:
    st.header("📤 Ghi nhận khoản chi")
    
    vi_thanh_toan = st.selectbox("Chọn ví thực hiện thanh toán:", ["Tiền mặt -> Tiền sinh hoạt", "Tiền mặt -> Tiền ăn", "Thẻ ngân hàng -> Tiền nhà"])
    muc_dich = st.text_input("Mục đích chi (Bắt buộc):", placeholder="Ví dụ: mua nước lọc, trà sữa...")
    so_tien_chi = st.number_input("Số tiền chi (VNĐ):", min_value=0, step=1000, value=10000)
    file_anh = st.file_uploader("Chọn ảnh hóa đơn kèm theo (nếu có):", type=["png", "jpg", "jpeg"])
    
    if st.button("XÁC NHẬN CHI TIÊU", type="primary"):
        if not muc_dich:
            st.warning("⚠️ Vui lòng nhập lý do / mục đích chi tiêu.")
        elif so_tien_chi <= 0:
            st.warning("⚠️ Số tiền chi tiêu phải lớn hơn 0 VNĐ.")
        else:
            with st.spinner("Đang lưu giao dịch chi tiêu..."):
                thoi_gian_hien_tai = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                payload = {
                    "sheetName": "ChiTieu",  # Dữ liệu đẩy vào sheet 'ChiTieu'
                    "action": "append",
                    "row": [thoi_gian_hien_tai, vi_thanh_toan, muc_dich, so_tien_chi]
                }
                
                ket_qua = send_data_to_sheets(payload)
                if ket_qua == "Success":
                    st.success(f"🎉 Đã ghi nhận khoản chi {so_tien_chi:,} VNĐ thành công!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"❌ Thất bại: {ket_qua}")

# --- TAB 4: QUẢN LÝ CẤU HÌNH ---
with tab4:
    st.header("⚙️ Quản lý Cấu hình Hệ thống")
    st.markdown("**Đường dẫn Web App đang chạy kết nối:**")
    st.code(WEB_APP_URL)
    
    if data_sheets:
        st.markdown("**Trạng thái hệ thống:** 🟢 Hoạt động bình thường")
    else:
        st.markdown("**Trạng thái hệ thống:** ❌ Mất kết nối Google Sheets")
