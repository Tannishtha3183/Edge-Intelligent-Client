from __future__ import annotations

import logging
import os
from typing import Dict, Any

from flask import Flask, render_template, request, jsonify, url_for

from config import configure_logging
from core.network_simulator import default_scenario_config, NetworkSimulator
from experiments.plots import generate_comparison_charts

configure_logging()
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global simulator instance (for now; later we can manage sessions).
current_scenario_name = "stable"
simulator = NetworkSimulator(default_scenario_config(current_scenario_name))

# Simple in-memory history of scenario changes
scenario_history: list[dict[str, str]] = []


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/simulator", methods=["GET", "POST"])
def simulator_control():
    global current_scenario_name, simulator

    if request.method == "POST":
        data: Dict[str, Any] = request.json or {}
        scenario = data.get("scenario", "stable")
        current_scenario_name = scenario
        simulator = NetworkSimulator(default_scenario_config(scenario))
        logger.info("Switched scenario to %s", scenario)

        scenario_history.append(
            {
                "scenario": scenario,
                "note": "User changed scenario via dashboard",
            }
        )

        return jsonify({"status": "ok", "scenario": scenario})

    return render_template(
        "simulator.html",
        current_scenario=current_scenario_name,
    )


# in app.py
@app.route("/monitor/state")
def monitor_state():
    state = simulator.next_state()
    return jsonify(
        {
            "latency_ms": state.latency_ms,
            "packet_loss": state.packet_loss,
            "is_disconnected": state.is_disconnected,
            "bandwidth_kbps": state.bandwidth_kbps,
            "quality_score": state.quality_score,
            "scenario": current_scenario_name,
        }
    )



@app.route("/monitor")
def monitor():
    return render_template("monitor.html")


@app.route("/comparison")
def comparison():
    try:
        generate_comparison_charts()
    except FileNotFoundError:
        logger.warning("metrics_multi.csv not found, please run experiments.run_scenarios first")
        # Fallback: show page without charts
        return render_template("comparison.html", charts=[])

    metrics = [
        "failure_rate",
        "retries",
        "avg_latency_ms",
        "success_rate",
        "data_loss",
        "recovery_time_ms",
        "reliability_index",
    ]

    chart_urls = [
        url_for("static", filename=f"charts/{m}.png") for m in metrics
    ]

    descriptions = {
        "failure_rate": (
            "Lower is better. Fraction of operations that never succeed even after retries. "
            "Shows how often the app permanently loses user actions under each network condition."
        ),
        "retries": (
            "Number of extra send attempts triggered by failures. "
            "High retries mean wasted bandwidth and battery; a smarter client should succeed with fewer retries."
        ),
        "avg_latency_ms": (
            "Average latency of successful operations. "
            "Captures user-perceived responsiveness; large increases under bad networks indicate poor behavior."
        ),
        "success_rate": (
            "Higher is better. Fraction of operations that eventually succeed. "
            "This is the main headline reliability metric for each client and scenario."
        ),
        "data_loss": (
            "Number of operations lost permanently. "
            "Critical for reliability-sensitive applications such as payments or medical updates."
        ),
        "recovery_time_ms": (
            "Time taken to flush cached operations after connectivity is restored. "
            "Lower is better; shows how quickly the client becomes consistent again after an outage."
        ),
        "reliability_index": (
            "Composite score combining success rate, failure rate, and data loss into a single indicator (0–1, higher is better). "
            "Summarizes overall reliability of each client in each scenario."
        ),
    }


    charts = [
        (m, url, descriptions.get(m, ""))
        for m, url in zip(metrics, chart_urls)
    ]
    return render_template(
        "comparison.html",
        charts=charts,
    )


@app.route("/history")
def history():
    return render_template(
        "history.html",
        scenario_history=scenario_history,
    )


if __name__ == "__main__":
    app.run(debug=True)
