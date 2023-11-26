from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.service import Service
import requests

import time, datetime
import pandas as pd
import numpy as np
import math, re, sys
import warnings

warnings.filterwarnings("ignore")

# Import functions to create column: skills (required skills)
from Spacy_text_analayzer import (
    Spacy_create_nlp,
    get_skills,
    unique_skills,
    update_LinkedinJobs_DF,
)


##########################################################################
#     I-Scraping Linkedin Jobs IDs using selenium and BeautifulSoup
##########################################################################
def get_user_credentials():
    """Get email@ and password for Linkedin"""
    with open("../data/user_credentials.txt", "r", encoding="utf-8") as file:
        user_credentials = file.readlines()
        user_credentials = [line.rstrip() for line in user_credentials]

    email_address, password = user_credentials[0], user_credentials[1]
    print(email_address, password)
    return email_address, password


def scroll_to_bottom(driver, sleep_time=120):
    """scrolling down to the bottom of the page to load all jobs
    Inputs:
        - sleep_time (seconds): provide extra time for the webpage to load (default= 120 seconds).
                            If the 25 jobs are not loaded within this timer,
                            we can adjust the time and test again.
    """
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    time.sleep(sleep_time)


def find_Job_Ids(soup):
    """Parse the HTML content of the page (using BeautifulSoup) and find Job Ids"""
    Job_Ids_on_the_page = []

    job_postings = soup.find_all("li", {"class": "jobs-search-results__list-item"})
    for job_posting in job_postings:
        Job_ID = job_posting.get("data-occludable-job-id")
        Job_Ids_on_the_page.append(Job_ID)
        # job_title = job_posting.find('a', class_='job-card-list__title').get_text().strip()
        # location = job_posting.find('li', class_='job-card-container__metadata-item').get_text().strip()

    return Job_Ids_on_the_page


description


def scraping_Job_Ids(
    keywords,
    location,
    email_address,
    password,
    chromedriver_path="../chromedriver/chromedriver.exe",
    sleep_time=120,
):
    """Scrape linkedin Job Ids using selenium and BeautifulSoup
    Inputs:
    - keywords (str): the Job title
    - location (str)
    - email_address and password: user credentials
    - chromedriver_path (str): path of the chromedriver
    - sleep_time (seconds): provide extra time for the webpage to load (default= 120 seconds).
                            If the 25 jobs are not loaded within this timer,
                            we can adjust the time and test again.
    """

    # 1. Instanciate the chrome service
    service = Service(executable_path=chromedriver_path)

    # 2. Instanciate the webdriver
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options, service=service)

    # 3. Open the LinkedIn login page
    driver.get("https://www.linkedin.com/login")
    time.sleep(5)  # waiting for the page to load

    # 4. Enter our email@ & pwd
    email_input = driver.find_element(By.ID, "username")
    password_input = driver.find_element(By.ID, "password")
    email_input.send_keys(email_address)
    password_input.send_keys(password)

    # 5. Click the login button
    password_input.send_keys(Keys.ENTER)

    time.sleep(10)

    # 6. Scraping Linkedin Jobs IDs
    ##############################################################################
    # Set the search query parameters: Job title and location.
    # Search results are displayed on many pages: `25` jobs are listed on each page.
    # We will navigate to every page using the `start` parameter (0,25,50...)
    # We need to scroll to the bottom of the page to load the full data.
    # To get Job Ids, we will parse the HTML content of the page using BeautifulSoup.

    List_Job_IDs = []

    # 6.1 Navigate to the first page (start=0) and scroll to the bottom of the page
    url = f"https://www.linkedin.com/jobs/search/?keywords={keywords}&location={location}&start=0"
    url = requests.utils.requote_uri(url)
    driver.get(url)
    scroll_to_bottom(driver, sleep_time)

    # 6.2 Get number of results (jobs) and number pages (each page will contains 25 jobs)

    # Parse the HTML content of the page using BeautifulSoup.
    soup = BeautifulSoup(driver.page_source, "html.parser")

    try:
        div_number_of_jobs = soup.find(
            "div", {"class": "jobs-search-results-list__subtitle"}
        )
        number_of_jobs = int(
            div_number_of_jobs.find("span").get_text().strip().split()[0]
        )
    except:
        number_of_jobs = 0

    number_of_pages = math.ceil(number_of_jobs / 25)
    print("number_of_jobs:", number_of_jobs)
    print("number_of_pages:", number_of_pages)

    # 6.3. Get Job Ids present on the first page.
    Jobs_on_this_page = find_Job_Ids(soup)
    List_Job_IDs.extend(Jobs_on_this_page)

    # Now that we've scraped the job IDs and number of results from the first page,
    # let's iterate over the remaining pages (i.e. 2..number_of_pages).

    # 7. Iterate over the remaining pages
    if number_of_pages > 1:
        for page_num in range(1, number_of_pages):
            print(f"Scraping page: {page_num}", end="...")

            # Navigate to the first page (start=0)
            url = f"https://www.linkedin.com/jobs/search/?keywords={keywords}&location={location}&start={25 * page_num}"
            url = requests.utils.requote_uri(url)

            driver.get(url)
            scroll_to_bottom(driver, sleep_time)

            # Parse the HTML content of the page using BeautifulSoup.
            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Get Job Ids present on the first page.
            Jobs_on_this_page = find_Job_Ids(soup)
            List_Job_IDs.extend(Jobs_on_this_page)
            print(f"Jobs found:{len(Jobs_on_this_page)}")

    # 8. Save results (ie. Job IDs) to csv file
    pd.DataFrame({"Job_Id": List_Job_IDs}).to_csv("../data/Job_Ids.csv", index=False)

    ## 9. Close the browser and shut down the ChromiumDriver executable that
    # is started when starting the ChromiumDriver.
    driver.quit()


##########################################################################
#     II- Scraping Job description using requests and BeautifulSoup
##########################################################################
import requests
from bs4 import BeautifulSoup


def remove_tags(html):
    """remove html tags from BeautifulSoup.text"""

    # parse html content
    soup = BeautifulSoup(html, "html.parser")

    for data in soup(["style", "script"]):
        # Remove tags
        data.decompose()

    # return data by retrieving the tag content
    return " ".join(soup.stripped_strings)


def scrape_Job_details():
    """Scraping Job details using requests and BeautifulSoup
    return pandas DataFrame containing Linkedin Job details
    """
    list_job_IDs = pd.read_csv("../data/Job_Ids.csv").Job_Id.to_list()

    job_url = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"

    job = {}
    list_jobs = []
    for j in range(0, len(list_job_IDs)):
        print(f"{j+1} ... read jobId:{list_job_IDs[j]}")

        resp = requests.get(job_url.format(list_job_IDs[j]))
        soup = BeautifulSoup(resp.text, "html.parser")
        # print(soup.prettify())

        job["Job_ID"] = list_job_IDs[j]
        # try:
        #     job["Job_html"] = resp.content
        # except:
        #     job["Job_html"]=None

        try:  # remove tags
            job["Job_txt"] = remove_tags(resp.content)
        except:
            job["Job_txt"] = None

        try:
            job["company"] = (
                soup.find("div", {"class": "top-card-layout__card"})
                .find("a")
                .find("img")
                .get("alt")
            )
        except:
            job["company"] = None

        try:
            job["job-title"] = (
                soup.find("div", {"class": "top-card-layout__entity-info"})
                .find("a")
                .text.strip()
            )
        except:
            job["job-title"] = None

        try:
            job["level"] = (
                soup.find("ul", {"class": "description__job-criteria-list"})
                .find("li")
                .text.replace("Seniority level", "")
                .strip()
            )
        except:
            job["level"] = None

        try:
            job["location"] = soup.find(
                "span", {"class": "topcard__flavor topcard__flavor--bullet"}
            ).text.strip()
        except:
            job["location"] = None

        try:
            job["posted-time-ago"] = soup.find(
                "span", {"class": "posted-time-ago__text topcard__flavor--metadata"}
            ).text.strip()
        except:
            job["posted-time-ago"] = None

        try:
            nb_candidats = soup.find(
                "span",
                {
                    "class": "num-applicants__caption topcard__flavor--metadata topcard__flavor--bullet"
                },
            ).text.strip()
            nb_candidats = int(nb_candidats.split()[0])
            job["nb_candidats"] = nb_candidats
        except:
            job["nb_candidats"] = None

        list_jobs.append(job)
        job = {}

    # create a pandas Datadrame
    jobs_DF = pd.DataFrame(list_jobs)

    return jobs_DF


##########################################################################
#           III- Preprocess data
##########################################################################
# Now that we've scraped all the Linkedin job details, let's process the data:
# 1. Create a posted_date column using posted_time_ago
# 2. Clean up columns: level and Job_txt
# 3. Create column 'skill'


def clean_Job_description(text):
    senetences_to_remove = [
        "Remove photo First name Last name Email Password (8+ characters) ",
        "By clicking Agree & Join",
        "you agree to the LinkedIn User Agreement",
        "Privacy Policy and Cookie Policy",
        "Continue Agree & Join or Apply on company website",
        "Security verification",
        "Close Already on LinkedIn ?",
        "Close Already on LinkedIn?",
        "Sign in Save Save job Save this job with your existing LinkedIn profile , or create a new one",
        "Sign in Save Save job Save this job with your existing LinkedIn profile, or create a new one",
        "Your job seeking activity is only visible to you",
        "Email Continue Welcome back",
    ]
    for sentence in senetences_to_remove:
        result = text.find(sentence)
        if result > -1:
            text = (
                text[:result] + text[result + len(sentence) :]
            )  # remove sentence from text

    return text


def get_posted_date(posted_time_ago, date_scraping):
    posted_date = None

    try:
        details = posted_time_ago.split()
        N_DAYS_AGO = int(details[0])
        day_week_month_year = details[1]
        if day_week_month_year.startswith("day"):
            N_DAYS_AGO = N_DAYS_AGO
        elif day_week_month_year.startswith("week"):
            N_DAYS_AGO = N_DAYS_AGO * 7
        elif day_week_month_year.startswith("month"):
            N_DAYS_AGO = N_DAYS_AGO * 30
        elif day_week_month_year.startswith("year"):
            N_DAYS_AGO = N_DAYS_AGO * 365
        else:
            N_DAYS_AGO = None

        posted_date = date_scraping - datetime.timedelta(days=N_DAYS_AGO)
    except:
        posted_date = None

    return posted_date


def Preprocess_data(jobs_DF):
    """
    Preprocess_data:
        # 1. Create a posted_date column using posted_time_ago
        # 2. Clean up columns: level and job_txt
        # 3. Create column: skills
    Inputs:
        - jobs_DF (pandas DF): the pandas DF containg the scraped Linkedin Jobs.
    Output:
        - jobs_DF (pandas DF): updated DF.

    """
    # 1. Add column scraping_date and posted_date
    jobs_DF["scraping_date"] = pd.to_datetime(datetime.date.today())
    jobs_DF["posted_date"] = np.vectorize(get_posted_date)(
        jobs_DF["posted-time-ago"], jobs_DF["scraping_date"]
    )
    # 2. Clean up columns: Level and Job_txt
    jobs_DF["Job_txt"] = jobs_DF["Job_txt"].apply(clean_Job_description)
    jobs_DF.level = jobs_DF.level.apply(
        lambda x: x.replace("Employment type\n        \n\n          ", "")
        if x is not None
        else x
    )

    # 3. Add/update column SKILLS
    # Load Spacy model containing the skill entity ruler.
    nlp_Spacy = Spacy_create_nlp()
    print(nlp_Spacy.pipe_names)

    jobs_DF["skills"] = (
        jobs_DF["Job_txt"].str.lower().apply(lambda x: get_skills(nlp_Spacy, x))
    )
    jobs_DF["skills"] = jobs_DF["skills"].apply(unique_skills)

    return jobs_DF


#################################################################
########        Main function
#################################################################


def scraping_main(
    keywords,
    location,
    chrome_driver_path="../chromedriver/chromedriver.exe",
    sleep_time=120,
):
    """
    Scraping Linkedin Jobs using selenium, requests and BeautifulSoup.
    Inputs
        - keywords (str): the Job title
        - location (str)
        - chromedriver_path (str): path of the chromedriver
        - sleep_time (seconds): provide extra time for the webpage to load (default= 120 seconds).
                                If the 25 jobs are not loaded within this timer,
                                we can adjust the time and test again.
    """

    # 1. update keywords, location (encode specieal caracters like comma)
    print("1. update keywords, location (encode specieal caracters like comma)...\n\n")
    keywords = keywords.replace(",", "%2C")
    location = location.replace(",", "%2C")

    # 2. Get user credentials (to sign in to Linkedin)
    print("2. Get user credentials...\n\n")
    email_address, password = get_user_credentials()

    # 3. Scraping Job_Ids with selenium and BeautifulSoup
    print("2. Scraping Job_Ids with selenium and BeautifulSoup ...\n\n")
    scraping_Job_Ids(
        keywords,
        location,
        email_address,
        password,
        chromedriver_path=chrome_driver_path,
        sleep_time=sleep_time,
    )

    # 4. Scraping Job description using Requests and BeautifulSoup
    print("Scraping Job description using requests and BeautifulSoup...\n\n")
    jobs_DF = scrape_Job_details()

    # 5. Preprocess data
    print("Preprocess data...\n\n")
    jobs_DF = pd.read_json(
        "../data/linkedin_jobs_scraped.json",
        convert_dates=["posted_date", "scraping_date"],
    )
    jobs_DF = Preprocess_data(jobs_DF)

    # 6. Save jobs_DF to json file
    print("Save jobs_DF to json file\n\n")
    jobs_DF.to_json("../data/linkedin_jobs_scraped.json")

    print("Scraping Linkedin Jobs: done.\n")


def main():
    if len(sys.argv) == 4:
        keywords, location, sleep_time_ = sys.argv[1:]
        scraping_main(keywords, location, sleep_time=sleep_time_)
    else:
        print(
            "Please provide the Keywords and location."
            "\nExample:\n"
            'python scraping_linkedin.py "data scientist" "Montreal, Quebec, Canada" 120'
        )


if __name__ == "__main__":
    main()
