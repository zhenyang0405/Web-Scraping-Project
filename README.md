# Automating WebScraping using Cloud Run

A demonstration on how to use Python to automate the process of getting the latest camera’s prices from [Moment](https://www.shopmoment.com/) website by using Cloud Run.

Cloud Run is a managed compute platform that enables you to run containers that are invocable via requests or events. Cloud Run is serverless.

## How it work

Every day at 9am Cloud Scheduler will send a HTTP POST request to Cloud Run, Cloud Run will start the automation by referencing the step in Dockerfile. The Dockerfile will create a docker container with:
1. Python 3.8 image
2. Manually install all the missing libraries
3. Install Chrome
4. Install Python dependencies
5. Copy local code to container image
6. Run the web server on container startup
7. Once the container has successfully been built, it will run the main.py file.

Main.py file will create a server using Python Flask. Cloud Run will start the process by POST to the main function.

The process will:
1. Access Google Spreadsheet
2. Create a chrome web driver
3. Go to moment website
4. Auto-scrolling with Selenium
5. Get the website HTML with BeautifulSoup
6. Extract the selected data
7. Save it in Google Spreadsheet
8. Get the formatted data from Google Spreadsheet
9. Send a message to Telegram using Telegram API and webhook

Once all the process had been successfully ended. Cloud Run will stop the container.


## Technologies Stack
1. Python
2. [Selenium](https://www.selenium.dev/)
3. [Flask](https://flask.palletsprojects.com/en/2.0.x/)
4. [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
5. [Requests](https://docs.python-requests.org/en/latest/)
6. Google Spreadsheet
7. Google [Cloud Run](https://cloud.google.com/run)
