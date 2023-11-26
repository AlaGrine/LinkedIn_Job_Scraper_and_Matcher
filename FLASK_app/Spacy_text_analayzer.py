import warnings

warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import json

# spacy
import spacy
from spacy.pipeline import EntityRuler
from spacy.lang.en import English
from spacy.tokens import Doc
from spacy.matcher import Matcher


#################################################################
########  Create nlp ruler with Spacy
#################################################################


def convect_skills_from_txt_to_Jsonl():
    """Convert skills (txt format) to patterns (jsonl format)"""

    # 1. Get list of skills from txt file
    file_txt = open("../data/Skills_in_Demand.txt", "r")
    list_skills_in_demand = []
    for x in file_txt.readlines():
        list_skills_in_demand.append(x.strip())
    file_txt.close()

    # 2. Create the skill patterns
    rule_patterns = []
    for skill in list_skills_in_demand:
        pattren = []
        for elt in skill.split(" "):
            pattren.append({"LOWER": elt})

        json_data = {"label": "SKILL", "pattern": pattren}
        # Convert the dictionary to a JSON string with double quotes
        json_string = json.dumps(json_data, ensure_ascii=True)
        rule_patterns.append(json_string)

    # 3. Save patterns to jsonl file
    file_jsonl = open("../data/Skill_patterns.jsonl", "w")
    for k in range(len(rule_patterns)):
        file_jsonl.write(rule_patterns[k] + "\n")
    file_jsonl.close()


def Spacy_create_nlp():
    """create nlp ruler with Spacy"""

    # # some skills are mapped as orgnizations (like SQL, NOSQL...) --> remove ner
    nlp = spacy.load("en_core_web_lg", disable=["ner"])
    # nlp = spacy.load("en_core_web_lg")

    print("Create Spacy ruler...\n\n")

    convect_skills_from_txt_to_Jsonl()  # create Skill_patterns.jsonl
    skill_pattern_path = "../data/Skill_patterns.jsonl"

    # Add entity ruler
    ruler = nlp.add_pipe("entity_ruler")
    ruler.from_disk(skill_pattern_path)
    # print(nlp.pipe_names, "\n\n")
    return nlp


########################################################################
######    create columns: skills, missing skills and match_score
########################################################################


def get_skills(nlp, text):
    doc = nlp(text)
    list_skills = []
    for ent in doc.ents:
        if ent.label_ == "SKILL":
            list_skills.append(ent.text.lower())  # lower
    return list_skills


def unique_skills(list_skills):
    return list(set(list_skills))


def get_match_score(job_skills, your_skills):
    """get a percentage of match skills.
    Inputs:
    - Job_skills (list): list of required skills.
    - your_skills (str): your skills (comma separated)
    """
    # convert your skills to list
    list_your_skills = your_skills.split(",")
    score = 0
    for x in job_skills:
        if x in your_skills:
            score += 1
    job_skills_len = len(job_skills)
    try:
        match_score = round(score / job_skills_len * 100, 1)
    except:
        match_score = None
    return match_score


def get_missing_skills(list_job_skills, str_your_skills, return_list=True):
    """Get job skills that are not on your skill list."""

    # convert your skills form str to List
    list_your_skills = str_your_skills.split(",")
    # convert your skills to lowercase
    list_your_skills = [str.lower(skill) for skill in list_your_skills]

    missing_skills = []

    for x in list_job_skills:
        if str.lower(x) not in list_your_skills:
            try:
                missing_skills.append(x)
            except:
                pass
    if return_list:
        return missing_skills  # return list
    else:
        return ",".join(missing_skills)  # return str


def update_LinkedinJobs_DF(df, your_skills):
    """update Jobs DF with your skills (precisely: match score and missing skills)"""
    # 1. convert list to str to avoid error in np.vectorize
    your_skills = ",".join(your_skills)

    # 2. create/update match score and missing skills columns
    df["match_score"] = np.vectorize(get_match_score)(df["skills"], your_skills)
    df["missing_skills"] = np.vectorize(get_missing_skills)(
        df["skills"], your_skills, return_list=False
    )
    df = df.sort_values(by="match_score", ascending=False)

    # 3. Saving data to json
    df.to_json("../data/linkedin_jobs_scraped.json")

    return df


#################################################################################
#   display the job and highlight the skills you do and you do not have
#################################################################################
from spacy.matcher import Matcher


def get_pattern(skill, rule_based_matching="LOWER"):
    """
    Extract pattern from skill (str)
    https://spacy.io/usage/rule-based-matching

    Example:
    skill = java --> pattern = [{'LOWER': 'java'}]
    skill = data scince --> pattern = [{'LOWER': 'data'},{'LOWER': 'science'}] # consecutive words
    """
    skill_split = skill.split()  # example: 'data science' --> ['data', 'science']
    pattern = []
    for obj in skill_split:
        pattern.append({rule_based_matching: obj})
    return pattern


def get_matchers(list_skills, missing_skills, spacy_nlp):
    # 1. Initialize the matchers with the spaCy vocabulary
    list_missing_skills = missing_skills
    matcher_OK = Matcher(spacy_nlp.vocab)  # you have this skill
    matcher_NOK = Matcher(spacy_nlp.vocab)  # you do not have this skill

    # 2. Add patterns
    for k, skill in enumerate(list_skills):
        # print(k, skill)
        pattern = get_pattern(skill)
        # print(k, pattern)

        if skill in list_missing_skills:
            matcher_NOK.add(f"rule_{k}", [pattern])  # you do not have this skill
        else:
            matcher_OK.add(f"rule_{k}", [pattern])  # you have this skill

    return matcher_OK, matcher_NOK


def get_indexes(list_matches):
    """Get word indexes in the Spacy nlp document.
    We will leverage the list_matches, which contains the list of all matches.
    For each match, the output has three elements.
    - The first element is the match ID.
    - The second and third elements are the positions of the matched tokens."""
    list_indexes = []
    for match in list_matches:
        start_index = match[1]
        end_index = match[2]
        for k in range(start_index, end_index):
            list_indexes.append(k)
    return list_indexes


def return_words_types(job_txt, list_required_skills, list_missing_skills, spacy_nlp):
    """Returns two lists:
    - list of words
    - list of the corresponding types (skill, missing skill, other words)"""

    Job_doc_nlp = spacy_nlp(job_txt)

    # create matchers
    matcher_OK, matcher_NOK = get_matchers(
        list_required_skills, list_missing_skills, spacy_nlp
    )

    # Get list of matches
    list_matches_OK = matcher_OK(Job_doc_nlp)
    list_matches_NOK = matcher_NOK(Job_doc_nlp)

    # Get index of words using matcher_OK (ie. you have the skill)
    indexes_SKILLS_OK = get_indexes(list_matches_OK)
    # Get index of words using matcher_NOK (ie. you do not have the skill)
    indexes_SKILLS_NOK = get_indexes(list_matches_NOK)

    # Get index of other words (not Skills)
    indexes_others = []

    for k, word in enumerate(Job_doc_nlp):
        if (k in indexes_SKILLS_OK) | (k in indexes_SKILLS_NOK):
            pass
        else:
            indexes_others.append(k)

    words = []
    types = []

    for k, word in enumerate(Job_doc_nlp):
        words.append(word)
        if k in indexes_SKILLS_NOK:
            types.append("SKILL-missing")
        elif k in indexes_SKILLS_OK:
            types.append("SKILL")
        else:
            types.append("other")

    return words, types
