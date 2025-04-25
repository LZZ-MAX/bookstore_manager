import sqlite3
import os

def connect_db() -> sqlite3.Connection:
    """
    連接到 SQLite 資料庫並返回連線物件。

    資料庫文件位於當前目錄，名稱為 'bookstore.db'。如果資料庫不存在，將會創建一個。

    返回:
        sqlite3.Connection: 連接到 SQLite 資料庫的連線物件。
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, 'bookstore.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db(conn: sqlite3.Connection) -> None:
    """
    初始化資料庫，創建會員、書籍和銷售記錄的表格。

    該函數創建三個表格：
    - `member`: 存儲會員信息（ID、姓名、電話、電子郵件）。
    - `book`: 存儲書籍信息（ID、書名、價格、庫存）。
    - `sale`: 存儲銷售記錄（ID、日期、會員ID、書籍ID、數量、折扣、總金額）。

    另外，如果 `member`、`book` 或 `sale` 表格是空的，則插入一些示範數據。

    參數:
        conn (sqlite3.Connection): 連接到 SQLite 資料庫的連線物件。
    """
    cursor = conn.cursor()

    cursor.executescript("""
        -- 創建會員表
        CREATE TABLE IF NOT EXISTS member (
            mid TEXT PRIMARY KEY,
            mname TEXT NOT NULL,
            mphone TEXT NOT NULL,
            memail TEXT
        );

        -- 創建書籍表
        CREATE TABLE IF NOT EXISTS book (
            bid TEXT PRIMARY KEY,
            btitle TEXT NOT NULL,
            bprice INTEGER NOT NULL,
            bstock INTEGER NOT NULL
        );

        -- 創建銷售記錄表
        CREATE TABLE IF NOT EXISTS sale (
            sid INTEGER PRIMARY KEY AUTOINCREMENT,
            sdate TEXT NOT NULL,
            mid TEXT NOT NULL,
            bid TEXT NOT NULL,
            sqty INTEGER NOT NULL,
            sdiscount INTEGER NOT NULL,
            stotal INTEGER NOT NULL,
            FOREIGN KEY (mid) REFERENCES member(mid),
            FOREIGN KEY (bid) REFERENCES book(bid)
        );
    """)

    cursor.execute("SELECT COUNT(*) FROM member")
    if cursor.fetchone()[0] == 0:
        cursor.executescript("""
            INSERT INTO member VALUES ('M001', 'Alice', '0912-345678', 'alice@example.com');
            INSERT INTO member VALUES ('M002', 'Bob', '0923-456789', 'bob@example.com');
            INSERT INTO member VALUES ('M003', 'Cathy', '0934-567890', 'cathy@example.com');

            INSERT INTO book VALUES ('B001', 'Python Programming', 600, 50);
            INSERT INTO book VALUES ('B002', 'Data Science Basics', 800, 30);
            INSERT INTO book VALUES ('B003', 'Machine Learning Guide', 1200, 20);

            INSERT INTO sale (sdate, mid, bid, sqty, sdiscount, stotal) VALUES ('2024-01-15', 'M001', 'B001', 2, 100, 1100);
            INSERT INTO sale (sdate, mid, bid, sqty, sdiscount, stotal) VALUES ('2024-01-16', 'M002', 'B002', 1, 50, 750);
            INSERT INTO sale (sdate, mid, bid, sqty, sdiscount, stotal) VALUES ('2024-01-17', 'M001', 'B003', 3, 200, 3400);
            INSERT INTO sale (sdate, mid, bid, sqty, sdiscount, stotal) VALUES ('2024-01-18', 'M003', 'B001', 1, 0, 600);
        """)

    conn.commit()

def add_sale(conn: sqlite3.Connection, sdate: str, mid: str, bid: str, sqty: int, sdiscount: int) -> tuple[bool, str]:
    """
    新增一筆銷售記錄到資料庫。

    該函數檢查輸入數據的有效性（例如，日期格式、庫存可用性），計算銷售總額，並更新書籍庫存。如果有任何輸入無效，將返回錯誤訊息。

    參數:
        conn (sqlite3.Connection): 連接到 SQLite 資料庫的連線物件。
        sdate (str): 銷售日期，格式為 'YYYY-MM-DD'。
        mid (str): 會員ID。
        bid (str): 書籍ID。
        sqty (int): 購買的書籍數量。
        sdiscount (int): 銷售折扣金額。

    返回:
        tuple[bool, str]: 一個元組，第一個值是布林值，表示是否成功，第二個值是訊息。
    """
    cursor = conn.cursor()

    if len(sdate) != 10 or sdate.count('-') != 2:
        return False, "❌ 日期格式錯誤，應為 YYYY-MM-DD。"

    if sqty <= 0 or sdiscount < 0:
        return False, "❌ 數量必須 > 0，折扣金額不得為負數。"

    cursor.execute("SELECT 1 FROM member WHERE mid = ?", (mid,))
    if cursor.fetchone() is None:
        return False, f"❌ 會員編號 {mid} 不存在。"

    cursor.execute("SELECT bprice, bstock FROM book WHERE bid = ?", (bid,))
    book = cursor.fetchone()
    if book is None:
        return False, f"❌ 書籍編號 {bid} 不存在。"

    bprice = book["bprice"]
    bstock = book["bstock"]

    if sqty > bstock:
        return False, f"❌ 庫存不足，目前庫存為 {bstock} 本。"

    stotal = bprice * sqty - sdiscount
    if stotal < 0:
        stotal = 0

    try:
        cursor.execute('''
            INSERT INTO sale (sdate, mid, bid, sqty, sdiscount, stotal)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (sdate, mid, bid, sqty, sdiscount, stotal))

        cursor.execute('''
            UPDATE book SET bstock = bstock - ?
            WHERE bid = ?
        ''', (sqty, bid))

        conn.commit()
        return True, f"✅ 銷售記錄已新增！(銷售總額: {stotal})"
    except sqlite3.IntegrityError as e:
        return False, f"❌ 錯誤：{e}"

def print_sale_report(conn: sqlite3.Connection) -> None:
    """
    輸出顯示所有銷售記錄的報表。

    報表包括銷售ID、日期、會員姓名、書籍標題、價格、數量、折扣和銷售總金額。

    參數:
        conn (sqlite3.Connection): 連接到 SQLite 資料庫的連線物件。
    """
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            s.sid, s.sdate, s.sqty, s.sdiscount, s.stotal,
            m.mname, b.btitle, b.bprice
        FROM sale s
        JOIN member m ON s.mid = m.mid
        JOIN book b ON s.bid = b.bid
        ORDER BY s.sid
    """)

    rows = cursor.fetchall()
    if not rows:
        print("⚠️ 沒有銷售紀錄。")
        return

    print("=" * 25 + " 銷售報表 " + "=" * 25)
    for idx, row in enumerate(rows, 1):
        sid = row["sid"]
        sdate = row["sdate"]
        mname = row["mname"]
        btitle = row["btitle"]
        bprice = row["bprice"]
        sqty = row["sqty"]
        sdiscount = row["sdiscount"]
        stotal = row["stotal"]

        print(f"銷售 #{idx}")
        print(f"銷售編號: {sid}")
        print(f"銷售日期: {sdate}")
        print(f"會員姓名: {mname}")
        print(f"書籍標題: {btitle}")
        print("-" * 50)
        print(f"{'單價':<8}{'數量':<8}{'折扣':<10}{'小計':<8}")
        print("-" * 50)
        print(f"{bprice:<10}{sqty:<10}{sdiscount:<12}{f'{stotal:,}':<5}")
        print("-" * 50)
        print(f"銷售總額: {f'{stotal:,}'}")
        print("=" * 50)

def update_sale(conn: sqlite3.Connection) -> None:
    """
    更新現有銷售記錄的折扣金額。

    該函數提示用戶選擇要更新的銷售記錄並輸入新的折扣金額。然後計算更新後的總金額並應用變更。

    參數:
        conn (sqlite3.Connection): 連接到 SQLite 資料庫的連線物件。
    """
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.sid, s.sdate, m.mname
        FROM sale s
        JOIN member m ON s.mid = m.mid
        ORDER BY s.sid
    """)
    sales = cursor.fetchall()

    if not sales:
        print("⚠️ 沒有銷售紀錄可更新。")
        return

    print("======== 銷售記錄列表 ========")
    for idx, row in enumerate(sales, 1):
        print(f"{idx}. 銷售編號: {row['sid']} - 會員: {row['mname']} - 日期: {row['sdate']}")
    print("================================")

    choice = input("請選擇要更新的銷售編號 (輸入數字或按 Enter 取消): ").strip()
    if not choice:
        print("➡️ 已取消更新。")
        return

    try:
        idx = int(choice)
        if idx < 1 or idx > len(sales):
            print("❌ 輸入的選項超出範圍。")
            return
        sid = sales[idx - 1]['sid']
    except ValueError:
        print("❌ 請輸入有效的數字。")
        return

    try:
        new_discount = int(input("請輸入新的折扣金額：").strip())
        if new_discount < 0:
            print("❌ 折扣金額不得為負數。")
            return
    except ValueError:
        print("❌ 折扣金額須為整數。")
        return

    cursor.execute("""
        SELECT s.sqty, b.bprice
        FROM sale s
        JOIN book b ON s.bid = b.bid
        WHERE s.sid = ?
    """, (sid,))
    data = cursor.fetchone()
    if not data:
        print("❌ 查無該銷售編號。")
        return

    bprice = data["bprice"]
    sqty = data["sqty"]
    stotal = max(bprice * sqty - new_discount, 0)

    cursor.execute("""
        UPDATE sale SET sdiscount = ?, stotal = ?
        WHERE sid = ?
    """, (new_discount, stotal, sid))
    conn.commit()

    print(f"✅ 銷售編號 {sid} 已更新！(銷售總額: {stotal:,})")

def delete_sale(conn: sqlite3.Connection) -> None:
    """
    刪除一筆銷售記錄。

    參數:
        conn (sqlite3.Connection): 連接到 SQLite 資料庫的連線物件。
    """
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.sid, s.sdate, m.mname
        FROM sale s
        JOIN member m ON s.mid = m.mid
        ORDER BY s.sid
    """)
    sales = cursor.fetchall()

    if not sales:
        print("⚠️ 沒有銷售紀錄可刪除。")
        return

    print("======== 銷售記錄列表 ========")
    for idx, row in enumerate(sales, 1):
        print(f"{idx}. 銷售編號: {row['sid']} - 會員: {row['mname']} - 日期: {row['sdate']}")
    print("================================")

    while True:
        choice = input("請選擇要刪除的銷售編號 (輸入數字或按 Enter 取消): ").strip()
        if choice == '':
            print("✅ 已取消刪除操作。")
            return
        try:
            choice = int(choice)
            if choice < 1 or choice > len(sales):
                print("❌ 錯誤：請輸入有效的數字")
                continue
        except ValueError:
            print("❌ 錯誤：請輸入有效的數字")
            continue
        break

    sid_to_delete = sales[choice - 1]["sid"]

    try:
        cursor.execute("DELETE FROM sale WHERE sid = ?", (sid_to_delete,))
        conn.commit()
        print(f"✅ 銷售編號 {sid_to_delete} 已刪除")
    except sqlite3.Error as e:
        print(f"❌ 刪除失敗：{e}")

def main() -> None:
    """
    主函數，提供用戶與書店系統交互的選單，允許他們新增、更新、刪除或查看銷售記錄。

    該函數運行主循環，向用戶提供不同的選項來管理銷售記錄。
    """
    conn = connect_db()
    initialize_db(conn)

    print('*' * 15 + '選單' + '*' * 15)
    print('1. 新增銷售紀錄')
    print('2. 顯示銷售報表')
    print('3. 更新銷售紀錄')
    print('4. 刪除銷售紀錄')
    print('5. 離開')

    while True:
        print('請選擇操作項目(Enter 離開)：')
        choice = input().strip()
        match choice:
            case '1':
                print('新增銷售紀錄')
                sdate = input("請輸入銷售日期 (YYYY-MM-DD)：").strip()
                mid = input("請輸入會員編號：").strip()
                bid = input("請輸入書籍編號：").strip()
                sqty = int(input("請輸入購買數量：").strip())
                sdiscount = int(input("請輸入折扣金額：").strip())
                success, msg = add_sale(conn, sdate, mid, bid, sqty, sdiscount)
                print(msg)
            case '2':
                print_sale_report(conn)
            case '3':
                update_sale(conn)
            case '4':
                delete_sale(conn)
            case '5':
                print("謝謝使用，再見！")
                break
            case _:
                print("無效的選項，請重新選擇。")
