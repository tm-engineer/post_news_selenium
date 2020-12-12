import argparse
import json
import os
import sys
import time
from datetime import date

import chromedriver_binary
from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, ElementClickInterceptedException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select

load_dotenv()
POST_DATA_FILE = os.environ['POST_DATA_FILE']
RETRY_TIMES = int(os.environ['RETRY_TIMES'])
RETRY_WAIT_SEC = float(os.environ['RETRY_WAIT_SEC'])


class News:
    def __init__(self, args, option_vals=[]):
        try:
            with open(POST_DATA_FILE) as f:
                self.post_data = json.load(f)
        except FileNotFoundError as e:
            sys.exit(f"{POST_DATA_FILE}が見つかりません。")

        self.year = str(args.year)
        self.month = str(args.month)
        self.day = str(args.day)
        print(f"{self.year}年{self.month}月{self.day}日で投稿予約します。")

        self.driver = self.get_driver(option_vals)
        self.wait = WebDriverWait(self.driver, int(os.environ['MAX_WAIT_SEC']))

    def get_driver(self, option_vals=[]):
        options_kwargs = {}
        if option_vals:
            chrome_options = webdriver.ChromeOptions()
            for val in option_vals:
                chrome_options.add_argument(val)
            options_kwargs['options'] = chrome_options

        return webdriver.Chrome(**options_kwargs)

    def access(self, url):
        self.driver.get(url)

    def login(self):
        id_form = self.wait.until(EC.visibility_of_element_located((By.NAME, 'id')))
        id_form.send_keys(os.environ['LOGIN_ID'])

        password_form = self.wait.until(EC.visibility_of_element_located((By.NAME, 'password')))
        password_form.send_keys(os.environ['LOGIN_PASSWORD'])
        password_form.submit()

    def select_template(self, id):
        template_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="form1"]/div/div/table/tbody/tr[1]/td/div[1]/a')))
        template_button.click()

        template_id = f"template_{id}"
        template_radio = self.wait.until(EC.element_to_be_clickable((By.ID, template_id)))
        template_radio.click()

        template_select_button = self.wait.until(EC.element_to_be_clickable((By.ID, 'load_1')))
        template_select_button.click()

    def reserve(self, year, month, day, hour, minute):
        for i in range(RETRY_TIMES):
            try:
                reserve_radio = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="reserve_state2"]')))
                reserve_radio.click()
                break
            except (StaleElementReferenceException, ElementClickInterceptedException):
                time.sleep(RETRY_WAIT_SEC)
        else:
            sys.exit('日時予約を選択できませんでした。')

        for i in range(RETRY_TIMES):
            try:
                reserve_year = self.wait.until(EC.visibility_of_element_located((By.NAME, 'reserve_year')))
                Select(reserve_year).select_by_value(year)

                reserve_month = self.wait.until(EC.visibility_of_element_located((By.NAME, 'reserve_month')))
                Select(reserve_month).select_by_value(month)

                reserve_day = self.wait.until(EC.visibility_of_element_located((By.NAME, 'reserve_day')))
                Select(reserve_day).select_by_value(day)

                reserve_hour = self.wait.until(EC.visibility_of_element_located((By.NAME, 'reserve_hour')))
                Select(reserve_hour).select_by_value(hour)

                reserve_minutes = self.wait.until(EC.visibility_of_element_located((By.NAME, 'reserve_minutes')))
                Select(reserve_minutes).select_by_value(minute)
                break

            except TimeoutException:
                time.sleep(RETRY_WAIT_SEC)
        else:
            sys.exit('投稿日時を予約できませんでした。')

    def submit(self):
        pre_submit_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="form1"]/div/div/div/p/input')))
        pre_submit_button.click()
        self.wait.until(EC.title_is('速報情報登録確認画面'))

        submit_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="form1"]/div/div/div/p/input[2]')))
        submit_button.click()
        self.wait.until(EC.title_is('速報情報登録完了画面'))

    def post(self):
        self.access(os.environ['POST_URL'])
        for data in self.post_data['post_data']:
            self.select_template(data['template_id'])
            self.reserve(self.year, self.month, self.day, data['reserve_hour'], data['reserve_minute'])
            self.submit()
            print(f"{data['template_id']}番のテンプレートを{data['reserve_hour']}時{data['reserve_minute']}分で投稿予約しました。")

    def execute(self):
        self.access(os.environ['LOGIN_URL'])
        self.login()
        self.post()
        print('登録が完了しました。')


if __name__ == '__main__':
    today = date.today()
    parser = argparse.ArgumentParser(description='オプションで投稿予約の年月日を指定できます。デフォルトは当日です。')
    parser.add_argument('-y', '--year', help='年をyyyyで指定', type=int, default=today.year)
    parser.add_argument('-m', '--month', help='月を指定', type=int, default=today.month)
    parser.add_argument('-d', '--day', help='日を指定', type=int, default=today.day)
    args = parser.parse_args()

    news = News(args, ['--headless'])
    news.execute()
