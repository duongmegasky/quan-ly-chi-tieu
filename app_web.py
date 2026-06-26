import streamlit as st
import json
import os
import requests
from datetime import datetime

# --- CẤU HÌNH HỆ THỐNG ---
FILE_SAVE = "dulieu_vi_cloud.json"

# DÁN ĐOẠN URL WEB APP GOOGLE APPS SCRIPT CỦA BẠN VÀO ĐÂY:
URL_CAU_NOI = "https://script.google.com/macros/s/AKfycbx3dXuQdWHLEH_BTogMnF6O-H0x-w4QHHakUgZevcQYT2DyDS8jHhzanZnaCDWf3IwWeg/exec"

st.set_page_config(page_title="Quản Lý Chi Tiêu Đa Nền Tảng", page_icon="💰", layout="wide")

# --- HÀM 1: ĐỒNG BỘ DỮ LIỆU LÊN GOOGLE SHEETS ---
def luu_du_lieu():
    # Bước 1: Lưu cục bộ làm bản backup dự phòng ngay lập tức
    with open(FILE_SAVE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.data, f, ensure_ascii=False, indent=4)
        
    # Bước 2: Chuẩn hóa dữ liệu sang dạng bảng phẳng để đẩy lên Google Sheets
    try:
        vi_tien = st.session_state.data["vi_tien"]
        lich_su = st.session_state.data["lich_su"]
        
        # Tạo bảng phẳng cho Tab vi_tien
        vi_tien_rows = [["Ví Lớn", "Ví Nhỏ", "Số Dư"]]
        for vt, cvn in vi_tien.items():
            for vn, sd in cvn.items():
                vi_tien_rows.append([vt, vn, sd])
                
        # Tạo bảng phẳng cho Tab lich_su
        lich_su_rows = [["Thời Gian", "Loại", "Ví Lớn", "Ví Nhỏ", "Số Tiền", "Mô Tả", "Ảnh"]]
        for x in lich_su:
            lich_su_rows.append([
                x.get("thoi_gian", ""),
                x.get("loai", ""),
                x.get("vi_to", ""),
                x.get("vi_nho", ""),
                x.get("so_tien", 0),
                x.get("mo_ta", ""),
                x.get("anh", "")
            ])
            
        # Thực hiện gọi API POST đẩy dữ liệu lên Google Script
        res1 = requests.post(URL_CAU_NOI, json={"action": "update_all", "sheetName": "vi_tien", "rows": vi_tien_rows}, timeout=10)
        res2 = requests.post(URL_CAU_NOI, json={"action": "update_all", "sheetName": "lich_su", "rows": lich_su_rows}, timeout=10)
        
        # Kiểm tra phản hồi thực tế từ máy chủ Google
        if res1.status_code != 200 or res2.status_code != 200:
            st.error(f"⚠️ Google Sheets phản hồi lỗi HTTP {res1.status_code}. Dữ liệu hiện tại đang được lưu tạm cục bộ trên thiết bị.")
            return False
        elif "html" in res1.text.lower() or "script error" in res1.text.lower():
            st.error("⚠️ Lỗi cấu hình Apps Script! Vui lòng kiểm tra quyền truy cập 'Anyone' trên Web App.")
            return False
        return True
    except Exception as e:
        st.warning(f"⚠️ Chưa thể kết nối tới Google Sheets ({e}). Ứng dụng đang chuyển sang chế độ lưu trữ cục bộ an toàn.")
        return False

# --- HÀM 2: TẢI DỮ LIỆU TỪ GOOGLE SHEETS HOẶC FILE CỤC BỘ ---
def tai_du_lieu():
    # Tạo cấu trúc dữ liệu mặc định ban đầu nếu chưa có gì
    mac_dinh = {
        "vi_tien": {
            "Ví Cá Nhân": {"Tiền Mặt": 0, "Thẻ Ngân Hàng": 0},
            "Ví Gia Đình": {"Quỹ Chung": 0}
        },
        "lich_su": []
    }
    
    # Ưu tiên tải dữ liệu từ Google Sheets về trước
    try:
        res = requests.get(URL_CAU_NOI, timeout=8)
        if res.status_code == 200 and "html" not in res.text.lower():
            sheets_data = res.json()
            new_vi_tien = {}
            new_lich_su = []
            
            # Phân tích dữ liệu từ tab vi_tien
            if "vi_tien" in sheets_data and len(sheets_data["vi_tien"]) > 1:
                for row in sheets_data["vi_tien"][1:]:
                    if len(row) >= 3:
                        vl, vn, sd = row[0], row[1], row[2]
                        if vl not in new_vi_tien: new_vi_tien[vl] = {}
                        new_vi_tien[vl][vn] = float(sd) if sd != "" else 0.0
            
            # Phân tích dữ liệu từ tab lich_su
            if "lich_su" in sheets_data and len(sheets_data["lich_su"]) > 1:
                for row in sheets_data["lich_su"][1:]:
                    if len(row) >= 6:
                        new_lich_su.append({
                            "thoi_gian": row[0], "loai": row[1], "vi_to": row[2],
                            "vi_nho": row[3], "so_tien": float(row[4]) if row[4] else 0,
                            "mo_ta": row[5], "anh": row[6] if len(row) > 6 else ""
                        })
            
            if new_vi_tien:
                st.session_state.data = {"vi_tien": new_vi_tien, "lich_su": new_lich_su}
                return True
    except Exception:
        pass
        
    # Nếu tải từ Google lỗi, lấy dữ liệu backup từ file cục bộ thiết bị
    if os.path.exists(FILE_SAVE):
        try:
            with open(FILE_SAVE, "r", encoding="utf-8") as f:
                st.session_state.data = json.load(f)
                return True
        except Exception:
            st.session_state.data = mac_dinh
    else:
        st.session_state.data = mac_dinh
    return False

# --- KHỞI TẠO DỮ LIỆU KHI CHẠY APP ---
if "data" not in st.session_state:
    tai_du_lieu()

# --- GIAO DIỆN ĐIỀU HƯỚNG ---
st.title("💰 Hệ Thống Quản Lý Chi Tiêu Đa Nền Tảng")
menu = st.sidebar.radio("Chức năng hệ thống", ["Ghi nhận khoản chi", "Thêm ví & Nạp tiền", "Lịch sử giao dịch", "Cấu hình Hệ thống"])

vi_tien = st.session_state.data["vi_tien"]
lich_su = st.session_state.data["lich_su"]

# --- CHỨC NĂNG 1: GHI NHẬN KHOẢN CHI ---
if menu == "Ghi nhận khoản chi":
    st.header("🛒 Ghi Nhận Khoản Chi Mới")
    
    col1, col2 = st.columns(2)
    with col1:
        vi_to_sel = st.selectbox("Chọn Ví Lớn:", list(vi_tien.keys()))
        vi_nho_sel = st.selectbox("Chọn Ví Nhỏ:", list(vi_tien[vi_to_sel].keys()) if vi_to_sel else [])
        
        so_du_hien_tai = vi_tien[vi_to_sel][vi_nho_sel] if vi_to_sel and vi_nho_sel else 0
        st.info(f"💳 Số dư hiện tại của ví này: **{so_du_hien_tai:,.0f} VNĐ**")
        
    with col2:
        mo_ta = st.text_input("Nội dung / Mô tả khoản chi:")
        so_tien = st.number_input("Số tiền chi (VNĐ):", min_value=0, step=1000, value=0)
        
    if st.button("🚀 Thực hiện Ghi nhận chi tiêu", use_container_width=True):
        if not mo_ta or so_tien <= 0:
            st.error("Vui lòng điền đầy đủ mô tả và số tiền hợp lệ!")
        elif so_tien > so_du_hien_tai:
            st.error("Số dư tài khoản không đủ để thực hiện giao dịch này!")
        else:
            # Trừ tiền và lưu lịch sử
            st.session_state.data["vi_tien"][vi_to_sel][vi_nho_sel] -= so_tien
            st.session_state.data["lich_su"].insert(0, {
                "thoi_gian": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "loai": "Chi tiêu",
                "vi_to": vi_to_sel,
                "vi_nho": vi_nho_sel,
                "so_tien": so_tien,
                "mo_ta": mo_ta,
                "anh": ""
            })
            if luu_du_lieu():
                st.success(f"🎉 Đã chi {so_tien:,.0f} VNĐ cho '{mo_ta}'. Hệ thống đã đồng bộ lên Google Sheets!")
                st.rerun()

# --- CHỨC NĂNG 2: THÊM VÍ & NẠP TIỀN ---
elif menu == "Thêm ví & Nạp tiền":
    st.header("➕ Quản Lý Tài Khoản & Nạp Tiền")
    tab1, tab2, tab3 = st.tabs(["💵 Nạp Tiền Vào Ví", "📁 Tạo Ví Lớn Mới", "📂 Tạo Ví Nhỏ Mới"])
    
    with tab1:
        v_to = st.selectbox("Chọn Ví Lớn cần nạp:", list(vi_tien.keys()), key="nap_to")
        v_nho = st.selectbox("Chọn Ví Nhỏ cần nạp:", list(vi_tien[v_to].keys()) if v_to else [], key="nap_nho")
        st_nap = st.number_input("Số tiền nạp thêm (VNĐ):", min_value=0, step=1000, key="tien_nap")
        mt_nap = st.text_input("Ghi chú nạp tiền:", value="Nạp tiền vào tài khoản", key="note_nap")
        
        if st.button("📥 Xác nhận nạp tiền", type="primary"):
            if st_nap > 0:
                st.session_state.data["vi_tien"][v_to][v_nho] += st_nap
                st.session_state.data["lich_su"].insert(0, {
                    "thoi_gian": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "loai": "Nạp tiền", "vi_to": v_to, "vi_nho": v_nho,
                    "so_tien": st_nap, "mo_ta": mt_nap, "anh": ""
                })
                luu_du_lieu()
                st.success("Đã hoàn tất nạp tiền!")
                st.rerun()
                
    with tab2:
        ten_vi_to_moi = st.text_input("Nhập tên Ví Lớn mới (Ví dụ: Ví Tiết Kiệm, Ví Kinh Doanh):")
        if st.button("Tạo Ví Lớn"):
            if ten_vi_to_moi and ten_vi_to_moi not in vi_tien:
                st.session_state.data["vi_tien"][ten_vi_to_moi] = {"Tài khoản chính": 0}
                luu_du_lieu()
                st.success(f"Đã khởi tạo thành công {ten_vi_to_moi}!")
                st.rerun()
                
    with tab3:
        v_to_thuoc = st.selectbox("Chọn Ví Lớn chứa ví nhỏ này:", list(vi_tien.keys()), key="thuoc_to")
        ten_vi_nho_moi = st.text_input("Nhập tên Ví Nhỏ mới (Ví dụ: Tiền Ăn, Quỹ tiêu vặt):")
        if st.button("Tạo Ví Nhỏ"):
            if v_to_thuoc and ten_vi_nho_moi and ten_vi_nho_moi not in vi_tien[v_to_thuoc]:
                st.session_state.data["vi_tien"][v_to_thuoc][ten_vi_nho_moi] = 0
                luu_du_lieu()
                st.success("Tạo ví nhỏ thành công!")
                st.rerun()

# --- CHỨC NĂNG 3: LỊCH SỬ GIAO DỊCH ---
elif menu == "Lịch sử giao dịch":
    st.header("📊 Nhật Ký Biến Động Số Dư")
    
    # Hiển thị bảng số dư tổng quan hiện tại
    st.subheader("Bảng cân đối số dư các ví")
    for vl, cvn in vi_tien.items():
        with st.expander(f"📂 {vl}"):
            for vn, sd in cvn.items():
                st.write(f"- **{vn}**: {sd:,.0f} VNĐ")
                
    # Hiển thị danh sách lịch sử
    st.subheader("Dòng lịch sử giao dịch chi tiết")
    if not lich_su:
        st.write("Chưa có giao dịch nào được ghi nhận.")
    else:
        for item in lich_su:
            color = "green" if item["loai"] == "Nạp tiền" else "red"
            sign = "+" if item["loai"] == "Nạp tiền" else "-"
            st.markdown(f"⏱️ `{item['thoi_gian']}` | **{item['vi_to']} -> {item['vi_nho']}** | <span style='color:{color}'>{sign} {item['so_tien']:,.0f} VNĐ</span> | Nội dung: *{item['mo_ta']}*", unsafe_allow_html=True)

# --- CHỨC NĂNG 4: CẤU HÌNH HỆ THỐNG & ĐỒNG BỘ ---
elif menu == "Cấu hình Hệ thống":
    st.header("⚙️ Quản Lý Cấu Hình Kết Nối")
    
    # Kiểm tra trạng thái trực tiếp bằng cách ping thử Apps Script URL
    st.subheader("Trạng thái kết nối Google Cloud")
    try:
        ping = requests.get(URL_CAU_NOI, timeout=5)
        if ping.status_code == 200 and "html" not in ping.text.lower():
            st.success("✅ Đã kết nối thành công tới máy chủ Google Sheets!")
        else:
            st.error("❌ Kết nối thất bại: URL trả về trang lỗi Web hoặc trang Đăng nhập Google.")
    except Exception as e:
        st.error(f"❌ Kết nối thất bại: Không tìm thấy máy chủ hoặc ngắt kết nối mạng ({e})")
        
    st.subheader("Thao tác thủ công")
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("🔄 Tải lại toàn bộ dữ liệu từ Google Sheets", use_container_width=True):
            if tai_du_lieu():
                st.success("Đã nạp lại bộ nhớ từ dữ liệu gốc trên Google Drive thành công!")
                st.rerun()
            else:
                st.error("Tải dữ liệu thất bại, hệ thống đang dùng bộ nhớ đệm cục bộ.")
                
    with col_b2:
        if st.button("📤 Ép đồng bộ dữ liệu App lên Google Sheets", use_container_width=True):
            if luu_du_lieu():
                st.success("Đã đồng bộ đè dữ liệu cục bộ lên toàn bộ Google Sheets!")
            else:
                st.error("Ép đồng bộ thất bại!")
