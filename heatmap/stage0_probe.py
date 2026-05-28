"""
stage0_probe.py — 阶段 0 自测

目的:
    1. 验证 TqKq 模拟账户能否登录
    2. 验证 SHFE.ag2608 的 5 档行情权限
    3. 验证账户基本信息读取

跑法:
    设环境变量后运行:
        export TQ_USER='你的快期账号'    # Windows PowerShell: $env:TQ_USER='...'
        export TQ_PASS='你的快期密码'
        python stage0_probe.py

预期(成功):
    - 30 秒内持续打印 5 档盘口
    - 最大档位深度 == 5
    - 账户余额、可用、风险度正常显示

ag 的活跃时段:
    日盘 09:00-10:15 / 10:30-11:30 / 13:30-15:00
    夜盘 21:00-次日 02:30  ← 推荐这段测,盘口动得最快
"""
import math
import os
import time

from tqsdk import TqApi, TqAuth, TqKq


SYMBOL = "SHFE.ag2608"
TQ_USER = os.environ.get("TQ_USER", "")
TQ_PASS = os.environ.get("TQ_PASS", "")
RUN_SECONDS = 30


def safe(v):
    """tqsdk 缺档位时为 nan/极大值,统一成 nan"""
    try:
        f = float(v)
        return float("nan") if math.isinf(f) or abs(f) > 1e17 else f
    except Exception:
        return float("nan")


def main():
    assert TQ_USER and TQ_PASS, "请先设环境变量 TQ_USER / TQ_PASS"

    print("连接 TqKq ...")
    api = TqApi(TqKq(), auth=TqAuth(TQ_USER, TQ_PASS))
    quote = api.get_quote(SYMBOL)
    account = api.get_account()
    print(f"已连接。订阅 {SYMBOL},等待行情({RUN_SECONDS} 秒)...\n")

    deadline = time.time() + RUN_SECONDS
    last_print = 0.0
    max_levels = 0

    try:
        while time.time() < deadline:
            api.wait_update()
            if not quote.datetime:
                continue
            if not api.is_changing(
                quote,
                ["bid_price1", "ask_price1", "bid_volume1", "ask_volume1"],
            ):
                continue

            now = time.time()
            if now - last_print < 1.0:
                continue
            last_print = now

            bids = [
                (
                    safe(getattr(quote, f"bid_price{i}")),
                    int(getattr(quote, f"bid_volume{i}") or 0),
                )
                for i in range(1, 6)
            ]
            asks = [
                (
                    safe(getattr(quote, f"ask_price{i}")),
                    int(getattr(quote, f"ask_volume{i}") or 0),
                )
                for i in range(1, 6)
            ]

            valid_b = sum(1 for p, v in bids if not math.isnan(p) and v > 0)
            valid_a = sum(1 for p, v in asks if not math.isnan(p) and v > 0)
            max_levels = max(max_levels, min(valid_b, valid_a))

            print(
                f"[{quote.datetime}]  最新 {quote.last_price}  "
                f"累计成交 {quote.volume}  price_tick={quote.price_tick}"
            )
            print(f"  卖5→卖1: {asks[::-1]}")
            print(f"  买1→买5: {bids}")
            print(f"  本帧有效档位: 买{valid_b}  卖{valid_a}")
            print(
                f"  账户  余额={account.balance:.2f}  "
                f"可用={account.available:.2f}  风险度={account.risk_ratio:.4f}\n"
            )

        print("=" * 50)
        print(f"测试完成。最大见到的档位深度:{max_levels}")
        if max_levels >= 5:
            print("✅ 有 5 档权限,后续按 5 档设计")
        elif max_levels >= 2:
            print(f"⚠️  只能拿到 {max_levels} 档,程序需降级显示")
        else:
            print("❌ 只能拿到 1 档,热力图价值大打折扣——考虑换合约或确认权限")
    finally:
        api.close()


if __name__ == "__main__":
    main()
