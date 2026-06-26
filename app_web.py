import streamlit as st
import json
import os
import shutil
from datetime import datetime
import pandas as pd

# Thiết lập cấu hình trang web (Giao diện rộng, tối ưu mobile)
st.set_page_config(page_title="Quản Lý Chi Tiêu", page_icon="💰", layout="centered")

# Đổi sang tên file mới tương thích hoàn toàn với Cloud
FILE_SAVE = "dulieu_vi_cloud.json"
THU_MUC_ANH = "anh_giao_dich"

if not os.path.exists(THU_MUC_ANH):
    os.makedirs(THU_MUC_ANH)

# Khởi tạo dữ liệu ban đầu
if "data" not in st.session_state:
    if os.path.exists(FILE_SAVE):
        with open(FILE_SAVE, "r", encoding="utf-8") as f:
            try:
                du_lieu_cu = json.load(f)
                if "vi_tien" not in du_lieu_cu:
                    st.session_state.data = {"vi_tien": du_lieu_cu, "lich_su": []}
                else:
                    st.session_state.data = du_lieu_cu
            except:
                st.session_state.data = {"vi_tien": {}, "lich_su": []}
    else:
        st.session_state.data = {"vi_tien": {}, "lich_su": []}

def luu_du_lieu():
    with open(FILE_SAVE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.data, f, ensure_ascii=False)

def ghi_lich_su(loai, vi_to, vi_nho, so_tien, mo_ta, file_anh):
    thoi_gian = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    anh_luu = ""
    if file_anh is not None:
        phan_mo_rong = os.path.splitext(file_anh.name)[1]
        ten_file_moi = f"{loai}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{phan_mo_rong}"
        anh_luu = os.path.join(THU_MUC_ANH, ten_file_moi)
        with open(anh_luu, "wb") as f:
            f.write(file_anh.getbuffer())

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

# Tab chức năng
tab1, tab2, tab3, tab4 = st.tabs(["📋 Danh sách & Lịch sử", "📥 Nạp tiền / Tạo ví", "📤 Ghi nhận Chi tiêu", "⚙️ Quản lý Ví"])

# TAB 1: DANH SÁCH VÍ & LỊCH SỬ
with tab1:
    st.subheader("📊 Danh sách ví hiện tại")
    vi_tien_dict = st.session_state.data["vi_tien"]
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
        
        # --- KHU VỰC SỬA / XÓA LỊCH SỬ GIAO DỊCH ---
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
                if st.button("✏️ Cập nhật thay đổi", type="primary", use_container_width=True):
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
                    st.success("Đã cập nhật thay đổi!")
                    st.rerun()
                    
            with btn_col2:
                if st.button("🗑️ XÓA dòng giao dịch này", type="secondary", use_container_width=True):
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
                    st.success("Đã xóa giao dịch!")
                    st.rerun()
    else:
        st.info("Chưa có lịch sử giao dịch.")

# TAB 2: NẠP TIỀN / KHỞI TẠO VÍ
with tab2:
    st.subheader("📥 Thêm ví hoặc Nạp thêm tiền")
    ten_vi_to = st.text_input("Tên Ví To (Ví dụ: Thẻ ngân hàng, Tiền mặt):", key="nap_vi_to").strip()
    ten_vi_nho = st.text_input("Tên Ví Nhỏ (Ví dụ: Tiền ăn, Tiền nhà):", key="nap_vi_nho").strip()
    tien_ban_dau = st.number_input("Số tiền nạp (VNĐ):", min_value=0, step=10000, value=0)
    mo_ta_nap = st.text_input("Mục đích nạp:", value="Khởi tạo/Nạp thêm").strip()
    anh_nap = st.file_uploader("Chọn ảnh bằng chứng nạp (nếu có):", type=["png", "jpg", "jpeg"], key="anh_nap")

    if st.button("🚀 NẠP TIỀN / LƯU VÍ", type="primary"):
        if not ten_vi_to or not ten_vi_nho:
            st.error("Vui lòng nhập đủ Tên Ví To và Tên Ví Nhỏ!")
        else:
            if ten_vi_to not in st.session_state.data["vi_tien"]:
                st.session_state.data["vi_tien"][ten_vi_to] = {}
            if ten_vi_nho in st.session_state.data["vi_tien"][ten_vi_to]:
                st.session_state.data["vi_tien"][ten_vi_to][ten_vi_nho] += tien_ban_dau
            else:
                st.session_state.data["vi_tien"][ten_vi_to][ten_vi_nho] = tien_ban_dau

            if tien_ban_dau > 0:
                ghi_lich_su("NẠP", ten_vi_to, ten_vi_nho, tien_ban_dau, mo_ta_nap, anh_nap)
            
            luu_du_lieu()
            st.success(f"Đã nạp thành công {tien_ban_dau:,} đ!")
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
        anh_chi = st.file_uploader("Chọn ảnh hóa đơn chi (nếu có):", type=["png", "jpg", "jpeg"], key="anh_chi")

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
                    st.session_state.data["vi_tien"][vi_to][vi_nho] -= so_tien_chi
                    ghi_lich_su("CHI", vi_to, vi_nho, so_tien_chi, mo_ta_chi, anh_chi)
                    luu_du_lieu()
                    st.success(f"Đã ghi nhận chi {so_tien_chi:,} đ!")
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
            if st.button("✏️ Đổi Tên"):
                if ten_moi:
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
                    st.success("Đổi tên thành công!")
                    st.rerun()
        
        with col2:
            st.write("Hành động nguy hiểm:")
            if st.button("❌ XÓA VÍ NÀY", type="secondary"):
                if vi_ql.startswith("[Ví To]"):
                    del st.session_state.data["vi_tien"][vi_ql.replace("[Ví To] ", "")]
                elif vi_ql.startswith("[Ví Nhỏ]"):
                    v_to, v_nho = vi_ql.replace("[Ví Nhỏ] ", "").split(" ➔ ")
                    del st.session_state.data["vi_tien"][v_to][v_nho]
                    if not st.session_state.data["vi_tien"][v_to]:
                        del st.session_state.data["vi_tien"][v_to]
                luu_du_lieu()
                st.success("Đã xóa ví thành công!")
                st.rerun()
