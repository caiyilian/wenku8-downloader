$env:PYTHONIOENCODING = "utf-8"
$logFile = "E:\projects\wenku8_download\batch_progress.log"
"下载开始: $(Get-Date)" | Out-File -FilePath $logFile -Encoding UTF8

$books = @(
    @{id=2255; name="魔女之旅"},
    @{id=5; name="狼与香辛料"},
    @{id=1973; name="欢迎来到实力至上主义的教室"},
    @{id=2883; name="义妹生活"},
    @{id=3057; name="败犬女主太多了"},
    @{id=2738; name="二十世纪电气目录"}
)

foreach ($book in $books) {
    "===== 开始: $($book.name) (id=$($book.id)) =====" | Out-File -FilePath $logFile -Append -Encoding UTF8
    $result = python E:\projects\wenku8_download\wenku8_downloader.py download $($book.id) 2>&1
    $result | Out-File -FilePath $logFile -Append -Encoding UTF8
    "===== 完成: $($book.name) =====" | Out-File -FilePath $logFile -Append -Encoding UTF8
    Start-Sleep -Seconds 10
}

"全部下载完成! $(Get-Date)" | Out-File -FilePath $logFile -Append -Encoding UTF8