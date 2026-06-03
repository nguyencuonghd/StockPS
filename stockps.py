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
        self.root.title("Hệ Thống Tín Hiệu Phái Sinh VN30F1M - Khung Tốc Độ 1 Phút (1M)")
        self.root.geometry("1100x680")
        
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

        # Bộ nút bấm chức năng
        self.btn_check_date = ttk.Button(control_frame, text="Quét Lịch Sử (1M)", command=self.run_check_date)
        self.btn_check_date.grid(row=0, column=2, padx=5, pady=5)

        self.btn_clear = ttk.Button(control_frame, text="Clear", command=self.clear_table)
        self.btn_clear.grid(row=0, column=3, padx=5, pady=5)

        self.btn_realtime = ttk.Button(control_frame, text="Bật Realtime (1M)", command=self.toggle_realtime)
        self.btn_realtime.grid(row=0, column=4, padx=5, pady=5)

        self.lbl_status = ttk.Label(control_frame, text="Trạng thái: Đang dừng", font=("Arial", 10, "bold"), foreground="gray")
        self.lbl_status.grid(row=0, column=5, padx=15, pady=5)

        # ---- Khung Hiển Thị Bảng Dữ Liệu ----
        table_frame = ttk.LabelFrame(self.root, text=" Danh Sách Tín Hiệu Xuất Hiện (Khung 1 Phút) ", padding=10)
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

        # Bắt sự kiện click dòng
        self.tree.bind("<<TreeviewSelect>>", self.on_select_line)

        # ---- KHUNG PHỤ: XEM CHI TIẾT TỰ ĐỘNG XUỐNG DÒNG ----
        detail_frame = ttk.LabelFrame(self.root, text=" Chi Tiết Thông Số Bộ Lọc Của Tín Hiệu 1M Được Chọn ", padding=10)
        detail_frame.pack(fill="x", padx=10, pady=10)

        self.txt_detail = tk.Text(detail_frame, height=4, font=("Arial", 10), wrap=tk.WORD, bg="#f9f9f9", fg="#333333")
        self.txt_detail.pack(fill="x", expand=True)
        self.txt_detail.insert(tk.END, "Chọn một tín hiệu trên bảng để xem phân tích thông số kỹ thuật chi tiết tại đây...")
        self.txt_detail.config(state="disabled")

    def on_select_line(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            return
        item_values = self.tree.item(selected_items[0], "values")
        if item_values and len(item_values) >= 6:
            explanation_text = item_values[5]
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

    # ---- MODE 1: QUÉT LỊCH SỬ KHUNG 1M ----
    def run_check_date(self):
        target_date = self.txt_date.get().strip()
        try:
            datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Lỗi định dạng", "Định dạng ngày phải là YYYY-MM-DD")
            return

        self.clear_table()

        q = Quote(symbol='VN30F1M', source='VCI')
        # Cấu hình tải dữ liệu khung 1m
        df = q.history(start=target_date, end=target_date, interval='1m')
        
        if df is None or df.empty:
            messagebox.showinfo("Thông báo", f"Không tìm thấy dữ liệu 1M cho ngày {target_date}.")
            return

        if 'datetime' in df.columns:
            df = df.rename(columns={'datetime': 'time'})
        elif 'time' not in df.columns and df.index.name == 'datetime':
            df = df.reset_index().rename(columns={'datetime': 'time'})

        df['time_str'] = df['time'].astype(str)
        df = df[df['time_str'].str.contains(target_date)].copy()
        df = df.drop(columns=['time_str']).reset_index(drop=True)

        if df.empty:
            messagebox.showinfo("Thông báo", f"Không có dữ liệu nến 1M thuộc ngày {target_date}.")
            return

        # Tính toán bộ chỉ báo tối ưu riêng cho khung 1M
        df['EMA_10'] = ta.ema(df['close'], length=10)
        df['EMA_30'] = ta.ema(df['close'], length=30)
        df['RSI'] = ta.rsi(df['close'], length=14)
        df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        df = df.dropna().reset_index(drop=True)
        
        for i in range(1, len(df)):
            current = df.iloc[i]
            prev = df.iloc[i-1]
            atr_val = current['ATR'] if current['ATR'] > 0 else 1.0
            close_px = current['close']
            
            # Tính độ dốc đường xu hướng EMA30 trên khung 1M
            ema30_slope = current['EMA_30'] - prev['EMA_30']
            scan_time_str = "History Backtest"
            
            # ĐIỀU KIỆN LONG KHUNG 1M (EMA10 cắt lên EMA30, RSI > 50, Độ dốc xu hướng > 0.05)
            if (prev['EMA_10'] <= prev['EMA_30'] and current['EMA_10'] > current['EMA_30']) and current['RSI'] > 50 and ema30_slope > 0.05:
                exp_text = f"[TÍN HIỆU LONG 1M]\n• Lý do: Khung 1M kích hoạt giao cắt phát tín hiệu sớm. Đường EMA10 ({round(current['EMA_10'],1)}) cắt lên trên đường xu hướng EMA30 ({round(current['EMA_30'],1)}).\n• Kiểm tra RSI: Đạt {round(current['RSI'],1)} (> 50), phe Long chính thức làm chủ khung ngắn hạn.\n• Kiểm tra Độ dốc: Độ dốc EMA30 đạt +{round(ema30_slope,2)} (> 0.05), xác nhận có lực đẩy Trend 1M rõ ràng."
                sig = ("⚡ LONG", current['time'], scan_time_str, round(close_px, 1), round(close_px + (1.5 * atr_val), 1), exp_text)
                self.tree.insert("", "end", values=sig, tags=("LONG",))
                
            # ĐIỀU KIỆN SHORT KHUNG 1M (EMA10 cắt xuống EMA30, RSI < 50, Độ dốc xu hướng < -0.05)
            elif (prev['EMA_10'] >= prev['EMA_30'] and current['EMA_10'] < current['EMA_30']) and current['RSI'] < 50 and ema30_slope < -0.05:
                exp_text = f"[TÍN HIỆU SHORT 1M]\n• Lý do: Khung 1M kích hoạt giao cắt phát tín hiệu sớm. Đường EMA10 ({round(current['EMA_10'],1)}) cắt xuống dưới đường xu hướng EMA30 ({round(current['EMA_30'],1)}).\n• Kiểm tra RSI: Giảm còn {round(current['RSI'],1)} (< 50), áp lực kích hoạt lệnh Short tháo chạy.\n• Kiểm tra Độ dốc: Độ dốc EMA30 đạt {round(ema30_slope,2)} (< -0.05), cấu trúc sụt giảm khung 1M được xác lập ổn định."
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
            self.btn_realtime.config(text="Bật Realtime (1M)")
            self.lbl_status.config(text="Trạng thái: Đang dừng", foreground="gray")
            self.txt_date.config(state="normal")
            self.btn_check_date.config(state="normal")
            self.btn_clear.config(state="normal")

    # ---- MODE 2: CHẠY REALTIME THEO KHUNG NẾN 1 PHÚT ----
    def realtime_loop(self):
        q = Quote(symbol='VN30F1M', source='VCI')
        print("Bot Realtime 1M đã kích hoạt...")
        
        while self.is_running_realtime:
            try:
                now = datetime.now()
                current_second = now.second
                
                # Để tối ưu nến 1M, quét ngay tại giây thứ 5 đến 12 của mỗi phút mới (khi nến vừa đóng được vài giây)
                if 5 <= current_second <= 12:
                    current_date = now.strftime('%Y-%m-%d')
                    df = q.history(start=current_date, end=current_date, interval='1m')
                    
                    if df is not None and len(df) >= 4:
                        if 'datetime' in df.columns: df = df.rename(columns={'datetime': 'time'})
                        elif 'time' not in df.columns and df.index.name == 'datetime':
                            df = df.reset_index().rename(columns={'datetime': 'time'})
                        
                        df = df.sort_values(by='time').reset_index(drop=True)
                        df['time_str'] = df['time'].astype(str)
                        df = df[df['time_str'].str.contains(current_date)].copy()
                        df = df.drop(columns=['time_str']).reset_index(drop=True)
                        
                        if len(df) < 4:
                            time.sleep(1)
                            continue
                            
                        self.lbl_status.config(text=f"Live 1M: {df.iloc[-1]['close']} ({now.strftime('%H:%M:%S')})")

                        # Lấy cây nến 1 phút vừa đóng hoàn toàn (index -2)
                        latest_closed_candle = df.iloc[-2]
                        candle_time = str(latest_closed_candle['time'])

                        if candle_time != self.last_triggered_time:
                            df['EMA_10'] = ta.ema(df['close'], length=10)
                            df['EMA_30'] = ta.ema(df['close'], length=30)
                            df['RSI'] = ta.rsi(df['close'], length=14)
                            df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
                            
                            current_data = df.iloc[-2]
                            prev_data = df.iloc[-3]
                            
                            self.last_triggered_time = candle_time
                            
                            atr_val = current_data['ATR'] if current_data['ATR'] > 0 else 1.0
                            close_px = current_data['close']
                            scan_time_str = now.strftime('%H:%M:%S')
                            
                            # Độ dốc xu hướng thực tế của khung 1M
                            ema30_slope = current_data['EMA_30'] - prev_data['EMA_30']
                            
                            if (prev_data['EMA_10'] <= prev_data['EMA_30'] and current_data['EMA_10'] > current_data['EMA_30']) and current_data['RSI'] > 50 and ema30_slope > 0.05:
                                exp_text = f"[TÍN HIỆU LONG LIVE 1M]\n• Vị thế quét thực tế lúc: {scan_time_str}\n• Chỉ báo kỹ thuật:\n  + EMA10 = {round(current_data['EMA_10'],1)} | EMA30 = {round(current_data['EMA_30'],1)}\n  + RSI = {round(current_data['RSI'],1)} (> 50)\n  + Độ dốc EMA30 = +{round(ema30_slope,2)} (> 0.05) -> Đạt tiêu chuẩn kích hoạt lệnh Long nhanh."
                                sig = ("⚡ LONG", candle_time, scan_time_str, round(close_px, 1), round(close_px + (1.5 * atr_val), 1), exp_text)
                                self.tree.insert("", 0, values=sig, tags=("LONG",))
                                
                            elif (prev_data['EMA_10'] >= prev_data['EMA_30'] and current_data['EMA_10'] < current_data['EMA_30']) and current_data['RSI'] < 50 and ema30_slope < -0.05:
                                exp_text = f"[TÍN HIỆU SHORT LIVE 1M]\n• Vị thế quét thực tế lúc: {scan_time_str}\n• Chỉ báo kỹ thuật:\n  + EMA10 = {round(current_data['EMA_10'],1)} | EMA30 = {round(current_data['EMA_30'],1)}\n  + RSI = {round(current_data['RSI'],1)} (< 50)\n  + Độ dốc EMA30 = {round(ema30_slope,2)} (< -0.05) -> Đạt tiêu chuẩn kích hoạt lệnh Short nhanh."
                                sig = ("🚨 SHORT", candle_time, scan_time_str, round(close_px, 1), round(close_px - (1.5 * atr_val), 1), exp_text)
                                self.tree.insert("", 0, values=sig, tags=("SHORT",))
                    
                    # Cho bot nghỉ 10 giây để thoát khỏi khung giờ quét của phút đó
                    time.sleep(10)
                else:
                    time.sleep(1)
                    
            except Exception as e:
                print(f"Lỗi vòng lặp realtime 1M: {e}")
                time.sleep(1)

if __name__ == "__main__":
    root = tk.Tk()
    app = BotPhaiSinhUI(root)
    root.mainloop()