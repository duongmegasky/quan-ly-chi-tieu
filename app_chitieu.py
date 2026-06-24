import tkinter as tk

from tkinter import messagebox, filedialog, ttk

import json

import os

import shutil

from datetime import datetime

import webbrowser



FILE_SAVE = "dulieu_vi_nangcap.json"

THU_MUC_ANH = "anh_giao_dich"



# Tự động tạo thư mục lưu ảnh hóa đơn nếu chưa có

if not os.path.exists(THU_MUC_ANH):

    os.makedirs(THU_MUC_ANH)



# Cấu trúc dữ liệu mới: Tách bạch Số dư và Lịch sử

data = {

    "vi_tien": {},

    "lich_su": []

}



# Tự động load và nâng cấp dữ liệu cũ (nếu có)

if os.path.exists(FILE_SAVE):

    with open(FILE_SAVE, "r", encoding="utf-8") as f:

        try: 

            du_lieu_cu = json.load(f)

            # Nếu là dữ liệu phiên bản cũ, tiến hành di chuyển vào mục "vi_tien"

            if "vi_tien" not in du_lieu_cu:

                data["vi_tien"] = du_lieu_cu

            else:

                data = du_lieu_cu

        except: pass



# --- CÁC BIẾN LƯU TẠM ĐƯỜNG DẪN ẢNH ---

anh_nap_tam = ""

anh_chi_tam = ""



def luu_du_lieu():

    with open(FILE_SAVE, "w", encoding="utf-8") as f:

        json.dump(data, f)



def ghi_lich_su(loai, vi_to, vi_nho, so_tien, mo_ta, duong_dan_anh=""):

    thoi_gian = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Tự động copy ảnh vào thư mục hệ thống để tránh mất file

    anh_luu = ""

    if duong_dan_anh and os.path.exists(duong_dan_anh):

        phan_mo_rong = os.path.splitext(duong_dan_anh)[1]

        ten_file_moi = f"{loai}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{phan_mo_rong}"

        anh_luu = os.path.join(THU_MUC_ANH, ten_file_moi)

        try:

            shutil.copy(duong_dan_anh, anh_luu)

        except Exception as e:

            messagebox.showerror("Lỗi copy ảnh", f"Không thể lưu ảnh: {e}")

            anh_luu = ""



    data["lich_su"].append({

        "thoi_gian": thoi_gian,

        "loai": loai,

        "vi_to": vi_to,

        "vi_nho": vi_nho,

        "so_tien": so_tien,

        "mo_ta": mo_ta,

        "anh": anh_luu

    })



def cap_nhat_giao_dien():

    for widget in khung_hien_thi.winfo_children():

        widget.destroy()

    

    danh_sach_chi_tieu = []

    danh_sach_quan_ly = []

    

    for vi_to, cac_vi_nho in data["vi_tien"].items():

        tk.Label(khung_hien_thi, text=f"■ {vi_to}", font=("Arial", 11, "bold"), fg="#b91c1c").pack(anchor="w", pady=(5, 0))

        danh_sach_quan_ly.append(f"[Ví To] {vi_to}")

        

        for vi_nho, so_tien in cac_vi_nho.items():

            tk.Label(khung_hien_thi, text=f"    + {vi_nho}: {so_tien:,} đ", font=("Arial", 11), fg="#1e3a8a").pack(anchor="w")

            danh_sach_chi_tieu.append(f"{vi_to} ➔ {vi_nho}")

            danh_sach_quan_ly.append(f"[Ví Nhỏ] {vi_to} ➔ {vi_nho}")

            

    menu_chon_vi['menu'].delete(0, 'end')

    if danh_sach_chi_tieu:

        bien_chon_vi.set(danh_sach_chi_tieu[0])

        for tuy_chon in danh_sach_chi_tieu:

            menu_chon_vi['menu'].add_command(label=tuy_chon, command=tk._setit(bien_chon_vi, tuy_chon))

    else: bien_chon_vi.set("")



    menu_quan_ly['menu'].delete(0, 'end')

    if danh_sach_quan_ly:

        bien_quan_ly.set(danh_sach_quan_ly[0])

        for tuy_chon in danh_sach_quan_ly:

            menu_quan_ly['menu'].add_command(label=tuy_chon, command=tk._setit(bien_quan_ly, tuy_chon))

    else: bien_quan_ly.set("")



# --- CHỨC NĂNG CHỌN ẢNH ---

def chon_anh_nap():

    global anh_nap_tam

    filepath = filedialog.askopenfilename(title="Chọn ảnh minh chứng nạp", filetypes=[("Ảnh", "*.png *.jpg *.jpeg")])

    if filepath:

        anh_nap_tam = filepath

        nhan_ten_anh_nap.config(text=os.path.basename(filepath))



def chon_anh_chi():

    global anh_chi_tam

    filepath = filedialog.askopenfilename(title="Chọn ảnh minh chứng chi", filetypes=[("Ảnh", "*.png *.jpg *.jpeg")])

    if filepath:

        anh_chi_tam = filepath

        nhan_ten_anh_chi.config(text=os.path.basename(filepath))



# --- CÁC HÀM XỬ LÝ CHÍNH ---

def them_vi_moi():

    global anh_nap_tam

    ten_vi_to = o_nhap_vi_to.get().strip()

    ten_vi_nho = o_nhap_vi_nho.get().strip()

    tien_ban_dau = o_nhap_tien_vi_moi.get().strip()

    mo_ta = o_nhap_mo_ta_nap.get().strip()



    if not ten_vi_to or not ten_vi_nho:

        messagebox.showwarning("Lỗi", "Vui lòng nhập đủ Tên Ví To và Tên Ví Nhỏ!")

        return

    if not tien_ban_dau.isdigit():

        messagebox.showwarning("Lỗi", "Số tiền ban đầu phải là số!")

        return

        

    tien_ban_dau = int(tien_ban_dau)



    if ten_vi_to not in data["vi_tien"]: data["vi_tien"][ten_vi_to] = {}

    if ten_vi_nho in data["vi_tien"][ten_vi_to]: data["vi_tien"][ten_vi_to][ten_vi_nho] += tien_ban_dau

    else: data["vi_tien"][ten_vi_to][ten_vi_nho] = tien_ban_dau



    # Ghi lại lịch sử nạp tiền

    if tien_ban_dau > 0:

        ghi_lich_su("NẠP", ten_vi_to, ten_vi_nho, tien_ban_dau, mo_ta if mo_ta else "Khởi tạo/Nạp thêm", anh_nap_tam)



    luu_du_lieu()

    cap_nhat_giao_dien()

    

    o_nhap_vi_to.delete(0, tk.END)

    o_nhap_vi_nho.delete(0, tk.END)

    o_nhap_tien_vi_moi.delete(0, tk.END)

    o_nhap_tien_vi_moi.insert(0, "0")

    o_nhap_mo_ta_nap.delete(0, tk.END)

    anh_nap_tam = ""

    nhan_ten_anh_nap.config(text="Chưa chọn ảnh")

    messagebox.showinfo("Thành công", f"Đã nạp tiền vào '{ten_vi_nho}'!")



def xac_nhan_chi():

    global anh_chi_tam

    lua_chon = bien_chon_vi.get()

    if not lua_chon: return

    

    vi_to, vi_nho = lua_chon.split(" ➔ ")

    so_tien_nhap = o_nhap_tien_chi.get().strip()

    mo_ta = o_nhap_mo_ta_chi.get().strip()



    if not so_tien_nhap.isdigit() or int(so_tien_nhap) <= 0:

        messagebox.showwarning("Lỗi", "Vui lòng nhập số tiền chi tiêu hợp lệ!")

        return

    if not mo_ta:

        messagebox.showwarning("Cảnh báo", "Bạn nên ghi rõ mục đích chi tiêu để dễ tra cứu!")

        return



    tien_tru = int(so_tien_nhap)

    if data["vi_tien"][vi_to][vi_nho] < tien_tru:

        messagebox.showwarning("Cảnh báo", f"Ví '{vi_nho}' không đủ tiền để chi!")

        return



    data["vi_tien"][vi_to][vi_nho] -= tien_tru

    

    # Ghi lại lịch sử chi tiền

    ghi_lich_su("CHI", vi_to, vi_nho, tien_tru, mo_ta, anh_chi_tam)

    

    luu_du_lieu()

    cap_nhat_giao_dien()

    

    o_nhap_tien_chi.delete(0, tk.END)

    o_nhap_mo_ta_chi.delete(0, tk.END)

    anh_chi_tam = ""

    nhan_ten_anh_chi.config(text="Chưa chọn ảnh")

    messagebox.showinfo("Thành công", f"Đã ghi nhận chi {tien_tru:,} đ!")



def xoa_vi():

    lua_chon = bien_quan_ly.get()

    if not lua_chon: return



    if messagebox.askyesno("Xác nhận xóa", f"Chắc chắn xóa '{lua_chon}'?\nLịch sử giao dịch cũ vẫn được giữ lại nhưng ví sẽ biến mất."):

        if lua_chon.startswith("[Ví To]"):

            del data["vi_tien"][lua_chon.replace("[Ví To] ", "")]

        elif lua_chon.startswith("[Ví Nhỏ]"):

            vi_to, vi_nho = lua_chon.replace("[Ví Nhỏ] ", "").split(" ➔ ")

            del data["vi_tien"][vi_to][vi_nho]

            if not data["vi_tien"][vi_to]: del data["vi_tien"][vi_to]



        luu_du_lieu()

        cap_nhat_giao_dien()



def doi_ten_vi():

    lua_chon = bien_quan_ly.get()

    ten_moi = o_nhap_ten_moi.get().strip()

    if not lua_chon or not ten_moi: return



    if lua_chon.startswith("[Ví To]"):

        ten_vi_cu = lua_chon.replace("[Ví To] ", "")

        if ten_moi in data["vi_tien"]: return messagebox.showwarning("Lỗi", "Tên Ví To đã tồn tại!")

        data["vi_tien"][ten_moi] = data["vi_tien"].pop(ten_vi_cu)

    elif lua_chon.startswith("[Ví Nhỏ]"):

        vi_to, vi_nho_cu = lua_chon.replace("[Ví Nhỏ] ", "").split(" ➔ ")

        if ten_moi in data["vi_tien"][vi_to]: return messagebox.showwarning("Lỗi", "Tên Ví Nhỏ đã tồn tại!")

        data["vi_tien"][vi_to][ten_moi] = data["vi_tien"][vi_to].pop(vi_nho_cu)



    luu_du_lieu()

    cap_nhat_giao_dien()

    o_nhap_ten_moi.delete(0, tk.END)

    messagebox.showinfo("Thành công", "Đã đổi tên thành công!")



# --- GIAO DIỆN XEM LỊCH SỬ CHI TIẾT ---

def mo_cua_so_lich_su():

    top = tk.Toplevel(app)

    top.title("Sổ Phụ Lịch Sử Giao Dịch")

    top.geometry("750x450")

    

    tk.Label(top, text="LỊCH SỬ GIAO DỊCH", font=("Arial", 12, "bold")).pack(pady=5)

    

    khung_bang = tk.Frame(top)

    khung_bang.pack(fill="both", expand=True, padx=10, pady=5)

    

    # Tạo bảng Treeview

    cot = ("thoi_gian", "loai", "vi", "so_tien", "mo_ta", "anh")

    bang = ttk.Treeview(khung_bang, columns=cot, show="headings", height=15)

    bang.heading("thoi_gian", text="Thời Gian")

    bang.heading("loai", text="Nạp/Chi")

    bang.heading("vi", text="Ví Tiền")

    bang.heading("so_tien", text="Số Tiền")

    bang.heading("mo_ta", text="Mục Đích")

    

    bang.column("thoi_gian", width=140)

    bang.column("loai", width=60, anchor="center")

    bang.column("vi", width=150)

    bang.column("so_tien", width=100, anchor="e")

    bang.column("mo_ta", width=250)

    bang.column("anh", width=0, stretch=tk.NO) # Ẩn cột đường dẫn ảnh

    

    thanh_cuon = ttk.Scrollbar(khung_bang, orient="vertical", command=bang.yview)

    bang.configure(yscrollcommand=thanh_cuon.set)

    thanh_cuon.pack(side="right", fill="y")

    bang.pack(side="left", fill="both", expand=True)

    

    # Đổ dữ liệu vào bảng (xếp mới nhất lên trên)

    for gd in reversed(data["lich_su"]):

        vi_gop = f"{gd['vi_to']} ➔ {gd['vi_nho']}"

        tien_str = f"{gd['so_tien']:,} đ"

        bang.insert("", "end", values=(gd["thoi_gian"], gd["loai"], vi_gop, tien_str, gd["mo_ta"], gd.get("anh", "")))



    def xem_anh_chung_tu():

        chon = bang.focus()

        if not chon: return messagebox.showinfo("Lưu ý", "Vui lòng chọn một dòng giao dịch để xem ảnh!")

        duong_dan = bang.item(chon, 'values')[5]

        if duong_dan and os.path.exists(duong_dan):

            try:

                os.startfile(duong_dan) # Mở bằng trình xem ảnh mặc định của Windows

            except:

                webbrowser.open("file://" + os.path.realpath(duong_dan))

        else:

            messagebox.showinfo("Thông báo", "Giao dịch này không có ảnh đính kèm.")



    tk.Button(top, text="🖼️ XEM ẢNH HÓA ĐƠN ĐÍNH KÈM", bg="#2563eb", fg="white", font=("Arial", 10, "bold"), command=xem_anh_chung_tu).pack(pady=10)





# --- XÂY DỰNG GIAO DIỆN CHÍNH ---

app = tk.Tk()

app.title("Quản Lý Chi Tiêu - Có Lưu Vết Lịch Sử")

app.geometry("550x950")

app.configure(padx=20, pady=15)



# 1. KHU VỰC HIỂN THỊ

tk.Label(app, text="DANH SÁCH VÍ TIỀN", font=("Arial", 14, "bold")).pack()

khung_hien_thi = tk.Frame(app, bg="#f8fafc", bd=1, relief="solid", padx=10, pady=5)

khung_hien_thi.pack(fill="x", pady=5)



tk.Button(app, text="📋 XEM TOÀN BỘ LỊCH SỬ & ẢNH MỞ RỘNG", bg="#475569", fg="white", font=("Arial", 10, "bold"), command=mo_cua_so_lich_su).pack(fill="x", pady=5)



# 2. KHU VỰC TẠO VÍ / NẠP TIỀN

tk.Label(app, text="--- NẠP TIỀN / KHỞI TẠO VÍ ---", font=("Arial", 11, "bold"), fg="#16a34a").pack(pady=(10, 5))

khung_tao_vi = tk.Frame(app)

khung_tao_vi.pack(fill="x")



tk.Label(khung_tao_vi, text="Tên Ví To:").grid(row=0, column=0, sticky="w", pady=2)

o_nhap_vi_to = tk.Entry(khung_tao_vi, width=28)

o_nhap_vi_to.grid(row=0, column=1, padx=5)



tk.Label(khung_tao_vi, text="Tên Ví Nhỏ:").grid(row=1, column=0, sticky="w", pady=2)

o_nhap_vi_nho = tk.Entry(khung_tao_vi, width=28)

o_nhap_vi_nho.grid(row=1, column=1, padx=5)



tk.Label(khung_tao_vi, text="Số tiền (VNĐ):").grid(row=2, column=0, sticky="w", pady=2)

o_nhap_tien_vi_moi = tk.Entry(khung_tao_vi, width=28)

o_nhap_tien_vi_moi.insert(0, "0")

o_nhap_tien_vi_moi.grid(row=2, column=1, padx=5)



tk.Label(khung_tao_vi, text="Mục đích nạp:").grid(row=3, column=0, sticky="w", pady=2)

o_nhap_mo_ta_nap = tk.Entry(khung_tao_vi, width=28)

o_nhap_mo_ta_nap.grid(row=3, column=1, padx=5)



khung_anh_nap = tk.Frame(khung_tao_vi)

khung_anh_nap.grid(row=4, column=0, columnspan=2, pady=5, sticky="w")

tk.Button(khung_anh_nap, text="Chọn Ảnh Bằng Chứng", command=chon_anh_nap).pack(side="left")

nhan_ten_anh_nap = tk.Label(khung_anh_nap, text="Chưa chọn ảnh", fg="gray", width=30, anchor="w")

nhan_ten_anh_nap.pack(side="left", padx=5)



tk.Button(app, text="NẠP TIỀN / LƯU VÍ", bg="#16a34a", fg="white", font=("Arial", 10, "bold"), command=them_vi_moi).pack(fill="x", pady=5)





# 3. KHU VỰC CHI TIÊU

tk.Label(app, text="--- GHI NHẬN CHI TIÊU ---", font=("Arial", 11, "bold"), fg="#dc2626").pack(pady=(15, 5))

khung_chi = tk.Frame(app)

khung_chi.pack(fill="x")



tk.Label(khung_chi, text="Chọn ví thanh toán:").grid(row=0, column=0, sticky="w", pady=2)

bien_chon_vi = tk.StringVar(app)

menu_chon_vi = tk.OptionMenu(khung_chi, bien_chon_vi, "")

menu_chon_vi.config(width=30)

menu_chon_vi.grid(row=0, column=1, padx=5)



tk.Label(khung_chi, text="Mục đích chi:").grid(row=1, column=0, sticky="w", pady=2)

o_nhap_mo_ta_chi = tk.Entry(khung_chi, width=35)

o_nhap_mo_ta_chi.grid(row=1, column=1, padx=5)



tk.Label(khung_chi, text="Số tiền chi (VNĐ):").grid(row=2, column=0, sticky="w", pady=2)

o_nhap_tien_chi = tk.Entry(khung_chi, width=35)

o_nhap_tien_chi.grid(row=2, column=1, padx=5)



khung_anh_chi = tk.Frame(khung_chi)

khung_anh_chi.grid(row=3, column=0, columnspan=2, pady=5, sticky="w")

tk.Button(khung_anh_chi, text="Chọn Ảnh Hóa Đơn", command=chon_anh_chi).pack(side="left")

nhan_ten_anh_chi = tk.Label(khung_anh_chi, text="Chưa chọn ảnh", fg="gray", width=30, anchor="w")

nhan_ten_anh_chi.pack(side="left", padx=5)



tk.Button(app, text="XÁC NHẬN CHI TIÊU", bg="#dc2626", fg="white", font=("Arial", 12, "bold"), command=xac_nhan_chi).pack(fill="x", pady=10)





# 4. KHU VỰC SỬA / XÓA VÍ

tk.Label(app, text="--- QUẢN LÝ VÍ (ĐỔI TÊN / XÓA) ---", font=("Arial", 11, "bold"), fg="#d97706").pack(pady=(15, 5))

bien_quan_ly = tk.StringVar(app)

menu_quan_ly = tk.OptionMenu(app, bien_quan_ly, "")

menu_quan_ly.config(width=45)

menu_quan_ly.pack(fill="x", pady=2)



khung_hanh_dong = tk.Frame(app)

khung_hanh_dong.pack(pady=5)

tk.Label(khung_hanh_dong, text="Tên mới:").grid(row=0, column=0, padx=2)

o_nhap_ten_moi = tk.Entry(khung_hanh_dong, width=15)

o_nhap_ten_moi.grid(row=0, column=1, padx=5)

tk.Button(khung_hanh_dong, text="Sửa Tên", bg="#d97706", fg="white", width=8, command=doi_ten_vi).grid(row=0, column=2, padx=5)

tk.Button(khung_hanh_dong, text="XÓA VÍ", bg="#991b1b", fg="white", width=8, command=xoa_vi).grid(row=0, column=3, padx=5)



cap_nhat_giao_dien()

app.mainloop()

