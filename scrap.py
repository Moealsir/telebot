import asyncio
import concurrent.futures
import random
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By

def read_user_agents(file_path):
    """
    Reads user agents from a file and returns them as a list.
    """
    with open(file_path, 'r') as file:
        user_agents = file.readlines()
    return [ua.strip() for ua in user_agents]

def get_random_user_agent(user_agents):
    """
    Selects a random user agent from the list.
    """
    return random.choice(user_agents)

def initialize_webdriver(path_to_chromedriver, user_agent):
    """
    Initializes the Selenium WebDriver with a custom user agent and headless mode.
    """
    service = Service(path_to_chromedriver)
    chrome_options = Options()
    
    # Add custom user agent
    chrome_options.add_argument(f'user-agent={user_agent}')
    
    # Enable headless mode and disable GPU usage
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # Optional: Set a window size for the headless browser
    chrome_options.add_argument('window-size=1920x1080')

    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def open_url(driver, url):
    """
    Opens a URL using the Selenium WebDriver.
    """
    try:
        driver.get(url)
        time.sleep(5)  # Wait for the page to load, adjust as necessary
    except Exception as e:
        print(f"An error occurred while opening the URL: {e}")

def close_webdriver(driver):
    """
    Closes the Selenium WebDriver.
    """
    try:
        driver.quit()
    except Exception as e:
        print(f"An error occurred while closing the WebDriver: {e}")

async def start_parsing(driver, option_value):
    """
    Changes the selection to the specified option and clicks the generate key button.
    Repeats up to 5 times if login fails, then restarts the WebDriver with a new user agent.
    """
    max_attempts = 5
    attempt = 1
    
    while attempt <= max_attempts:
        try:
            # Change the selection to the specified option
            select_element = driver.find_element(By.ID, "appSelect")
            select = Select(select_element)
            select.select_by_value(option_value)
            time.sleep(1)  # Wait for 1 second

            # Click on the generate key button
            generate_button = driver.find_element(By.XPATH, "/html/body/div/div[1]/button")
            generate_button.click()
            time.sleep(5)  # Wait for the page to respond, adjust as necessary
            
            # Check the results
            pre_element = driver.find_element(By.ID, "jsonDataDisplay")
            pre_text = pre_element.text
            
            # Count login failures and successes
            login_failed_count = pre_text.count("Login failed. Skipping key generation.")
            login_successful = "Login successful, wait while the keys are generated..." in pre_text
            
            if login_successful:
                print(f"Login successful on attempt {attempt}.")
                return True  # Indicate that parsing was successful
            elif login_failed_count >= 4:
                print(f"Login failed {login_failed_count} times. Re-clicking button...")
                attempt += 1  # Increment attempt counter
            else:
                print(f"Attempt {attempt} did not succeed. Checking again...")
                attempt += 1  # Increment attempt counter

            # If maximum attempts reached, restart WebDriver
            if attempt > max_attempts:
                print("Maximum attempts reached. Restarting WebDriver with a new user agent.")
                close_webdriver(driver)
                return False  # Indicate that WebDriver needs to be restarted
                
        except Exception as e:
            print(f"An error occurred while interacting with the page: {e}")
            return False  # Indicate that WebDriver needs to be restarted

async def monitor_key_generation(driver, timeout=240):
    """
    Monitors the key generation process and parses the generated keys within a given timeout.
    """
    keys = []
    failed_keys = 0
    keys_to_generate = 4
    start_time = time.time()
    count = 1
    
    while time.time() - start_time < timeout:
        try:
            # Find the pre element and get its text
            pre_element = driver.find_element(By.ID, "jsonDataDisplay")
            pre_text = pre_element.text
            
            # Parse the keys and count the failed keys
            lines = pre_text.split("\n")
            keys = [line.split(": ")[1] for line in lines if line.startswith("Generated key:")]
            failed_keys = len([line for line in lines if line == "No valid keys found."])
            
            # Print the keys and count of failed keys
            if keys:
                if count == 2:
                    print(f"Generated keys: {keys}")
                    await append_keys_to_file(keys)
                    break
                else:
                    print(f'Try number {count}')
                    count += 1
            
            # Check if the generation is complete
            if len(keys) + failed_keys == keys_to_generate:
                break
            
            # Wait for 5 seconds before checking again
            time.sleep(5)
        except Exception as e:
            print(f"An error occurred while monitoring key generation: {e}")
            break

    return keys, failed_keys

async def append_keys_to_file(keys):
    """
    Appends the final generated keys to the specified file.
    """
    try:
        with open('keys.txt', 'a') as file:
            for key in keys:
                file.write(f'{key}\n')
    except Exception as e:
        print(f"An error occurred while writing the keys to file: {e}")

async def process_option(option):
    """
    Processes a single option, including initializing the WebDriver, interacting with the page, and saving keys.
    """
    path_to_chromedriver = '/bin/chromedriver'  # Update with your actual path
    url = 'https://iappsbest.github.io/Pages/KeyGen.html'  # Update with your actual URL
    user_agents_file = 'user-agents.txt'  # Path to your user agents file

    # Read user agents from file
    user_agents = read_user_agents(user_agents_file)

    for _ in range(3):  # Number of attempts per option
        user_agent = get_random_user_agent(user_agents)
        driver = initialize_webdriver(path_to_chromedriver, user_agent)

        try:
            open_url(driver, url)

            # Start parsing and interacting with the page
            if await start_parsing(driver, option):
                keys, failed_keys = await monitor_key_generation(driver, timeout=240)
                if keys:
                    print(f"Final generated keys for {option}: {keys}")
                break  # Exit the loop if parsing was successful

        finally:
            close_webdriver(driver)

async def process_all_options():
    """
    Processes all options and restarts the process after completing all options.
    """
    options = ["Clone", "Bike", "Chain", "Train"]  # Replace with actual option values

    while True:  # Infinite loop to restart the process
        with concurrent.futures.ThreadPoolExecutor() as executor:
            loop = asyncio.get_event_loop()
            await asyncio.gather(*[loop.run_in_executor(executor, lambda opt=option: asyncio.run(process_option(opt))) for option in options])
        
        print("Completed all options. Restarting the process...")

if __name__ == "__main__":
    asyncio.run(process_all_options())


