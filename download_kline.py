import akshare as ak
import pandas as pd
import sqlite3
import time
from tqdm import tqdm

# =========================
# 配置
# =========================
DB_PATH = "a_share_kline.db"
START_DATE = "20260101"
END_DATE = "20260213"
RETRY = 3
SLEEP = 0

# =========================
# 数据库初始化（重建）
# =========================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS kline")

    cursor.execute("""
    CREATE TABLE kline (
        ts_code TEXT,
        name TEXT,
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
# 获取股票列表（过滤 ST / 科创板 / 北交所）
# =========================
def get_stock_list():
    df = ak.stock_info_a_code_name()

    # 过滤 ST
    df = df[~df["name"].str.contains("ST")]

    # 排除科创板 688 开头
    df = df[~df["code"].str.startswith("688")]

    # 排除北交所 8 开头
    df = df[~df["code"].str.startswith("8")]
    df = df[~df["code"].str.startswith("920")]

    print(f"📊 过滤后股票数量: {len(df)}")

    return df[["code", "name"]]

# =========================
# 下载单只股票
# =========================
def download_stock(code, name):
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
            df["name"] = name

            return df[[
                "ts_code", "name", "trade_date",
                "open", "close", "high", "low",
                "volume", "amount"
            ]]

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

    stock_df = get_stock_list()
    total = len(stock_df)

    print(f"📊 股票总数（过滤后）: {total}")

    success = 0
    fail = 0

    for _, row in tqdm(stock_df.iterrows(), total=total, desc="⬇️ 下载进度", ncols=80):
        code = row["code"]
        name = row["name"]

        df = download_stock(code, name)

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
