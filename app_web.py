import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Cấu hình trang Streamlit
st.set_page_config(page_title="Quản Lý Chi Tiêu Đa Nền Tảng", page_icon="💰", layout="centered")

# =====================================================================
# CẤU HÌNH ĐƯỜNG DẪN GOOGLE APPS SCRIPT CỦA BẠN
# =====================================================================
API_URL = "https://script.google.com/macros/s/AKfycbx3dXuQdWHLEH_BTogMnF6O-H0x-w4QHHakUgZevcQYT2DyDS8jHhzanZnaCDWf3IwWeg/exec"
SHEET_NAME = "GiaoDich"  # Tên trang tính lưu trữ trong file Google Sheets

# =====================================================================
# CÁC HÀM XỬ LÝ KẾT NỐI API (ĐỌC / GHI DỮ LIỆU) - ĐÃ TỐI ƯU JSON & CACHE
# =====================================================================
@st.cache_data(ttl=60)  # Tối ưu: Lưu bộ nhớ đệm trong 60 giây để tránh lag khi chuyển tab liên tục
def get_all_data():
    """Lấy dữ liệu từ Google Sheets qua phương thức doGet"""
    try:
        response = requests.get(API_URL)
        if response.status_code == 200:
            return response.json()
        return {}
    except Exception as e:
        st.error(f"Lỗi kết nối tải dữ liệu: {e}")
        return {}

def send_data(action, row=None, rows=None):
    """Gửi yêu cầu ghi/sửa/xóa dữ liệu qua phương thức doPost và xử lý phản hồi JSON phản hồi"""
    payload = {"action": action, "sheetName": SHEET_NAME}
    if row is not None:
        payload["row"] = row
    if rows is not None:
        payload["rows"] = rows
    try:
        res = requests.post(API_URL, json=payload)
        if res.status_code == 200:
            res_json = res.json()
            # Kiểm tra trạng thái "success" trả về từ cấu trúc Apps Script mới nâng cấp
            if res_json.get("status") == "success":
                return True, res_json.get("message", "Thành công")
            else:
                return False, res_json.get("message", "Lỗi phản hồi hệ thống")
        return False, f"HTTP Error {res.status_code}"
    except Exception as e:
        return False, str(e)

# =====================================================================
# TẢI VÀ XỬ LÝ DỮ LIỆU BAN ĐẦU
# =====================================================================
data_sheets = get_all_data()

# Tạo cấu trúc bảng dữ liệu chuẩn nếu Google Sheet chưa có gì hoặc bị lỗi
if SHEET_NAME in data_sheets and len(data_sheets[SHEET_NAME]) > 0:
    headers = data_sheets[SHEET_NAME][0]
    raw_rows = data_sheets[SHEET_NAME][1:]
    if len(raw_rows) == 0:
        df = pd.DataFrame(columns=["Thời Gian", "Loại", "Ví Tiền", "Số Tiền", "Mục Đích"])
    else:
        df = pd.DataFrame(raw_rows, columns=headers)
        df["Số Tiền"] = pd.to_numeric(df["Số Tiền"], errors='coerce').fillna(0)
else:
    df = pd.DataFrame(columns=["Thời Gian", "Loại", "Ví Tiền", "Số Tiền", "Mục Đích"])

# Quét lịch sử dữ liệu để tự động lấy danh sách ví đã từng tạo
danh_sach_vi_to_co_san = ["Tiền mặt", "Thẻ ngân hàng"]
danh_sach_vi_nho_co_san = ["Tiền sinh hoạt", "Tiền dự phòng", "Tiền ăn", "Tiền nhà"]

if not df.empty:
    for vt in df["Ví Tiền"].dropna().unique():
        if " -> " in str(vt):
            v_to, v_nho = str(vt).split(" -> ", 1)
            if v_to not in danh_sach_vi_to_co_san:
                danh_sach_vi_to_co_san.append(v_to)
            if v_nho not in danh_sach_vi_nho_co_san:
                danh_sach_vi_nho_co_san.append(v_nho)

# =====================================================================
# GIAO DIỆN CHÍNH ỨNG DỤNG
# =====================================================================
st.title("💰 Quản Lý Chi Tiêu Đa Nền Tảng")

# Tạo 4 tab chức năng như thiết kế của bạn
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Danh sách & Lịch sử", 
    "📥 Nạp tiền / Tạo ví", 
    "📤 Ghi nhận Chi tiêu", 
    "⚙️ Quản lý Ví"
])

# ---------------------------------------------------------------------
# TAB 1: DANH SÁCH VÍ & LỊCH SỬ GIAO DỊCH
# ---------------------------------------------------------------------
with tab1:
    st.header("📊 Danh sách ví hiện tại")
    
    # Tính toán số dư của từng ví phụ dựa trên toàn bộ lịch sử giao dịch
    balances = {}
    if not df.empty:
        for _, row in df.iterrows():
            vt = str(row["Ví Tiền"])
            if " -> " in vt:
                v_to, v_nho = vt.split(" -> ", 1)
                loai = row["Loại"]
                try:
                    so_tien = float(row["Số Tiền"])
                except:
                    so_tien = 0
                
                if v_to not in balances:
                    balances[v_to] = {}
                if v_nho not in balances[v_to]:
                    balances[v_to][v_nho] = 0
                    
                if loai == "NẠP":
                    balances[v_to][v_nho] += so_tien
                elif loai == "CHI":
                    balances[v_to][v_nho] -= so_tien

        if balances:
            for v_to, vi_nhos in balances.items():
                with st.expander(f"■ {v_to}", expanded=True):
                    for v_nho, bal in vi_nhos.items():
                        st.write(f"🔹 **{v_nho}:** {bal:,} đ")
        else:
            st.info("Chưa có thông tin ví nào. Hãy chuyển qua tab 'Nạp tiền / Tạo ví' để bắt đầu.")

    st.markdown("---")
    st.header("📜 Lịch sử giao dịch")
    if not df.empty:
        # Hiển thị bảng từ mới nhất đến cũ nhất
        st.dataframe(df.iloc[::-1], use_container_width=True)
        
        # ----------------- CÔNG CỤ SỬA / XÓA DÒNG GIAO DỊCH -----------------
        st.markdown("---")
        st.subheader("🛠️ Công cụ Quản lý Lịch sử (Sửa / Xóa Giao Dịch)")
        
        options_giao_dich = []
        for idx, row in df.iterrows():
            options_giao_dich.append(f"[{row['Thời Gian']}] {row['Loại']} | {row['Ví Tiền']} | {int(row['Số Tiền']):,}đ - {row['Mục Đích']}")
            
        selected_option = st.selectbox("Chọn dòng giao dịch muốn can thiệp:", options_giao_dich)
        selected_idx = options_giao_dich.index(selected_option)
        current_row = df.iloc[selected_idx]
        
        sua_muc_dich = st.text_input("Sửa Mục đích / Mô tả:", value=current_row["Mục Đích"])
        sua_so_tien = st.number_input("Sửa Số tiền (đ):", value=int(current_row["Số Tiền"]), step=1000)
        
        # Hộp thoại xác nhận SỬA
        @st.dialog("Xác nhận cập nhật giao dịch")
        def confirm_update(idx, old_row, new_mục_đích, new_số_tiền):
            st.write("Bạn có chắc chắn muốn cập nhật thay đổi cho dòng giao dịch này?")
            st.warning(f"Nội dung cũ: {old_row['Mục Đích']} | {int(old_row['Số Tiền']):,}đ")
            st.success(f"Nội dung mới: {new_mục_đích} | {new_số_tiền:,}đ")
            if st.button("Xác nhận lưu thay đổi", type="primary", use_container_width=True):
                df.at[idx, "Mục Đích"] = new_mục_đích
                df.at[idx, "Số Tiền"] = new_số_tiền
                
                # Chuyển đổi DataFrame thành dạng mảng 2 chiều tuần tự để update lại toàn bộ
                all_rows = [df.columns.tolist()] + df.values.tolist()
                success, msg = send_data("update_all", rows=all_rows)
                if success:
                    st.success("Đã cập nhật lên Google Sheets!")
                    st.cache_data.clear()  # Xóa bộ nhớ đệm để ép tải dữ liệu mới ngay lập tức
                    st.rerun()
                else:
                    st.error(f"Gặp lỗi khi gửi dữ liệu: {msg}")

        # Hộp thoại xác nhận XÓA
        @st.dialog("Xác nhận XÓA vĩnh viễn")
        def confirm_delete(idx, row_del):
            st.error("Cảnh báo: Giao dịch này sẽ bị xóa hoàn toàn khỏi Google Sheets!")
            st.write(f"**Thời gian:** {row_del['Thời Gian']} | **Ví:** {row_del['Ví Tiền']} | **Số tiền:** {int(row_del['Số Tiền']):,}đ")
            if st.button("Tôi muốn xóa dòng này", type="primary", use_container_width=True):
                df_new = df.drop(idx)
                all_rows = [df_new.columns.tolist()] + df_new.values.tolist()
                success, msg = send_data("update_all", rows=all_rows)
                if success:
                    st.success("Đã xóa dòng giao dịch!")
                    st.cache_data.clear()  # Xóa bộ nhớ đệm
                    st.rerun()
                else:
                    st.error(f"Gặp lỗi khi thực hiện lệnh xóa: {msg}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📝 Cập nhật thay đổi", type="primary", use_container_width=True):
                confirm_update(selected_idx, current_row, sua_muc_dich, sua_so_tien)
        with col2:
            if st.button("🗑️ XÓA dòng giao dịch này", use_container_width=True):
                confirm_delete(selected_idx, current_row)
    else:
        st.info("Chưa có lịch sử giao dịch nào được ghi nhận.")

# ---------------------------------------------------------------------
# TAB 2: NẠP TIỀN / TẠO VÍ
# ---------------------------------------------------------------------
with tab2:
    st.header("📩 Thêm ví hoặc Nạp thêm tiền")
    
    # 1. Xử lý Dropdown Ví To
    options_vi_to = danh_sach_vi_to_co_san + ["+ Thêm mới..."]
    vi_to_chon = st.selectbox("Chọn Ví To (Ví dụ: Thẻ ngân hàng, Tiền mặt...):", options_vi_to, key="sel_vi_to")
    if vi_to_chon == "+ Thêm mới...":
        ten_vi_to = st.text_input("Nhập tên Ví To mới hoàn toàn:", placeholder="Ví dụ: Ví MoMo, Thẻ Techcombank...")
    else:
        ten_vi_to = vi_to_chon

    # 2. Xử lý Dropdown Ví Nhỏ
    options_vi_nho = danh_sach_vi_nho_co_san + ["+ Thêm mới..."]
    vi_nho_chon = st.selectbox("Chọn Ví Nhỏ (Ví dụ: Tiền ăn, Tiền nhà...):", options_vi_nho, key="sel_vi_nho")
    if vi_nho_chon == "+ Thêm mới...":
        ten_vi_nho = st.text_input("Nhập tên Ví Nhỏ mới hoàn toàn:", placeholder="Ví dụ: Tiền học phí, Tiền mua sắm...")
    else:
        ten_vi_nho = vi_nho_chon

    # Nhập số tiền nạp
    so_tien_nap = st.number_input("Số tiền nạp (VNĐ):", min_value=0, step=1000, key="num_vi_nap")
    muc_dich_nap = "Khởi tạo/Nạp thêm"

    # Định nghĩa Popup hộp thoại xác nhận khi Nạp tiền / Tạo ví
    @st.dialog("Xác nhận Nạp tiền / Tạo ví mới")
    def dialog_xac_nhan_nap(v_to, v_nho, s_tien):
        st.write("Bạn có chắc chắn muốn thực hiện hành động lưu thông tin này?")
        st.info(f"📁 **Ví đích:** {v_to} -> {v_nho}\n\n💰 **Số tiền nạp:** {s_tien:,} VNĐ")
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("Có, Lưu lại", type="primary", use_container_width=True):
                time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                vi_full = f"{v_to} -> {v_nho}"
                row_data = [time_now, "NẠP", vi_full, s_tien, muc_dich_nap]
                
                success, msg = send_data("append", row=row_data)
                if success:
                    st.success("Đã ghi nhận nạp tiền thành công!")
                    st.cache_data.clear() # Xóa bộ nhớ đệm
                    st.rerun()
                else:
                    st.error(f"Lỗi đồng bộ dữ liệu: {msg}")
        with col_c2:
            if st.button("Không, Hủy bỏ", use_container_width=True):
                st.rerun()

    # Nút bấm chính kích hoạt Dialog hỏi xác nhận
    if st.button("XÁC NHẬN NẠP TIỀN / TẠO VÍ", type="primary", use_container_width=True):
        if not ten_vi_to or not ten_vi_nho:
            st.error("Vui lòng điền đầy đủ hoặc chọn tên Ví To và Ví Nhỏ!")
        elif so_tien_nap <= 0:
            st.error("Số tiền nạp vào ví phải lớn hơn 0đ!")
        else:
            dialog_xac_nhan_nap(ten_vi_to, ten_vi_nho, so_tien_nap)

# ---------------------------------------------------------------------
# TAB 3: GHI NHẬN KHOẢN CHI TIÊU
# ---------------------------------------------------------------------
with tab3:
    st.header("📤 Ghi nhận khoản chi")
    
    # Gom danh sách tổ hợp ví thực tế đang có để người dùng chọn nhanh khi chi tiêu
    danh_sach_vi_chi = []
    if not df.empty:
        danh_sach_vi_chi = df["Ví Tiền"].dropna().unique().tolist()
    if not danh_sach_vi_chi:
        danh_sach_vi_chi = [f"{vt} -> {vn}" for vt in danh_sach_vi_to_co_san for vn in danh_sach_vi_nho_co_san]

    vi_thanh_toan = st.selectbox("Chọn ví thanh toán:", danh_sach_vi_chi, key="sel_vi_chi")
    muc_dich_chi = st.text_input("Mục đích chi (Bắt buộc):", placeholder="Ví dụ: mua 2 chai nước lọc")
    so_tien_chi = st.number_input("Số tiền chi (VNĐ):", min_value=0, step=1000, key="num_vi_chi")
    
    # Tính năng phụ đính kèm ảnh hóa đơn
    st.file_uploader("Chọn ảnh hóa đơn chi (nếu có):", type=["png", "jpg", "jpeg"])

    # Định nghĩa Popup hộp thoại xác nhận khi Ghi nhận khoản Chi tiêu
    @st.dialog("Xác nhận Ghi nhận Chi tiêu")
    def dialog_xac_nhan_chi(v_chi, m_dich, s_tien):
        st.write("Bạn có chắc chắn muốn ghi nhận khoản chi tiêu này vào hệ thống không?")
        st.error(f"💳 **Ví thanh toán:** {v_chi}\n\n📝 **Mục đích:** {m_dich}\n\n💸 **Số tiền:** {s_tien:,} VNĐ")
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            if st.button("Đúng, Xác nhận", type="primary", use_container_width=True):
                time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                row_data = [time_now, "CHI", v_chi, s_tien, m_dich]
                
                success, msg = send_data("append", row=row_data)
                if success:
                    st.success("Đã ghi nhận khoản chi tiêu!")
                    st.cache_data.clear() # Xóa bộ nhớ đệm
                    st.rerun()
                else:
                    st.error(f"Không thể ghi nhận dữ liệu: {msg}")
        with col_d2:
            if st.button("Hủy bỏ lệnh chi", use_container_width=True):
                st.rerun()

    # Nút bấm xác nhận chi
    if st.button("XÁC NHẬN CHI TIÊU", type="primary", use_container_width=True):
        if not muc_dich_chi:
            st.error("Vui lòng nhập mục đích chi tiêu bắt buộc!")
        elif so_tien_chi <= 0:
            st.error("Số tiền chi ra phải lớn hơn 0đ!")
        else:
            dialog_xac_nhan_chi(vi_thanh_toan, muc_dich_chi, so_tien_chi)

# ---------------------------------------------------------------------
# TAB 4: HƯỚNG DẪN & THÔNG TIN CẤU HÌNH
# ---------------------------------------------------------------------
with tab4:
    st.header("⚙️ Quản lý Cấu hình Hệ thống")
    st.markdown(f"""
    * **Ứng dụng Web App đang kết nối trực tiếp đến:**
      `{API_URL}`
    * **Trạng thái kết nối Google Sheets:** {"✅ Đã kết nối thành công" if data_sheets else "❌ Thất bại (Kiểm tra lại Apps Script)"}
    """)
    st.info("💡 Hệ thống đã tích hợp cơ chế bộ nhớ đệm thông minh (Cache) giúp ứng dụng hoạt động mượt mà và tự động giải phóng bộ nhớ để đồng bộ tức thì sau mỗi giao dịch thành công.")
