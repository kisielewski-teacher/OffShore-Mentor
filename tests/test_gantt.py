import altair as alt
import pandas as pd

from viz.gantt import gantt_chart


def _sample_df():
    return pd.DataFrame(
        [
            {
                "fault_id": "F001",
                "turbine_id": "T001",
                "start": 0,
                "end": 10,
                "vessel_name": "Baltic Hawk",
                "cost_pln": 45000,
                "priority": 1,
            },
            {
                "fault_id": "F002",
                "turbine_id": "T002",
                "start": None,
                "end": None,
                "vessel_name": None,
                "cost_pln": 0,
                "priority": 2,
            },
        ]
    )


def test_gantt_chart_returns_none_when_nothing_scheduled():
    df = pd.DataFrame(
        [{"fault_id": "F001", "turbine_id": "T001", "start": None, "end": None,
          "vessel_name": None, "cost_pln": 0, "priority": 1}]
    )
    assert gantt_chart(df) is None


def test_gantt_chart_returns_none_for_empty_dataframe():
    df = pd.DataFrame(columns=["fault_id", "turbine_id", "start", "end", "vessel_name", "cost_pln", "priority"])
    assert gantt_chart(df) is None


def test_gantt_chart_builds_chart_for_scheduled_rows():
    chart = gantt_chart(_sample_df())
    assert isinstance(chart, alt.Chart)


def test_gantt_chart_filters_out_unscheduled_rows():
    chart = gantt_chart(_sample_df())
    # only the scheduled row (start is not NA) should remain in the chart data
    assert len(chart.data) == 1
    assert chart.data.iloc[0]["fault_id"] == "F001"
