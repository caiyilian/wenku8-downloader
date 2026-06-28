# -*- coding: utf-8 -*-
"""继续下载剩余2本"""
import sys, os, time
sys.path.insert(0, '.')
from wenku8_downloader import Wenku8Client

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

log_file = open('final_progress.log', 'w', encoding='utf-8')
def log(msg):
    print(msg)
    log_file.write(msg + '\n')
    log_file.flush()

# 先删除空文件夹
import shutil
empty_dir = os.path.join('downloads', '败北女角太多了！(败犬女主太多了！)')
if os.path.exists(empty_dir) and not os.listdir(empty_dir):
    os.rmdir(empty_dir)
    log(f"已删除空文件夹: {empty_dir}")

books = [
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
log("全部下载完成!")
log(f"{'='*60}")
log_file.close()