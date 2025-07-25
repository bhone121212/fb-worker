from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import os

from .. import logger
from ..constants import APPLICATION_ROOT_PATH, CURRENT_PROFILE
from ..database.worker_credentials_dao import block_proxy, set_finished
from .proxy import close_proxy_url, get_proxy_url


class Browser:
    def __init__(self):
        self.browser = None
        self.proxy = None
        self.credentials = None

    def get_browser(self):
        return self.browser

    def get_credentials(self):
        return self.credentials

    def open_by_proxy(self, proxy):
        if self.browser:
            print("close previous browser")
            self.close()

        return self.open_common(proxy, None)

    def open(self, credentials):
        if self.browser:
            print("close previous browser")
            self.close()

        self.credentials = credentials
        return self.open_common(credentials.proxy, credentials.user_agent)

    def open_common(self, proxy, user_agent):
        try:
            self.browser, self.proxy = get_chromedriver(proxy, user_agent)
            return self.browser, self.proxy
        except Exception as e:
            self.disable_proxy(e)
            self.close()
        return None, None

    def disable_proxy(self, e):
        exception_message = str(e)
        print("browser are not able to open. error: {}".format(exception_message))
        if proxy_not_connected_exception(exception_message):
            if self.credentials:
                block_proxy(self.credentials)
                logger.log("set credentials empty")
                self.credentials = None

    def close(self):
        print("close browser and proxy")
        try:
            if self.proxy:
                close_proxy_url(self.proxy)
                self.proxy = None
            if self.browser:
                self.browser.quit()
            if self.credentials:
                set_finished(self.credentials)
            else:
                logger.log("credentials are empty")
        except Exception as e:
            print("browser closed with error: {}".format(str(e)))


"""def get_chromedriver(proxy, user_agent=None):
    chrome_options = webdriver.ChromeOptions()

    if CURRENT_PROFILE == 'prod':
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

    chrome_options.add_argument('--disable-notifications')
    # TODO enable images
    # chrome_options.add_argument('--blink-settings=imagesEnabled=false')
    proxy_url = get_proxy_url(proxy)
    chrome_options.add_argument('--proxy-server=' + proxy_url)

    if user_agent:
        chrome_options.add_argument('--user-agent=%s' % user_agent.userAgentData)
        chrome_options.add_argument('--window-size=%s' % (str(user_agent.window_size.width) + "," +
                                                          str(user_agent.window_size.height)))

    if CURRENT_PROFILE == 'prod':
        return webdriver.Chrome(chrome_options=chrome_options), proxy_url
    else:
        return webdriver.Chrome(APPLICATION_ROOT_PATH + '/chromedriver', chrome_options=chrome_options), proxy_url"""
        
def get_chromedriver(proxy, user_agent=None):
    chrome_options = webdriver.ChromeOptions()
    if CURRENT_PROFILE == 'prod':
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--headless')  
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

    # Common Options
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--mute-audio')
    chrome_options.add_argument('--window-size=1920,1080')  # 👀 Makes browser look real

    # 🕵️ Set proxy
    proxy_url = get_proxy_url(proxy)
    chrome_options.add_argument('--proxy-server=' + proxy_url)

    # 🧠 Set User-Agent & screen size
    if user_agent:
        chrome_options.add_argument(f"--user-agent={user_agent.userAgentData}")
        chrome_options.add_argument(f"--window-size={user_agent.window_size.width},{user_agent.window_size.height}")

    # 🧠 Start ChromeDriver
    if CURRENT_PROFILE == 'prod':
        driver = webdriver.Chrome(options=chrome_options)
    else:
        driver_path = os.path.join(APPLICATION_ROOT_PATH, 'chromedriver')
        driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)

    # 🎩 Stealth Patch (Anti-bot tricks via CDP)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
        window.chrome = { runtime: {} };
        window.navigator.permissions.query = (parameters) =>
            parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : window.navigator.permissions.query(parameters);
        window.alert = () => console.log('[Alert blocked]');
        """
    })

    return driver, proxy_url


def open_tab(browser, link):
    logger.log('Go to direct link {}'.format(link))
    browser.execute_script(f"window.open(\"{link}\")")
    browser.implicitly_wait(1)
    logger.log('Switch to new tab')
    browser.switch_to.window(browser.window_handles[-1])


def close_tab(browser, return_tab_index=0):
    browser.close()
    browser.switch_to.window(window_name=browser.window_handles[return_tab_index])
    del browser.window_handles[-1]


def proxy_not_connected_exception(exception_message):
    return "Max retries exceeded with url:" in exception_message


browser_service = Browser()
logger.set_browser(browser_service)
