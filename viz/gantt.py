import altair as alt
import pandas as pd


def gantt_chart(df: pd.DataFrame):
    """
    Tworzy wykres Gantta na podstawie DataFrame z harmonogramem.
    Wymagane kolumny:
    - start
    - end
    - fault_id
    - vessel_name
    """

    # Filtrujemy tylko zaplanowane zadania
    df_plot = df[df["start"].notna()].copy()

    if df_plot.empty:
        return None

    chart = (
        alt.Chart(df_plot)
        .mark_bar()
        .encode(
            x=alt.X("start:Q", title="Godzina startu"),
            x2="end:Q",
            y=alt.Y("fault_id:N", title="Usterka", sort=None),
            color=alt.Color("vessel_name:N", title="Statek"),
            tooltip=[
                "fault_id",
                "turbine_id",
                "vessel_name",
                "start",
                "end",
                "cost_pln",
                "priority",
            ],
        )
        .properties(height=450)
    )

    return chart
