from datetime import datetime, timedelta
from random import randint
from time import sleep

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.action_chains import ActionChains
#from selenium.webdriver.support import expected_conditions as EC
#from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.ui import WebDriverWait

from .. import logger
from ..constants import CURRENT_PROFILE
from ..database.posts_dao import save_post
from ..utils.url_utils import get_param
from ..constants import *
from ..utils.datetime_utils import parse_datetime
from dateutil.relativedelta import relativedelta

def get_date_time_from_post(browser, post):
    try:
        #span_element = post.find_element(By.CSS_SELECTOR,"span[aria-labelledby]")        
        browser.execute_script("arguments[0].scrollIntoView(false); window.scrollBy(0, -300);", post)
        status_link = WebDriverWait(post, 10).until(ec.presence_of_element_located((By.CSS_SELECTOR, "div[class='xu06os2 x1ok221b']>span>div>span>span>span>a[class][role='link'][tabindex='0'], div[class='xu06os2 x1ok221b']>span>span>span>span>a[class][role='link'][tabindex='0'], div[class='xu06os2 x1ok221b']>span>div>span>span>a[class][role='link'][tabindex='0'], div[class='xu06os2 x1ok221b']>span>div>span>span>span>a[class][role='link'][tabindex='0']")))
        #status_link = WebDriverWait(post, 10).until(ec.presence_of_element_located((By.CSS_SELECTOR, "span>a[attributionsrc][role='link'][tabindex='0']>span>span>span")))
        actions = ActionChains(browser)
        actions.move_to_element(status_link).perform()            
        span_element = WebDriverWait(browser, 10).until(ec.presence_of_element_located((By.CSS_SELECTOR, 
        "div.__fb-dark-mode > div[style]:not([hidden]) > div > div > span[class='x193iq5w xeuugli x13faqbe x1vvkbs x1xmvt09 x1nxh6w3 x1sibtaa xo1l8bm xzsf02u'], \
        div.__fb-dark-mode > div > div[style]:not([hidden]) > div > div > span[class='x193iq5w xeuugli x13faqbe x1vvkbs x1xmvt09 x1nxh6w3 x1sibtaa xo1l8bm xzsf02u'], \
        div.__fb-dark-mode > div > div[style]:not([hidden]) > div > div > span[class='x6zurak x18bv5gf x193iq5w xeuugli x13faqbe x1vvkbs xt0psk2 xzsf02u xlh3980 xvmahel x1x9mg3 xo1l8bm'], \
        div.__fb-dark-mode > div[style]:not([hidden]) > div > div > span[class], \
        div.__fb-dark-mode > div[style]:not([hidden]) > div > div > div >span[class], \
        div.__fb-light-mode > div[style]:not([hidden]) > div > div > span[class='x193iq5w xeuugli x13faqbe x1vvkbs x1xmvt09 x1nxh6w3 x1sibtaa xo1l8bm xzsf02u'],\
        div.__fb-light-mode > div[style]:not([hidden]) > div > div > span[class],\
        div.__fb-light-mode > div[style]:not([hidden]) > div > div > div > span[class]")))
        post_date_time = browser.execute_script("return arguments[0].textContent;", span_element) 
        logger.log("Found time_stamp: {}".format(post_date_time))
        if post_date_time:            
            return parse_datetime(post_date_time)
    except:
        logger.log("\033[91mDate time doesn't found\033[0m")
    return None
"""def get_date_time_from_post(browser, post):
    try:
        span_element = post.find_element(By.CSS_SELECTOR,"span[aria-labelledby][class='x1rg5ohu x6ikm8r x10wlt62 x16dsc37 xt0b8zv']")
        aria_labelledby_value = span_element.get_attribute("aria-labelledby")
        
        # Use the value of aria-labelledby to find the corresponding element
        # Escape the ID value for the selector
        escaped_aria_labelledby_value = aria_labelledby_value.replace(":", "")
        logger.log(f"Replace aria_labelledby value: {escaped_aria_labelledby_value}")
        time_stamp_element = WebDriverWait(browser, 10).until(
            ec.presence_of_element_located((By.XPATH, f"//div[@hidden='true']//div//span[contains(@id,'{escaped_aria_labelledby_value}')]"))
        )        
        post_date_time = browser.execute_script("return arguments[0].textContent;", time_stamp_element)
        logger.log(f"Found time_stamp_element: {post_date_time}")
                
        if post_date_time:            
            return parse_datetime(post_date_time)
    except Exception as e:
        logger.log("Date time doesn't found: {e}")
    return None"""


def scroll_till_the_end(browser):
    last_height = browser.execute_script("return document.body.scrollHeight")

    while True:
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        random_sleep()
        new_height = browser.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


def scroll_to_until(browser, task, get_posts_function, get_date_from_post, remove_from_scope_function):
    logger.log("start scroll to until date: {}".format(task.until))
    while True:
        logger.log("scroll down")
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        random_sleep()
        scrolled_posts = get_posts_function(browser)
        if len(scrolled_posts) == 0:
            logger.log("scrolling finished. There are no more posts")
            return

        for sp in scrolled_posts:
            sp_date = get_date_from_post(sp)
            sp.fb_date = sp_date
            logger.log("date time from post: {} until date: {}".format(sp_date, task.until))
            if sp_date and sp_date < task.until:
                logger.log("finish scroll to until date: {}".format(task.until))
                return

        #post_ids = []
        #for post in scrolled_posts:
        #    post_ids.append("#" + post.get_attribute("id"))

        remove_from_scope_function(browser, scrolled_posts)
        logger.log("continue scroll down to until date")

#locator function rebuild
def loading_indicator_focus(browser):
    logger.log("try focus to loading indicator")
    try:
        WebDriverWait(browser, 2).until(
            ec.presence_of_element_located((By.CSS_SELECTOR, ".centeredIndicator"))
        )
        browser.execute_script("var nav=document.querySelector('.suspended-feed');"
                               "if(nav){nav.focus();}")
        logger.log("focus complete")
    except Exception as e:
        logger.log("no loading indicator")


def scroll_till_retro(browser, task, get_posts_function, get_date_from_post, parse_post, remove_from_scope_function):
    if task.until:
        scroll_to_until(browser, task, get_posts_function, get_date_from_post, remove_from_scope_function)

    logger.log("scroll to retro date: {}".format(task.retro))
    task_id = task.id
    posts = []
    while True:
        logger.log("scroll down")
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        random_sleep()
        loading_indicator_focus(browser)

        scrolled_posts = get_posts_function(browser)
        if len(scrolled_posts) == 0:
            logger.log("scrolling finished. There are no more posts")
            return posts

        logger.log("{} posts was found".format(len(scrolled_posts)))
        logger.log("start filtering by retro: {}".format(task.retro))
        retro_posts = []
        until_posts = []
        retro_date = task.retro
        if retro_date is None:
            five_day_ago = datetime.today()- timedelta(days=5)
        else:
            five_day_ago = retro_date
        for sp in scrolled_posts:
            #logger.log(f"Found sp_post: {sp}")
            sp_date = get_date_from_post(browser, sp)
            sp.fb_date = sp_date
            logger.log("date time from post: {}".format(sp_date))
            if sp_date and sp_date > five_day_ago:
                if not task.until or sp_date < task.until:
                    logger.log("added")
                    retro_posts.append(sp)
                    posts.append(sp)

                    post_obj = parse_post(browser, sp, task_id, sp_date)
                    if post_obj:
                        save_post(post_obj)
                else:
                    until_posts.append(sp)
                    logger.log("hasn't added by until condition")
            else:
                logger.log("hasn't added by retro condition")

        logger.log("{} remaining posts after filtering".format(len(retro_posts)))
        if len(retro_posts) == 0:
            if len(until_posts) > 0:
                logger.log("Scroll till until count will be = 0 current: {}".format(str(len(until_posts))))
            else:
                logger.log("scrolling finished. Next posts are after retro date")
                return posts

        #post_ids = []
        #for post in scrolled_posts:
         #   post_ids.append("#" + post.get_attribute("id"))

        remove_from_scope_function(browser, scrolled_posts)


def open_post(browser, link):
    browser.get(link)
    random_sleep()
    if "videos" in browser.current_url and browser.current_url != link:
        try:
            background = WebDriverWait(browser, 5).until(
                ec.presence_of_element_located((By.XPATH, "//div[contains(@class, 'fullScreenAvailable')]//a")))
            background.click()
        except Exception as e:
            logger.log("Background layer doesn't find")


def random_sleep():
    logger.log_alive()

    if CURRENT_PROFILE == 'prod':
        sleep(randint(1, 5))
    else:
        sleep(1)


def get_fb_id(user_element, link):
    try:
        fb_id = None
        if "profile.php" in link:
            fb_id = get_param(link, "id")

        if not fb_id:
            param = get_param(user_element.get_attribute("data-hovercard"), "id")
            logger.log("FB_id found: {}".format(param))
            return param
        else:
            logger.log("FB_id found: {}".format(fb_id))
            return fb_id
    except:
        logger.log("FB_id not found in attribute data-hovercard")

