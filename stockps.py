# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from datetime import datetime
import pandas as pd
import pandas_ta as ta
from vnstock.api.quote import Quote

class BotPhaiSinhUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Hệ Thống Tín Hiệu Phái Sinh VN30F1M - Premium")
        self.root.geometry("1100x680") # Tăng chiều cao để chứa khung hiển thị chi tiết
        
        self.is_running_realtime = False
        self.realtime_thread = None
        self.last_triggered_time = None

        self.setup_ui()

    def setup_ui(self):
        # ---- Khung Điều Khiển (Control Panel) ----
        control_frame = ttk.LabelFrame(self.root, text=" Cấu hình & Điều khiển ", padding=10)
        control_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(control_frame, text="Nhập ngày (YYYY-MM-DD):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.txt_date = ttk.Entry(control_frame, width=12)
        self.txt_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.txt_date.grid(row=0, column=1, padx=5, pady=5)

        self.btn_check_date = ttk.Button(control_frame, text="Quét Lịch Sử", command=self.run_check_date)
        self.btn_check_date.grid(row=0, column=2, padx=5, pady=5)

        self.btn_clear = ttk.Button(control_frame, text="Clear", command=self.clear_table)
        self.btn_clear.grid(row=0, column=3, padx=5, pady=5)

        self.btn_realtime = ttk.Button(control_frame, text="Bật Realtime (5M)", command=self.toggle_realtime)
        self.btn_realtime.grid(row=0, column=4, padx=5, pady=5)

        self.lbl_status = ttk.Label(control_frame, text="Trạng thái: Đang dừng", font=("Arial", 10, "bold"), foreground="gray")
        self.lbl_status.grid(row=0, column=5, padx=15, pady=5)

        # ---- Khung Hiển Thị Bảng Dữ Liệu ----
        table_frame = ttk.LabelFrame(self.root, text=" Danh Sách Tín Hiệu Xuất Hiện ", padding=10)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("type", "time", "scan_time", "price", "target1", "explanation")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        self.tree.heading("type", text="Loại Lệnh")
        self.tree.heading("time", text="Thời Điểm Đóng Nến")
        self.tree.heading("scan_time", text="Thời Điểm Quét Live")
        self.tree.heading("price", text="Giá Khớp (Close)")
        self.tree.heading("target1", text="Target 1 (+1.5 ATR)")
        self.tree.heading("explanation", text="Giải Thích Tín Hiệu (Click dòng để xem chi tiết ở dưới)")

        self.tree.column("type", width=90, anchor="center")
        self.tree.column("time", width=130, anchor="center")
        self.tree.column("scan_time", width=130, anchor="center")
        self.tree.column("price", width=110, anchor="center")
        self.tree.column("target1", width=130, anchor="center")
        self.tree.column("explanation", width=390, anchor="w")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.tag_configure("LONG", foreground="green", font=("Arial", 10, "bold"))
        self.tree.tag_configure("SHORT", foreground="red", font=("Arial", 10, "bold"))

        # BẮT SỰ KIỆN: Khi người dùng click chọn dòng trên bảng
        self.tree.bind("<<TreeviewSelect>>", self.on_select_line)

        # ---- KHUNG PHỤ: XEM CHI TIẾT GIẢI THÍCH XUỐNG DÒNG TỰ ĐỘNG ----
        detail_frame = ttk.LabelFrame(self.root, text=" Chi Tiết Thông Số Bộ Lọc Của Tín Hiệu Được Chọn ", padding=10)
        detail_frame.pack(fill="x", padx=10, pady=10)

        # Sử dụng widget Text (hỗ trợ wrap=tk.WORD để tự động xuống dòng mượt mà)
        self.txt_detail = tk.Text(detail_frame, height=4, font=("Arial", 10), wrap=tk.WORD, bg="#f9f9f9", fg="#333333")
        self.txt_detail.pack(fill="x", expand=True)
        self.txt_detail.insert(tk.END, "Chọn một tín hiệu trên bảng để xem phân tích thông số kỹ thuật chi tiết tại đây...")
        self.txt_detail.config(state="disabled") # Khóa lại không cho người dùng gõ đè chữ vào

    def on_select_line(self, event):
        """Hàm xử lý khi click vào dòng: Lấy cột giải thích đẩy xuống ô chi tiết"""
        selected_items = self.tree.selection()
        if not selected_items:
            return
        
        # Lấy mảng giá trị của dòng được chọn
        item_values = self.tree.item(selected_items[0], "values")
        if item_values and len(item_values) >= 6:
            explanation_text = item_values[5] # Cột thứ 6 là explanation
            
            # Mở khóa, xóa text cũ, chèn text mới có hỗ trợ tự động xuống dòng, rồi khóa lại
            self.txt_detail.config(state="normal")
            self.txt_detail.delete("1.0", tk.END)
            self.txt_detail.insert(tk.END, explanation_text)
            self.txt_detail.config(state="disabled")

    def clear_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.txt_detail.config(state="normal")
        self.txt_detail.delete("1.0", tk.END)
        self.txt_detail.insert(tk.END, "Chọn một tín hiệu trên bảng để xem phân tích thông số kỹ thuật chi tiết tại đây...")
        self.txt_detail.config(state="disabled")

    # ---- MODE 1: QUÉT LỊCH SỬ ----
    def run_check_date(self):
        target_date = self.txt_date.get().strip()
        try:
            datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Lỗi định dạng", "Định dạng ngày phải là YYYY-MM-DD")
            return

        self.clear_table()

        q = Quote(symbol='VN30F1M', source='VCI')
        df = q.history(start=target_date, end=target_date, interval='5m')
        
        if df is None or df.empty:
            messagebox.showinfo("Thông báo", f"Không tìm thấy dữ liệu giao dịch cho ngày {target_date}.")
            return

        if 'datetime' in df.columns:
            df = df.rename(columns={'datetime': 'time'})
        elif 'time' not in df.columns and df.index.name == 'datetime':
            df = df.reset_index().rename(columns={'datetime': 'time'})

        df['time_str'] = df['time'].astype(str)
        df = df[df['time_str'].str.contains(target_date)].copy()
        df = df.drop(columns=['time_str']).reset_index(drop=True)

        if df.empty:
            messagebox.showinfo("Thông báo", f"Không có dữ liệu nến 5m thuộc ngày {target_date}.")
            return

        df['EMA_5'] = ta.ema(df['close'], length=5)
        df['EMA_20'] = ta.ema(df['close'], length=20)
        df['RSI'] = ta.rsi(df['close'], length=14)
        df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        df = df.dropna().reset_index(drop=True)
        
        for i in range(1, len(df)):
            current = df.iloc[i]
            prev = df.iloc[i-1]
            atr_val = current['ATR'] if current['ATR'] > 0 else 1.0
            close_px = current['close']
            
            ema20_slope = current['EMA_20'] - prev['EMA_20']
            scan_time_str = "History Backtest"
            
            if (prev['EMA_5'] <= prev['EMA_20'] and current['EMA_5'] > current['EMA_20']) and current['RSI'] > 50 and ema20_slope > 0.15:
                exp_text = f"[TÍN HIỆU LONG]\n• Lý do: Đường EMA5 ({round(current['EMA_5'],1)}) đã cắt lên trên đường xu hướng EMA20 ({round(current['EMA_20'],1)}).\n• Kiểm tra RSI: Chỉ số Động lượng RSI đạt {round(current['RSI'],1)} (> 50), xác nhận phe Mua đang kiểm soát.\n• Kiểm tra Độ dốc: Độ dốc EMA20 đạt +{round(ema20_slope,2)} (> 0.15), thị trường có xu hướng tăng mạnh, không phải sideway."
                sig = ("⚡ LONG", current['time'], scan_time_str, round(close_px, 1), round(close_px + (1.5 * atr_val), 1), exp_text)
                self.tree.insert("", "end", values=sig, tags=("LONG",))
                
            elif (prev['EMA_5'] >= prev['EMA_20'] and current['EMA_5'] < current['EMA_20']) and current['RSI'] < 50 and ema20_slope < -0.15:
                exp_text = f"[TÍN HIỆU SHORT]\n• Lý do: Đường EMA5 ({round(current['EMA_5'],1)}) đã cắt xuống dưới đường xu hướng EMA20 ({round(current['EMA_20'],1)}).\n• Kiểm tra RSI: Chỉ số Động lượng RSI giảm còn {round(current['RSI'],1)} (< 50), xác nhận áp lực Bán tháo chủ động.\n• Kiểm tra Độ dốc: Độ dốc EMA20 đạt {round(ema20_slope,2)} (< -0.15), xác nhận cấu trúc sập trend giảm uy tín."
                sig = ("🚨 SHORT", current['time'], scan_time_str, round(close_px, 1), round(close_px - (1.5 * atr_val), 1), exp_text)
                self.tree.insert("", "end", values=sig, tags=("SHORT",))

    def toggle_realtime(self):
        if not self.is_running_realtime:
            self.is_running_realtime = True
            self.btn_realtime.config(text="Dừng Realtime")
            self.lbl_status.config(text="Trạng thái: Đang quét...", foreground="green")
            self.txt_date.config(state="disabled")
            self.btn_check_date.config(state="disabled")
            self.btn_clear.config(state="disabled")
            
            self.realtime_thread = threading.Thread(target=self.realtime_loop, daemon=True)
            self.realtime_thread.start()
        else:
            self.is_running_realtime = False
            self.btn_realtime.config(text="Bật Realtime (5M)")
            self.lbl_status.config(text="Trạng thái: Đang dừng", foreground="gray")
            self.txt_date.config(state="normal")
            self.btn_check_date.config(state="normal")
            self.btn_clear.config(state="normal")

    # ---- MODE 2: CHẠY REALTIME TỐI ƯU (Quét trễ 15 giây để ổn định dữ liệu) ----
    def realtime_loop(self):
        q = Quote(symbol='VN30F1M', source='VCI')
        
        print("Bot Realtime đã kích hoạt chế độ: Đợi dữ liệu sàn ổn định (Delay 15s)...")
        
        while self.is_running_realtime:
            try:
                now = datetime.now()
                current_second = now.second
                
                # CHỈ QUÉT KHI ĐỒNG HỒ BƯỚC SANG GIÂY THỨ 15 ĐẾN GIÂY THỨ 25 CỦA MỖI PHÚT
                # Điều này đảm bảo nến trước đó đã đóng được ít nhất 15 giây trên Server sàn
                if 15 <= current_second <= 25:
                    current_date = now.strftime('%Y-%m-%d')
                    df = q.history(start=current_date, end=current_date, interval='5m')
                    
                    if df is not None and len(df) >= 4:
                        if 'datetime' in df.columns: df = df.rename(columns={'datetime': 'time'})
                        elif 'time' not in df.columns and df.index.name == 'datetime':
                            df = df.reset_index().rename(columns={'datetime': 'time'})
                        
                        df = df.sort_values(by='time').reset_index(drop=True)
                        
                        # Lọc cô lập dữ liệu ngày hôm nay tránh dính cache
                        df['time_str'] = df['time'].astype(str)
                        df = df[df['time_str'].str.contains(current_date)].copy()
                        df = df.drop(columns=['time_str']).reset_index(drop=True)
                        
                        if len(df) < 4:
                            time.sleep(1)
                            continue
                            
                        # Hiển thị ticker nháy giá trị realtime đầu thanh điều khiển
                        self.lbl_status.config(text=f"Live: {df.iloc[-1]['close']} ({now.strftime('%H:%M:%S')})")

                        # Lấy cây nến đã ĐÓNG CỬA HOÀN TOÀN (Kế cuối: index -2)
                        latest_closed_candle = df.iloc[-2]
                        candle_time = str(latest_closed_candle['time'])

                        # KIỂM TRA KHÓA THỜI GIAN: Nếu nến này chưa từng được phân tích tín hiệu
                        if candle_time != self.last_triggered_time:
                            
                            # Tính toán bộ chỉ báo kỹ thuật lên chuỗi dữ liệu sạch
                            df['EMA_5'] = ta.ema(df['close'], length=5)
                            df['EMA_20'] = ta.ema(df['close'], length=20)
                            df['RSI'] = ta.rsi(df['close'], length=14)
                            df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
                            
                            current_data = df.iloc[-2] # Nến vừa đóng
                            prev_data = df.iloc[-3]    # Nến trước đó liền kề
                            
                            # Khóa luôn mốc thời gian để phút sau không chạy lại nến này nữa
                            self.last_triggered_time = candle_time
                            
                            atr_val = current_data['ATR'] if current_data['ATR'] > 0 else 1.0
                            close_px = current_data['close']
                            
                            # Ghi nhận chính xác mốc thời gian hệ thống phát hiện ra tín hiệu
                            scan_time_str = now.strftime('%H:%M:%S')
                            
                            # --- CHỈ KIỂM TRA ĐIỀU KIỆN CHO DUY NHẤT CẶP NẾN MỚI ĐÓNG ---
                            # LỆNH LONG
                            if (prev_data['EMA_5'] <= prev_data['EMA_20'] and current_data['EMA_5'] > current_data['EMA_20']) and current_data['RSI'] > 45:
                                sig = ("⚡ LONG", candle_time, scan_time_str, round(close_px, 1),
                                       round(close_px + (1.5 * atr_val), 1), round(close_px + (2.5 * atr_val), 1), round(close_px + (4.0 * atr_val), 1))
                                self.tree.insert("", 0, values=sig, tags=("LONG",))
                                
                            # LỆNH SHORT
                            elif (prev_data['EMA_5'] >= prev_data['EMA_20'] and current_data['EMA_5'] < current_data['EMA_20']) and current_data['RSI'] < 55:
                                sig = ("🚨 SHORT", candle_time, scan_time_str, round(close_px, 1),
                                       round(close_px - (1.5 * atr_val), 1), round(close_px - (2.5 * atr_val), 1), round(close_px - (4.0 * atr_val), 1))
                                self.tree.insert("", 0, values=sig, tags=("SHORT",))
                    
                    # Sau khi xử lý xong trong "khung giờ vàng" (giây thứ 15-25), cho bot ngủ 10 giây 
                    # để đẩy đồng hồ ra khỏi khoảng an toàn này, tránh bị quét lặp trong cùng 1 phút.
                    time.sleep(11)
                else:
                    # Nếu chưa đến giây thứ 15, cho bot nghỉ ngắn 1 giây rồi check lại đồng hồ hệ thống
                    time.sleep(1)
                    
            except Exception as e:
                print(f"Lỗi vòng lặp realtime: {e}")
                time.sleep(1)

if __name__ == "__main__":
    root = tk.Tk()
    app = BotPhaiSinhUI(root)
    root.mainloop()