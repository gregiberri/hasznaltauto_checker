import os
import time
import re
import warnings
import datetime
import pandas as pd
import schedule
import selenium
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

warnings.filterwarnings('ignore')

HASZNALTAUTO_PAGE = 'https://www.hasznaltauto.hu/'
info_elements = ('cm³', 'kw', 'le')

# Selenium script
options = Options()
options.add_argument("disable-infobars")
options.add_argument('--headless')
options.add_argument("--disable-extensions")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--no-sandbox")
options.add_argument("--disable-setuid-sandbox")
options.add_argument("--remote-debugging-port=9222")  # this


def download_hasznaltauto_to_csv():
    driver = webdriver.Chrome('/usr/bin/chromedriver', options=options)
    cars_to_check = pd.read_csv('cars_to_check.csv')

    for _, (BRAND, MODELL) in cars_to_check.iterrows():
        print(f'\ndownload {BRAND} {MODELL}')

        driver.get(HASZNALTAUTO_PAGE)

        # click agree on pop-up
        try:
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[id=didomi-notice-agree-button]"))).click()
        except TimeoutException:
            print('No pop-up loaded')

        # write brand name
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[id=mui-2]")))
        inputElement = driver.find_element(By.ID, "mui-2")
        inputElement.send_keys(BRAND)
        inputElement.send_keys(Keys.RETURN)

        # write model name
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[id=mui-4]")))
        inputElement = driver.find_element(By.ID, "mui-4")
        inputElement.send_keys(MODELL)
        inputElement.send_keys(Keys.RETURN)

        # press search
        search_panel_element = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, 'szemelyauto')))
        search_panel_element.find_element(By.CLASS_NAME, 'MuiButton-root').click()

        all_element_info = []
        todays_date = datetime.datetime.today().strftime('%Y-%m-%d')
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, 'bodyContainer')))
        try:
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "pagination")))
            page_number = int(driver.find_element(By.CLASS_NAME, "pagination").text.split()[-1])
        except selenium.common.exceptions.TimeoutException:
            print('No pages found. Downloading only from this page.')
            page_number = 1
        for page in tqdm(range(page_number)):
            # get the elements on the page
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[id=talalati]")))
            elements = driver.find_elements(By.CLASS_NAME, "row.talalati-sor")

            # strip the info
            element_info = []
            for element in elements:
                text = element.text.split('\n')
                ar, hirdetes = [''], ['']
                info = [''] * 5
                sorted_infos = ['', 0, 0, 0, 0, 0]

                try:
                    for text_element in text[1:]:
                        if ' Ft' in text_element:
                            try:
                                ar = [int(''.join(re.findall(r'\d+', text_element)))]
                            except ValueError:
                                ar = 0

                        elif sum([info_element in text_element.lower() for info_element in info_elements]) >= 2 and len(text_element.split(', ')) > 3:
                            infos = text_element.split(', ')

                            sorted_infos[0] = infos[0]
                            for info in infos[1:]:
                                if info.lower().endswith(' cm³'):
                                    sorted_infos[2] = int(info[:-3].replace(' ', ''))
                                elif info.lower().endswith(' kw'):
                                    sorted_infos[3] = int(info[:-3])
                                elif info.lower().endswith(' le'):
                                    sorted_infos[4] = int(info[:-3])
                                elif info.lower().endswith(' km'):
                                    sorted_infos[5] = int(info[:-3].replace(' ', ''))
                                else:
                                    try:
                                        sorted_infos[1] = int(infos[1].split('/')[0])
                                    except ValueError as e:
                                        print(e)
                        elif 'Hirdetés' in text_element:
                            hirdetes = [int(text_element[-9:-1])]

                    element_info.append(hirdetes + ar + sorted_infos + [text[0]] + [todays_date] * 2)

                except Exception as e:
                    print(f'\nSomething went wrong with an ad. \nError: {e}')

            all_element_info.extend(element_info)

            # next_page
            try:
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CLASS_NAME, "next"))).click()
            except TimeoutException:
                break

        print(f'element number: {len(all_element_info)}')

        df = pd.DataFrame(all_element_info, columns=['id', 'price', 'type', 'year', 'cm3', 'kw', 'le', 'km',
                                                     'title', 'first_seen', 'last_seen'])
        df = df.set_index(['id'])

        current_folder_name = os.path.join('/hasznaltauto_tables', f'{BRAND}_{MODELL}')
        if not os.path.exists(current_folder_name):
            os.makedirs(current_folder_name)
        todays_csv_file_name = os.path.join(current_folder_name, f'{BRAND}_{MODELL}_{todays_date}.csv')
        df.loc[:, ['price', 'type', 'year', 'cm3', 'kw', 'le', 'km', 'title']].to_csv(todays_csv_file_name)

        csv_file_name = os.path.join(current_folder_name, f'{BRAND}_{MODELL}.csv')
        if os.path.exists(csv_file_name):
            old_df = pd.read_csv(csv_file_name, index_col='id')
            intersection = old_df.index.intersection(df.index)
            df = df[~df.index.duplicated()]  # delete duplicates
            old_df.loc[intersection, 'last_seen'] = df.loc[intersection]['last_seen']
            df = df.drop(intersection)
            print(f'new elements: {len(df)}')
            df = old_df.append(df)

        df.to_csv(csv_file_name)

    driver.close()


schedule.every().day.at("01:00").do(download_hasznaltauto_to_csv)

while True:
    schedule.run_pending()
    time.sleep(60)  # wait one minute
