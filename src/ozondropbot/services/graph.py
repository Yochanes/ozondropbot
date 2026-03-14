from __future__ import annotations

from io import BytesIO
from datetime import datetime

import matplotlib.pyplot as plt
import seaborn as sns


def build_price_history_plot(title: str, history: list[dict]) -> BytesIO:
    sns.set_theme(style="whitegrid")
    timestamps = [datetime.fromisoformat(x["timestamp"]) for x in history]
    prices = [x["price"] for x in history]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(timestamps, prices, marker="o", linewidth=2)
    ax.set_title(title)
    ax.set_ylabel("Цена, ₽")
    ax.set_xlabel("Время")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()

    buf = BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf
