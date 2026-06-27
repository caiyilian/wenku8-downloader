# wenku8-downloader

轻小说文库 (wenku8.net) 小说下载器。无需登录，通过逐章抓取的方式下载小说全文，按卷保存为 TXT 文件。

## 功能

- ✅ **按 book_id 下载全部卷** — 给定 wenku8 书籍 ID，自动下载所有章节
- ✅ **按 URL 下载** — 直接粘贴小说页面完整链接
- ✅ **按书名搜索** — 通过 Bing 搜索尝试查找小说 ID
- ✅ **按卷分文件** — 每卷保存为一个独立的 TXT 文件
- ✅ **防风控** — 自动轮换 User-Agent，指数退避重试，请求间隔可配置
- ✅ **交互模式** — 无参数运行进入交互菜单

## 安装

### 依赖

- Python 3.7+
- `requests`
- `beautifulsoup4`
- `lxml`

```bash
pip install requests beautifulsoup4 lxml
```

### 下载

```bash
git clone https://github.com/caiyilian/wenku8-downloader.git
cd wenku8-downloader
```

## 用法

### 交互模式

```bash
python wenku8_downloader.py
```

交互菜单提供搜索、按 ID 下载、按 URL 下载三个选项。

### 命令行模式

```bash
# 按 book_id 下载
python wenku8_downloader.py download 2255

# 按完整 URL 下载
python wenku8_downloader.py download https://www.wenku8.net/book/2255.htm

# 搜索小说（不一定 100% 能找到）
python wenku8_downloader.py search 魔女之旅
```

## book_id 获取方式

wenku8 的小说页面 URL 中的数字即为 book_id：

```
https://www.wenku8.net/book/2255.htm  →  book_id = 2255
```

示例 ID：

| 书名 | book_id | 卷数 |
|------|---------|------|
| 魔女之旅 | 2255 | 26 |
| 狼与香辛料 | 5 | 27 |
| 欢迎来到实力至上主义的教室 | 1973 | 35 |

## 搜索说明

wenku8 的站内搜索需要登录，脚本使用以下方式寻找小说：

1. **Bing 搜索** — 搜索 `wenku8 <关键词>` 从结果中提取 book_id
2. **站内搜索** — 尝试直接调用（已失效，备选）

热门小说通常能搜到。如果搜索失败，请直接使用 book_id 下载。

## 配置

可在脚本顶部修改以下常量：

```python
REQUEST_DELAY = 3.0    # 每次请求间隔（秒）
MAX_RETRIES = 5        # 风控重试次数
OUTPUT_DIR = "downloads"  # 下载输出目录
```

## 注意事项

- 脚本通过逐章抓取公开页面工作，**无需登录**
- 为减轻服务器负担，默认请求间隔 3 秒
- 如触发 Cloudflare 风控，脚本会自动重试
- 请支持正版小说

## 项目结构

```
wenku8-downloader/
├── wenku8_downloader.py   # 主程序
├── downloads/             # 下载目录（自动创建）
└── README.md
```

## License

MIT
