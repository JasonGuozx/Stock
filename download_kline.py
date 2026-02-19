import akshare as ak
import pandas as pd
import sqlite3
import time
from tqdm import tqdm

# =========================
# 配置
# =========================
DB_PATH = "a_share_kline.db"
START_DATE = "20251001"
END_DATE = "20260213"
RETRY = 3          # 重试次数
SLEEP = 0.5        # 请求间隔（防封）

# =========================
# 数据库初始化
# =========================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS kline (
        ts_code TEXT,
        trade_date TEXT,
        open REAL,
        close REAL,
        high REAL,
        low REAL,
        volume REAL,
        amount REAL,
        PRIMARY KEY (ts_code, trade_date)
    )
    """)

    conn.commit()
    conn.close()

# =========================
# 获取股票列表（过滤 ST）
# =========================
def get_stock_list():
    df = ak.stock_info_a_code_name()
    df = df[~df["name"].str.contains("ST")]
    return df["code"].tolist()

# =========================
# 下载单只股票
# =========================
def download_stock(code):
    for _ in range(RETRY):
        try:
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=START_DATE,
                end_date=END_DATE,
                adjust="qfq"
            )
            if df is None or df.empty:
                return None

            df = df.rename(columns={
                "日期": "trade_date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
                "成交额": "amount"
            })

            df["ts_code"] = code
            return df[["ts_code","trade_date","open","close","high","low","volume","amount"]]

        except Exception:
            time.sleep(1)

    return None

# =========================
# 写入数据库
# =========================
def save_to_db(df):
    conn = sqlite3.connect(DB_PATH)
    df.to_sql("kline", conn, if_exists="append", index=False)
    conn.close()

# =========================
# 主程序
# =========================
def main():
    init_db()
    stock_list = get_stock_list()
    total = len(stock_list)

    print(f"📊 股票总数（已过滤ST）: {total}")

    success = 0
    fail = 0

    # tqdm 进度条（滚动更新，不刷屏）
    for code in tqdm(stock_list, desc="⬇️ 下载进度", ncols=80):
        df = download_stock(code)

        if df is not None:
            save_to_db(df)
            success += 1
        else:
            fail += 1

        time.sleep(SLEEP)

    print("\n✅ 下载完成")
    print(f"成功: {success}")
    print(f"失败: {fail}")
    print(f"数据库: {DB_PATH}")

# =========================
if __name__ == "__main__":
    main()
