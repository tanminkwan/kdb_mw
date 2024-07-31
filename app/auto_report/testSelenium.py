import selenium
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import re
from html2text import html2text
import os, sys

def check_tasks(driver, chks):

    #uncheck 전체일정
    all_chk = driver.find_element_by_id('calendarIds0')
    if all_chk.is_selected():
        driver.find_element_by_xpath('//*[@id="calendarIds0"]/following-sibling::label').click()

    time.sleep(1)

    for i in range(1,8):
        chk = driver.find_element_by_id('calendarIds'+str(i))
        lbl = driver.find_element_by_xpath('//*[@id="calendarIds'+str(i)+'"]/following-sibling::label')
        if i in chks and not chk.is_selected():
            lbl.click()
        elif i not in chks and chk.is_selected():
            lbl.click()

    time.sleep(2)

def gather_tasks(driver, today, persons):

    trs = driver.find_elements_by_xpath('//*[@id="listSchedules"]/tbody/tr')

    tasks = []
    dayoffs = []

    for tr in trs:
        
        clsname = tr.get_attribute('class')
        if clsname.startswith('schedule-date'):
            
            if tr.get_attribute('data-date') == today:
                #print(tr.get_attribute('data-date'))

                try:
                    if clsname == 'schedule-date':
                        obj = tr.find_element_by_xpath('.//td[4]/div')
                    else:    
                        obj = tr.find_element_by_xpath('.//td[2]/div')
                    #print(re.sub('<[^<]+?>','|',content))
                    content = obj.get_attribute('title')
                    head    = obj.text

                    class_text = obj.get_attribute('class')
                    print('HHGG class_text : ', class_text)


                    if head.startswith('[개인일정]'):
        
                        person = next(( p for p in persons if p in head),'')
                        
                        if person:
                            content = head.replace('[개인일정] ','')
                            dayoffs.append({'person':person, 'content':content})
                        
                    elif head.startswith('[작업]'):

                        print('HHG :',content)
                        if 'imageView.do?' in content:
                            continue

                        # 미들웨어 작업 식별자
                        if not 'SMCLD202102041501558810' in class_text:
                            continue
                        text = html2text(content)
                        #contents = [ p.strip() for p in re.split('제목 : |일시 :|내용 :', text) if p.strip()]
                        #jobs.append({'type':'task', 'title':contents[0], 'date':contents[1], 'content':contents[2]})
                        contents = [ p.strip().replace('\n\\','\n') for p in re.split('\n내용 :\n\n', text) if p.strip()]
                        
                        if len(contents) != 2:
                            continue

                        content_ = contents[1]
                        if content_[:1] == '\\':
                            content_ = content_[1:]

                        raw_contents = [ p.strip() for p in re.split('<br/>내용 : <p>', content) if p.strip()]
                        
                        if len(raw_contents) == 2:
                            tasks.append({'type':'mw', 'content':content_, 'raw_content':raw_contents[1]})
                        else:
                            tasks.append({'type':'mw', 'content':content_, 'raw_content':raw_contents[0]})

                        
                except selenium.common.exceptions.NoSuchElementException as e:
                    continue

    return tasks, dayoffs

#chmo = webdriver.ChromeOptions()
#chmo.add_experimental_option('useAutomationExtension', False)
#driver = webdriver.Chrome(options=chmo)
#f_tab_h = driver.current_window_handle

#driver.find_element_by_tag_name('body').send_keys(Keys.CONTROL + 't')

def open_schedule_page(driver, url, login_id, login_pw):

    driver.maximize_window()

    time.sleep(1)

    driver.get(url)
    driver.implicitly_wait(3)

    driver.find_element_by_xpath('//*[@id="id"]').send_keys(login_id)
    driver.find_element_by_xpath('//*[@id="pw"]').send_keys(login_pw)
    driver.find_element_by_xpath('//*[@id="btnLOGIN"]').click()

    menu1 = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.ID, 'sp_N201311051514584831108PJT202101281746'))
    )
    menu1.click()

    menu2 = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.ID, 'mzv_N201408221617329034428PJT202101281746'))
    )
    menu2.click()
    driver.find_element_by_xpath('//*[@id="mzv_N201311051701286401661PJT202101281746"]').click()

    time.sleep(5)
    driver.switch_to.frame(driver.find_element_by_id('ifr_content'))

    return 1

#action = ActionChains(driver)
#action.key_down(Keys.CONTROL).click(new_tab_link).key_up(Keys.CONTROL).perform()
#time.sleep(5)
#print('1 1:',driver.window_handles)
#print('1 2:',driver.current_window_handle)

#driver.execute_script('''window.open("","_blank");''')
#print('2 1:',driver.window_handles)
#print('2 2:',driver.current_window_handle)
#driver.quit()

def getTasks(url, login_id, login_pw, chks, persons, now):

    if getattr(sys, 'frozen', False):
        driver = webdriver.Chrome(os.path.join(sys._MEIPASS, "chromedriver.exe"))
    else:
        driver = webdriver.Chrome()

    open_schedule_page(driver, url, login_id, login_pw)
    check_tasks(driver, chks)
    today = now.strftime("%Y%m%d")
    tasks, dayoffs = gather_tasks(driver, today, persons)
    print('HHG :',tasks, dayoffs)
    driver.quit()
    
    return tasks, dayoffs

if __name__ == "__main__":

    url = 'http://10.1.10.101:8080/openpms/'
    login_id = 'tiffanie.kim'
    login_pw = '1q2w3e4r5t!!'

    #driver = open_schedule_page(url, login_id, login_pw)

    chks = [2, 5]
    #check_tasks(driver, chks)

    #today = datetime.now().strftime("%Y%m%d")
    #today = '20211001'
    persons = ['김형기','최용타','강인모','허재영']

    #tasks = gather_tasks(driver, today, persons)
    tasks, dayoffs = getTasks(url, login_id, login_pw, chks, persons)
    print(tasks, dayoffs)

