from datetime import datetime
from random import randint
from time import sleep
import requests

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains


from .. import logger
from ..database import DBSession
from ..database.models import Comment, Content, Photo, User, Video, All_comment
from ..database.subtasks_dao import save_personal_page_subtask
from ..utils.count_utils import string_count_to_int
from ..utils.user_utils import trim_full_link
from .common_parsing import get_fb_id, open_post
from ..utils.datetime_utils import parse_datetime
from ..utils.date_time_comment import convert_date_comment


class CommentData:
    def __init__(self, author_name, author_link, author_fb_id, image, video, text, comment_id, date, likes_count, class_name):
        self.author_name = author_name
        self.author_link = author_link
        self.author_fb_id = author_fb_id
        self.image = image
        self.video = video
        self.text = text
        self.comment_id = comment_id
        self.date = date
        self.likes_count = likes_count
        self.children = []
        self.class_name = class_name

    def add_children(self, children):
        for child in children or []:
            self.children.append(child)


# New integrated function to click an icon
def click_icon(driver):
    try:
        icon_div = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((
                By.CSS_SELECTOR,
                "div.x9f619.x1n2onr6.x1ja2u2z.x6s0dn4.x3nfvp2.xxymvpz"
            ))
        )
        icon_div.click()
        print("Icon clicked successfully.")
    except Exception as e:
        print(f"Error clicking icon: {e}")


# New integrated function to click "Show all comments"
def click_show_all_comments(driver):
    try:
        show_all_comments_element = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((
                By.XPATH,
                "//span[contains(text(), 'Show all comments, including potential spam.')]"
            ))
        )
        show_all_comments_element.click()
        print("Clicked 'Show all comments'.")
    except Exception as e:
        print(f"Error clicking 'Show all comments': {e}")


# Global variable to track total clicks across function calls
view_more_clicks = 0  # ? Track total clicks across calls

def click_view_more_buttons(driver, last_popup, max_clicks=3):
    """
    Finds and clicks the 'View more comments' button up to 3 times total
    and clicks 'View replies' if present inside the popup.
    """
    global view_more_clicks  # Track clicks across function calls

    try:
        clicked = False  # Track if any button was clicked
        
        #Locate "View more comments" button (limit clicks to max_clicks)
        view_more_xpath = "//span[contains(text(), 'View more comments') or contains(text(), 'View more')]"
        view_more_buttons = last_popup.find_elements(By.XPATH, view_more_xpath)

        for button in view_more_buttons:
            if view_more_clicks >= max_clicks:
                print("Max 'View more comments' clicks reached (3). Stopping.")
                break  # Stop clicking after 3 clicks total

            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
            sleep(1)  # Allow smooth scrolling
            button.click()
            view_more_clicks += 1  # ? Track total clicks
            print(f"Clicked 'View more comments' ({view_more_clicks}/3). Waiting for comments to load...")
            sleep(4)  # Wait for comments to load
            clicked = True

        #Locate and click "View replies" button (unlimited clicks)
        view_replies_xpath = "//span[contains(text(), 'View') and contains(text(), 'repl')]"
        view_replies_buttons = last_popup.find_elements(By.XPATH, view_replies_xpath)

        for button in view_replies_buttons:
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
            sleep(1)  # Allow smooth scrolling
            button.click()
            print("? Clicked 'View replies'. Waiting for replies to load...")
            sleep(4)  # Wait for replies to load
            clicked = True

        return clicked  # Return True if any button was clicked

    except Exception as e:
        print(f"Error clicking buttons: {e}")
        return False  # No buttons were found or clicked


def scroll_popup_to_end(driver):
    try:
        print("Waiting for all popups to appear...")

        # Wait for popups (either type)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR, "div[role='dialog'], div.x1jx94hy.x78zum5.xdt5ytf.x2lah0s.xw2csxc.x1odjw0f.xmd6oqt.x13o0s5z"
            ))
        )

        # Find all popups matching either selector
        popups = driver.find_elements(By.CSS_SELECTOR, "div[role='dialog']") + driver.find_elements(By.CSS_SELECTOR, 
            "div.x1jx94hy.x78zum5.xdt5ytf.x2lah0s.xw2csxc.x1odjw0f.xmd6oqt.x13o0s5z")

        if not popups:
            print("No popups found.")
            return
        
        last_popup = popups[-1]  # Select the last popup
        print(f"Located {len(popups)} popups, selecting the last one.")

        # Identify the scrollable container inside the last popup
        scrollable_popup = None
        for child in last_popup.find_elements(By.XPATH, ".//*"):
            if driver.execute_script("return arguments[0].scrollHeight > arguments[0].clientHeight;", child):
                scrollable_popup = child
                break

        # If no child is scrollable, use the whole popup
        if not scrollable_popup:
            print("? No valid nested scrollable container found. Using popup itself.")
            scrollable_popup = last_popup

        print("Scrollable popup identified. Searching for comments...")

        last_comment_count = 0
        scroll_attempts = 0
        max_scroll_attempts = 2  
        no_new_comments_count = 0  

        while scroll_attempts < max_scroll_attempts:
            # ? Click "View More Comments" & "View Replies"
            # ? Click "View More Comments" up to 3 times
            if view_more_clicks < 3 and click_view_more_buttons(driver, last_popup):
                sleep(3)  # Wait for more comments or replies to load
                continue 

            # ? Find all loaded comments
            comment_sections = last_popup.find_elements(By.XPATH, "//div[contains(@aria-label, 'Comment by')]")
            current_comment_count = len(comment_sections)

            # Stop if no new comments are loading
            if current_comment_count == last_comment_count:
                no_new_comments_count += 1
                if no_new_comments_count >= 3:
                    print("No new comments loaded after multiple attempts. Stopping.")
                    break
            else:
                no_new_comments_count = 0  

            if current_comment_count > 0:
                last_comment = comment_sections[-1]  

                print(f"Found {current_comment_count} comments, scrolling to the last one.")
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", last_comment)
                sleep(4)  

            last_comment_count = current_comment_count
            scroll_attempts += 1

        print("Finished scrolling to the last comment inside the popup.")

    except TimeoutException:
        print("TimeoutException: Popups or comments did not appear.")
    except Exception as e:
        print(f"Error while scrolling inside the last popup: {e}")

# Global counter
friend_requests_sent = 0  

def add_friend_if_exists(browser, comment, retry_count=0):
    """
    Opens a user profile from a comment, switches to the new tab, and clicks 'Add Friend' if available.
    Only sends 3 friend requests max.
    Retries up to 3 times in case of stale elements.
    """
    global friend_requests_sent  
    MAX_RETRIES = 3  

    if retry_count >= MAX_RETRIES:
        print("? Too many stale element retries. Skipping this comment.")
        return  

    if friend_requests_sent >= 3:
        print("? Limit reached: 3 friend requests sent.")
        return  

    try:
        # ? Ensure the comment is still valid
        try:
            WebDriverWait(browser, 5).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'x1lliihq')]"))
            )
        except TimeoutException:
            print("? Comment disappeared, skipping...")
            return  

        # ? Scroll to comment
        browser.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", comment)
        sleep(2)

        # ? Locate the profile link inside the comment
        profile_xpath = ".//a[contains(@href, 'facebook.com/profile.php?id=') or contains(@href, 'facebook.com/')]"
        profile_element = WebDriverWait(comment, 5).until(
            EC.presence_of_element_located((By.XPATH, profile_xpath))
        )

        # ? Extract profile URL
        profile_url = profile_element.get_attribute("href")
        if not profile_url:
            print("? Profile URL not found, skipping...")
            return

        # ? Extract profile name
        try:
            profile_name_element = profile_element.find_element(By.XPATH, ".//span[contains(@class, 'x193iq5w')]")
            profile_name = profile_name_element.text.strip()
        except:
            profile_name = "Unknown"

        print(f"??? Opening profile: {profile_name} ({profile_url})")

        # ? Open the profile in a new tab
        browser.execute_script(f"window.open('{profile_url}', '_blank');")
        sleep(2)  

        # ? Switch to the new tab
        browser.switch_to.window(browser.window_handles[-1])

        # ? Wait for the profile page to load
        WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        print(f"? Opened profile: {profile_url}")

        # ? Locate and click 'Add Friend' button
        add_friend_xpaths = [
            "//div[@aria-label='Add friend' and contains(@class, 'x1i10hfl')]",  # ? Most common
            "//button[@aria-label='Add friend']",  # ? Alternative button
        ]
        add_friend_button = None
        for xpath in add_friend_xpaths:
            try:
                add_friend_button = WebDriverWait(browser, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                break  # ? Stop checking after the first valid button is found
            except TimeoutException:
                continue  

        if add_friend_button:
            ActionChains(browser).move_to_element(add_friend_button).click().perform()
            print(f"? Sent friend request to {profile_name}")
            friend_requests_sent += 1
            sleep(2)  
        else:
            print(f"? No 'Add Friend' button found for {profile_name}. Skipping.")

        # ? Close the profile tab and switch back
        browser.close()
        browser.switch_to.window(browser.window_handles[0])
        print(f"?? Switched back to comments section")

    except StaleElementReferenceException:
        print(f"? Stale element encountered, retrying... ({retry_count + 1}/{MAX_RETRIES})")
        sleep(2)
        add_friend_if_exists(browser, comment, retry_count + 1)  # ? Retry correctly
        return  

    except Exception as e:
        print(f"? Error processing comment: {e}")
        browser.close()
        browser.switch_to.window(browser.window_handles[0])  

    print(f"?? Total friend requests sent: {friend_requests_sent}")      
        

def search_view_more(browser):
    """
    Checks for the "View More Comments" button and clicks it if found.
    Returns True if the button is clicked, otherwise False.
    """
    try:
        # Look for the "View More Comments" button
        view_more_button = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'View more comments')]"))
        )
        if view_more_button:
            view_more_button.click()
            sleep(2)  # Allow time for comments to load
            print("Clicked 'View more comments'.")
            return True
    except Exception as e:
        print(f"No 'View more comments' button found: {e}")
        return False



def parse_comment(comment):
    """
    Parse a single comment element to extract structured data.
    """
    def has_xpath(xpath):
        """
        Checks if a given XPath exists within the comment element.
        """
        try:
            return comment.find_element(By.XPATH, xpath) is not None
        except Exception:
            return False

    def get_image_link(comment):
        """
        Extracts the image link from the comment if available.
        """
        try:
            xpath = ".//div[@class='x78zum5 xv55zj0 x1vvkbs']//div//img"
            if has_xpath(xpath):
                photo_element = comment.find_element(By.XPATH, xpath)
                photo_link = photo_element.get_attribute("src")
                logger.log(f"Photo Link: {photo_link}")
                return photo_link
        except Exception as e:
            logger.log(f"Error extracting image link: {e}")
        return None

    def get_video_link(comment):
        """
        Extracts the video link from the comment if available.
        """
        # Placeholder as per the current code logic
        return ""

    
    def get_comment_id(comment):
        """
        Extracts the comment ID from the comment element.
        """
        try:
            # Locate the anchor tag containing the comment ID
            author_element = comment.find_element(By.XPATH, ".//a[contains(@href, 'comment_id')]")
            comment_url = author_element.get_attribute("href")
            
            # Extract the part after 'comment_id='
            if "comment_id=" in comment_url:
                comment_id_part = comment_url.split("comment_id=")[1]
                
                # ? Handle both '%' and '&' as delimiters
                comment_id = comment_id_part.split("&")[0].split("%")[0]
                
                print(f"? Extracted Comment ID: {comment_id}")
                return comment_id
            else:
                print("? No 'comment_id' found in URL")
                return None
        except Exception as e:
            print(f"? Error extracting comment ID: {e}")
            return None

    
    def see_more_button_click(comment):
        """
        Clicks the 'See More' button within a comment if it exists.
        """
        try:
            # Locate the "See More" button within the comment
            see_more_button = comment.find_element(By.XPATH, ".//div[@role='button' and contains(text(), 'See more')]")
            # Click the "See More" button
            see_more_button.click()
            print("Clicked 'See More' button.")
        except NoSuchElementException:
            print("No 'See More' button found in this comment.")

    def get_comment_text(comment):
        """
        Extracts the full text content of the comment using the specified class after clicking 'See More', if present.
        """
        try:
            # Click the 'See More' button if it exists
            see_more_button_click(comment)
            
            # Locate the text element using the specified class
            text_element = comment.find_element(By.XPATH, ".//div[contains(@class, 'x1lliihq') and contains(@class, 'xjkvuk6') and contains(@class, 'x1iorvi4')]")
            
            # Extract the text content
            comment_text = text_element.text.strip()
            print(f"Extracted Comment Text: {comment_text}")
            return comment_text
        except NoSuchElementException:
            print("No comment text found with the specified class.")
            return None
        except Exception as e:
            print(f"Error extracting comment text: {e}")
            return None
    
    def extract_user_id_from_link(link):
        """Extracts the post_id from the URL."""
        try:
            status = "NA"
            if "profile.php?id" in link:
                status = link.split("=")[1].split("&")[0]
            else:
                status = link.split("/")[3].split("?")[0]        
            return status
        except IndexError:
            return "NA"
        except Exception as ex:
            logger.exception(f'Error at extract_id_from_link: {ex}')
            return "NA"            

    def get_author_data(comment):
        """
        Extracts the author details (name, profile link, and Facebook ID) from a comment element.
        """
        try:
            # Locate the author link element
            author_element = comment.find_element(By.XPATH, ".//a[contains(@href, 'facebook.com')]")

            # Extract author name using the updated XPath
            try:
                name_element = comment.find_element(By.XPATH, ".//span[contains(@class, 'x193iq5w') and @dir='auto']")
                author_name = name_element.text.strip()
            except Exception:
                author_name = "Unknown"

            # Extract the author's profile link
            author_link = trim_full_link(author_element.get_attribute("href"))            

            # Extract Facebook ID from the link
            author_fb_id = extract_user_id_from_link(author_link)

            print(f"Author Name: {author_name}, Link: {author_link}, FB ID: {author_fb_id}")
            return author_name, author_link, author_fb_id
        except Exception as e:
            print(f"Error extracting author data: {e}")
            return None, None, None
        

    def get_comment_date(comment):
        """
        Extracts the date from the comment.
        """
        try:
            date_element = comment.find_element(By.XPATH, ".//div[@class='x6s0dn4 x3nfvp2']//a")
            date_text = date_element.text
            parsed_date = parse_datetime(date_text)
            logger.log(f"Comment Date: {parsed_date}")
            return parsed_date
        except Exception as e:
            logger.log(f"Error extracting comment date: {e}")
        return None

    def get_comments_like_count(comment):
        """
        Extracts the reaction count from the given comment element.
        """
        try:
            # Locate the div element containing the aria-label with reaction count
            reaction_element = comment.find_element(By.XPATH, ".//div[contains(@aria-label, 'reaction')]")
            
            # Extract the aria-label text
            aria_label = reaction_element.get_attribute("aria-label")
            
            # Parse the reaction count from the text
            reaction_count = int(aria_label.split()[0])  # Extract the first part, which is the number
            print(f"Reaction Count: {reaction_count}")
            return reaction_count
        except Exception as e:
            print(f"No found reaction count")
            return 0

    def get_class_name(comment):
        """
        Extracts the CSS class name for the comment.
        """
        try:
            class_name = comment.get_attribute("class").split(" ")[0]
            # logger.log(f"Comment Class Name: {class_name}")
            return class_name
        except Exception as e:
            logger.log(f"Error extracting class name: {e}")
        return None

    # Extracting all comment details
    author_name, author_link, author_fb_id = get_author_data(comment)
    if not author_name or not author_link:
        logger.log("Missing author data; skipping comment.")
        return None  # Skip this comment if author data is missing

    return CommentData(
        author_name=author_name,
        author_link=author_link,
        author_fb_id=author_fb_id,
        image=get_image_link(comment),
        video=get_video_link(comment),
        text=get_comment_text(comment),
        comment_id=get_comment_id(comment),
        date=get_comment_date(comment),
        likes_count=get_comments_like_count(comment),
        class_name=get_class_name(comment),
    )


def parse_comments(credentials, browser, subtask):
    post = subtask.post
    source_url = post.fb_post_link
    #source_url = 'https://www.facebook.com/khitthitnews/posts/pfbid02BRshzyXvYjXTFvVaQDNMuuxCvJaDhEWUwg4H4ACCZjTwQU8DnzbrVkVGDE2W3KJUl'
    # source_url = 'https://www.facebook.com/watch/?v=2022226218257970'
    browser.get(source_url)
    sleep(3)
    print(f"Opened post: {source_url}")

    click_icon(browser)  # Click the icon to expand comments

    click_show_all_comments(browser)  # Click "Show all comments"    
    
    scroll_popup_to_end(browser)  # ? Scroll to load all comments

    comments = search_comments(browser)  # ? Find comments again after scrolling    

    # ? Save comments to the database
    comment_objects = collect_root_comments(comments)

    save_users = {u.link: u for u in DBSession.query(User).filter(User.link.in_(get_distinct_authors(comment_objects))).all()}
    saved_comments = {c.fb_comment_id: c for c in DBSession.query(Comment).filter(Comment.fb_comment_id.in_(get_comments_fb_ids(comment_objects))).all()}
    save_comments(None, comment_objects, save_users, saved_comments, post)
    
    for comment in comments:
        add_friend_if_exists(browser, comment)  # ? Process friend requests first

    

def search_comments(browser):
    try:
        print("Searching for comments...")

        # ? Corrected XPath for finding both comments and replies
        comments_xpath = "//div[contains(@aria-label, 'Comment by')] | //div[contains(@aria-label, 'Reply by')]"

        # Wait for comments and replies to appear
        comments = WebDriverWait(browser, 30).until(
            EC.presence_of_all_elements_located((By.XPATH, comments_xpath))
        )

        print(f"? Found {len(comments)} comments.")
        return comments

    except TimeoutException:
        print("? TimeoutException: Comments did not load within 30 seconds.")
    except NoSuchElementException:
        print("? No comments found on this page.")
    except Exception as e:
        print(f"? Error searching comments: {e}")

        # Save page source for debugging
        with open("debug_page_source.html", "w", encoding="utf-8") as f:
            f.write(browser.page_source)
        print("?? Saved page source to 'debug_page_source.html' for debugging.")

    return []


def collect_root_comments(comments):
    """
    Collect root-level comments without verbose logging for iterations.
    """
    comment_objects = []
    for comment in comments:
        root_comment = parse_comment(comment)
        if root_comment is None:
            continue  # Skip this comment if parsing failed
        root_comment.add_children(collect_child_comments(comment))  # ? Extract child replies
        comment_objects.append(root_comment)
    return comment_objects


def collect_child_comments(comment):
    """
    Collects all child comments (replies) of a given comment.
    """
    child_comments_data = []
    try:
        print("?? Searching for replies inside the comment...")

        # ? Corrected XPath for replies
        child_comments = comment.find_elements(By.XPATH, ".//div[contains(@aria-label, 'Reply by') or contains(@aria-label, 'Reply')]")

        if not child_comments:
            print("? No replies found inside this comment.")
            return []

        print(f"? Found {len(child_comments)} reply comments.")

        for index, child_comment in enumerate(child_comments, start=1):
            print(f"?? Parsing reply {index} of {len(child_comments)}.")

            # ? Extract reply data (text, author, ID, date, likes)
            parsed_child = parse_comment(child_comment)
            if parsed_child:
                child_comments_data.append(parsed_child)
            else:
                print(f"? Skipping reply {index} as it returned None.")

    except Exception as e:
        print(f"? Error while parsing child comments: {e}")

    return child_comments_data


def save_comments(parent_comment, comments, save_users, saved_comments, post):
    """
    Save comments to the database if they do not already exist.
    """
    def save_comment(c, parent_comment, post, save_users): 
        logger.log("Start author_link Save")
        
        # Check if the author already exists in the database
        if c.author_link not in save_users:
            logger.log(f"New author link: {c.author_link}")
            user = User(name=c.author_name, link=c.author_link, fb_id=c.author_fb_id)
            save_personal_page_subtask(post, user)  # Additional tasks for a new user
            DBSession.add(user)
            DBSession.commit()
            save_users[c.author_link] = user  # Add to local cache
        else:
            logger.log("Author already in DB")
            user = save_users[c.author_link]
        
        # Check if the comment already exists in the database
        if c.comment_id in saved_comments:
            logger.log(f"Comment already exists in DB: {c.comment_id}")
            return saved_comments[c.comment_id]
        
        # Create a new Content object
        content = Content(text=c.text)
        add_id = All_comment(content=content, network_id=1)
        DBSession.add(add_id)
        DBSession.commit()
        logger.log("Start image Save")
        
        # Save image if available
        if c.image is not None:
            photo = Photo(photo_link=c.image, content=content)
            DBSession.add(photo)
            DBSession.commit()
        
        # Save video if available
        if c.video is not None:
            video = Video(video_link=c.video, content=content)
            DBSession.add(video)
            DBSession.commit()
        
        # Save the comment
        comment = Comment(post=post, user=user, content=content, fb_comment_id=c.comment_id, date=c.date,
                          likes_count=c.likes_count)
        if parent_comment:
            comment.parent_comment = parent_comment
        DBSession.add(comment)
        DBSession.commit()
        logger.log(f"Saved comment id: {comment.fb_comment_id} to DB")
        
        # Add the comment to the local cache
        saved_comments[c.comment_id] = comment
        return comment

    def get_saved_comment(c, parent_comment, post, save_users, saved_comments):
        """
        Check and save the comment if it does not already exist in the database.
        """
        if c.comment_id in saved_comments:
            logger.log(f"Comment already exists, skipping: {c.comment_id}")
            return saved_comments[c.comment_id]
        else:
            logger.log(f"New comment, saving: {c.comment_id}")
            return save_comment(c, parent_comment, post, save_users)

    for c in comments:
        comment = get_saved_comment(c, parent_comment, post, save_users, saved_comments)
        if len(c.children) > 0:
            logger.log(f"Saving {len(c.children)} child comments for comment id: {c.comment_id}")
            save_comments(comment, c.children, save_users, saved_comments, post)


def get_distinct_authors(comment_objects):
    def get_authors(comments):
        for c in comments:
            authors.add(c.author_link)
            if len(c.children) > 0:
                get_authors(c.children)

    authors = set()
    get_authors(comment_objects)
    logger.log("Author Check - {}".format(authors))
    return authors


def get_comments_fb_ids(comment_objects):
    def get_comments(comments):
        for c in comments:
            comments_fb_ids.add(c.comment_id)
            if len(c.children) > 0:
                get_comments(c.children)

    comments_fb_ids = set()
    get_comments(comment_objects)
    logger.log("ID Check - {}".format(comments_fb_ids))
    return comments_fb_ids