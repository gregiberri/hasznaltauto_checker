import os
import platform
import re
import time
import warnings
import datetime
import pandas as pd
from selenium.webdriver import ActionChains, Keys
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

warnings.filterwarnings('ignore')

HASZNALTAUTO_PAGE = 'https://www.hasznaltauto.hu/'

print(platform.system())
if platform.system() == 'Linux':
    browser_executable_path = 'firefox/linux/geckodriver'
elif platform.system() == 'Mac':
    browser_executable_path = 'firefox/mac/geckodriver'
else:
    raise SystemError('Unknown operating system.')


while True:
    cars_to_check = pd.read_csv('cars_to_check.csv')

    options = Options()
    options.headless = True
    driver = webdriver.Firefox(options=options, executable_path=browser_executable_path, log_path=None)

    for _, (BRAND, MODELL) in cars_to_check.iterrows():
        print(f'\ndownload {BRAND} {MODELL}')

        driver.get(HASZNALTAUTO_PAGE)
        time.sleep(2)

        marka = driver.find_element_by_xpath('//*[@id="szemelyauto"]/div/form/div[1]/div/div[1]/div/div')
        marka.click()
        ActionChains(driver).send_keys(BRAND).perform()
        ActionChains(driver).send_keys(Keys.RETURN).perform()

        modell = driver.find_element_by_xpath('//*[@id="szemelyauto"]/div/form/div[1]/div/div[2]/div/div')
        modell.click()
        ActionChains(driver).send_keys(MODELL).perform()
        ActionChains(driver).send_keys(Keys.RETURN).perform()

        # kereses = driver.find_element_by_xpath('//*[@id="szemelyauto"]/div/form/div[2]/div[2]/button[1]')
        # kereses.click()
        ActionChains(driver).send_keys(Keys.RETURN).perform()
        time.sleep(2)

        all_element_info = []
        page = 1
        todays_date = datetime.datetime.today().strftime('%Y-%m-%d')
        while True:
            print(f'\tloading page: {page}')
            # get the elements on the page
            elements = driver.find_elements_by_xpath('//*[contains(@class, "row talalati-sor")]')

            # strip the info
            element_info = []
            for element in elements:
                text = element.text.split('\n')
                ar, hirdetes = [''], ['']
                info = [''] * 5

                for text_element in text[1:]:
                    if ' Ft' in text_element:
                        try:
                            ar = [int(''.join(re.findall(r'\d+', text_element)))]
                        except ValueError:
                            ar = 0

                    elif 'kw' in text_element.lower() and 'le' in text_element.lower() \
                            and len(text_element.split(', ')) > 3:
                        infos = text_element.split(', ')

                        sorted_infos = ['', 0, 0, 0, 0, 0]
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

                element_info.append(hirdetes + ar + sorted_infos + [text[0]] + [todays_date]*2)

            all_element_info.extend(element_info)

            # next_page
            try:
                next_page = driver.find_element_by_xpath('//*[@class="next"]')
                next_page.click()
                page += 1
                time.sleep(2)
            except:
                break

        print(f'element number: {len(all_element_info)}')

        df = pd.DataFrame(all_element_info, columns=['id', 'price', 'type', 'year', 'cm3', 'kw', 'le', 'km',
                                                     'title', 'first_seen', 'last_seen'])
        df = df.set_index(['id'])

        current_folder_name = os.path.join('hasznaltauto_tables', f'{BRAND}_{MODELL}')
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

    current_date_and_time = datetime.datetime.now()
    secs_added = datetime.timedelta(seconds=24*60*60)
    future_date_and_time = current_date_and_time + secs_added

    print(f'\nSleep time until: {future_date_and_time}')
    time.sleep(24*60*60)
