import json
from time import sleep
from urllib.parse import quote
from requests import post, Session, get
from bs4 import BeautifulSoup

files = {"data": "data.json", "config": "config.json"}
urls = {
    "login": "https://iut.uisbax.com/login",
    "announcements": "https://iut.uisbax.com/announcement/student",
    "root": "https://iut.uisbax.com",
}
parser = "html.parser"


try:
    with open(files["data"], "x") as f:
        print("Ah, first run I see. Creating data file...")
        f.write('{"sent": []}')
        print("Done.")
except FileExistsError:
    pass

old_sent = json.load(open(files["data"]))
config = json.load(open(files["config"]))

if (
    config["username"] == ""
    or config["password"] == ""
    or config["token"] == ""
    or config["chat"] == ""
    or type(config["vrijeme"]) is not int
):
    print("Idi u config.json i popuni sve podatke.")
    exit()

print(
    f"""

    ______  ________   ____        __ 
   /  _/ / / /_  __/  / __ )____  / /_
   / // / / / / /    / __  / __ \/ __/
 _/ // /_/ / / /    / /_/ / /_/ / /_  
/___/\____/ /_/    /_____/\____/\__/  
                                      

Timer je trenutno na {config["vrijeme"]} minuta.
"""
)
x = 1
while True:
    with Session() as session:
        login_page = session.get(urls["login"])
        response = post(
            "https://iut.uisbax.com/login",
            cookies=session.cookies,
            data={
                "_token": BeautifulSoup(login_page.text, parser).find(
                    "input", {"name": "_token"}
                )["value"],
                "login": config["username"],
                "password": config["password"],
                "lang": "0",
            },
        )
        if (
            "Došlo je do greške." in response.text
            or "Polje šifra ne moze sadržavati manje od 6 simbola." in response.text
        ):
            print("Sifra i ime ne valjaju. Resetujem config...")
            json.dump(
                {"username": "", "password": "", "token": "", "chat": ""},
                open(files["config"], "w"),
                indent=3,
            )
            exit()
        session.cookies = response.cookies
        announcements_table = BeautifulSoup(response.text, parser).find(
            "table", {"class": "table table-striped table-bordered dt-responsive"}
        )

        announcements = [
            {
                "title": row.find(
                    "td", {"class": "td-announcements announcement-title"}
                ).text,
                "author": row.find_all("td", {"class": "td-announcements"})[1].text,
                "date": row.find_all("td", {"class": "td-announcements"})[2].text,
                "link": row.find(
                    "td", {"class": "text-center actionButtonsTable"}
                ).find("a")["href"],
            }
            for row in announcements_table.find_all("tr")
            if row.parent.name == "tbody"
        ]

        try:
            new_sent = [
                announcement
                for announcement in announcements
                if announcement["link"] not in [x["link"] for x in old_sent["sent"]]
            ]
        except KeyError:
            new_sent = announcements

        for announcement in new_sent:
            page = session.get(
                urls["root"] + announcement["link"], cookies=session.cookies
            )
            announcement["content"] = [
                x.text for x in BeautifulSoup(page.text, parser).find_all("p")
            ][3]
            announcement["attachments"] = [
                x["href"] for x in BeautifulSoup(page.text, parser).find_all("a")
            ]
        if new_sent:
            print(f"[{x}] New announcements: {len(new_sent)}")

        for announcement in new_sent[::-1]:
            message = f"<strong>{announcement['title']}</strong>\n<em>Objavio/la {announcement['author']} na {announcement['date']}</em>\n\n{announcement['content']}\n\n"
            if len(announcement["attachments"]) > 0:
                message += "Fajlovi:\n" + quote("\n".join(announcement["attachments"]))
            resp = get(
                f'https://api.telegram.org/bot{config["token"]}/sendMessage?chat_id={config["chat"]}&parse_mode=HTML&text={message}'
            )
            if resp.status_code != 200:
                print("You messed up the token/channel id. Nice try.")
                exit()

            sleep(0.5)

        old_sent["sent"] = announcements

        with open(files["data"], "w") as f:
            json.dump(old_sent, f, indent=3)

    if config["extra_output"]:
        print(
            f"[{x}] Gledam ponovo za {config['vrijeme']} minuta."
        )
        x += 1
    sleep(60 * config["vrijeme"])
