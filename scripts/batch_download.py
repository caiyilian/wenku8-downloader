# -*- coding: utf-8 -*-
"""批量下载6本小说 - 直接写入日志文件"""
import sys, os, time
sys.path.insert(0, '.')
from wenku8_downloader import Wenku8Client

# 直接写日志，避免 stdout 编码问题
log_file = open('batch_progress.log', 'w', encoding='utf-8')

def log(msg):
    print(msg)
    log_file.write(msg + '\n')
    log_file.flush()

books = [
    (2255, '魔女之旅'),
    (5, '狼与香辛料'),
    (1973, '欢迎来到实力至上主义的教室'),
    (2883, '义妹生活'),
    (3057, '败犬女主太多了'),
    (2738, '二十世纪电气目录'),
]

client = Wenku8Client(delay=2.0)

for book_id, name in books:
    log(f"\n{'='*60}")
    log(f"开始下载: {name} (book_id={book_id})")
    log(f"{'='*60}")
    try:
        client.download_book(book_id)
        log(f"[OK] {name} 下载完成")
    except Exception as e:
        log(f"[FAIL] {name} 下载失败: {e}")
    log("休息 10 秒...")
    time.sleep(10)

log(f"\n{'='*60}")
log("所有书籍下载完成!")
log(f"{'='*60}")
log_file.close()