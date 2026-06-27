import streamlit as st
import json
import os
import requests
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageOps

# --- CẤU HÌNH HỆ THỐNG ---
FILE_SAVE = "dulieu_vi_cloud.json"
THU_MUC_ANH = "anh_giao_dich"

# DÁN ĐOẠN URL WEB APP GOOGLE APPS SCRIPT CỦA BẠN VÀO ĐÂY:
URL_CAU_NOI = "https://script.google.com/macros/s/AKfycbx3dXuQdWLEH_BTogMnF6O-H0x-w4QHHakUgZevcQYT2DyDS8jHhzanZnaCDWf3IwWeg/exec"

st.set_page_config(page_title="Quản Lý Chi Tiêu Đa Nền Tảng", page_icon="💰", layout="wide")

if not os.path.exists(THU_MUC_ANH):
    os.makedirs(THU_MUC_ANH)

MUI_GIO_VN = timezone(timedelta(hours=7))

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
                
        # Thêm cột "Số Dư Lúc Đó" vào cấu trúc bảng lịch sử trên Google Sheets
        lich_su_rows = [["Thời Gian", "Loại", "Ví Lớn", "Ví Nhỏ", "Số Tiền", "Mô Tả", "Ảnh", "Số Dư Lúc Đó"]]
        for x in lich_su:
            lich_su_rows.append([
                x.get("thoi_gian", ""),
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

# --- HÀM TẢI DỮ LIỆU TỪ GOOGLE SHEETS ---
def tai_du_lieu():
    mac_dinh = {"vi_tien": {"ví của Dương": {"tiền sinh hoạt": 0}}, "lich_su": []}
    try:
        res = requests.get(URL_CAU_NOI, timeout=8)
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
                            "thoi_gian": row[0], "loai": row[1], "vi_to": row[2],
                            "vi_nho": row[3], "so_tien": float(row[4]) if row[4] else 0,
                            "mo_ta": row[5], "anh": row[6] if len(row) > 6 else "",
                            "so_du_luc_do": float(row[7]) if len(row) > 7 and row[7] != "" else 0.0
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

# --- HÀM TÍNH LẠI TOÀN BỘ SỐ DƯ & SỐ DƯ THỜI ĐIỂM ĐÓ ---
def recalculate_balances():
    """Quét lũy tiến toàn bộ lịch sử để tính số dư hiện tại và số dư ngay tại thời điểm xảy ra GD"""
    for vl in st.session_state.data["vi_tien"]:
        for vn in st.session_state.data["vi_tien"][vl]:
            st.session_state.data["vi_tien"][vl][vn] = 0.0
            
    # Duyệt ngược từ dòng lịch sử cũ nhất tiến dần tới mới nhất
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
            # Lưu lại trạng thái số dư ví con ngay sau khi khớp lệnh này
            item["so_du_luc_do"] = st.session_state.data["vi_tien"][vt][vn]

if "data" not in st.session_state:
    tai_du_lieu()
    recalculate_balances()

vi_tien = st.session_state.data["vi_tien"]
lich_su = st.session_state.data["lich_su"]

# --- GIAO DIỆN ĐIỀU HƯỚNG ---
st.title(" 💸 Hệ Thống Quản Lý Chi Tiêu Đa Nền Tảng")
menu = st.sidebar.radio(
    "Chức năng hệ thống", 
    ["Xem số dư các ví", "Ghi nhận khoản chi", "Thêm ví & Nạp tiền", "Lịch sử giao dịch", "Cấu hình Hệ thống"]
)

# --- MỤC MỚI BỔ SUNG: XEM SỐ DƯ TẤT CẢ CÁC VÍ ---
if menu == "Xem số dư các ví":
    st.header("📊 Bảng Kê Số Dư Tài Khoản")
    
    # Tính tổng tài sản thực tế trong toàn hệ thống
    tong_tai_san = sum(sum(cvn.values()) for cvn in vi_tien.values())
    st.metric(label="💰 TỔNG TÀI SẢN (Tất cả các ví cộng lại)", value=f"{tong_tai_san:,.0f} VNĐ")
    st.markdown("---")
    
    # Hiển thị từng Ví Lớn và cấu trúc Ví Nhỏ bên trong
    for vl, cvn in vi_tien.items():
        tong_vi_lon = sum(cvn.values())  # Tính tổng ví lớn = các ví con cộng lại
        
        st.subheader(f"📁 {vl} (Tổng: {tong_vi_lon:,.0f} VNĐ)")
        if not cvn:
            st.info("Ví lớn này chưa có ví con nào.")
        else:
            # Tạo các cột ngang hiển thị danh sách ví con tương ứng
            cols = st.columns(len(cvn) if len(cvn) <= 4 else 4)
            for idx, (vn, sd) in enumerate(cvn.items()):
                with cols[idx % len(cols)]:
                    st.metric(label=f"📂 {vn}", value=f"{sd:,.0f} VNĐ")
        st.markdown("<br>", unsafe_allow_html=True)

# --- CHỨC NĂNG 1: GHI NHẬN KHOẢN CHI ---
elif menu == "Ghi nhận khoản chi":
    st.header("🛒 Ghi Nhận Khoản Chi Mới")
    col1, col2 = st.columns(2)
    with col1:
        vi_to_sel = st.selectbox("Chọn Ví Lớn:", list(vi_tien.keys()))
        vi_nho_sel = st.selectbox("Chọn Ví Nhỏ:", list(vi_tien[vi_to_sel].keys()) if vi_to_sel else [])
        so_du_hien_tai = vi_tien[vi_to_sel][vi_nho_sel] if vi_to_sel and vi_nho_sel else 0
        st.info(f"💳 Số dư hiện tại của ví này: **{so_du_hien_tai:,.0f} VNĐ**")
        anh_chi_file = st.file_uploader("📷 Chụp hoặc tải ảnh hóa đơn chi:", type=["png", "jpg", "jpeg"], key="upload_chi")
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
            st.session_state.data["lich_su"].insert(0, {
                "thoi_gian": datetime.now(MUI_GIO_VN).strftime("%Y-%m-%d %H:%M:%S"),
                "loai": "Chi tiêu", "vi_to": vi_to_sel, "vi_nho": vi_nho_sel,
                "so_tien": so_tien, "mo_ta": mo_ta, "anh": duong_dan_anh
            })
            recalculate_balances()  # Cập nhật số dư và tính số dư thời điểm đó
            if luu_du_lieu():
                st.toast(f"🎉 Đã ghi nhận chi {so_tien:,.0f} VNĐ!", icon="✅")
                st.success(f"🎉 Đã ghi nhận thành công khoản chi cho: '{mo_ta}'. Đã đồng bộ lên Cloud!")
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
        anh_nap_file = st.file_uploader("📷 Chụp hoặc tải ảnh hóa đơn nạp:", type=["png", "jpg", "jpeg"], key="upload_nap")
        
        if st.button("📥 Xác nhận nạp tiền", type="primary"):
            if st_nap > 0:
                duong_dan_anh = xu_ly_va_luu_anh(anh_nap_file, "NAP")
                st.session_state.data["lich_su"].insert(0, {
                    "thoi_gian": datetime.now(MUI_GIO_VN).strftime("%Y-%m-%d %H:%M:%S"),
                    "loai": "Nạp tiền", "vi_to": v_to, "vi_nho": v_nho,
                    "so_tien": st_nap, "mo_ta": mt_nap, "anh": duong_dan_anh
                })
                recalculate_balances()  # Đồng bộ tính toán
                if luu_du_lieu():
                    st.toast("📥 Nạp tiền thành công và đã đồng bộ!", icon="✅")
                    st.success(f"✅ Đã nạp thành công {st_nap:,.0f} VNĐ vào {v_to} -> {v_nho}!")
                    st.rerun()
                
    with tab2:
        ten_vi_to_moi = st.text_input("Nhập tên Ví Lớn mới (Ví dụ: Ví Tiết Kiệm, Ví Kinh Doanh):")
        if st.button("Tạo Ví Lớn"):
            if ten_vi_to_moi and ten_vi_to_moi not in vi_tien:
                st.session_state.data["vi_tien"][ten_vi_to_moi] = {"Tài khoản chính": 0}
                if luu_du_lieu():
                    st.toast(f"Đã tạo Ví Lớn: {ten_vi_to_moi}", icon="📁")
                    st.success(f"📁 Đã khởi tạo thành công Ví Lớn: {ten_vi_to_moi}!")
                    st.rerun()
                
    with tab3:
        v_to_thuoc = st.selectbox("Chọn Ví Lớn chứa ví nhỏ này:", list(vi_tien.keys()), key="thuoc_to")
        ten_vi_nho_moi = st.text_input("Nhập tên Ví Nhỏ mới (Ví dụ: Tiền Ăn, Quỹ tiêu vặt):")
        if st.button("Tạo Ví Nhỏ"):
            if v_to_thuoc and ten_vi_nho_moi and ten_vi_nho_moi not in vi_tien[v_to_thuoc]:
                st.session_state.data["vi_tien"][v_to_thuoc][ten_vi_nho_moi] = 0
                if luu_du_lieu():
                    st.toast(f"Đã tạo Ví Nhỏ: {ten_vi_nho_moi}", icon="📂")
                    st.success(f"📂 Đã tạo thành công Ví Nhỏ trong mục {v_to_thuoc}!")
                    st.rerun()

    with tab4:
        st.subheader("🗑️ Xóa Ví Không Sử Dụng")
        danh_sach_xoa = []
        for vt, cvn in vi_tien.items():
            danh_sach_xoa.append(f"[Ví Lớn] {vt}")
            for vn in cvn.keys():
                danh_sach_xoa.append(f"[Ví Nhỏ] {vt} ➔ {vn}")
                
        if danh_sach_xoa:
            muc_muon_xoa = st.selectbox("Chọn mục ví muốn xóa vĩnh viễn:", danh_sach_xoa)
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
                recalculate_balances()
                if luu_du_lieu():
                    st.toast("Đã xóa mục ví thành công!", icon="🗑️")
                    st.success("Đã cập nhật cấu trúc ví mới lên Google Sheets!")
                    st.rerun()

# --- CHỨC NĂNG 3: LỊCH SỬ GIAO DỊCH (CÓ SỬA ĐỔI & HIỂN THỊ SỐ DƯ LÚC ĐÓ) ---
elif menu == "Lịch sử giao dịch":
    st.header("📊 Nhật Ký Biến Động Số Dư")
    
    st.subheader("🛠️ Khu Vực Chỉnh Sửa / Xóa Giao Dịch Lỗi")
    if not lich_su:
        st.info("Chưa có giao dịch nào để chỉnh sửa.")
    else:
        danh_sach_chon_sua = []
        for idx, item in enumerate(lich_su):
            danh_sach_chon_sua.append(f"[{idx}] {item.get('thoi_gian','')} | {item.get('loai','')} | {item.get('mo_ta','')[:20]}... | {item.get('so_tien',0):,.0f}đ")
            
        chon_ban_ghi = st.selectbox("Chọn dòng giao dịch bạn muốn sửa đổi hoặc xóa:", danh_sach_chon_sua)
        idx_sua = int(chon_ban_ghi.split("]")[0].replace("[", ""))
        item_sua = lich_su[idx_sua]
        
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            loai_moi = st.selectbox("Sửa Loại GD:", ["Chi tiêu", "Nạp tiền"], index=0 if item_sua.get("loai") == "Chi tiêu" else 1)
            vi_to_moi = st.selectbox("Sửa Ví Lớn:", list(vi_tien.keys()), index=list(vi_tien.keys()).index(item_sua.get("vi_to")) if item_sua.get("vi_to") in vi_tien else 0)
        with col_s2:
            vi_nho_moi = st.selectbox("Sửa Ví Nhỏ:", list(vi_tien[vi_to_moi].keys()) if vi_to_moi else [], index=list(vi_tien[vi_to_moi].keys()).index(item_sua.get("vi_nho")) if vi_to_moi and item_sua.get("vi_nho") in vi_tien[vi_to_moi] else 0)
            so_tien_moi = st.number_input("Sửa Số tiền (VNĐ):", min_value=0, value=int(item_sua.get("so_tien", 0)), step=1000)
        with col_s3:
            mo_ta_moi = st.text_input("Sửa Mô tả:", value=item_sua.get("mo_ta", ""))
            thoi_gian_moi = st.text_input("Sửa Thời gian:", value=item_sua.get("thoi_gian", ""))

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("💾 CẬP NHẬT THAY ĐỔI", type="primary", use_container_width=True):
                st.session_state.data["lich_su"][idx_sua] = {
                    "thoi_gian": thoi_gian_moi, "loai": loai_moi, "vi_to": vi_to_moi,
                    "vi_nho": vi_nho_moi, "so_tien": so_tien_moi, "mo_ta": mo_ta_moi, "anh": item_sua.get("anh", "")
                }
                recalculate_balances()
                if luu_du_lieu():
                    st.toast("Đã sửa đổi giao dịch và cập nhật lại toàn bộ số dư thời điểm!", icon="📝")
                    st.success("Đã cập nhật thay đổi thành công lên Cloud Sheets!")
                    st.rerun()
        with col_btn2:
            if st.button("🗑️ XÓA HẲN GIAO DỊCH NÀY", type="secondary", use_container_width=True):
                st.session_state.data["lich_su"].pop(idx_sua)
                recalculate_balances()
                if luu_du_lieu():
                    st.toast("Đã xóa giao dịch thành công!", icon="🗑️")
                    st.success("Đã xóa bản ghi giao dịch và đồng bộ tính lại tiền thành công!")
                    st.rerun()

    st.markdown("---")
    st.subheader("📋 Dòng lịch sử giao dịch chi tiết")
    if not lich_su:
        st.write("Chưa có giao dịch nào được ghi nhận.")
    else:
        for item in lich_su:
            loai_gd = item.get("loai", "Chi tiêu")
            color = "green" if loai_gd == "Nạp tiền" else "red"
            sign = "+" if loai_gd == "Nạp tiền" else "-"
            
            t_gian = item.get("thoi_gian", "Không rõ")
            v_t = item.get("vi_to", "Không rõ")
            v_n = item.get("vi_nho", "Không rõ")
            s_t = item.get("so_tien", 0)
            m_t = item.get("mo_ta", "")
            sd_luc_do = item.get("so_du_luc_do", 0)  # Lấy số dư tại thời điểm đó
            
            # Đã cấu hình thêm hiển thị "(Số dư lúc đó: X VNĐ)"
            st.markdown(f"⏱️ `{t_gian}` | **{v_t} ➔ {v_n}** | <span style='color:{color}'>{sign} {s_t:,.0f} VNĐ</span> *(Số dư lúc đó: **{sd_luc_do:,.0f}** VNĐ)* | Nội dung: *{m_t}*", unsafe_allow_html=True)
            if item.get("anh") and os.path.exists(item["anh"]):
                st.image(item["anh"], caption="Ảnh hóa đơn đính kèm", width=150)

# --- CHỨC NĂNG 4: CẤU HÌNH HỆ THỐNG & ĐỒNG BỘ ---
elif menu == "Cấu hình Hệ thống":
    st.header("⚙️ Quản Lý Cấu Hình Kết Nối")
    try:
        ping = requests.get(URL_CAU_NOI, timeout=5)
        if ping.status_code == 200 and "html" not in ping.text.lower():
            st.success("✅ Đã kết nối thành công tới máy chủ Google Sheets!")
        else:
            st.error("❌ Kết nối thất bại: URL lỗi.")
    except Exception as e:
        st.error(f"❌ Kết nối thất bại: {e}")
        
    st.subheader("Thao tác thủ công")
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("🔄 Tải lại toàn bộ dữ liệu từ Google Sheets", use_container_width=True):
            if tai_du_lieu():
                recalculate_balances()
                st.success("Đã nạp lại bộ nhớ từ dữ liệu gốc thành công!")
                st.rerun()
    with col_b2:
        if st.button("📤 Ép đồng bộ dữ liệu App lên Google Sheets", use_container_width=True):
            recalculate_balances()
            if luu_du_lieu():
                st.success("Đã đồng bộ đè dữ liệu lên Google Sheets thành công!")
