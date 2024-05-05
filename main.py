import requests
from bs4 import BeautifulSoup
import os
import json
import pandas as pd


def name_process(name: str) -> list[str] | tuple[str, str, str]:
    if not name or name.strip() == "":
        return ["", "", ""]
    name = name.split(" ")
    match len(name):
        case 0:
            fn = ""
            mn = ""
            ln = ""
        case 1:
            fn = name[0]
            mn = ""
            ln = ""
        case 2:
            fn = name[0]
            mn = ""
            ln = name[1]
        case 3:
            fn = name[0]
            mn = name[1]
            ln = name[2]
        case _:
            fn = name[0]
            mn = name[1]
            ln = ""
            for i in range(2, len(name)):
                ln += name[i] + " "
            ln = ln[:-1]
    return fn, mn, ln


def get_links_from_list(list_url: str):
    output = []
    list_name = list_url.split("/")[-1]
    # load cache
    if os.path.exists(f"./cache/lists/{list_name}.txt"):
        with open(f"./cache/lists/{list_name}.txt", "r") as f:
            return json.load(f)
    # purge cache
    content = requests.get(list_url)
    soup = BeautifulSoup(content.text, "html.parser")
    company_list = soup.find("div", {"class": "pr-list"}).find_all("a", {"class": "pr-list__item"})
    for this_company in company_list:
        company_url = f"https://prowly.com{this_company["href"]}"
        company_name = this_company.find('div', {"class": "pr-list__item_name"}).text
        influence_score = this_company.find('div', {"class": "pr-list__item_influence"}).text
        influence_score = int(influence_score.strip().replace(" / 100", ""))
        output.append({"name": company_name, "url": company_url, "influence_score": influence_score})
        with open(f"./cache/lists/{list_name}.txt", "w+") as f:
            json.dump(output, f, indent=4)
    return output


def deep_lookup_journalist(journalist_url: str):
    journalist_name = journalist_url.split("/")[-1]
    # load cache
    if os.path.exists(f"./cache/journalist/{journalist_name}.json"):
        with open(f"./cache/journalist/{journalist_name}.json", "r") as f:
            return json.load(f)
    # purge cache
    print(f"Crawling {journalist_url}")
    content = requests.get(journalist_url)
    soup = BeautifulSoup(content.text, "html.parser")
    journalist_panel = soup.find("div", {"class": "pr-profile__items"})
    try:
        journalist_location = journalist_panel.find("div", {"class": "pr-profile__item_location"}).find('div', {"class": "pr-profile__location"}).text
    except AttributeError:
        journalist_location = "Unknown"
    try:
        journalist_topics = [topic.text for topic in journalist_panel.find_all("li", {"class": "pr-profile__topics-item"})]
    except AttributeError:
        journalist_topics = []
    try:
        journalist_influence_score = journalist_panel.find("div", {"class": "pr-profile__item_score"}).find('div', {"class": "pr-profile__location"}).text
        journalist_influence_score = int(journalist_influence_score.strip().replace(" / 100", ""))
    except AttributeError:
        journalist_influence_score = 0

    print(f"Getting {journalist_name} from {journalist_url}, {journalist_location}, {journalist_topics}, {journalist_influence_score}")
    this_journalist_details = {
        "location": journalist_location,
        "topics": journalist_topics,
        "influence_score": journalist_influence_score
    }
    with open(f"./cache/journalist/{journalist_name}.json", "w+") as f:
        json.dump(this_journalist_details, f, indent=4)
    return this_journalist_details


def get_journalist_from_company(company_url: str, company_influence_score: int = 0):
    output = []
    company_name = company_url.split("/")[-1]
    # load cache
    if os.path.exists(f"./cache/company/{company_name}.json"):
        with open(f"./cache/company/{company_name}.json", "r") as f:
            output = json.load(f)
    else:
        print(f"Crawling {company_url}")
        # purge cache
        content = requests.get(company_url)
        soup = BeautifulSoup(content.text, "html.parser")

        # website
        website_panel = soup.find("div", {"class": "pr-outlet__web"})
        try:
            website = website_panel.find("a", {"class": "pr-outlet__website"}).text
        except AttributeError:
            return []

        journalist_list = soup.find("div", {"class": "pr-outlet__journalists"}).find_all("div", {
            "class": "pr-outlet__journalist-info"})
        for journalist in journalist_list:
            journalist_name = journalist.find('a', {"class": "pr-outlet__journalist-name"}).text
            fist_name, middle_name, last_name = name_process(journalist_name)
            journalist_url = f"https://prowly.com{journalist.find('a', {"class": "pr-outlet__journalist-name"}).get("href")}"
            journalist_title = journalist.find('div', {"class": "pr-outlet__journalist-role"}).text
            journalist_details = deep_lookup_journalist(journalist_url)
            this_journalist_full_details = {
                "company": company_name,
                "company_url": website,
                "name": journalist_name,
                "first_name": fist_name,
                "middle_name": middle_name,
                "last_name": last_name,
                "title": journalist_title,
                "location": journalist_details["location"],
                "topics": journalist_details["topics"],
                "influence_score": journalist_details["influence_score"],
                "company_influence_score": company_influence_score,
                "url": journalist_url,
            }
            output.append(this_journalist_full_details)
        with open(f"./cache/company/{company_name}.json", "w+") as f:
            json.dump(output, f, indent=4)
    df = pd.DataFrame(output)
    df.to_excel(f'./output2/{company_name}.xlsx', index=False)
    print(f"Saved {company_name}.xlsx")
    return output


if __name__ == "__main__":
    os.makedirs("./cache/lists/", exist_ok=True)
    os.makedirs("./cache/company/", exist_ok=True)
    os.makedirs("./cache/journalist/", exist_ok=True)
    os.makedirs("./output2/", exist_ok=True)
    company_metadata = get_links_from_list(
        "https://prowly.com/profiles/outlet-lists/top-100-outlets-in-united-states")
    for company in company_metadata:
        journalists = get_journalist_from_company(company["url"], company["influence_score"])
