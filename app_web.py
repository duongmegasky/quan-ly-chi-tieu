import streamlit as st
import json
import os
import requests
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageOps  # Thư viện xử lý và nén ảnh chụp từ điện thoại

# --- CẤU HÌNH HỆ THỐNG ---
FILE_SAVE = "dulieu_vi_cloud.json"
THU_MUC_ANH = "anh_giao_dich"

# DÁN ĐOẠN URL WEB APP GOOGLE APPS SCRIPT CỦA BẠN VÀO ĐÂY:
URL_CAU_NOI = "https://script.google.com/macros/s/AKfycbx3dXuQdWLEH_BTogMnF6O-H0x-w4QHHakUgZevcQYT2DyDS8jHhzanZnaCDWf3IwWeg/exec"

st.set_page_config(page_title="Quản Lý Chi Tiêu Đa Nền Tảng", page_icon="💰", layout="wide")

if not os.path.exists(THU_MUC_ANH):
    os.makedirs(THU_MUC_ANH)

# Cấu hình cứng múi giờ Việt Nam (UTC+7) không phụ thuộc vào giờ của Server Cloud
MUI_GIO_VN = timezone(timedelta(hours=7))

# --- HÀM XỬ LÝ VÀ TỐI ƯU ẢNH CHỤP ĐIỆN THOẠI ---
def xu_ly_va_luu_anh(file_anh, loai_gd):
    if file_anh is None:
        return ""
    try:
        img = Image.open(file_anh)
        img = ImageOps.exif_transpose(img)  # Sửa lỗi ảnh bị ngược/xoay nghiêng do cảm biến điện thoại
        img.thumbnail((1200, 1200))         # Giảm độ phân giải để app chạy mượt, tránh lag dung lượng lớn
        
        thoi_gian_chuoi = datetime.now(MUI_GIO_VN).strftime("%Y%m%d_%H%M%S")
        ten_file = f"{loai_gd}_{thoi_gian_chuoi}.jpg"
        duong_dan = os.path.join(THU_MUC_ANH, ten_file)
        
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(duong_dan, "JPEG", quality=80)  # Nén chất lượng hóa đơn xuống 80% để tiết kiệm bộ nhớ
        return duong_dan
    except Exception as e:
        st.error(f"⚠️ Lỗi xử lý ảnh chụp: {e}")
        return ""

# --- HÀM ĐỒNG BỘ DỮ LIỆU LÊN GOOGLE SHEETS ---
def luu_du_lieu():
    # 1. Lưu cục bộ làm bản backup dự phòng ngay lập tức
    with open(FILE_SAVE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.data, f, ensure_ascii=False, indent=4)
        
    # 2. Chuẩn hóa dữ liệu sang dạng bảng phẳng để đẩy lên Google Sheets
    try:
        vi_tien = st.session_state.data["vi_tien"]
        lich_su = st.session_state.data["lich_su"]
        
        vi_tien_rows = [["Ví Lớn", "Ví Nhỏ", "Số Dư"]]
        for vt, cvn in vi_tien.items():
            for vn, sd in cvn.items():
                vi_tien_rows.append([vt, vn, sd])
                
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
            
        res1 = requests.post(URL_CAU_NOI, json={"action": "update_all", "sheetName": "vi_tien", "rows": vi_tien_rows}, timeout=10)
        res2 = requests.post(URL_CAU_NOI, json={"action": "update_all", "sheetName": "lich_su", "rows": lich_su_rows}, timeout=10)
        
        if res1.status_code != 200 or res2.status_code != 200:
            st.error(f"⚠️ Google Sheets phản hồi lỗi HTTP. Dữ liệu hiện tại đang được bảo toàn cục bộ.")
            return False
        return True
    except Exception as e:
        st.warning(f"⚠️ Chưa thể đồng bộ tới Google Sheets ({e}). Đang chạy chế độ offline.")
        return False

# --- HÀM TẢI DỮ LIỆU TỪ GOOGLE SHEETS ---
def tai_du_lieu():
    mac_dinh = {
        "vi_tien": {
            "Ví Cá Nhân": {"Tiền Mặt": 0, "Thẻ Ngân Hàng": 0}
        },
        "lich_su": []
    }
    try:
        res = requests.get(URL_CAU_NOI, timeout=8)
        if res.status_code == 200 and "html" not in res.text.lower():
            sheets_data = res.json()
            new_vi_tien = {}
            new_lich_su = []
            
            if "vi_tien" in sheets_data and len(sheets_data["vi_tien"]) > 1:
                for row in sheets_data["vi_tien"][1:]:
                    if len(row) >= 3:
                        vl, vn, sd = row[0], row[1], row[2]
                        if vl not in new_vi_tien: new_vi_tien[vl] = {}
                        new_vi_tien[vl][vn] = float(sd) if sd != "" else 0.0
            
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

if "data" not in st.session_state:
    tai_du_lieu()

vi_tien = st.session_state.data["vi_tien"]
lich_su = st.session_state.data["lich_su"]

# --- GIAO DIỆN ĐIỀU HƯỚNG SIDEBAR ---
st.title("💰 Hệ Thống Quản Lý Chi Tiêu Đa Nền Tảng")
menu = st.sidebar.radio("Chức năng hệ thống", ["Ghi nhận khoản chi", "Thêm ví & Nạp tiền", "Lịch sử giao dịch", "Cấu hình Hệ thống"])

# --- CHỨC NĂNG 1: GHI NHẬN KHOẢN CHI ---
if menu == "Ghi nhận khoản chi":
    st.header("🛒 Ghi Nhận Khoản Chi Mới")
    
    col1, col2 = st.columns(2)
    with col1:
        vi_to_sel = st.selectbox("Chọn Ví Lớn:", list(vi_tien.keys()))
        vi_nho_sel = st.selectbox("Chọn Ví Nhỏ:", list(vi_tien[vi_to_sel].keys()) if vi_to_sel else [])
        
        so_du_hien_tai = vi_tien[vi_to_sel][vi_nho_sel] if vi_to_sel and vi_nho_sel else 0
        st.info(f"💳 Số dư hiện tại của ví này: **{so_du_hien_tai:,.0f} VNĐ**")
        
        # Thêm mục đính kèm ảnh hóa đơn chi tiêu
        anh_chi_file = st.file_uploader("📷 Chụp hoặc tải ảnh hóa đơn chi (PNG, JPG):", type=["png", "jpg", "jpeg"], key="upload_chi")
        
    with col2:
        mo_ta = st.text_input("Nội dung / Mô tả khoản chi:")
        so_tien = st.number_input("Số tiền chi (VNĐ):", min_value=0, step=1000, value=0)
        
    if st.button("🚀 Thực hiện Ghi nhận chi tiêu", use_container_width=True):
        if not mo_ta or so_tien <= 0:
            st.error("Vui lòng điền đầy đủ mô tả và số tiền hợp lệ!")
        elif so_tien > so_du_hien_tai:
            st.error("Số dư tài khoản không đủ để thực hiện giao dịch này!")
        else:
            duong_dan_anh = xu_ly_va_luu_anh(anh_chi_file, "CHI")
            st.session_state.data["vi_tien"][vi_to_sel][vi_nho_sel] -= so_tien
            st.session_state.data["lich_su"].insert(0, {
                "thoi_gian": datetime.now(MUI_GIO_VN).strftime("%Y-%m-%d %H:%M:%S"),
                "loai": "Chi tiêu",
                "vi_to": vi_to_sel,
                "vi_nho": vi_nho_sel,
                "so_tien": so_tien,
                "mo_ta": mo_ta,
                "anh": duong_dan_anh
            })
            if luu_du_lieu():
                st.success(f"🎉 Đã chi {so_tien:,.0f} VNĐ cho '{mo_ta}'. Hệ thống đã đồng bộ lên Google Sheets!")
                st.rerun()

# --- CHỨC NĂNG 2: THÊM VÍ / NẠP TIỀN / XÓA VÍ ---
elif menu == "Thêm ví & Nạp tiền":
    st.header("➕ Quản Lý Tài Khoản & Nạp Tiền")
    tab1, tab2, tab3, tab4 = st.tabs(["💵 Nạp Tiền Vào Ví", "📁 Tạo Ví Lớn Mới", "📂 Tạo Ví Nhỏ Mới", "❌ Xóa Ví"])
    
    with tab1:
        v_to = st.selectbox("Chọn Ví Lớn cần nạp:", list(vi_tien.keys()), key="nap_to")
        v_nho = st.selectbox("Chọn Ví Nhỏ cần nạp:", list(vi_tien[v_to].keys()) if v_to else [], key="nap_nho")
        st_nap = st.number_input("Số tiền nạp thêm (VNĐ):", min_value=0, step=1000, key="tien_nap")
        mt_nap = st.text_input("Ghi chú nạp tiền:", value="Nạp tiền vào tài khoản", key="note_nap")
        
        # Thêm mục đính kèm ảnh bằng chứng nạp tiền
        anh_nap_file = st.file_uploader("📷 Chụp hoặc tải ảnh hóa đơn nạp (PNG, JPG):", type=["png", "jpg", "jpeg"], key="upload_nap")
        
        if st.button("📥 Xác nhận nạp tiền", type="primary"):
            if st_nap > 0:
                duong_dan_anh = xu_ly_va_luu_anh(anh_nap_file, "NAP")
                st.session_state.data["vi_tien"][v_to][v_nho] += st_nap
                st.session_state.data["lich_su"].insert(0, {
                    "thoi_gian": datetime.now(MUI_GIO_VN).strftime("%Y-%m-%d %H:%M:%S"),
                    "loai": "Nạp tiền", "vi_to": v_to, "vi_nho": v_nho,
                    "so_tien": st_nap, "mo_ta": mt_nap, "anh": duong_dan_anh
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

    with tab4:
        st.subheader("🗑️ Xóa Ví Không Sử Dụng")
        st.warning("⚠️ Cảnh báo: Việc xóa ví sẽ xóa cấu hình ví này khỏi hệ thống. Hãy chắc chắn số dư ví đã được xử lý về 0 trước khi xóa.")
        
        danh_sach_xoa = []
        for vt, cvn in vi_tien.items():
            danh_sach_xoa.append(f"[Ví Lớn] {vt}")
            for vn in cvn.keys():
                danh_sach_xoa.append(f"[Ví Nhỏ] {vt} ➔ {vn}")
                
        if not danh_sach_xoa:
            st.info("Chưa có cấu trúc ví nào dữ liệu để xóa.")
        else:
            muc_muon_xoa = st.selectbox("Chọn mục ví muốn xóa vĩnh viễn:", danh_sach_xoa)
            
            # Tạo hộp kiểm chắc chắn trước khi thực thi lệnh xóa
            xac_nhan_xoa = st.checkbox("Tôi đồng ý xóa ví này và hiểu rằng hành động này không thể hoàn tác.")
            
            if st.button("🔥 XÁC NHẬN XÓA VÍ VĨNH VIỄN", type="secondary", disabled=not xac_nhan_xoa, use_container_width=True):
                if muc_muon_xoa.startswith("[Ví Lớn]"):
                    ten_vi_lon = muc_muon_xoa.replace("[Ví Lớn] ", "")
                    del st.session_state.data["vi_tien"][ten_vi_lon]
                elif muc_muon_xoa.startswith("[Ví Nhỏ]"):
                    ten_vi_lon, ten_vi_nho = muc_muon_xoa.replace("[Ví Nhỏ] ", "").split(" ➔ ")
                    del st.session_state.data["vi_tien"][ten_vi_lon][ten_vi_nho]
                    if not st.session_state.data["vi_tien"][ten_vi_lon]:
                        del st.session_state.data["vi_tien"][ten_vi_lon]
                        
                luu_du_lieu()
                st.success("Đã xóa mục ví thành công và cập nhật đồng bộ lên Google Sheets!")
                st.rerun()

# --- CHỨC NĂNG 3: LỊCH SỬ GIAO DỊCH ---
elif menu == "Lịch sử giao dịch":
    st.header("📊 Nhật Ký Biến Động Số Dư")
    
    st.subheader("Bảng cân đối số dư các ví")
    for vl, cvn in vi_tien.items():
        with st.expander(f"📂 {vl}"):
            for vn, sd in cvn.items():
                st.write(f"- **{vn}**: {sd:,.0f} VNĐ")
                
    st.subheader("Dòng lịch sử giao dịch chi tiết")
    if not lich_su:
        st.write("Chưa có giao dịch nào được ghi nhận.")
    else:
        for item in lich_su:
            color = "green" if item["loai"] == "Nạp tiền" else "red"
            sign = "+" if item["loai"] == "Nạp tiền" else "-"
            
            # Hiển thị thông tin giao dịch cơ bản
            st.markdown(f"⏱️ `{item['thoi_gian']}` | **{item['vi_to']} -> {item['vi_nho']}** | <span style='color:{color}'>{sign} {item['so_tien']:,.0f} VNĐ</span> | Nội dung: *{item['mo_ta']}*", unsafe_allow_html=True)
            
            # Nếu giao dịch có đính kèm ảnh và tệp ảnh tồn tại trên máy, hiển thị ảnh nhỏ bên dưới
            if item.get("anh") and os.path.exists(item["anh"]):
                st.image(item["anh"], caption="Ảnh hóa đơn đính kèm", width=150)

# --- CHỨC NĂNG 4: CẤU HÌNH HỆ THỐNG & ĐỒNG BỘ ---
elif menu == "Cấu hình Hệ thống":
    st.header("⚙️ Quản Lý Cấu Hình Kết Nối")
    
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
