"""测试 HTTP API 登录与下载。"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cwdz.crawler.api_client import TingsimpleApiClient

USER, PWD = "yghtcw", "yghtcw123!"


def log(msg):
    print(msg, flush=True)


end = datetime.now()
start = end - timedelta(days=7)

with TingsimpleApiClient() as client:
    log("=== HTTP 登录 ===")
    client.login(USER, PWD)
    log("登录成功")

    log("\n=== 获取车场 ===")
    parks = client.get_all_park_ids()
    log(f"车场数量: {len(parks)}")

    log("\n=== 导出+下载 ===")
    path = client.download_reconciliation(
        start.strftime("%Y-%m-%d"),
        end.strftime("%Y-%m-%d"),
        username=USER,
        password=PWD,
        on_progress=log,
    )
    log(f"\n✓ 完成: {path}")
