# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from datetime import datetime
import pandas as pd
import pandas_ta as ta
import requests
from vnstock.api.quote import Quote
# Nhập thư viện hiển thị thông báo hệ thống
from plyer import notification 

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

        columns = ("type", "time", "scan_time", "price", "target1", "resistance", "support")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.signal_explanations = {}
        
        self.tree.heading("type", text="Loại Lệnh")
        self.tree.heading("time", text="Thời Điểm Đóng Nến")
        self.tree.heading("scan_time", text="Thời Điểm Quét Live")
        self.tree.heading("price", text="Giá Khớp (Close)")
        self.tree.heading("target1", text="Target 1 (+1.5 ATR)")
        self.tree.heading("resistance", text="Kháng Cự")
        self.tree.heading("support", text="Hỗ Trợ")

        self.tree.column("type", width=90, anchor="center")
        self.tree.column("time", width=130, anchor="center")
        self.tree.column("scan_time", width=130, anchor="center")
        self.tree.column("price", width=110, anchor="center")
        self.tree.column("target1", width=130, anchor="center")
        self.tree.column("resistance", width=120, anchor="center")
        self.tree.column("support", width=120, anchor="center")

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
        self.txt_detail = tk.Text(detail_frame, height=6, font=("Arial", 10), wrap=tk.WORD, bg="#f9f9f9", fg="#333333")
        self.txt_detail.pack(fill="x", expand=True)
        self.txt_detail.insert(tk.END, "Chọn một tín hiệu trên bảng để xem phân tích thông số kỹ thuật chi tiết tại đây...")
        self.txt_detail.config(state="disabled") # Khóa lại không cho người dùng gõ đè chữ vào

    def on_select_line(self, event):
        """Đưa phân tích chi tiết của dòng được chọn vào khung bên dưới."""
        selected_items = self.tree.selection()
        if not selected_items:
            return

        explanation_text = self.signal_explanations.get(selected_items[0], "")
        self.txt_detail.config(state="normal")
        self.txt_detail.delete("1.0", tk.END)
        self.txt_detail.insert(tk.END, explanation_text)
        self.txt_detail.config(state="disabled")

    def clear_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.signal_explanations.clear()
        self.txt_detail.config(state="normal")
        self.txt_detail.delete("1.0", tk.END)
        self.txt_detail.insert(tk.END, "Chọn một tín hiệu trên bảng để xem phân tích thông số kỹ thuật chi tiết tại đây...")
        self.txt_detail.config(state="disabled")

    def send_desktop_notification(self, signal_type, price, target, candle_time, resistance=None, support=None):
        """Gửi thông báo desktop; lỗi thư viện/Windows không làm gián đoạn quét tín hiệu."""
        levels = ""
        if resistance is not None and support is not None:
            levels = f"\nKháng cự: {resistance} | Hỗ trợ: {support}"
        try:
            notification.notify(
                title=f"{signal_type} VN30F1M - Tín hiệu mới",
                message=f"Giá: {price} | Target: {target} | Nến: {candle_time}{levels}",
                app_name="StockPS",
                timeout=10,
            )
        except Exception as e:
            print(f"Không thể gửi thông báo desktop: {e}")

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
        df['Resistance'] = df['high'].rolling(window=20).max()
        df['Support'] = df['low'].rolling(window=20).min()
        df = df.dropna().reset_index(drop=True)
        
        for i in range(1, len(df)):
            current = df.iloc[i]
            prev = df.iloc[i-1]
            atr_val = current['ATR'] if current['ATR'] > 0 else 1.0
            close_px = current['close']
            
            ema20_slope = current['EMA_20'] - prev['EMA_20']
            scan_time_str = "History Backtest"
            
            # Lấy giá trị kháng cự / hỗ trợ tại thời điểm nến hiện tại
            res_val = round(current['Resistance'], 1) if 'Resistance' in current and not pd.isna(current['Resistance']) else close_px
            sup_val = round(current['Support'], 1) if 'Support' in current and not pd.isna(current['Support']) else close_px

            if (prev['EMA_5'] <= prev['EMA_20'] and current['EMA_5'] > current['EMA_20']) and current['RSI'] > 50 and ema20_slope > 0.15:
                exp_text = (f"[TÍN HIỆU LONG - SÓNG TĂNG]\n"
                            f"- Giá hiện tại: {round(close_px, 1)} | Target (+1.5 ATR): {round(close_px + (1.5 * atr_val), 1)}\n"
                            f"- 🟢 Kháng cự gần nhất (Cản trên): {res_val} (Vùng có thể chốt lời hoặc xem xét Short lướt sóng)\n"
                            f"- 🟢 Hỗ trợ gần nhất (Cản dưới): {sup_val} (Vùng chặn lỗ an toàn)\n"
                            f"- Lý do: EMA5 cắt lên EMA20, RSI={round(current['RSI'],1)}, Độ dốc={round(ema20_slope,2)}")
                
                sig = ("⚡ LONG", current['time'], scan_time_str, round(close_px, 1), round(close_px + (1.5 * atr_val), 1), res_val, sup_val)
                item_id = self.tree.insert("", "end", values=sig, tags=("LONG",))
                self.signal_explanations[item_id] = exp_text
                target_price = round(close_px + (1.5 * atr_val), 1)
                self.send_desktop_notification("LONG", round(close_px, 1), target_price, current['time'], res_val, sup_val)
                tele_msg = f"⚡ **VN30F1M - TÍN HIỆU LONG (LỊCH SỬ)** ⚡\n🕒 Nến: `{current['time']}`\n💵 Giá khớp: **{round(close_px, 1)}**\n🎯 Target (+1.5 ATR): `{target_price}`\n\n{exp_text}"
                self.send_telegram_message(tele_msg)
                
            elif (prev['EMA_5'] >= prev['EMA_20'] and current['EMA_5'] < current['EMA_20']) and current['RSI'] < 50 and ema20_slope < -0.15:
                exp_text = (f"[TÍN HIỆU SHORT - SÓNG GIẢM]\n"
                            f"- Giá hiện tại: {round(close_px, 1)} | Target (-1.5 ATR): {round(close_px - (1.5 * atr_val), 1)}\n"
                            f"- 🔴 Kháng cự gần nhất (Cản trên): {res_val} (Vùng mở Short hoặc phòng hộ Hedging chuẩn)\n"
                            f"- 🔴 Hỗ trợ gần nhất (Cản dưới): {sup_val} (Vùng chốt lời kỳ vọng)\n"
                            f"- Lý do: EMA5 cắt xuống EMA20, RSI={round(current['RSI'],1)}, Độ dốc={round(ema20_slope,2)}")
                
                sig = ("🚨 SHORT", current['time'], scan_time_str, round(close_px, 1), round(close_px - (1.5 * atr_val), 1), res_val, sup_val)
                item_id = self.tree.insert("", "end", values=sig, tags=("SHORT",))
                self.signal_explanations[item_id] = exp_text
                target_price = round(close_px - (1.5 * atr_val), 1)
                self.send_desktop_notification("SHORT", round(close_px, 1), target_price, current['time'], res_val, sup_val)
                tele_msg = f"⚡ **VN30F1M - TÍN HIỆU SHORT (LỊCH SỬ)** ⚡\n🕒 Nến: `{current['time']}`\n💵 Giá khớp: **{round(close_px, 1)}**\n🎯 Target (-1.5 ATR): `{target_price}`\n\n{exp_text}"
                self.send_telegram_message(tele_msg)

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

    # ---- MODE 2: CHẠY REALTIME TỐI ƯU ----
    def realtime_loop(self):
        q = Quote(symbol='VN30F1M', source='VCI')
        while self.is_running_realtime:
            try:
                now = datetime.now()
                current_second = now.second
                
                if 15 <= current_second <= 25:
                    current_date = now.strftime('%Y-%m-%d')
                    df = q.history(start=current_date, end=current_date, interval='5m')
                    
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
                            
                        self.lbl_status.config(text=f"Live: {df.iloc[-1]['close']} ({now.strftime('%H:%M:%S')})")

                        latest_closed_candle = df.iloc[-2]
                        candle_time = str(latest_closed_candle['time'])

                        if candle_time != self.last_triggered_time:
                            df['EMA_5'] = ta.ema(df['close'], length=5)
                            df['EMA_20'] = ta.ema(df['close'], length=20)
                            df['RSI'] = ta.rsi(df['close'], length=14)
                            df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
                            # Thêm Kháng cự và Hỗ trợ động dựa trên đỉnh/đáy 20 nến 5m gần nhất (Donchian / Rolling Channel)
                            df['Resistance'] = df['high'].rolling(window=20).max()
                            df['Support'] = df['low'].rolling(window=20).min()
                            
                            current_data = df.iloc[-2]
                            prev_data = df.iloc[-3]
                            
                            self.last_triggered_time = candle_time
                            
                            atr_val = current_data['ATR'] if current_data['ATR'] > 0 else 1.0
                            close_px = current_data['close']
                            scan_time_str = now.strftime('%H:%M:%S')
                            
                            ema20_slope = current_data['EMA_20'] - prev_data['EMA_20']
                            res_val = round(current_data['Resistance'], 1) if pd.notna(current_data['Resistance']) else round(close_px, 1)
                            sup_val = round(current_data['Support'], 1) if pd.notna(current_data['Support']) else round(close_px, 1)
                            
                            if (prev_data['EMA_5'] <= prev_data['EMA_20'] and current_data['EMA_5'] > current_data['EMA_20']) and current_data['RSI'] > 50 and ema20_slope > 0.15:
                                exp_text = f"[TÍN HIỆU LONG LIVE]\n• Lý do: Cắt lên xu hướng ngắn hạn.\n• Chi tiết thông số quét thực tế lúc {scan_time_str}:\n  + EMA5 = {round(current_data['EMA_5'],1)} | EMA20 = {round(current_data['EMA_20'],1)}\n  + RSI = {round(current_data['RSI'],1)} (> 50)\n  + Độ dốc EMA20 = +{round(ema20_slope,2)} (> 0.15) -> Đủ điều kiện xác lập xu hướng tăng."
                                sig = ("⚡ LONG", candle_time, scan_time_str, round(close_px, 1), round(close_px + (1.5 * atr_val), 1), res_val, sup_val)
                                item_id = self.tree.insert("", 0, values=sig, tags=("LONG",))
                                self.signal_explanations[item_id] = exp_text
                                # 📢 Bắn thông báo màn hình máy tính
                                target_price = round(close_px + (1.5 * atr_val), 1)
                                # self.send_desktop_notification("LONG", round(close_px, 1), target_price, candle_time, res_val, sup_val)
                                tele_msg = f"⚡ **VN30F1M - TÍN HIỆU LONG** ⚡\n🕒 Giờ: `{scan_time_str}` (Nến: `{candle_time}`)\n💵 Giá khớp: **{round(close_px, 1)}**\n🎯 Target (+1.5 ATR): `{round(close_px + (1.5 * atr_val), 1)}`\n\n{exp_text}"
                                self.send_telegram_message(tele_msg)
                                
                            elif (prev_data['EMA_5'] >= prev_data['EMA_20'] and current_data['EMA_5'] < current_data['EMA_20']) and current_data['RSI'] < 50 and ema20_slope < -0.15:
                                exp_text = f"[TÍN HIỆU SHORT LIVE]\n• Lý do: Cắt xuống bẻ gãy xu hướng.\n• Chi tiết thông số quét thực tế lúc {scan_time_str}:\n  + EMA5 = {round(current_data['EMA_5'],1)} | EMA20 = {round(current_data['EMA_20'],1)}\n  + RSI = {round(current_data['RSI'],1)} (< 50)\n  + Độ dốc EMA20 = {round(ema20_slope,2)} (< -0.15) -> Đủ điều kiện xác lập xu hướng sập gãy."
                                sig = ("🚨 SHORT", candle_time, scan_time_str, round(close_px, 1), round(close_px - (1.5 * atr_val), 1), res_val, sup_val)
                                item_id = self.tree.insert("", 0, values=sig, tags=("SHORT",))
                                self.signal_explanations[item_id] = exp_text
                                # 📢 Bắn thông báo màn hình máy tính
                                target_price = round(close_px - (1.5 * atr_val), 1)
                                tele_msg = f"⚡ **VN30F1M - TÍN HIỆU SHORT** ⚡\n🕒 Giờ: `{scan_time_str}` (Nến: `{candle_time}`)\n💵 Giá khớp: **{round(close_px, 1)}**\n🎯 Target (+1.5 ATR): `{round(close_px - (1.5 * atr_val), 1)}`\n\n{exp_text}"
                                self.send_telegram_message(tele_msg)
                                # self.send_desktop_notification("SHORT", round(close_px, 1), target_price, candle_time, res_val, sup_val)

                    time.sleep(11)
                else:
                    time.sleep(1)
                    
            except Exception as e:
                print(f"Lỗi vòng lặp realtime: {e}")
                time.sleep(1)

    def send_telegram_message(self, message):
        TOKEN = "9170119862:AAEZWIOe4cdAigoOXyzYWzkfov69xExAQdY"
        CHAT_ID = "1689615894"
        
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"  # Giúp định dạng chữ đậm, nghiêng nếu muốn
        }
        try:
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code != 200:
                print(f"Lỗi gửi Telegram: {response.text}")
        except Exception as e:
            print(f"Không thể kết nối Telegram: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = BotPhaiSinhUI(root)
    root.mainloop()