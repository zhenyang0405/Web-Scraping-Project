import gspread
import requests
import os
import time
import pandas as pd
import chromedriver_binary
from flask import Flask
from datetime import date, timedelta
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains


def send_message(id, message, telegram_url, token):
    payload = {"chat_id": id, "text": message, "parse_mode": "MarkdownV2"}
    response = requests.post(f"{telegram_url}{token}/sendMessage", params=payload)
    print(f"Message send: {'Success!' if response.status_code == 200 else 'Fail!!!'}")

app = Flask(__name__)

@app.route("/", methods=["POST"])
def main():

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("window-size=1024,768")
    chrome_options.add_argument("--no-sandbox")

    # Create credentials to access google spreadsheet
    gc = gspread.service_account(filename='GOOGLESHEET JSON FILE PUT HERE')
    sh = gc.open('Cameras - Daily Price Information')
    print(sh)

    # Request moment site
    url = 'https://www.shopmoment.com/cameras'

    response = requests.get(url)

    html = response.content
    soup = BeautifulSoup(html, 'html.parser')

    headers = ["Brands", "Name", "Special Message", "Current Price", "Retail Price", "No. of Reviews", "Status", "Link"]
    moment_df = pd.DataFrame(columns=headers)

    browser = webdriver.Chrome(ChromeDriverManager().install() ,options=chrome_options)
    browser.get(url)
    time.sleep(1)

    scroll = True

    while scroll == True:
        try:
            time.sleep(3)
            browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            action = ActionChains(browser)
            load_more = browser.find_element_by_xpath('//*[@id="shopGridContainer"]/div[2]/div[2]/button')
            browser.execute_script("arguments[0].scrollIntoView();", load_more)
            action.move_to_element(load_more)
            action.click()
            action.perform()
            print("Action clicked!")
        except NoSuchElementException:
            scroll = False
            print("No more button!")

    time.sleep(5)
    all_products = browser.find_elements_by_css_selector('article.product-card-display')

    print(f"Number of products: {len(all_products)}")

    home = 'https://www.shopmoment.com'

    for i in range(len(all_products)):
        all_products_html = all_products[i].get_attribute('outerHTML')
        product = BeautifulSoup(all_products_html, "html.parser")

        brands = product.find("header", {"class": "product-card-display__bottom__header"}).find("a").text.strip()
        title = product.find("header", {"class": "product-card-display__bottom__header"}).find("h2", {"class": "product-card-title__title"}).text.strip()
        reviews = product.find("footer", {"class": "product-card-display__bottom__footer"}).find("span", {"class": "product-card-rating__total-reviews"})
        current_price = product.find("footer", {"class": "product-card-display__bottom__footer"}).find("span", {"class": "product-card-pricing__price"}).text.strip().lstrip("$").rstrip("+").replace(",", "")
        retail_price = product.find("footer", {"class": "product-card-display__bottom__footer"}).find("del", {"class": "product-card-pricing__price--retail"})
        special_message = product.find("div", {"class": "product-card-display__top"}).find("figure", {"class": "product-card-notifier"})
        availability = product.find("div", {"class": "product-card-display__top"}).select(".product-card-action")[0].text.strip()
        link = product.find("div", {"class": "product-card-display__top"}).find("a").get("href")

        if reviews == None:
            reviews = "0"
        else:
            reviews = reviews.text.strip().lstrip("(").rstrip(")")

        if special_message == None:
            special_message = " "
        else:
            special_message = special_message.text.strip()

        if retail_price == None:
            retail_price = " "
        else:
            retail_price = retail_price.text.strip().lstrip("$").replace(",", "")

        if availability == "Add to cart":
            availability = "Available"

        full_link = home + link

        current_product = {"Brands": brands, "Name": title, "Special Message": special_message, "Current Price": current_price, "Retail Price": retail_price, "No. of Reviews": reviews, "Status": availability, "Link": full_link}
        moment_df = moment_df.append(current_product, ignore_index=True)

    time.sleep(5)
    browser.close()

    moment_df.sort_values(by=["Brands", "Name"], inplace=True, ignore_index=True)
    moment_df["Current Price"] = moment_df["Current Price"].astype("float64")
    moment_df["No. of Reviews"] = moment_df["No. of Reviews"].astype("int")


    ############ Compare Prices and Saving to google spreadsheet #################

    year, month, day = str(date.today()).split("-")

    today = date.today()
    yesterday = today - timedelta(days=1)
    y_year, y_month, y_day = str(yesterday).split("-")

    try:
        yesterday_worksheet = sh.worksheet(f"{y_day}{y_month}{y_year}")
        yesterday_df = pd.DataFrame(yesterday_worksheet.get_all_records())
        yesterday_df = yesterday_df.rename({"Current Price": "Yesterday Price"}, axis=1)

        merged = moment_df.merge(yesterday_df, how="left",
                                left_on=["Name", "Current Price"],
                                right_on=["Name", "Yesterday Price"])


        differences = merged["Current Price"] - merged["Yesterday Price"]
        differences.fillna("New", inplace=True)

        moment_df.insert(5, "Price Differences", differences)

        worksheet_name = day + month + year
        today_worksheet = sh.add_worksheet(title=worksheet_name, rows="100", cols="20")
        today_worksheet.update([moment_df.columns.values.tolist()] + moment_df.values.tolist())
    except gspread.exceptions.WorksheetNotFound:
        worksheet_name = day + month + year
        today_worksheet = sh.add_worksheet(title=worksheet_name, rows="100", cols="20")

        today_worksheet.update([moment_df.columns.values.tolist()] + moment_df.values.tolist())

    print("Successfully updated the extracted data to google spreadsheet!")


    ################### Telegram API #####################

    telegram_url = 'https://api.telegram.org/bot'
    token = 'TELEGRAM TOKEN PUT HERE'
    method = '/getMe'

    full_url = telegram_url + token + method
    bot = requests.get(full_url)
    print(f"Telegram bot status code: {bot.status_code}")

    test_response = requests.get(f"{telegram_url}{token}/getUpdates")

    my_id = 'YOUR TELEGRAM ID'
    cell_f1 = today_worksheet.acell("F1").value
    print(f"Cell F1: {cell_f1}")

    new_product_arr = []
    price_increase_arr = []
    price_decrease_arr = []
    if cell_f1 == "Price Differences":
        for v in today_worksheet.get_all_values()[1:]:
            price_difference = v[5]
            if price_difference == '0':
                continue
            elif price_difference == 'New':
                new_product_arr.append(v)
            elif int(price_difference) > 0:
                price_increase_arr.append(v)
            elif int(price_difference) < 0:
                price_decrease_arr.append(v)

    text = ''
    text += f"*Date: {day}/{month}/{year}*\n\n"

    if len(new_product_arr) != 0:
        text += f"_*__New Product__*_\n"
        for p in new_product_arr:
            name = p[1].replace("-", "\-").replace("+", "\+").replace(".", "\.")
            price = p[3].replace(".", "\.")
            text += f"Brands: {p[0]}\nName: {name}\nPrice: USD {price}\n"
            if p[2] != ' ':
                t = p[2].replace("!", "\!").replace(".", "\.")
                text += f"Special: {t}\n"
            link = p[8].replace(".", "\.").replace("-", "\-")
            text += f"Link: {link}\n\n"

    if len(price_decrease_arr) != 0:
        text += f"_*__Price Drop__*_\n"
        for p in price_decrease_arr:
            name = p[1].replace("-", "\-").replace("+", "\+").replace(".", "\.")
            price = p[3].replace(".", "\.")
            text += f"Brands: {p[0]}\nName: {name}\nPrice: USD {price}\n"
            if p[2] != ' ':
                t = p[2].replace("!", "\!").replace(".", "\.")
                text += f"Special: {t}\n"
            link = p[8].replace(".", "\.").replace("-", "\-")
            text += f"Link: {link}\n\n"

    if len(price_increase_arr) != 0:
        text += f"_*__Price Increase__*_\n"
        for p in price_increase_arr:
            name = p[1].replace("-", "\-").replace("+", "\+").replace(".", "\.")
            price = p[3].replace(".", "\.")
            text += f"Brands: {p[0]}\nName: {name}\nPrice: USD {price}\n"
            if p[2] != ' ':
                t = p[2].replace("!", "\!").replace(".", "\.")
                text += f"Special: {t}\n"
            link = p[8].replace(".", "\.").replace("-", "\-")
            text += f"Link: {link}\n\n"

    if len(new_product_arr) == 0 and len(price_decrease_arr) == 0 and len(price_increase_arr) == 0:
        text += "There is no changes\.\nVisit https://www\.shopmoment\.com to explore more products\.\n"

    send_message(my_id, text, telegram_url, token)
    return "Done!"

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
