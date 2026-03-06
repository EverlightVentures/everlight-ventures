import requests
from bs4 import BeautifulSoup

# URL of the webpage you want to scrape
url = 'http://example.com'

# Send a GET request to the webpage
response = requests.get(url)

# If the GET request is successful, the status code will be 200
if response.status_code == 200:
    # Get the content of the response
    content = response.content
    
    # Create a BeautifulSoup object and specify the parser
    soup = BeautifulSoup(content, 'html.parser')

    # Find the data you want to scrape: for instance, let's assume you're looking for text within paragraph 'p' tags
    paragraphs = soup.find_all('p')

    # Open the text file in write mode
    with open('output.txt', 'w') as f:
        # Loop through the paragraphs
        for paragraph in paragraphs:
            # Write the text of the paragraph to the file
            # Note: paragraph.text returns the text inside the paragraph tags
            f.write(paragraph.text + '\n')