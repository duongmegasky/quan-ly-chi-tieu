import streamlit as st
import json
import os
import requests
import time
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageOps

# --- CẤU HÌNH HỆ THỐNG ---
FILE_SAVE = "dulieu_vi_cloud.json"
THU_MUC_ANH = "anh_giao_dich"

# DÁN ĐOẠN URL WEB APP GOOGLE APPS SCRIPT CỦA BẠN VÀO ĐÂY:
URL_CAU_NOI = "https://script.google.com/macros/s/AKfycbx3dXuQdWHLEH_BTogMnF6O-H0x-w4QHHakUgZevcQYT2DyDS8jHhzanZnaCDWf3IwWeg/exec"

st.set_page_config(page_title="Quản Lý Chi Tiêu Đa Nền Tảng", page_icon="💰", layout="wide")

if not os.path.exists(THU_MUC_ANH):
    os.makedirs(THU_MUC_ANH)

MUI_GIO_VN = timezone(timedelta(hours=7))

# --- HÀM CHUẨN HÓA THỜI GIAN ĐỒNG NHẤT ---
def chuan_hoa_thoi_gian(chuoi_tg):
    if not chuoi_tg:
        return "Không rõ"
    chuoi_str = str(chuoi_tg).strip()
    if "T" in chuoi_str:
        chuoi_str = chuoi_str.replace("T", " ").split(".")[0].replace("Z", "")
    return chuoi_str

# --- HÀM XỬ LÝ VÀ TỐI ƯU ẢNH ---
def xu_ly_va_luu_anh(file_anh, loai_gd):
    if file_anh is None:
        return ""
    try:
        img = Image.open(file_anh)
        img = ImageOps.exif_transpose(img)
        img.thumbnail((1200, 1200))
        thoi_gian_chuoi = datetime.now(MUI_GIO_VN).strftime("%Y%m%d_%H%M%S")
        ten_file = f"{loai_gd}_{thoi_gian_chuoi}.jpg"
        duong_dan = os.path.join(THU_MUC_ANH, ten_file)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(duong_dan, "JPEG", quality=80)
        return duong_dan
    except Exception as e:
        st.error(f"⚠️ Lỗi xử lý ảnh chụp: {e}")
        return ""

# --- HÀM ĐỒNG BỘ DỮ LIỆU LÊN GOOGLE SHEETS ---
def luu_du_lieu():
    with open(FILE_SAVE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.data, f, ensure_ascii=False, indent=4)
        
    try:
        vi_tien = st.session_state.data["vi_tien"]
        lich_su = st.session_state.data["lich_su"]
        
        vi_tien_rows = [["Ví Lớn", "Ví Nhỏ", "Số Dư"]]
        for vt, cvn in vi_tien.items():
            for vn, sd in cvn.items():
                vi_tien_rows.append([vt, vn, sd])
                
        lich_su_rows = [["Thời Gian", "Loại", "Ví Lớn", "Ví Nhỏ", "Số Tiền", "Mô Tả", "Ảnh", "Số Dư Lúc Đó"]]
        for x in lich_su:
            lich_su_rows.append([
                chuan_hoa_thoi_gian(x.get("thoi_gian", "")),
                x.get("loai", ""),
                x.get("vi_to", ""),
                x.get("vi_nho", ""),
                x.get("so_tien", 0),
                x.get("mo_ta", ""),
                x.get("anh", ""),
                x.get("so_du_luc_do", 0)
            ])
            
        res1 = requests.post(URL_CAU_NOI, json={"action": "update_all", "sheetName": "vi_tien", "rows": vi_tien_rows}, timeout=10)
        res2 = requests.post(URL_CAU_NOI, json={"action": "update_all", "sheetName": "lich_su", "rows": lich_su_rows}, timeout=10)
        
        return res1.status_code == 200 and res2.status_code == 200
    except Exception:
        return False

# --- HÀM TẢI DỮ LIỆU TỪ GOOGLE SHEETS (AUTO-RETRY 3 LẦN) ---
def tai_du_lieu():
    mac_dinh = {"vi_tien": {"ví của Dương": {"tiền sinh hoạt": 0}}, "lich_su": []}
    
    for lan_thu in range(3):
        try:
            res = requests.get(URL_CAU_NOI, timeout=5)
            if res.status_code == 200 and "html" not in res.text.lower():
                sheets_data = res.json()
                new_vi_tien, new_lich_su = {}, []
                
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
                                "thoi_gian": chuan_hoa_thoi_gian(row[0]), 
                                "loai": row[1], "vi_to": row[2],
                                "vi_nho": row[3], "so_tien": float(row[4]) if row[4] else 0,
                                "mo_ta": row[5], "anh": row[6] if len(row) > 6 else "" ,
                                "so_du_luc_do": float(row[7]) if len(row) > 7 and row[7] != "" else 0.0
                            })
                if new_vi_tien:
                    st.session_state.data = {"vi_tien": new_vi_tien, "lich_su": new_lich_su}
                    st.session_state.trang_thai_cloud = True
                    return True
        except Exception:
            time.sleep(1.5)
            
    st.session_state.trang_thai_cloud = False
    if os.path.exists(FILE_SAVE):
        try:
            with open(FILE_SAVE, "r", encoding="utf-8") as f:
                st.session_state.data = json.load(f)
                for x in st.session_state.data.get("lich_su", []):
                    x["thoi_gian"] = chuan_hoa_thoi_gian(x.get("thoi_gian", ""))
                return True
        except Exception:
            st.session_state.data = mac_dinh
    else:
        st.session_state.data = mac_dinh
    return False

# --- HÀM TÍNH LẠI TOÀN BỘ SỐ DƯ ---
def recalculate_balances():
    for vl in st.session_state.data["vi_tien"]:
        for vn in st.session_state.data["vi_tien"][vl]:
            st.session_state.data["vi_tien"][vl][vn] = 0.0
            
    for item in reversed(st.session_state.data["lich_su"]):
        vt = item.get("vi_to", "Không rõ")
        vn = item.get("vi_nho", "Không rõ")
        loai = item.get("loai", "Chi tiêu")
        so_tien = item.get("so_tien", 0)
        
        if vt in st.session_state.data["vi_tien"] and vn in st.session_state.data["vi_tien"][vt]:
            if loai == "Nạp tiền":
                st.session_state.data["vi_tien"][vt][vn] += so_tien
            else:
                st.session_state.data["vi_tien"][vt][vn] -= so_tien
            item["so_du_luc_do"] = st.session_state.data["vi_tien"][vt][vn]

# --- CỬA SỔ XÁC NHẬN DIALOG ---
@st.dialog("📝 Xác nhận cập nhật thay đổi")
def xac_nhan_cap_nhat_dialog(idx, du_lieu_moi):
    st.warning("Bạn có chắc chắn muốn ghi đè thông tin mới này lên dữ liệu cũ không?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✔️ Xác nhận lưu", type="primary", use_container_width=True):
            st.session_state.data["lich_su"][idx] = du_lieu_moi
            recalculate_balances()
            if luu_du_lieu():
                st.toast("Đã cập nhật thay đổi thành công!", icon="✅")
                st.rerun()
    with col2:
        if st.button("❌ Hủy", use_container_width=True):
            st.rerun()

@st.dialog("🗑️ Xác nhận xóa vĩnh viễn")
def xac_nhan_xoa_dialog(idx, thong_tin_xoa):
    st.error("⚠️ CẢNH BÁO: Giao dịch này sẽ bị xóa vĩnh viễn.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔥 Đồng ý xóa", type="secondary", use_container_width=True):
            st.session_state.data["lich_su"].pop(idx)
            recalculate_balances()
            if luu_du_lieu():
                st.toast("Đã xóa giao dịch thành công!", icon="🗑️")
                st.rerun()
    with col2:
        if st.button("❌ Hủy", use_container_width=True):
            st.rerun()

# --- KHỞI TẠO STATE ---
if "trang_thai_cloud" not in st.session_state:
    st.session_state.trang_thai_cloud = True

if "data" not in st.session_state:
    tai_du_lieu()
    recalculate_balances()

if "index_can_sua" not in st.session_state:
    st.session_state.index_can_sua = 0

vi_tien = st.session_state.data["vi_tien"]
lich_su = st.session_state.data["lich_su"]

# --- TIÊU ĐỀ APP ---
st.title(" 💸 Hệ Thống Quản Lý Chi Tiêu Đa Nền Tảng")

# --- BANNER POKA-YOKE TOÀN DIỆN ---
if not st.session_state.trang_thai_cloud:
    st.error("🚨 CẢNH BÁO: Mất kết nối tới dữ liệu đám mây Google Sheets! Tất cả tính năng thêm/sửa/xóa đã tạm thời bị KHÓA để bảo vệ an toàn dữ liệu. Vui lòng vào mục 'Cấu hình Hệ thống' bấm Tải lại hoặc F5.")

menu = st.sidebar.radio(
    "Chức năng hệ thống", 
    ["Xem số dư các ví", "Ghi nhận khoản chi", "Chuyển tiền giữa các ví", "Thêm ví & Nạp tiền", "Lịch sử giao dịch", "Cấu hình Hệ thống"]
)

# --- CHỨC NĂNG: XEM SỐ DƯ TẤT CẢ CÁC VÍ ---
if menu == "Xem số dư các ví":
    st.header("📊 Bảng Kê Số Dư Tài Khoản")
    
    # TÍNH NĂNG MỚI: LỰA CHỌN KHOẢNG THỜI GIAN ĐỂ THỐNG KÊ CHI TIÊU/NẠP VÀO
    st.markdown("### 🔍 Lọc thống kê thu chi theo khoảng thời gian")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        ngay_dau = st.date_input("Từ ngày:", value=datetime.now(MUI_GIO_VN).date() - timedelta(days=30), key="view_ngay_dau")
    with col_d2:
        ngay_cuoi = st.date_input("Đến ngày:", value=datetime.now(MUI_GIO_VN).date(), key="view_ngay_cuoi")
        
    tong_nap_khoang_tg = 0.0
    tong_chi_khoang_tg = 0.0
    
    for item in lich_su:
        try:
            tg_dong = chuan_hoa_thoi_gian(item.get("thoi_gian", "")).split(" ")[0]
            ngay_gd = datetime.strptime(tg_dong, "%Y-%m-%d").date()
            if ngay_dau <= ngay_gd <= ngay_cuoi:
                loai_gd = item.get("loai", "")
                so_tien_gd = float(item.get("so_tien", 0))
                if loai_gd == "Nạp tiền":
                    tong_nap_khoang_tg += so_tien_gd
                elif loai_gd in ["Chi tiêu", "Chuyển đi"]:
                    tong_chi_khoang_tg += so_tien_gd
        except Exception:
            pass
            
    # Tách biệt hiển thị 2 mục Nạp và Chi riêng rẽ
    col_metric1, col_metric2 = st.columns(2)
    with col_metric1:
        st.metric(label="📥 TỔNG TIỀN NẠP VÀO (Trong khoảng thời gian trên)", value=f"{tong_nap_khoang_tg:,.0f} VNĐ")
    with col_metric2:
        st.metric(label="💸 TỔNG TIỀN CHI TIÊU / CHUYỂN ĐI (Trong khoảng thời gian trên)", value=f"{tong_chi_khoang_tg:,.0f} VNĐ")
        
    st.markdown("---")
    
    tong_tai_san = sum(sum(cvn.values()) for cvn in vi_tien.values())
    st.metric(label="💰 TỔNG TÀI SẢN HIỆN TẠI (Tất cả các ví cộng lại)", value=f"{tong_tai_san:,.0f} VNĐ")
    st.markdown("---")
    
    for vl, cvn in vi_tien.items():
        tong_vi_lon = sum(cvn.values())
        st.subheader(f"📁 {vl} (Tổng: {tong_vi_lon:,.0f} VNĐ)")
        if not cvn:
            st.info("Ví lớn này chưa có ví con nào.")
        else:
            cols = st.columns(len(cvn) if len(cvn) <= 4 else 4)
            for idx, (vn, sd) in enumerate(cvn.items()):
                with cols[idx % len(cols)]:
                    st.metric(label=f"📂 {vn}", value=f"{sd:,.0f} VNĐ")

# --- CHỨC NĂNG: GHI NHẬN KHOẢN CHI ---
elif menu == "Ghi nhận khoản chi":
    st.header("🛒 Ghi Nhận Khoản Chi Mới")
    col1, col2 = st.columns(2)
    with col1:
        vi_to_sel = st.selectbox("Chọn Ví Lớn:", list(vi_tien.keys()))
        vi_nho_sel = st.selectbox("Chọn Ví Nhỏ:", list(vi_tien[vi_to_sel].keys()) if vi_to_sel else [])
        so_du_hien_tai = vi_tien[vi_to_sel][vi_nho_sel] if vi_to_sel and vi_nho_sel else 0
        st.info(f"💳 Số dư hiện tại của ví này: **{so_du_hien_tai:,.0f} VNĐ**")
        anh_chi_file = st.file_uploader("📷 Chụp hoặc tải ảnh hóa đơn chi:", type=["png", "jpg", "jpeg"])
    with col2:
        mo_ta = st.text_input("Nội dung / Mô tả khoản chi:")
        so_tien = st.number_input("Số tiền chi (VNĐ):", min_value=0, step=1000, value=0)
        
    if st.button("🚀 Thực hiện Ghi nhận chi tiêu", use_container_width=True, disabled=not st.session_state.trang_thai_cloud):
        if not mo_ta or so_tien <= 0:
            st.error("Vui lòng điền đầy đủ mô tả và số tiền hợp lệ!")
        elif so_tien > so_du_hien_tai:
            st.error("Số dư tài khoản không đủ để thực hiện giao dịch này!")
        else:
            duong_dan_anh = xu_ly_va_luu_anh(anh_chi_file, "CHI")
            st.session_state.data["lich_su"].insert(0, {
                "thoi_gian": datetime.now(MUI_GIO_VN).strftime("%Y-%m-%d %H:%M:%S"),
                "loai": "Chi tiêu", "vi_to": vi_to_sel, "vi_nho": vi_nho_sel,
                "so_tien": so_tien, "mo_ta": mo_ta, "anh": duong_dan_anh
            })
            recalculate_balances()
            if luu_du_lieu():
                st.toast(f"🎉 Đã ghi nhận chi {so_tien:,.0f} VNĐ!", icon="✅")
                st.success(f"🎉 Đã ghi nhận thành công khoản chi cho: '{mo_ta}'. Đã đồng bộ lên Cloud!")
                st.rerun()

# --- CHỨC NĂNG: CHUYỂN TIỀN GIỮA CÁC VÍ ---
elif menu == "Chuyển tiền giữa các ví":
    st.header("🔄 Chuyển Tiền Qua Lại Giữa Các Ví Nội Bộ")
    
    col_nguon, col_dich = st.columns(2)
    with col_nguon:
        st.subheader("📦 Từ Ví Nguồn (Trừ tiền)")
        vi_to_nguon = st.selectbox("Chọn Ví Lớn Nguồn:", list(vi_tien.keys()), key="to_nguon")
        vi_nho_nguon = st.selectbox("Chọn Ví Nhỏ Nguồn:", list(vi_tien[vi_to_nguon].keys()) if vi_to_nguon else [], key="nho_nguon")
        so_du_nguon = vi_tien[vi_to_nguon][vi_nho_nguon] if vi_to_nguon and vi_nho_nguon else 0
        st.info(f"💳 Số dư khả dụng: **{so_du_nguon:,.0f} VNĐ**")
        
    with col_dich:
        st.subheader("🎯 Đến Ví Đích (Cộng tiền)")
        vi_to_dich = st.selectbox("Chọn Ví Lớn Đích:", list(vi_tien.keys()), key="to_dich")
        vi_nho_dich = st.selectbox("Chọn Ví Nhỏ Đích:", list(vi_tien[vi_to_dich].keys()) if vi_to_dich else [], key="nho_dich")
        so_du_dich = vi_tien[vi_to_dich][vi_nho_dich] if vi_to_dich and vi_nho_dich else 0
        st.info(f"💳 Số dư hiện tại: **{so_du_dich:,.0f} VNĐ**")
        
    st.markdown("---")
    col_txt, col_num = st.columns(2)
    with col_txt:
        mo_ta_chuyen = st.text_input("Ghi chú nội dung chuyển tiền:", value="Chuyển quỹ nội bộ")
    with col_num:
        so_tien_chuyen = st.number_input("Số tiền muốn chuyển (VNĐ):", min_value=0, step=1000, value=0)
        
    if st.button("🚀 Thực Hiện Lệnh Chuyển Tiền", type="primary", use_container_width=True, disabled=not st.session_state.trang_thai_cloud):
        if so_tien_chuyen <= 0:
            st.error("Vui lòng điền số tiền cần chuyển lớn hơn 0 VNĐ!")
        elif vi_to_nguon == vi_to_dich and vi_nho_nguon == vi_nho_dich:
            st.error("🚨 Lỗi Poka-yoke: Ví nguồn và Ví đích đang trùng nhau hoàn toàn! Vui lòng chọn ví đích khác.")
        elif so_tien_chuyen > so_du_nguon:
            st.error(f"🚨 Sai số dư: Ví nguồn chỉ còn {so_du_nguon:,.0f} VNĐ, không đủ để chuyển {so_tien_chuyen:,.0f} VNĐ!")
        else:
            thoi_gian_gd = datetime.now(MUI_GIO_VN).strftime("%Y-%m-%d %H:%M:%S")
            
            st.session_state.data["lich_su"].insert(0, {
                "thoi_gian": thoi_gian_gd,
                "loai": "Chuyển đi",
                "vi_to": vi_to_nguon,
                "vi_nho": vi_nho_nguon,
                "so_tien": so_tien_chuyen,
                "mo_ta": f"🔄 [CHUYỂN VÍ] Sang {vi_to_dich}➔{vi_nho_dich} | {mo_ta_chuyen}",
                "anh": ""
            })
            
            st.session_state.data["lich_su"].insert(0, {
                "thoi_gian": thoi_gian_gd,
                "loai": "Nạp tiền",
                "vi_to": vi_to_dich,
                "vi_nho": vi_nho_dich,
                "so_tien": so_tien_chuyen,
                "mo_ta": f"📥 [NHẬN VÍ] Từ {vi_to_nguon}➔{vi_nho_nguon} | {mo_ta_chuyen}",
                "anh": ""
            })
            
            recalculate_balances()
            if luu_du_lieu():
                st.toast(f"🎉 Đã chuyển thành công {so_tien_chuyen:,.0f} VNĐ!", icon="✅")
                st.success(f"🎉 Thành công! Đã chuyển tiền từ {vi_nho_nguon} sang {vi_nho_dich} và đồng bộ lên Google Sheets!")
                st.rerun()

# --- CHỨC NĂNG: THÊM VÍ / NẠP TIỀN / XÓA VÍ ---
elif menu == "Thêm ví & Nạp tiền":
    st.header("➕ Quản Lý Tài Khoản & Nạp Tiền")
    tab1, tab2, tab3, tab4 = st.tabs(["💵 Nạp Tiền Vào Ví", "📁 Tạo Ví Lớn Mới", "📂 Tạo Ví Nhỏ Mới", "❌ Xóa Ví"])
    
    with tab1:
        v_to = st.selectbox("Chọn Ví Lớn cần nạp:", list(vi_tien.keys()), key="nap_to")
        v_nho = st.selectbox("Chọn Ví Nhỏ cần nạp:", list(vi_tien[v_to].keys()) if v_to else [], key="nap_nho")
        st_nap = st.number_input("Số tiền nạp thêm (VNĐ):", min_value=0, step=1000, key="tien_nap")
        mt_nap = st.text_input("Ghi chú nạp tiền:", value="Nạp tiền vào tài khoản", key="note_nap")
        anh_nap_file = st.file_uploader("📷 Chụp hoặc tải ảnh hóa đơn nạp:", type=["png", "jpg", "jpeg"], key="upload_nap")
        
        if st.button("📥 Xác nhận nạp tiền", type="primary", disabled=not st.session_state.trang_thai_cloud):
            if st_nap > 0:
                duong_dan_anh = xu_ly_va_luu_anh(anh_nap_file, "NAP")
                st.session_state.data["lich_su"].insert(0, {
                    "thoi_gian": datetime.now(MUI_GIO_VN).strftime("%Y-%m-%d %H:%M:%S"),
                    "loai": "Nạp tiền", "vi_to": v_to, "vi_nho": v_nho,
                    "so_tien": st_nap, "mo_ta": mt_nap, "anh": duong_dan_anh
                })
                recalculate_balances()
                if luu_du_lieu():
                    st.toast("📥 Nạp tiền thành công và đã đồng bộ!", icon="✅")
                    st.rerun()
                
    with tab2:
        ten_vi_to_moi = st.text_input("Nhập tên Ví Lớn mới:")
        if st.button("Tạo Ví Lớn", disabled=not st.session_state.trang_thai_cloud):
            if ten_vi_to_moi and ten_vi_to_moi not in vi_tien:
                st.session_state.data["vi_tien"][ten_vi_to_moi] = {"Tài khoản chính": 0}
                if luu_du_lieu(): st.rerun()
                
    with tab3:
        v_to_thuoc = st.selectbox("Chọn Ví Lớn chứa ví nhỏ này:", list(vi_tien.keys()))
        ten_vi_nho_moi = st.text_input("Nhập tên Ví Nhỏ mới:")
        if st.button("Tạo Ví Nhỏ", disabled=not st.session_state.trang_thai_cloud):
            if v_to_thuoc and ten_vi_nho_moi and ten_vi_nho_moi not in vi_tien[v_to_thuoc]:
                st.session_state.data["vi_tien"][v_to_thuoc][ten_vi_nho_moi] = 0
                if luu_du_lieu(): st.rerun()

    with tab4:
        st.subheader("🗑️ Xóa Ví Không Sử Dụng")
        danh_sach_xoa = []
        for vt, cvn in vi_tien.items():
            danh_sach_xoa.append(f"[Ví Lớn] {vt}")
            for vn in cvn.keys(): danh_sach_xoa.append(f"[Ví Nhỏ] {vt} ➔ {vn}")
                
        if danh_sach_xoa:
            muc_muon_xoa = st.selectbox("Chọn mục ví muốn xóa vĩnh viễn:", danh_sach_xoa)
            xac_nhan_xoa = st.checkbox("Tôi đồng ý xóa ví này.")
            if st.button("🔥 XÁC NHẬN XÓA VÍ VĨNH VIỄN", type="secondary", disabled=not xac_nhan_xoa or not st.session_state.trang_thai_cloud, use_container_width=True):
                if muc_muon_xoa.startswith("[Ví Lớn]"):
                    del st.session_state.data["vi_tien"][muc_muon_xoa.replace("[Ví Lớn] ", "")]
                elif muc_muon_xoa.startswith("[Ví Nhỏ]"):
                    ten_vi_lon, ten_vi_nho = muc_muon_xoa.replace("[Ví Nhỏ] ", "").split(" ➔ ")
                    del st.session_state.data["vi_tien"][ten_vi_lon][ten_vi_nho]
                recalculate_balances()
                if luu_du_lieu(): st.rerun()

# --- CHỨC NĂNG: LỊCH SỬ GIAO DỊCH (ĐÃ NÂNG CẤP HIỂN THỊ SỐ DƯ & ẢNH) ---
elif menu == "Lịch sử giao dịch":
    st.header("📊 Nhật Ký Biến Động Số Dư")
    st.subheader("🛠️ Khu Vực Chỉnh Sửa / Xóa Giao Dịch Lỗi")
    if not lich_su:
        st.info("Chưa có giao dịch nào để chỉnh sửa.")
    else:
        danh_sach_chon_sua = []
        for idx, item in enumerate(lich_su):
            tg_chuan = chuan_hoa_thoi_gian(item.get('thoi_gian',''))
            danh_sach_chon_sua.append(f"[{idx}] {tg_chuan} | {item.get('loai','')} | {item.get('mo_ta','')[:20]}... | {item.get('so_tien',0):,.0f}đ")
            
        if st.session_state.index_can_sua >= len(lich_su):
            st.session_state.index_can_sua = 0
            
        chon_ban_ghi = st.selectbox("Chọn dòng giao dịch bạn muốn sửa đổi hoặc xóa:", danh_sach_chon_sua, index=st.session_state.index_can_sua)
        idx_sua = int(chon_ban_ghi.split("]")[0].replace("[", ""))
        st.session_state.index_can_sua = idx_sua
        item_sua = lich_su[idx_sua]
        
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            loai_moi = st.selectbox("Sửa Loại GD:", ["Chi tiêu", "Nạp tiền", "Chuyển đi"], index=0 if item_sua.get("loai") == "Chi tiêu" else (1 if item_sua.get("loai") == "Nạp tiền" else 2))
            vi_to_moi = st.selectbox("Sửa Ví Lớn:", list(vi_tien.keys()), index=list(vi_tien.keys()).index(item_sua.get("vi_to")) if item_sua.get("vi_to") in vi_tien else 0)
        with col_s2:
            vi_nho_moi = st.selectbox("Sửa Ví Nhỏ:", list(vi_tien[vi_to_moi].keys()) if vi_to_moi else [], index=list(vi_tien[vi_to_moi].keys()).index(item_sua.get("vi_nho")) if vi_to_moi and item_sua.get("vi_nho") in vi_tien[vi_to_moi] else 0)
            so_tien_moi = st.number_input("Sửa Số tiền (VNĐ):", min_value=0, value=int(item_sua.get("so_tien", 0)), step=1000)
        with col_s3:
            mo_ta_moi = st.text_input("Sửa Mô tả:", value=item_sua.get("mo_ta", ""))
            thoi_gian_moi = st.text_input("Sửa Thời gian:", value=chuan_hoa_thoi_gian(item_sua.get("thoi_gian", "")))

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("💾 CẬP NHẬT THAY ĐỔI", type="primary", use_container_width=True, disabled=not st.session_state.trang_thai_cloud):
                du_lieu_moi = {
                    "thoi_gian": chuan_hoa_thoi_gian(thoi_gian_moi), "loai": loai_moi, "vi_to": vi_to_moi,
                    "vi_nho": vi_nho_moi, "so_tien": so_tien_moi, "mo_ta": mo_ta_moi, "anh": item_sua.get("anh", "")
                }
                xac_nhan_cap_nhat_dialog(idx_sua, du_lieu_moi)
        with col_btn2:
            if st.button("🗑️ XÓA HẲN GIAO DỊCH NÀY", type="secondary", use_container_width=True, disabled=not st.session_state.trang_thai_cloud):
                xac_nhan_xoa_dialog(idx_sua, item_sua)

    st.markdown("---")
    st.subheader("📋 Dòng lịch sử giao dịch chi tiết")
    
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1: ngay_bat_dau = st.date_input("Từ ngày:", value=datetime.now(MUI_GIO_VN).date() - timedelta(days=30))
    with col_f2: ngay_ket_thuc = st.date_input("Đến ngày:", value=datetime.now(MUI_GIO_VN).date())
    with col_f3: vi_to_loc = st.selectbox("Lọc theo Ví Lớn:", ["Tất cả"] + list(vi_tien.keys()))
    with col_f4: vi_nho_loc = st.selectbox("Lọc theo Ví Nhỏ:", ["Tất cả"] if vi_to_loc == "Tất cả" else ["Tất cả"] + list(vi_tien[vi_to_loc].keys()))
            
    lich_su_loc = []
    for idx_goc, item in enumerate(lich_su):
        if (vi_to_loc == "Tất cả" or item.get("vi_to") == vi_to_loc) and (vi_nho_loc == "Tất cả" or item.get("vi_nho") == vi_nho_loc):
            try:
                ngay_gd = datetime.strptime(chuan_hoa_thoi_gian(item.get("thoi_gian", "")).split(" ")[0], "%Y-%m-%d").date()
                if ngay_bat_dau <= ngay_gd <= ngay_ket_thuc: 
                    lich_su_loc.append((idx_goc, item))
            except Exception: 
                lich_su_loc.append((idx_goc, item))
                    
    if not lich_su_loc:
        st.info("Chưa có giao dịch nào thỏa mãn bộ lọc.")
    else:
        # THAY THẾ TOÀN BỘ VÒNG LẶP NÚT BẤM CŨ THÀNH CONTAINER HIỂN THỊ CHI TIẾT SỐ DƯ VÀ ẢNH
        for idx_goc, item in lich_su_loc:
            sign = "+" if item.get("loai") == "Nạp tiền" else "-"
            sd_luc_do = item.get("so_du_luc_do", 0)
            
            with st.container(border=True):
                col_info, col_btn = st.columns([6, 1])
                with col_info:
                    st.markdown(f"⏱️ **{chuan_hoa_thoi_gian(item.get('thoi_gian'))}** | **{item.get('vi_to')}** ➔ **{item.get('vi_nho')}**")
                    st.markdown(f"💰 **Số tiền:** `{sign}{item.get('so_tien',0):,.0f} VNĐ` ({item.get('loai')}) | 🧾 **Số dư lúc đó:** `{sd_luc_do:,.0f} VNĐ`")
                    st.markdown(f"📝 **Mô tả:** {item.get('mo_ta')}")
                    
                    # KIỂM TRA VÀ VẼ ẢNH RA MÀN HÌNH NHẬT KÝ
                    duong_dan_anh = item.get("anh", "")
                    if duong_dan_anh:
                        if os.path.exists(duong_dan_anh):
                            st.image(duong_dan_anh, caption="📸 Ảnh minh chứng đính kèm", width=300)
                        elif str(duong_dan_anh).startswith("http"):
                            st.image(duong_dan_anh, caption="📸 Ảnh minh chứng (Đám mây)", width=300)
                with col_btn:
                    if st.button("✏️ Sửa/Xóa", key=f"btn_row_{idx_goc}", use_container_width=True):
                        st.session_state.index_can_sua = idx_goc
                        st.rerun()

# --- CHỨC NĂNG: CẤU HÌNH HỆ THỐNG & ĐỒNG BỘ ---
elif menu == "Cấu hình Hệ thống":
    st.header("⚙️ Quản Lý Cấu Hình Kết Nối")
    
    if st.session_state.trang_thai_cloud:
        st.success("✅ Đã kết nối thành công tới máy chủ Google Sheets!")
    else:
        st.error("❌ Kết nối thất bại: URL lỗi hoặc mất mạng quốc tế.")
        
    st.subheader("Thao tác thủ công")
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("🔄 Tải lại toàn bộ dữ liệu từ Google Sheets", use_container_width=True):
            if tai_du_lieu():
                recalculate_balances()
                st.success("Đã kết nối lại thành công!")
                st.rerun()
    with col_b2:
        if st.button("📤 Ép đồng bộ dữ liệu App lên Google Sheets", use_container_width=True, disabled=not st.session_state.trang_thai_cloud):
            recalculate_balances()
            if luu_du_lieu(): st.success("Đồng bộ thành công!")
