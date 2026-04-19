from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")  # non-GUI backend for server-side image generation

import matplotlib.pyplot as plt  # type: ignore
import pandas as pd  # type: ignore


RESULTS_MULTI_PATH = os.path.join("results", "metrics_multi.csv")
CHART_DIR = os.path.join("static", "charts")


def ensure_chart_dir() -> None:
    os.makedirs(CHART_DIR, exist_ok=True)


def generate_comparison_charts() -> None:
    ensure_chart_dir()
    if not os.path.exists(RESULTS_MULTI_PATH):
        raise FileNotFoundError(f"{RESULTS_MULTI_PATH} not found, run experiments.run_scenarios first")

    df = pd.read_csv(RESULTS_MULTI_PATH)

    # Derived metrics per run.
    df["avg_latency_ms"] = df["total_latency_ms"] / df["successes"].replace(0, 1)
    df["success_rate"] = df["successes"] / df["total_ops"].replace(0, 1)
    df["failure_rate"] = df["failures"] / df["total_ops"].replace(0, 1)

    # Composite reliability index in [0, 1], higher is better.
    # Intuition: reward success, penalize failures and data loss relative to total_ops.
    df["reliability_index"] = (
        0.7 * df["success_rate"]
        - 0.3 * df["failure_rate"]
        - 0.0005 * df["data_loss"]
    )

    # For reliability_index, ignore complete_drop (no realistic success possible).
    df_ri = df[df["scenario"] != "complete_drop"].copy()

    metrics_to_plot = [
        "failure_rate",
        "retries",
        "avg_latency_ms",
        "success_rate",
        "data_loss",
        "recovery_time_ms",   # <- add this
        "reliability_index",
    ]


    grouped = df.groupby(["scenario", "version"])
    grouped_ri = df_ri.groupby(["scenario", "version"])

    means = grouped[metrics_to_plot[:-1]].mean().reset_index()
    stds = grouped[metrics_to_plot[:-1]].std().reset_index()

    # reliability_index handled separately on df_ri
    ri_means = grouped_ri["reliability_index"].mean().reset_index()
    ri_stds = grouped_ri["reliability_index"].std().reset_index()

    for metric in metrics_to_plot:
        fig, ax = plt.subplots(figsize=(6, 4))

        if metric == "reliability_index":
            mean_pivot = ri_means.pivot(index="scenario", columns="version", values=metric)
            std_pivot = ri_stds.pivot(index="scenario", columns="version", values=metric)
        else:
            mean_pivot = means.pivot(index="scenario", columns="version", values=metric)
            std_pivot = stds.pivot(index="scenario", columns="version", values=metric)

        x = range(len(mean_pivot.index))
        width = 0.35
        scenarios = mean_pivot.index.tolist()

        versions = mean_pivot.columns.tolist()

        colors = {
            "baseline": "#7A8C58",          # olive
            "proposed_no_cache": "#B0A16E", # desaturated olive
            "proposed": "#D9C8A9",          # cream
        }

        offsets = {
            "baseline": -0.35,
            "proposed_no_cache": 0.0,
            "proposed": 0.35,
        }

        for v in versions:
            vals = mean_pivot[v].tolist()
            errs = std_pivot[v].tolist()
            ax.bar(
                [i + offsets[v] for i in x],
                vals,
                width / 1.2,
                yerr=errs,
                label=v.replace("_", " ").title(),
                capsize=3,
                color=colors.get(v, "#cccccc"),
                edgecolor="#555555",
            )


        ax.set_xticks(list(x))
        ax.set_xticklabels(scenarios, rotation=30, ha="right")
        ax.set_title(metric)
        ax.set_ylabel(metric)
        ax.set_facecolor("#F9F5EC")
        ax.legend()
        plt.tight_layout()

        out_path = os.path.join(CHART_DIR, f"{metric}.png")
        plt.savefig(out_path)
        plt.close(fig)
