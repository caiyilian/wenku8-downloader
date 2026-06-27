#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wenku8 轻小说下载器
===================
功能：
  1. 按书名搜索小说（自动从 wenku8 和 web 搜索中匹配）
  2. 按 book_id 直接下载全部卷
  3. 逐章抓取，适当 sleep 避免频率过高
  4. 按卷分文件保存为 txt

用法：
  python wenku8_downloader.py search <关键词>
  python wenku8_downloader.py download <book_id>
  python wenku8_downloader.py download <完整URL>
  python wenku8_downloader.py          # 交互模式
"""

import requests
import urllib3
import re
import os
import sys
import time
import json
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup

urllib3.disable_warnings()

# ============================================================
# 配置
# ============================================================
REQUEST_DELAY = 3.0         # 每次请求间隔（秒）
MAX_RETRIES = 5             # 最大重试次数
OUTPUT_DIR = "downloads"    # 下载输出目录

# ============================================================
# Wenku8 客户端
# ============================================================
class Wenku8Client:
    BASE = "https://www.wenku8.net"

    __USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]

    def __init__(self, delay=REQUEST_DELAY):
        self.session = requests.Session()
        self.session.verify = False
        self.session.trust_env = False
        self.session.headers.update({
            "User-Agent": self.__USER_AGENTS[0],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        self.delay = delay
        self.last_request_time = 0
        self._ua_index = 0

    def _rotate_ua(self):
        """轮换 User-Agent"""
        self._ua_index = (self._ua_index + 1) % len(self.__USER_AGENTS)
        self.session.headers.update({"User-Agent": self.__USER_AGENTS[self._ua_index]})

    def _is_blocked(self, text):
        """检查是否被 Cloudflare 拦截"""
        return ('Please enable cookies' in text
                or 'Error 1015' in text
                or 'Cloudflare' in text
                or 'cf-browser-verification' in text)

    def _request(self, url, **kwargs):
        """带频率限制和重试的请求"""
        last_err = None
        for attempt in range(MAX_RETRIES):
            # 频率限制
            elapsed = time.time() - self.last_request_time
            if elapsed < self.delay:
                time.sleep(self.delay - elapsed)

            try:
                resp = self.session.get(url, timeout=30, **kwargs)
                resp.encoding = 'gbk'
                self.last_request_time = time.time()

                # 检查是否被 Cloudflare 拦截
                if self._is_blocked(resp.text[:1000]):
                    wait = (attempt + 1) * 5  # 5s, 10s, 15s...
                    print(f"  [被风控] 等待 {wait}s 后重试 ({attempt+1}/{MAX_RETRIES})")
                    self._rotate_ua()
                    time.sleep(wait)
                    continue

                return resp

            except (requests.ConnectionError, requests.Timeout) as e:
                last_err = e
                wait = (attempt + 1) * 3
                print(f"  [连接错误] 等待 {wait}s 后重试 ({attempt+1}/{MAX_RETRIES})")
                self._rotate_ua()
                time.sleep(wait)

        raise RuntimeError(f"请求失败 (重试 {MAX_RETRIES} 次后): {url}") from last_err

    def _request_post(self, url, data, **kwargs):
        """带频率限制的POST请求"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        resp = self.session.post(url, data=data, timeout=30, **kwargs)
        resp.encoding = 'gbk'
        self.last_request_time = time.time()
        return resp

    # ----------------------------------------------------------
    # 搜索
    # ----------------------------------------------------------
    def search(self, keyword):
        """
        搜索小说，利用 web 搜索查找 "wenku8 + 关键词" 来定位 book_id。
        返回匹配结果列表：
          [{ "name": str, "author": str, "aid": str, "info": str }, ...]
        """
        results = []

        # 方法1：直接调用 wenku8 搜索（已失效需登录，但有枣没枣打一杆）
        try:
            results = self._search_wenku8(keyword)
            if results:
                return results
        except Exception:
            pass

        # 方法2：使用 web 搜索（主方案）
        try:
            results = self._search_web(keyword)
            if results:
                return results
        except Exception:
            pass

        return results

    def _search_wenku8(self, keyword):
        """通过 wenku8 搜索接口"""
        keyword_gbk = keyword.encode('gbk')
        from urllib.parse import quote_from_bytes
        encoded = quote_from_bytes(keyword_gbk)
        url = f"{self.BASE}/modules/article/search.php?searchtype=articlename&searchkey={encoded}"

        resp = self._request(url, allow_redirects=True)

        # 检查是否被重定向到登录页
        if 'login.php' in resp.url.lower():
            return []

        soup = BeautifulSoup(resp.text, 'lxml')
        results = []
        for tr in soup.find_all('tr'):
            links = tr.find_all('a')
            for link in links:
                href = link.get('href', '')
                m = re.search(r'/book/(\d+)\.htm', href)
                if m:
                    results.append({
                        'name': link.get_text(strip=True),
                        'aid': m.group(1),
                        'author': '',
                        'info': ''
                    })
                    break

        return results

    def _search_web(self, keyword):
        """
        通过 Bing 搜索 "wenku8 <keyword>"，
        从结果中提取 wenku8 链接 -> book_id -> 回查书名。
        """
        seen_aids = set()
        candidates = []

        # 搜索关键词
        for query in [f'wenku8 {keyword}', f'{keyword} 轻小说 文库']:
            try:
                from urllib.parse import quote
                url = f"https://www.bing.com/search?q={quote(query)}"
                resp = self._request(url)

                # 匹配所有 wenku8 链接中的 book_id
                for m in re.finditer(
                    r'(?:https?://)?www\.wenku8\.net/(?:book/(\d+)|novel/\d+/(\d+))\.htm',
                    resp.text
                ):
                    aid = m.group(1) or m.group(2)
                    if aid and aid not in seen_aids:
                        seen_aids.add(aid)
                        candidates.append(aid)
            except Exception:
                continue

        candidates = list(dict.fromkeys(candidates))[:15]

        # 回查每个候选的书名和作者
        results = []
        for aid in candidates:
            try:
                info = self.get_book_info(aid)
                results.append({
                    'name': info['title'],
                    'author': info['author'],
                    'aid': info['book_id'],
                    'info': ''
                })
            except Exception:
                results.append({
                    'name': f'未知(book_id={aid})',
                    'author': '',
                    'aid': aid,
                    'info': ''
                })

        return results

    # ----------------------------------------------------------
    # 获取书籍信息
    # ----------------------------------------------------------
    def get_book_info(self, book_id):
        """
        从 book 页面获取：
          - title: 书名
          - author: 作者
          - cat_id: 分类编号（用于 TOC URL）
        """
        url = f"{self.BASE}/book/{book_id}.htm"
        resp = self._request(url)

        soup = BeautifulSoup(resp.text, 'lxml')

        # 书名：通常在 <span style="font-size:16px; font-weight: bold;"> 中
        title_tag = soup.find('span', style=re.compile(r'font-size:\s*16px'))
        title = title_tag.get_text(strip=True) if title_tag else f"book_{book_id}"
        # 清理书名：移除 "[投一票!]" 等后缀
        title = re.sub(r'\s*\[[^\]]*\]\s*', '', title).strip()

        # 作者：在表格中，格式 "作者：XXX" 或 "作者:XXX" (GBK编码)
        author = ""
        for td in soup.find_all('td'):
            text = td.get_text(strip=True)
            # 匹配 "作者:白石定规" 或类似格式（包含 作者 二字）
            if '\u4f5c\u8005' in text:  # 作者
                m = re.search(r'[：:]\s*(.+)', text)
                if m:
                    author = m.group(1).strip()
                break
            # 也支持 GBK 编码的文本匹配
            if '\u4f5c\u8005' in text.encode('gbk', errors='ignore').decode('gbk', errors='ignore'):
                m = re.search(r'[：:]\s*(.+)', text.encode('gbk', errors='ignore').decode('gbk', errors='ignore'))
                if m:
                    author = m.group(1).strip()
                break

        # 从 TOC 链接获取 cat_id
        cat_id = None
        for a in soup.find_all('a', href=True):
            href = a['href']
            m = re.search(r'/novel/(\d+)/' + str(book_id) + '/index\.htm', href)
            if m:
                cat_id = m.group(1)
                break

        # 如果没找到，从图片 URL 推断
        if not cat_id:
            for img in soup.find_all('img', src=True):
                src = img['src']
                m = re.search(r'/image/(\d+)/' + str(book_id), src)
                if m:
                    cat_id = m.group(1)
                    break

        return {
            'title': title,
            'author': author,
            'book_id': str(book_id),
            'cat_id': str(cat_id) if cat_id else None
        }

    # ----------------------------------------------------------
    # 获取目录（所有卷和章节）
    # ----------------------------------------------------------
    def get_toc(self, book_id, cat_id):
        """
        解析目录页，返回：
          [
            {
              "volume": "第一卷",
              "chapters": [
                { "title": "第一话 xxx", "url": "https://..." },
                ...
              ]
            },
            ...
          ]
        """
        url = f"{self.BASE}/novel/{cat_id}/{book_id}/index.htm"
        resp = self._request(url)

        soup = BeautifulSoup(resp.text, 'lxml')

        volumes = []
        current_volume = None

        for tr in soup.find_all('tr'):
            # 卷标题行：<td class="vcss" colspan="4" vid="...">第一卷</td>
            vcss = tr.find('td', class_='vcss')
            if vcss:
                vol_name = vcss.get_text(strip=True)
                current_volume = {
                    'volume': vol_name,
                    'chapters': []
                }
                volumes.append(current_volume)
                continue

            # 章节行：包含 <td class="ccss"><a href="82491.htm">第一话</a></td>
            if current_volume is not None:
                for td in tr.find_all('td', class_='ccss'):
                    a = td.find('a')
                    if a and a.get('href'):
                        href = a['href']
                        # href 可能是相对路径（如 "82491.htm"）
                        if not href.startswith('http'):
                            full_url = f"{self.BASE}/novel/{cat_id}/{book_id}/{href}"
                        else:
                            full_url = href
                        title = a.get_text(strip=True)
                        if title:  # 跳过空标题
                            current_volume['chapters'].append({
                                'title': title,
                                'url': full_url
                            })

        return volumes

    # ----------------------------------------------------------
    # 获取章节正文
    # ----------------------------------------------------------
    def get_chapter_text(self, url):
        """
        抓取章节页，提取正文文本。
        返回清洗后的纯文本。
        """
        resp = self._request(url)
        soup = BeautifulSoup(resp.text, 'lxml')

        # 正文在 <div id="content"> 中
        content_div = soup.find('div', id='content')
        if content_div:
            text = content_div.get_text('\n', strip=True)
        else:
            # 备选：直接从 body 提取
            body = soup.find('body')
            text = body.get_text('\n', strip=True) if body else ""

        # 清洗：移除 "手机阅读" 等干扰文本
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            # 跳过广告和导航行
            if not line:
                continue
            if any(skip in line for skip in [
                'www.wenku8.com', 'wenku8.com', '轻小说文库',
                '手机阅读', '小说目录', '上一页', '下一页',
                '推荐本篇', '字体大小', '加入收藏', '推荐本书',
                'Ai女友', '勇士之塔',
            ]):
                continue
            lines.append(line)

        return '\n'.join(lines)

    # ----------------------------------------------------------
    # 下载整本书
    # ----------------------------------------------------------
    def download_book(self, book_id_or_url, output_dir=OUTPUT_DIR):
        """
        下载整本书，按卷保存为 txt 文件。
        返回下载了哪些卷的信息。
        """
        # 解析 book_id
        if str(book_id_or_url).startswith('http'):
            m = re.search(r'/book/(\d+)\.htm', book_id_or_url)
            if m:
                book_id = m.group(1)
            else:
                print("错误：无法从 URL 中提取 book_id")
                return
        else:
            book_id = str(book_id_or_url)

        print(f"正在获取书籍信息 (book_id={book_id})...")
        info = self.get_book_info(book_id)
        if not info.get('cat_id'):
            print("错误：无法获取分类编号，下载中止")
            return

        print(f"  书名: {info['title']}")
        print(f"  作者: {info['author']}")
        print(f"  分类: {info['cat_id']}")

        # 创建输出目录
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', info['title'])
        book_dir = os.path.join(output_dir, safe_title)
        os.makedirs(book_dir, exist_ok=True)

        # 获取目录
        print("正在获取目录...")
        volumes = self.get_toc(info['book_id'], info['cat_id'])
        print(f"  共 {len(volumes)} 卷")

        total_chapters = sum(len(v['chapters']) for v in volumes)
        print(f"  共 {total_chapters} 章节")

        # 下载每一卷
        downloaded = []
        chapter_count = 0
        for vol in volumes:
            vol_name = vol['volume']
            chapters = vol['chapters']
            if not chapters:
                continue

            # 卷文件名
            safe_vol = re.sub(r'[\\/:*?"<>|]', '_', vol_name) if vol_name else f"vol_{volumes.index(vol)+1}"
            vol_filename = f"{safe_vol}.txt"
            vol_path = os.path.join(book_dir, vol_filename)

            print(f"\n下载卷: {vol_name} ({len(chapters)} 章)")
            vol_lines = []

            for ch in chapters:
                chapter_count += 1
                print(f"  [{chapter_count}/{total_chapters}] {ch['title']}...", end=' ', flush=True)
                try:
                    text = self.get_chapter_text(ch['url'])
                    # 添加章节标题
                    vol_lines.append(f"{ch['title']}\n{'-'*40}")
                    vol_lines.append(text)
                    vol_lines.append('\n\n')
                    print("OK")
                except Exception as e:
                    print(f"失败: {e}")

            # 写入文件
            if vol_lines:
                with open(vol_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(vol_lines))
                downloaded.append({
                    'volume': vol_name,
                    'file': vol_path,
                    'chapters': len(chapters)
                })
                print(f"  -> 已保存: {vol_path}")

        # 总结
        print(f"\n{'='*50}")
        print(f"下载完成!")
        print(f"  书名: {info['title']}")
        print(f"  作者: {info['author']}")
        print(f"  保存路径: {book_dir}")
        print(f"  共 {len(downloaded)} 卷, {chapter_count} 章节")
        for d in downloaded:
            print(f"    {d['volume']}: {d['file']} ({d['chapters']} 章)")

        return downloaded


# ============================================================
# CLI 入口
# ============================================================
def print_results(results, page=1):
    """打印搜索结果的表格"""
    if not results:
        print("没有找到结果。")
        return

    print(f"\n{'='*60}")
    print(f"找到 {len(results)} 个结果:")
    print(f"{'='*60}")
    for i, r in enumerate(results, 1):
        print(f"  [{i}] {r['name']}")
        print(f"      ID: {r['aid']}")
        if r.get('author'):
            print(f"      作者: {r['author']}")
        if r.get('info'):
            print(f"      {r['info']}")
        print()


def interactive_mode():
    """交互模式"""
    client = Wenku8Client()

    print("=" * 50)
    print("  轻小说文库 (wenku8.net) 下载器")
    print("=" * 50)
    print()
    print("该脚本通过逐章抓取的方式下载小说全文(Python实现)")
    print()
    print("【搜索说明】")
    print("  站内搜索已关闭，脚本会通过 Bing 搜索来查找小说ID。")
    print("  部分冷门小说可能搜不到，此时选择 [2] 直接输入 book_id 即可。")
    print("  book_id 获取方式: 打开小说页面，URL中的数字就是")
    print("    例如 https://www.wenku8.net/book/2255.htm → book_id = 2255")
    print()

    while True:
        print("\n请选择操作:")
        print("  [1] 搜索小说")
        print("  [2] 输入 book_id 直接下载")
        print("  [3] 输入 book URL 直接下载")
        print("  [q] 退出")
        choice = input("> ").strip()

        if choice in ('q', 'Q'):
            break

        elif choice == '1':
            keyword = input("请输入搜索关键词 (书名): ").strip()
            if not keyword:
                continue
            print(f"\n正在搜索 \"{keyword}\"...")
            results = client.search(keyword)
            print_results(results)

            if results:
                print("请输入要下载的序号 [1-{}], 或 0 跳过: ".format(len(results)), end='')
                try:
                    idx = int(input().strip())
                    if 1 <= idx <= len(results):
                        aid = results[idx - 1]['aid']
                        client.download_book(aid)
                except ValueError:
                    pass

        elif choice == '2':
            book_id = input("请输入 book_id (例如 2255): ").strip()
            if book_id:
                client.download_book(book_id)

        elif choice == '3':
            url = input("请输入完整的 book URL (例如 https://www.wenku8.net/book/2255.htm): ").strip()
            if url:
                client.download_book(url)

    print("再见!")


def main():
    if len(sys.argv) < 2:
        interactive_mode()
        return

    command = sys.argv[1].lower()

    if command == 'search':
        if len(sys.argv) < 3:
            print("用法: python wenku8_downloader.py search <关键词>")
            return
        keyword = ' '.join(sys.argv[2:])
        client = Wenku8Client()
        print(f"正在搜索 \"{keyword}\"...")
        results = client.search(keyword)
        print_results(results)
        if results:
            print("要下载请使用: python wenku8_downloader.py download <book_id>")
        else:
            print()
            print("搜索不到？可以试试：")
            print("  1. 在浏览器打开 https://www.wenku8.net，站内搜索找到小说")
            print("  2. 从地址栏复制 book_id（URL中的数字）")
            print("  3. 用 python wenku8_downloader.py download <book_id> 下载")

    elif command == 'download':
        if len(sys.argv) < 3:
            print("用法: python wenku8_downloader.py download <book_id 或 URL>")
            return
        target = sys.argv[2]
        client = Wenku8Client()
        client.download_book(target)

    else:
        print(f"未知命令: {command}")
        print("可用命令: search, download")
        print("无参数则进入交互模式")


if __name__ == '__main__':
    main()
