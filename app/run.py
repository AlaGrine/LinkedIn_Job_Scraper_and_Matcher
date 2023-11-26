import pandas as pd
import numpy as np
from flask import Flask
from flask import render_template, request, jsonify, flash
import plotly
import json

from plotly_figures import return_plots_dashboard, return_plots_resume_analyzer
from scraping_linkedin import scraping_main
from pdf_reader import pdf_miner
from Spacy_text_analayzer import (
    Spacy_create_nlp,
    get_skills,
    unique_skills,
    update_LinkedinJobs_DF,
    return_words_types,
    get_missing_skills,
    get_match_score,
)
import warnings

warnings.filterwarnings("ignore")

app = Flask(__name__)

# Global variables
NB_TOP_MATCHING_JOBS_TO_DISPLAY = 51  # Number of top matching jobs to display
CHROME_DRIVER_PATH = "../chromedriver/chromedriver.exe"
SLEEP_TIME = 120  # provide extra time for the webpage to load.
LINKEDIN_job_URL = "https://www.linkedin.com/jobs/search/?currentJobId="

# 1. create nlp with Spacy
nlp = Spacy_create_nlp()

df = pd.read_json(
    "../data/linkedin_jobs_scraped.json",
    convert_dates=["posted_date", "scraping_date"],
)

last_scraping_date = "None"
try:
    last_scraping_date = str(df.scraping_date.unique()[0])
    last_scraping_date = last_scraping_date[:-8]
except:
    last_scraping_date = "None"

num_jobs = len(df)  # number of scraped Linkedin Jobs

# 2. create plots with plotly
graphs_dahboard = return_plots_dashboard(df)


# 3. Scraping page
@app.route("/")
@app.route("/scraping")
def scraping_flask():
    # Encode plotly graphs in JSON
    ids = ["graph-{}".format(i) for i, _ in enumerate(graphs_dahboard)]
    graphJSON = json.dumps(graphs_dahboard, cls=plotly.utils.PlotlyJSONEncoder)

    # Render web page with plotly graphs
    return render_template(
        "scraping.html",
        ids=ids,
        graphJSON=graphJSON,
        scraping_date=last_scraping_date,
        num_jobs=num_jobs,
    )


# 4. Dashboard page
@app.route("/dashboard")
def dashboard():
    # Encode plotly graphs in JSON
    ids = ["graph-{}".format(i) for i, _ in enumerate(graphs_dahboard)]
    graphJSON = json.dumps(graphs_dahboard, cls=plotly.utils.PlotlyJSONEncoder)

    # Render web page with plotly graphs
    return render_template("dashboard.html", ids=ids, graphJSON=graphJSON)


# 5. Web page to display scraping results
@app.route("/go_scraping")
def go():
    # Save user input in query
    query_keywords = request.args.get("query_keywords", "")
    query_location = request.args.get("query_location", "")

    message = ""

    # Show error message if query_keywords or query_location is empty:
    if (query_keywords.strip() == "") | (query_location.strip() == ""):
        message = "Please enter keywords and location."
        return render_template("go_scraping.html", num_jobs=0, message=message, ids=[])

    try:
        # 5.1. Linkedin Scraping
        scraping_main(
            query_keywords,
            query_location,
            chrome_driver_path=CHROME_DRIVER_PATH,
            sleep_time=SLEEP_TIME,
        )

        # 5.2. read json file containing scraping results (Linkedin jobs)
        df = pd.read_json(
            "../data/linkedin_jobs_scraped.json",
            convert_dates=["posted_date", "scraping_date"],
        )

        num_jobs = len(df)
        graphs_dahboard = return_plots_dashboard(df)

        # 5.3 Encode plotly graphs in JSON
        ids = ["graph-{}".format(i) for i, _ in enumerate(graphs_dahboard)]
        graphJSON = json.dumps(graphs_dahboard, cls=plotly.utils.PlotlyJSONEncoder)
    except:
        pass

    # This will render the go_scraping.html file.
    return render_template(
        "go_scraping.html",
        num_jobs=num_jobs,
        ids=ids,
        graphJSON=graphJSON,
        message=message,
        scraping_date="None",
    )


# 6. Resume analyzer page
@app.route("/resume_analyzer")
def resume_analyzer_flask():
    return render_template("resume_analyzing.html", ids=[], graphJSON=[])


# 7. Web page to display "Resume analyzer" results
@app.route("/go_analyzer")
def go_analyzer_flask():
    # 7.1. Save user input in query
    query_resume_path = request.args.get("query_resume_path", "")

    # 7.2. PDF reader
    if query_resume_path == "":
        resume_txt = ""
        list_your_skills = []
        list_required_skills = []
        num_skills = -1
        ids = []
        graphJSON = []
        message = "Please select a resume file (.pdf)"

        #####################################
        # top matching jobs
        #####################################
        nb_top_matching = 0
        list_Job_ID = []
        list_Job_txt = []
        list_company = []
        list_job_title = []
        list_level = []
        list_location = []
        list_posted_time_ago = []
        list_nb_candidats = []
        # list_scraping_date = []
        list_posted_date = []
        list_skills = []
        list_match_score = []
        list_missing_skills = []
    else:
        message = ""
        resume_txt = pdf_miner(query_resume_path)

        # 7.3. Get your skills
        list_your_skills = get_skills(nlp, resume_txt)
        list_your_skills = list(set(list_your_skills))  # remove dupplications
        num_skills = len(list_your_skills)  # number of skills

        # 7.4. read json file containing scraping results (Linkedin jobs)
        df = pd.read_json(
            "../data/linkedin_jobs_scraped.json",
            convert_dates=["posted_date", "scraping_date"],
        )
        list_required_skills = []
        for skills in df.skills.values:
            for skill in skills:
                list_required_skills.append(skill)

        # 7.5. Create graphs with Plotly
        graphs_analyzer = return_plots_resume_analyzer(
            list_required_skills, list_your_skills, nb_skills_to_show=50
        )
        ids = ["graph-{}".format(i) for i, _ in enumerate(graphs_analyzer)]
        graphJSON = json.dumps(graphs_analyzer, cls=plotly.utils.PlotlyJSONEncoder)

        # 7.6. Update update_LinkedinJobs_DF with your skills
        # pricisely: add columns missing_skills and match_score
        df = update_LinkedinJobs_DF(df, your_skills=list_your_skills)

        # 7.7. Create lists containg top matching Jobs
        nb_top_matching = min(
            NB_TOP_MATCHING_JOBS_TO_DISPLAY,
            len(df.head(NB_TOP_MATCHING_JOBS_TO_DISPLAY)),
        )

        list_Job_ID = df.head(nb_top_matching)["Job_ID"].to_list()
        list_Job_txt = df.head(nb_top_matching)["Job_txt"].to_list()
        list_company = df.head(nb_top_matching)["company"].to_list()
        list_job_title = df.head(nb_top_matching)["job-title"].to_list()
        list_level = df.head(nb_top_matching)["level"].to_list()
        list_location = df.head(nb_top_matching)["location"].to_list()
        list_posted_time_ago = df.head(nb_top_matching)["posted-time-ago"].to_list()
        list_nb_candidats = df.head(nb_top_matching)["nb_candidats"].to_list()
        # list_scraping_date = df.head(nb_top_matching)["scraping_date"].to_list()
        list_posted_date = df.head(nb_top_matching)["posted_date"].to_list()
        list_skills = df.head(nb_top_matching)["skills"].to_list()
        list_match_score = df.head(nb_top_matching)["match_score"].to_list()
        list_missing_skills = df.head(nb_top_matching)["missing_skills"].to_list()

    # Render web page with plotly graphs
    return render_template(
        "go_analyzer.html",
        ids=ids,
        graphJSON=graphJSON,
        your_skills=list_your_skills,
        num_skills=num_skills,
        message=message,
        ###########################################
        # top matching jobs
        ###########################################
        nb_top_matching=nb_top_matching,
        list_Job_ID=list_Job_ID,
        list_Job_txt=list_Job_txt,
        list_company=list_company,
        list_job_title=list_job_title,
        list_level=list_level,
        list_location=list_location,
        list_posted_time_ago=list_posted_time_ago,
        list_nb_candidats=list_nb_candidats,
        # list_scraping_date=list_scraping_date,
        list_posted_date=list_posted_date,
        list_skills=list_skills,
        list_match_score=list_match_score,
        list_missing_skills=list_missing_skills,
    )


# 8. `display_job` page
@app.route("/display_Job")
def display_Job():
    # Get job_id from request.args
    job_id = request.args.get("job_id", "")

    df = pd.read_json(
        "../data/linkedin_jobs_scraped.json",
        convert_dates=["posted_date", "scraping_date"],
    )

    df = df[df.Job_ID == int(job_id)].copy()

    Job_ID = df["Job_ID"].values[0]
    Job_txt = df["Job_txt"].values[0]
    company = df["company"].values[0]
    job_title = df["job-title"].values[0]
    level = df["level"].values[0]
    location = df["location"].values[0]
    posted_time_ago = df["posted-time-ago"].values[0]
    nb_candidats = df["nb_candidats"].values[0]
    scraping_date = df["scraping_date"].values[0]
    posted_date = df["posted_date"].values[0]
    skills = df["skills"].values[0]
    match_score = df["match_score"].values[0]
    missing_skills = df["missing_skills"].values[0]  # str
    try:
        missing_skills = missing_skills.split(",")  # convert to list
    except:
        pass

    # return word_type (Skills OK, Skills NOK, other words)
    words, types = [], []
    try:
        words, types = return_words_types(
            Job_txt,
            list_required_skills=skills,
            list_missing_skills=missing_skills,
            spacy_nlp=nlp,
        )
    except:
        words, types = [], []

    # render html page.
    return render_template(
        "display_Job.html",
        Job_ID=Job_ID,
        Job_txt=Job_txt,
        company=company,
        job_title=job_title,
        level=level,
        location=location,
        posted_time_ago=posted_time_ago,
        nb_candidats=nb_candidats,
        scraping_date=scraping_date,
        posted_date=posted_date,
        skills=skills,
        match_score=match_score,
        missing_skills=missing_skills,
        words=words,
        types=types,
        nb_words=len(words),
        job_url=LINKEDIN_job_URL + job_id,
    )


# 10. `resume_vs_job` page
@app.route("/resume_vs_job")
def resume_vs_job_flask():
    return render_template("resume_vs_Job.html")


# 11. Web page to display "Resume vs Job" results
@app.route("/go_resume_vs_Job")
def go_resume_vs_Job_flask():
    # 1. Save user input in query
    query_resume_path = request.args.get("query_resume_path", "")
    query_job_descreption = request.args.get("query_job_descreption", "")

    # 2. PDF reader
    if (query_resume_path == "") | (query_job_descreption == ""):
        resume_txt = ""
        num_skills = -1
        match_score = -1
        missing_skills = ""
        list_your_skills = []
        list_required_skills = []
        message = "Please select a resume file (.pdf) and add a job descreption."
        words, types = [], []

    else:
        message = ""
        resume_txt = pdf_miner(query_resume_path)

        # 3. Get your skills
        list_your_skills = get_skills(nlp, resume_txt)
        list_your_skills = list(set(list_your_skills))  # remove dupplications
        num_skills = len(list_your_skills)  # number of skills

        # 4. Get required skills
        list_required_skills = unique_skills(get_skills(nlp, query_job_descreption))

        # Get missing_skills and match_score (use functions defined in resume_analyser.py)
        your_skills = ",".join(list_your_skills)  # list to str
        match_score = get_match_score(list_required_skills, your_skills)
        missing_skills = get_missing_skills(list_required_skills, your_skills)

        # return word_indexes (Skills OK, Skills NOK, other words)
        words, types = [], []
        try:
            words, types = return_words_types(
                query_job_descreption,
                list_required_skills=list_required_skills,
                list_missing_skills=missing_skills,
                spacy_nlp=nlp,
            )
        except:
            words, types = [], []

    # Render web page with plotly graphs
    return render_template(
        "go_resume_vs_Job.html",
        num_skills=num_skills,
        match_score=match_score,
        missing_skills=missing_skills,
        list_your_skills=list_your_skills,
        list_required_skills=list_required_skills,
        message=message,
        words=words,
        types=types,
        nb_words=len(words),
    )


def main():
    app.run(host="0.0.0.0", port=3001, debug=True)


if __name__ == "__main__":
    main()
