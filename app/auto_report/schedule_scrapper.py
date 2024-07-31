import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import re
from html2text import html2text
import os, sys

class ScheduleScraper:
    def __init__(self, driver_path=None, headless=True):
        chrome_options = webdriver.ChromeOptions()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        if driver_path:
            self.driver = webdriver.Chrome(driver_path, options=chrome_options)
        else:
            self.driver = webdriver.Chrome(options=chrome_options)
        
        self.wait = WebDriverWait(self.driver, 15)
    
    def __open_schedule_page(self, url, login_id, login_pw):
        self.driver.maximize_window()
        time.sleep(1)
        self.driver.get(url)
        self.driver.implicitly_wait(3)
        
        self.driver.find_element(By.XPATH, '//*[@id="id"]').send_keys(login_id)
        self.driver.find_element(By.XPATH, '//*[@id="pw"]').send_keys(login_pw)
        self.driver.find_element(By.XPATH, '//*[@id="btnLOGIN"]').click()
        
        menu1 = self.wait.until(EC.presence_of_element_located((By.ID, 'sp_N201311051514584831108PJT202101281746')))
        menu1.click()

        menu2 = self.wait.until(EC.presence_of_element_located((By.ID, 'mzv_N201408221617329034428PJT202101281746')))
        menu2.click()
        self.driver.find_element(By.XPATH, '//*[@id="mzv_N201311051701286401661PJT202101281746"]').click()
        
        time.sleep(5)
        self.driver.switch_to.frame(self.driver.find_element(By.ID, 'ifr_content'))

    def __check_tasks(self, chks):
        all_chk = self.driver.find_element(By.ID, 'calendarIds0')
        if all_chk.is_selected():
            self.driver.find_element(By.XPATH, '//*[@id="calendarIds0"]/following-sibling::label').click()
        
        time.sleep(1)

        for i in range(1, 8):
            chk = self.driver.find_element(By.ID, f'calendarIds{i}')
            lbl = self.driver.find_element(By.XPATH, f'//*[@id="calendarIds{i}"]/following-sibling::label')
            if i in chks and not chk.is_selected():
                lbl.click()
            elif i not in chks and chk.is_selected():
                lbl.click()

        time.sleep(2)
    
    def __gather_tasks(self, today, persons):
        trs = self.driver.find_elements(By.XPATH, '//*[@id="listSchedules"]/tbody/tr')
        tasks = []
        dayoffs = []

        for tr in trs:
            clsname = tr.get_attribute('class')
            if clsname.startswith('schedule-date'):
                if tr.get_attribute('data-date') == today:
                    try:
                        if clsname == 'schedule-date':
                            obj = tr.find_element(By.XPATH, './/td[4]/div')
                        else:
                            obj = tr.find_element(By.XPATH, './/td[2]/div')
                        
                        content = obj.get_attribute('title')
                        head = obj.text

                        class_text = obj.get_attribute('class')

                        if head.startswith('[개인일정]'):
                            person = next((p for p in persons if p in head), '')
                            if person:
                                content = head.replace('[개인일정] ', '')
                                dayoffs.append({'person': person, 'content': content})
                        
                        elif head.startswith('[작업]'):
                            if 'imageView.do?' in content:
                                continue
                            if not 'SMCLD202102041501558810' in class_text:
                                continue
                            text = html2text(content)
                            contents = [p.strip().replace('\n\\', '\n') for p in re.split('\n내용 :\n\n', text) if p.strip()]
                            if len(contents) != 2:
                                continue
                            content_ = contents[1]
                            if content_[:1] == '\\':
                                content_ = content_[1:]
                            raw_contents = [p.strip() for p in re.split('<br/>내용 : <p>', content) if p.strip()]
                            if len(raw_contents) == 2:
                                tasks.append({'type': 'mw', 'content': content_, 'raw_content': raw_contents[1]})
                            else:
                                tasks.append({'type': 'mw', 'content': content_, 'raw_content': raw_contents[0]})
                    except selenium.common.exceptions.NoSuchElementException:
                        continue

        return tasks, dayoffs

    def get_tasks(self, url: str, login_id: str, login_pw: str, chks: list, persons: list, now: datetime):
        self.__open_schedule_page(url, login_id, login_pw)
        self.__check_tasks(chks)
        today = now.strftime("%Y%m%d")
        tasks, dayoffs = self.__gather_tasks(today, persons)
        self.driver.quit()
        return tasks, dayoffs

if __name__ == "__main__":
    url = 'http://10.1.10.101:8080/openpms/'
    login_id = 'tiffanie.kim'
    login_pw = '1q2w3e4r5t!!'
    chks = [2, 5]
    persons = ['김형기', '최용타', '강인모', '허재영']
    now = datetime.now()

    scraper = ScheduleScraper()
    tasks, dayoffs = scraper.get_tasks(url, login_id, login_pw, chks, persons, now)
    print('Tasks:', tasks)
    print('Dayoffs:', dayoffs)
