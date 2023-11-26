import json
import plotly
import pandas as pd
import numpy as np
import colorlover as cl
from plotly.graph_objs import Bar, Pie, Histogram, Heatmap, Scatter

from wordcloud_parameters import worldcloud_generator, wordcloud_params

import warnings

warnings.filterwarnings("ignore")


def return_plots_resume_analyzer(
    list_required_skills, list_your_skills, nb_skills_to_show=50
):
    """Return Plotly graph config (resume_analyzer page)."""

    # 1. Your skills
    your_skills_pd = pd.Series(list_your_skills).value_counts()
    your_skills_pd = pd.DataFrame(your_skills_pd).rename(
        columns={"count": "your_skills"}
    )

    # 2. required skills (Linkedin Jobs)
    skills_occurence_pd = (
        pd.Series(list_required_skills).value_counts()
        / pd.Series(list_required_skills).count()
        * 100
    )
    skills_occurence_pd = skills_occurence_pd.sort_values(ascending=False)
    skills_occurence_pd = pd.DataFrame(skills_occurence_pd).rename(
        columns={"count": "required_skills"}
    )

    # 3. concat Your skills and required skills
    skills_matching_df = pd.concat([skills_occurence_pd, your_skills_pd], axis=1)
    skills_matching_df = skills_matching_df.fillna(0)
    skills_matching_df.your_skills = skills_matching_df.your_skills.astype("int")
    skills_matching_df = skills_matching_df[:nb_skills_to_show]

    # 4. Create visuals
    colors = ["rgb(33,113,181)"] * nb_skills_to_show  # if you have the skill
    for i in range(50):
        if skills_matching_df[:nb_skills_to_show].your_skills[i] == 0:
            colors[i] = "rgb(239,59,44)"  # if you dont have this skill

    graphs_analyzer = [
        # Graph 1 - Distribution of Categories
        {
            "data": [
                Bar(
                    x=skills_matching_df[:nb_skills_to_show].index,
                    y=skills_matching_df[:nb_skills_to_show].required_skills,
                    marker_color=colors,
                )
            ],
            "layout": {
                "title": {
                    "text": f"Top {nb_skills_to_show} skills in demand versus your skills",
                    # "text": "",
                    "font": {"size": 24},
                },
                # "title": f"Top {nb_skills_to_show} skills in demand versus your skills",
                "yaxis": {"title": "%"},
                "xaxis": {"title": ""},
            },
        }
    ]
    return graphs_analyzer


def return_plots_dashboard(df):
    """Return Plotly graph config (Dashboard page)."""

    try:
        # 1. Job Level and days since job posting
        level_counts = (
            df.groupby("level").count()["Job_ID"].sort_values(ascending=False)
        )
        level_counts = level_counts / level_counts.sum()
        level_counts = level_counts[:5]
        level_names = list(level_counts.index)
        days_ago = (df["scraping_date"] - df["posted_date"]) / np.timedelta64(1, "D")

        # 2. WordCloud (Most common skills)
        list_skills = []
        for skills in df.skills.values:
            for skill in skills:
                list_skills.append(skill)

        wc = worldcloud_generator(
            pd.Series(list_skills), background_color="white", max_words=200
        )
        # 2.1 Get wordcloud parametres (positions, word frequency, colors...)
        (
            position_x_list,
            position_y_list,
            freq_list,
            size_list,
            color_list,
            word_list,
        ) = wordcloud_params(wc)

        #####################################################
        #                   Dashboard figures
        #####################################################

        # Color palette (using colorlover):
        blue = cl.flipper()["seq"]["9"]["Blues"]
        red = cl.flipper()["seq"]["9"]["Reds"]
        orange = cl.flipper()["seq"]["9"]["BuPu"]
        colors = [blue[7], red[4], blue[3], red[5], orange[4]]

        # 3. Create visuals
        graphs_dahboard = [
            # Graph 1 - Pie chart - Distribution of Level
            {
                "data": [
                    Pie(
                        labels=level_names,
                        values=level_counts,
                        # textinfo='label+percent',
                        hole=0.5,
                        marker={"colors": colors},
                        sort=False,
                    )
                ],
                "layout": {
                    "title": {"text": "Level distribution", "font": {"size": 24}},
                    "showlegend": True,
                    "hoverlabel": dict(
                        bgcolor="#444", font_size=13, font_family="Lato, sans-serif"
                    ),
                    "legend": {
                        "orientation": "h",
                        "xanchor": "center",
                        "x": 0.5,
                        "y": -0.15,
                    },
                },
            },
            # Graph 2 - Distribution of days_ago
            {
                "data": [Histogram(x=days_ago)],
                "layout": {
                    # "title": "Days since job posting",
                    "title": {
                        "text": "Days since job posting",
                        "font": {"size": 24},
                    },
                    "yaxis": {"title": "Count"},
                    "xaxis": {"title": "Days"},
                },
            },
            # Graph 3 - Wordcloud (skills)
            {
                "data": [
                    Scatter(
                        x=position_x_list,
                        y=position_y_list,
                        textfont=dict(size=size_list, color=color_list),
                        hoverinfo="text",
                        # hovertext=['{0}{1}'.format(w, f) for w, f in zip(word_list, freq_list)],
                        mode="text",
                        text=word_list,
                    )
                ],
                "layout": {
                    "title": {"text": "Skills in demand", "font": {"size": 24}},
                    "xaxis": {
                        "showgrid": False,
                        "showticklabels": False,
                        "zeroline": False,
                    },
                    "yaxis": {
                        "showgrid": False,
                        "showticklabels": False,
                        "zeroline": False,
                    },
                    "height": 700,
                },
            },
        ]
    except:
        graphs_dahboard = []

    return graphs_dahboard
