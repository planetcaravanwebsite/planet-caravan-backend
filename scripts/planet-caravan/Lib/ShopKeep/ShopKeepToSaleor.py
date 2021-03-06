import os
import glob
from time import sleep

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

class ShopKeepToSaleor:
    def __init__(self, environment):
        self.environment = environment
        self.timeout = int(os.getenv('SK_TIMEOUT'))
        self.browser = None
        self.download_dir = os.getcwd()
        self.stock_file = 'planetcaravan_stock_items.csv'

    def run(self):
        url = os.getenv('SK_HOSTNAME')
        chrome_version = os.getenv('CHROMEDRIVER_VERSION')

        # Open up a browser
        chrome_options = webdriver.ChromeOptions()
        preferences = {"download.default_directory": self.download_dir,
                       "directory_upgrade": True,
                       "safebrowsing.enabled": True}

        chrome_options.add_experimental_option("prefs", preferences)
        chrome_options.add_argument("--window-size=1920,1080")

        if self.environment == 'local':
            self.browser = webdriver.Chrome(
                ChromeDriverManager(version=chrome_version).install(),
                options=chrome_options)
        else:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--no-sandbox")
            # chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")

            self.browser = webdriver.Chrome(
                ChromeDriverManager(version=chrome_version).install(),
                chrome_options=chrome_options)


        self.browser.get(url)

        # Sequence of events
        self.cleanup()
        self.login()
        self.generate_report()
        self.download_file()
        return self.return_file()

    def cleanup(self):
        for fname in glob.glob(f'{self.download_dir}/*.csv'):
            os.remove(fname)

    def login(self):
        print("Logging in...")

        store = os.getenv('SK_STORE')
        username = os.getenv('SK_USER')
        password = os.getenv('SK_PASSWORD')

        # Wait to load
        element_present = EC.presence_of_element_located((By.ID, 'backoffice-login'))
        WebDriverWait(self.browser, self.timeout).until(element_present)

        # Log in
        storename_field = self.browser.find_element_by_id('store_name')
        username_field = self.browser.find_element_by_id('login')
        password_field = self.browser.find_element_by_id('password')

        storename_field.send_keys(store)
        username_field.send_keys(username)
        password_field.send_keys(password)

        submit = self.browser.find_element_by_id('submit')

        submit.click()

    def get_main_frame(self):
        iframe_path = '//iframe[contains(@title, "iframe")]'
        self.wait_for_element(iframe_path)
        iframe = self.browser.find_element_by_xpath(iframe_path)
        self.browser.switch_to_frame(iframe)

    def generate_report(self):
        print("Generating Report...")

        # Open the menu
        menu_xpath = '//*[contains(@class, "ls-bonfire-sidebar")]//a[contains(@data-test,"SidebarLink-1-Reports")]'
        self.wait_then_click(menu_xpath)

        sleep(0.5)

        report_path = '//a[contains(@data-test, "SidebarLink-2-Stock")]'
        self.wait_then_click(report_path)

        # Switch to the iframe content
        self.get_main_frame()

        # Request a new export
        export_xpath = '//button[contains(@class, "button") and contains(text(), "Export Stock Items")]'
        self.wait_then_click(export_xpath)

        print("Exporting...")

        # Go to the export center
        export_center = '//div[contains(@class, "modal-body")]//a[contains(text(), "Export Center")]'
        self.wait_then_click(export_center, 20)

    def download_file(self):
        # # Go to Export Center
        # self.wait_then_click(
        #     '//div[contains(@class, "navigation__link")]/a[contains(text(), "Export Center")]')

        attempts = 20
        download_xpath = '//div[contains(@class, "ReactVirtualized__Table__row")][1]//span[contains(@class, "export-action--ready")]/a'

        while attempts > 0:
            print(f'Waiting for export to be ready ({attempts} attempts remaining)...')
            # Wait for the download button; then refresh until it's available
            sleep(1)

            try:
                # Sort by Created at, so the newest is at the top
                sort_xpath = '//*[contains(@class, "ReactVirtualized__Table")]/span[contains(@title, "Created At")]'
                self.wait_then_click(sort_xpath)
                sleep(0.1)
                self.browser.find_element_by_xpath(sort_xpath).click()

                self.wait_then_click(download_xpath, 15)
                sleep(1)
                break
            except:
                attempts = attempts - 1
                self.browser.refresh()
                sleep(1)
                self.get_main_frame()

        if attempts == 0:
            raise Exception("Could not download stock file.")

    def return_file(self):
        attempts = 20
        file = f'{self.download_dir}/{self.stock_file}'
        while attempts > 0:
            print(
                f'Waiting for download to complete ({attempts} attempts remaining)...')
            sleep(5)

            if os.path.isfile(file):
                return os.path.abspath(file)

            attempts -= 1

        raise Exception("Stock file download taking too long.")

    def wait_for_element(self, xpath, max_time=10):
        if not max_time:
            max_time = self.timeout
        attempts = 0

        while attempts < 5:
            try:
                element_present = EC.presence_of_element_located((By.XPATH, xpath))
                WebDriverWait(self.browser, max_time).until(element_present)
                return self.browser.find_element_by_xpath(xpath)

            except:
                attempts += 1
        raise Exception(f'Could not wait for element: {xpath} (Attempted {attempts} times).')

    def wait_then_click(self, xpath, max_time=10):
        element = self.wait_for_element(xpath, max_time)
        sleep(0.05)
        element.click()

