import streamlit as st
import json
import os
import shutil
from datetime import datetime
import pandas as pd
import requests  
from PIL import Image, ImageOps  # Thêm Pillow để xử lý ảnh chụp từ điện thoại

# Thiết lập cấu hình trang web (Giao diện rộng, tối ưu mobile)
st.set_page_config(page_title="Quản Lý Chi Tiêu", page_icon="💰", layout="centered")

# Cấu hình lưu trữ và Đường link cầu nối Google Sheets của bạn
FILE_SAVE = "dulieu_vi_cloud.json"
THU_MUC_ANH = "anh_giao_dich"
URL_CAU_NOI = "https://script.google.com/macros/s/AKfycbx3dXuQdWLEH_BTogMnF6O-H0x-w4QHHakUgZevcQYT2DyDS8jHhzanZnaCDWf3IwWeg/exec"

if not os.path.exists(THU_MUC_ANH):
    os.makedirs(THU_MUC_ANH)

# --- HÀM TẢI DỮ LIỆU TỪ GOOGLE SHEETS ---
def tai_du_lieu_tu_sheets():
    try:
        response = requests.get(URL_CAU_NOI, timeout=10)
        if response.status_code == 200:
            gs_data = response.json()
            vi_tien = {}
            lich_su = []
            
            # 1. Đọc dữ liệu từ sheet "vi_tien"
            if "vi_tien" in gs_data and len(gs_data["vi_tien"]) > 1:
                rows = gs_data["vi_tien"]
                for row in rows[1:]:  
                    if len(row) >= 3:
                        vt, vn, sd = str(row[0]).strip(), str(row[1]).strip(), row[2]
                        if vt and vn:
                            if vt not in vi_tien:
                                vi_tien[vt] = {}
                            try: vi_tien[vt][vn] = int(float(sd))
                            except: vi_tien[vt][vn] = 0
            
            # 2. Đọc dữ liệu từ sheet "lich_su"
            if "lich_su" in gs_data and len(gs_data["lich_su"]) > 1:
                rows = gs_data["lich_su"]
                for row in rows[1:]:  
                    if len(row) >= 6:
                        anh_path = str(row[6]).strip() if len(row) > 6 else ""
                        try: so_tien = int(float(row[4]))
                        except: so_tien = 0
                        lich_su.append({
                            "thoi_gian": str(row[0]),
                            "loai": str(row[1]),
                            "vi_to": str(row[2]),
                            "vi_nho": str(row[3]),
                            "so_tien": so_tien,
                            "mo_ta": str(row[5]),
                            "anh": anh_path
                        })
            
            if vi_tien or lich_su:
                return {"vi_tien": vi_tien, "lich_su": lich_su}
    except Exception as e:
        st.warning(f"⚠️ Không thể kết nối lấy dữ liệu từ Google Sheets ({e}). Đang dùng dữ liệu dự phòng.")
    
    if os.path.exists(FILE_SAVE):
        with open(FILE_SAVE, "r", encoding="utf-8") as f:
            try:
                du_lieu_cu = json.load(f)
                if "vi_tien" not in du_lieu_cu:
                    return {"vi_tien": du_lieu_cu, "lich_su": []}
                return du_lieu_cu
            except:
                pass
    return {"vi_tien": {}, "lich_su": []}

# --- HÀM ĐỒNG BỘ DỮ LIỆU LÊN GOOGLE SHEETS ---
def luu_du_lieu():
    with open(FILE_SAVE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.data, f, ensure_ascii=False)
        
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
            
        requests.post(URL_CAU_NOI, json={"action": "update_all", "sheetName": "vi_tien", "rows": vi_tien_rows}, timeout=10)
        requests.post(URL_CAU_NOI, json={"action": "update_all", "sheetName": "lich_su", "rows": lich_su_rows}, timeout=10)
    except Exception as e:
        st.error(f"❌ Lỗi đồng bộ lên Google Sheets: {e}")

if "data" not in st.session_state:
    st.session_state.data = tai_du_lieu_tu_sheets()

# --- HÀM GHI LỊCH SỬ VÀ XỬ LÝ ẢNH CHỤP ĐIỆN THOẠI ---
def ghi_lich_su(loai, vi_to, vi_nho, so_tien, mo_ta, file_anh):
    thoi_gian = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    anh_luu = ""
    if file_anh is not None:
        try:
            # Sử dụng Pillow để mở file ảnh tải lên từ điện thoại
            img = Image.open(file_anh)
            
            # Khắc phục lỗi ảnh chụp từ điện thoại bị ngược/xoay nghiêng bằng thông số EXIF
            img = ImageOps.exif_transpose(img)
            
            # Hạ độ phân giải tối đa xuống kích thước vừa phải để tối ưu tốc độ app và bộ nhớ
            img.thumbnail((1200, 1200))
            
            # Đổi toàn bộ đuôi ảnh thành .jpg thống nhất
            ten_file_moi = f"{loai}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            anh_luu = os.path.join(THU_MUC_ANH, ten_file_moi)
            
            # Chuyển hệ màu nếu là ảnh trong suốt (PNG) sang RGB để lưu dạng JPEG
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
                
            # Nén chất lượng ảnh xuống 80% (vừa nhẹ vừa đủ rõ nét hóa đơn)
            img.save(anh_luu, "JPEG", quality=80)
        except Exception as e:
            st.error(f"⚠️ Có lỗi khi xử lý ảnh chụp điện thoại: {e}")
            anh_luu = ""

    st.session_state.data["lich_su"].append({
        "thoi_gian": thoi_gian,
        "loai": loai,
        "vi_to": vi_to,
        "vi_nho": vi_nho,
        "so_tien": so_tien,
        "mo_ta": mo_ta,
        "anh": anh_luu
    })

# --- GIAO DIỆN CHÍNH ---
st.title("💰 Quản Lý Chi Tiêu Đa Nền Tảng")

tab1, tab2, tab3, tab4 = st.tabs(["📋 Danh sách & Lịch sử", "📥 Nạp tiền / Tạo ví", "📤 Ghi nhận Chi tissue", "⚙️ Quản lý Ví"])

vi_tien_dict = st.session_state.data["vi_tien"]

# TAB 1: DANH SÁCH VÍ & LỊCH SỬ
with tab1:
    st.subheader("📊 Danh sách ví hiện tại")
    if not vi_tien_dict:
        st.info("Chưa có ví nào được tạo.")
    else:
        for vi_to, cac_vi_nho in vi_tien_dict.items():
            with st.expander(f"■ {vi_to}", expanded=True):
                for vi_nho, so_tien in cac_vi_nho.items():
                    st.write(f"🔹 **{vi_nho}**: {so_tien:,} đ")

    st.markdown("---")
    st.subheader("📜 Lịch sử giao dịch")
    lich_su_list = st.session_state.data["lich_su"]
    if lich_su_list:
        df = pd.DataFrame(lich_su_list)
        df_hien_thi = df.copy()
        df_hien_thi["Ví tiền"] = df_hien_thi["vi_to"] + " ➔ " + df_hien_thi["vi_nho"]
        df_hien_thi = df_hien_thi[["thoi_gian", "loai", "Ví tiền", "so_tien", "mo_ta", "anh"]]
        df_hien_thi.columns = ["Thời Gian", "Loại", "Ví Tiền", "Số Tiền (đ)", "Mục Đích", "Đường dẫn ảnh"]
        
        st.dataframe(df_hien_thi.iloc[::-1], use_container_width=True)
        
        st.markdown("---")
        st.caption("🛠️ **Công cụ Quản lý Lịch sử (Sửa / Xóa Giao Dịch)**")
        
        options_lich_su = list(range(len(lich_su_list)))
        format_func = lambda idx: f"[{lich_su_list[idx]['thoi_gian']}] {lich_su_list[idx]['loai']} | {lich_su_list[idx]['vi_to']}➔{lich_su_list[idx]['vi_nho']} | {lich_su_list[idx]['so_tien']:,}đ - {lich_su_list[idx]['mo_ta']}"
        
        selected_idx = st.selectbox("Chọn dòng giao dịch muốn can thiệp:", options=reversed(options_lich_su), format_func=format_func)
        
        if selected_idx is not None:
            gd_chon = lich_su_list[selected_idx]
            
            if gd_chon.get("anh") and os.path.exists(gd_chon["anh"]):
                st.image(gd_chon["anh"], caption="Ảnh hóa đơn hiện tại", width=200)
                
            col_edit1, col_edit2 = st.columns(2)
            with col_edit1:
                new_mo_ta = st.text_input("Sửa Mục đích / Mô tả:", value=gd_chon["mo_ta"])
            with col_edit2:
                new_so_tien = st.number_input("Sửa Số tiền (đ):", min_value=0, value=int(gd_chon["so_tien"]), step=1000)
                
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if "confirm_edit_ls" not in st.session_state:
                    st.session_state.confirm_edit_ls = False
                
                if not st.session_state.confirm_edit_ls:
                    if st.button("✏️ Cập nhật thay đổi", type="primary", use_container_width=True):
                        st.session_state.confirm_edit_ls = True
                        st.rerun()
                else:
                    st.warning("❓ Bạn có muốn CẬP NHẬT dòng này?")
                    c_ed1, c_ed2 = st.columns(2)
                    with c_ed1:
                        if st.button("👍 Có, Sửa", type="primary", use_container_width=True):
                            vi_t = gd_chon["vi_to"]
                            vi_n = gd_chon["vi_nho"]
                            loai_gd = gd_chon["loai"]
                            
                            if vi_t in st.session_state.data["vi_tien"] and vi_n in st.session_state.data["vi_tien"][vi_t]:
                                if loai_gd == "NẠP":
                                    st.session_state.data["vi_tien"][vi_t][vi_n] -= gd_chon["so_tien"]
                                elif loai_gd == "CHI":
                                    st.session_state.data["vi_tien"][vi_t][vi_n] += gd_chon["so_tien"]
                            
                            if vi_t in st.session_state.data["vi_tien"] and vi_n in st.session_state.data["vi_tien"][vi_t]:
                                if loai_gd == "NẠP":
                                    st.session_state.data["vi_tien"][vi_t][vi_n] += new_so_tien
                                elif loai_gd == "CHI":
                                    st.session_state.data["vi_tien"][vi_t][vi_n] -= new_so_tien
                            
                            st.session_state.data["lich_su"][selected_idx]["mo_ta"] = new_mo_ta
                            st.session_state.data["lich_su"][selected_idx]["so_tien"] = new_so_tien
                            
                            luu_du_lieu()
                            st.success("Đã cập nhật thay đổi thành công lên Google Sheets!")
                            st.session_state.confirm_edit_ls = False
                            st.rerun()
                    with c_ed2:
                        if st.button("👎 Không, Hủy", type="secondary", use_container_width=True):
                            st.session_state.confirm_edit_ls = False
                            st.rerun()
                    
            with btn_col2:
                if "confirm_del_ls" not in st.session_state:
                    st.session_state.confirm_del_ls = False
                
                if not st.session_state.confirm_del_ls:
                    if st.button("🗑️ XÓA dòng giao dịch này", type="secondary", use_container_width=True):
                        st.session_state.confirm_del_ls = True
                        st.rerun()
                else:
                    st.error("❓ Bạn có chắc muốn XÓA vĩnh viễn?")
                    c_del1, c_del2 = st.columns(2)
                    with c_del1:
                        if st.button("👍 Có, Xóa dòng", type="primary", use_container_width=True):
                            vi_t = gd_chon["vi_to"]
                            vi_n = gd_chon["vi_nho"]
                            loai_gd = gd_chon["loai"]
                            
                            if vi_t in st.session_state.data["vi_tien"] and vi_n in st.session_state.data["vi_tien"][vi_t]:
                                if loai_gd == "NẠP":
                                    st.session_state.data["vi_tien"][vi_t][vi_n] -= gd_chon["so_tien"]
                                elif loai_gd == "CHI":
                                    st.session_state.data["vi_tien"][vi_t][vi_n] += gd_chon["so_tien"]
                            
                            if gd_chon.get("anh") and os.path.exists(gd_chon["anh"]):
                                try: os.remove(gd_chon["anh"])
                                except: pass
                                
                            st.session_state.data["lich_su"].pop(selected_idx)
                            luu_du_lieu()
                            st.success("Đã xóa giao dịch thành công trên Google Sheets!")
                            st.session_state.confirm_del_ls = False
                            st.rerun()
                    with c_del2:
                        if st.button("👎 Không, Giữ lại", type="secondary", use_container_width=True):
                            st.session_state.confirm_del_ls = False
                            st.rerun()
    else:
        st.info("Chưa có lịch sử giao dịch.")

# TAB 2: NẠP TIỀN / KHỞI TẠO VÍ (CẬP NHẬT DROPDOWN THÔNG MINH)
with tab2:
    st.subheader("📥 Thêm ví hoặc Nạp thêm tiền")
    
    # --- XỬ LÝ DROPDOWN CHO VÍ LỚN ---
    danh_sach_vi_to_cu = list(vi_tien_dict.keys())
    options_vi_to = ["+ Tạo Ví Lớn Mới"] + danh_sach_vi_to_cu
    
    # Thiết lập cơ chế tự động nhảy vị trí nếu vừa tạo mới
    idx_default_to = 0
    if "last_created_vi_to" in st.session_state and st.session_state.last_created_vi_to in options_vi_to:
        idx_default_to = options_vi_to.index(st.session_state.last_created_vi_to)
        
    select_vi_to = st.selectbox("Chọn Ví Lớn:", options=options_vi_to, index=idx_default_to)
    
    if select_vi_to == "+ Tạo Ví Lớn Mới":
        ten_vi_to = st.text_input("Nhập tên Ví Lớn mới (Ví dụ: Thẻ ngân hàng, Tiền mặt):", key="nap_vi_to_moi").strip()
    else:
        ten_vi_to = select_vi_to

    # --- XỬ LÝ DROPDOWN CHO VÍ NHỎ ---
    options_vi_nho = ["+ Tạo Ví Nhỏ Mới"]
    if select_vi_to != "+ Tạo Ví Lớn Mới" and select_vi_to in vi_tien_dict:
        options_vi_nho += list(vi_tien_dict[select_vi_to].keys())
        
    idx_default_nho = 0
    if "last_created_vi_nho" in st.session_state and st.session_state.last_created_vi_nho in options_vi_nho:
        idx_default_nho = options_vi_nho.index(st.session_state.last_created_vi_nho)
        
    select_vi_nho = st.selectbox("Chọn Ví Nhỏ:", options=options_vi_nho, index=idx_default_nho)
    
    if select_vi_nho == "+ Tạo Ví Nhỏ Mới":
        ten_vi_nho = st.text_input("Nhập tên Ví Nhỏ mới (Ví dụ: Tiền ăn, Tiền nhà):", key="nap_vi_nho_moi").strip()
    else:
        ten_vi_nho = select_vi_nho

    tien_ban_dau = st.number_input("Số tiền nạp (VNĐ):", min_value=0, step=10000, value=0)
    mo_ta_nap = st.text_input("Mục đích nạp:", value="Khởi tạo/Nạp thêm", key="mo_ta_nap_input").strip()
    anh_nap = st.file_uploader("Chọn hoặc chụp ảnh bằng chứng nạp (PNG, JPG):", type=["png", "jpg", "jpeg"], key="anh_nap")

    if "confirm_nap" not in st.session_state:
        st.session_state.confirm_nap = False

    if not st.session_state.confirm_nap:
        if st.button("🚀 NẠP TIỀN / LƯU VÍ", type="primary"):
            if not ten_vi_to or not ten_vi_nho:
                st.error("Vui lòng không để trống tên Ví Lớn và Ví Nhỏ!")
            else:
                st.session_state.confirm_nap = True
                st.rerun()
    else:
        st.warning(f"❓ Bạn có chắc chắn muốn NẠP {tien_ban_dau:,} đ vào ví [{ten_vi_to} ➔ {ten_vi_nho}]?")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("👍 Có, Xác nhận nạp", type="primary", use_container_width=True):
                # Lưu trạng thái để tự động hiển thị trên dropdown sau khi load lại trang
                st.session_state.last_created_vi_to = ten_vi_to
                st.session_state.last_created_vi_nho = ten_vi_nho
                
                if ten_vi_to not in st.session_state.data["vi_tien"]:
                    st.session_state.data["vi_tien"][ten_vi_to] = {}
                if ten_vi_nho in st.session_state.data["vi_tien"][ten_vi_to]:
                    st.session_state.data["vi_tien"][ten_vi_to][ten_vi_nho] += tien_ban_dau
                else:
                    st.session_state.data["vi_tien"][ten_vi_to][ten_vi_nho] = tien_ban_dau

                if tien_ban_dau > 0:
                    ghi_lich_su("NẠP", ten_vi_to, ten_vi_nho, tien_ban_dau, mo_ta_nap, anh_nap)
                
                luu_du_lieu()
                st.success(f"Đã xử lý thành công ví [{ten_vi_to} ➔ {ten_vi_nho}]!")
                st.session_state.confirm_nap = False
                st.rerun()
        with col_c2:
            if st.button("👎 Không, Hủy bỏ", type="secondary", use_container_width=True):
                st.session_state.confirm_nap = False
                st.rerun()

# TAB 3: GHI NHẬN CHI TIÊU
with tab3:
    st.subheader("📤 Ghi nhận khoản chi")
    danh_sach_chi_tieu = []
    for vt, cvn in vi_tien_dict.items():
        for vn in cvn.keys():
            danh_sach_chi_tieu.append(f"{vt} ➔ {vn}")
            
    if not danh_sach_chi_tieu:
        st.warning("Vui lòng tạo ví trước khi ghi nhận chi tiêu.")
    else:
        lua_chon_vi = st.selectbox("Chọn ví thanh toán:", danh_sach_chi_tieu)
        mo_ta_chi = st.text_input("Mục đích chi (Bắt buộc):").strip()
        so_tien_chi = st.number_input("Số tiền chi (VNĐ):", min_value=0, step=10000, value=0)
        anh_chi = st.file_uploader("Chọn hoặc chụp ảnh hóa đơn chi (PNG, JPG):", type=["png", "jpg", "jpeg"], key="anh_chi")

        if "confirm_chi" not in st.session_state:
            st.session_state.confirm_chi = False

        if not st.session_state.confirm_chi:
            if st.button("🔥 XÁC NHẬN CHI TIÊU", type="primary"):
                if not mo_ta_chi:
                    st.error("Bạn phải điền mục đích chi tiêu!")
                elif so_tien_chi <= 0:
                    st.error("Số tiền chi phải lớn hơn 0!")
                else:
                    vi_to, vi_nho = lua_chon_vi.split(" ➔ ")
                    if st.session_state.data["vi_tien"][vi_to][vi_nho] < so_tien_chi:
                        st.error(f"Ví '{vi_nho}' không đủ số dư để chi!")
                    else:
                        st.session_state.confirm_chi = True
                        st.rerun()
        else:
            st.warning(f"❓ Bạn có chắc chắn muốn CHI {so_tien_chi:,} đ từ ví [{lua_chon_vi}]?")
            col_ch1, col_ch2 = st.columns(2)
            with col_ch1:
                if st.button("👍 Có, Xác nhận chi", type="primary", use_container_width=True):
                    vi_to, vi_nho = lua_chon_vi.split(" ➔ ")
                    st.session_state.data["vi_tien"][vi_to][vi_nho] -= so_tien_chi
                    ghi_lich_su("CHI", vi_to, vi_nho, so_tien_chi, mo_ta_chi, anh_chi)
                    luu_du_lieu()
                    st.success(f"Đã ghi nhận chi {so_tien_chi:,} đ và cập nhật lên Google Sheets!")
                    st.session_state.confirm_chi = False
                    st.rerun()
            with col_ch2:
                if st.button("👎 Không, Hủy bỏ", type="secondary", use_container_width=True):
                    st.session_state.confirm_chi = False
                    st.rerun()

# TAB 4: QUẢN LÝ VÍ (ĐỔI TÊN / XÓA)
with tab4:
    st.subheader("⚙️ Chỉnh sửa hoặc Xóa Ví")
    danh_sach_quan_ly = []
    for vt, cvn in vi_tien_dict.items():
        danh_sach_quan_ly.append(f"[Ví To] {vt}")
        for vn in cvn.keys():
            danh_sach_quan_ly.append(f"[Ví Nhỏ] {vt} ➔ {vn}")
            
    if not danh_sach_quan_ly:
        st.info("Chưa có ví nào để quản lý.")
    else:
        vi_ql = st.selectbox("Chọn mục cần xử lý:", danh_sach_quan_ly)
        
        col1, col2 = st.columns(2)
        with col1:
            ten_moi = st.text_input("Nhập tên mới nếu muốn sửa tên:").strip()
            
            if "confirm_rename_vi" not in st.session_state:
                st.session_state.confirm_rename_vi = False
                
            if not st.session_state.confirm_rename_vi:
                if st.button("✏️ Đổi Tên"):
                    if not ten_moi:
                        st.error("Vui lòng nhập tên mới trước khi bấm đổi!")
                    else:
                        st.session_state.confirm_rename_vi = True
                        st.rerun()
            else:
                st.warning(f"❓ Đổi tên sang '{ten_moi}'?")
                c_rn1, c_rn2 = st.columns(2)
                with c_rn1:
                    if st.button("👍 Có, Đổi tên", type="primary", use_container_width=True):
                        if vi_ql.startswith("[Ví To]"):
                            ten_cu = vi_ql.replace("[Ví To] ", "")
                            if ten_moi in st.session_state.data["vi_tien"]:
                                st.error("Tên Ví To đã tồn tại!")
                            else:
                                st.session_state.data["vi_tien"][ten_moi] = st.session_state.data["vi_tien"].pop(ten_cu)
                        elif vi_ql.startswith("[Ví Nhỏ]"):
                            v_to, v_nho_cu = vi_ql.replace("[Ví Nhỏ] ", "").split(" ➔ ")
                            if ten_moi in st.session_state.data["vi_tien"][v_to]:
                                st.error("Tên Ví Nhỏ đã tồn tại!")
                            else:
                                st.session_state.data["vi_tien"][v_to][ten_moi] = st.session_state.data["vi_tien"][v_to].pop(v_nho_cu)
                        luu_du_lieu()
                        st.success("Đổi tên ví thành công!")
                        st.session_state.confirm_rename_vi = False
                        st.rerun()
                with c_rn2:
                    if st.button("👎 Không", type="secondary", use_container_width=True):
                        st.session_state.confirm_rename_vi = False
                        st.rerun()
        
        with col2:
            st.write("Hành động nguy hiểm:")
            if "confirm_xoa_vi" not in st.session_state:
                st.session_state.confirm_xoa_vi = False
                
            if not st.session_state.confirm_xoa_vi:
                if st.button("❌ XÓA VÍ NÀY", type="secondary"):
                    st.session_state.confirm_xoa_vi = True
                    st.rerun()
            else:
                st.error("❓ Bạn có CHẮC CHẮN muốn XÓA ví này?")
                c_xvi1, c_xvi2 = st.columns(2)
                with c_xvi1:
                    if st.button("👍 Có, Xóa hẳn", type="primary", use_container_width=True):
                        if vi_ql.startswith("[Ví To]"):
                            del st.session_state.data["vi_tien"][vi_ql.replace("[Ví To] ", "")]
                        elif vi_ql.startswith("[Ví Nhỏ]"):
                            v_to, v_nho = vi_ql.replace("[Ví Nhỏ] ", "").split(" ➔ ")
                            del st.session_state.data["vi_tien"][v_to][v_nho]
                            if not st.session_state.data["vi_tien"][v_to]:
                                del st.session_state.data["vi_tien"][v_to]
                        luu_du_lieu()
                        st.success("Đã xóa ví thành công trên hệ thống và Google Sheets!")
                        st.session_state.confirm_xoa_vi = False
                        st.rerun()
                with c_xvi2:
                    if st.button("👎 Không, Giữ lại", type="secondary", use_container_width=True):
                        st.session_state.confirm_xoa_vi = False
                        st.rerun()
