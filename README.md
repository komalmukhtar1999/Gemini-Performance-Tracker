# Gemini Sales Insights

A backend system that uses **Google Gemini** to analyze sales data and provide insights on both individual sales representatives and overall team performance.


## Table of Contents

- [Installation](#installation)
- [Setting Up Gemini API](#setting-up-gemini-api)
- [Running the Application](#running-the-application)
- [Testing the API with Postman](#testing-the-api-with-postman)
  - [API Endpoints](#api-endpoints)
- [Using the Client](#using-the-client)
- [Tech Stack & Tools Used](#tech-stack--tools-used)
- [Contributors](#contributors)


## Installation

To install the required packages, run:

```bash
pip install -r requirements.txt
```
## Create a Google Gemini  free API Key:
Log in to Google AI Studio.
Click “Get API Key”
Copy the API key paste it in app.py in place of 
GEMINI_API_KEY = "your_gemini_api_key_here"
## Run the Project
```bash
python app.py
```
## Testing the API with Postman
## API Endpoints
### 1. Rep Performance
 http://localhost:8000/api/rep_performance?rep_id=183
 Replace rep_id with an employee ID from the dataset.
 Returns individual sales rep record + Gemini analysis.

## 2. Team Performance
 http://localhost:8000/api/team_performance
 Returns overall team summary + insights.
## 3. Performance Trends
 http://localhost:8000/api/performance_trends?time_period=monthly
 check trend monthly or weekly by changing time_period parameter
 Returns sales trends + forecast.

## Using the Client
 You can also test the system directly from the terminal:
 python client.py rep 183
 python client.py team
 python client.py trends --time-period monthly

## Tech Stack & Tools Used
 Programming Language: Python
 Framework: Flask
 LLM: Google Gemini (gemini-pro) via free API
 IDE: Visual Studio Code
 API Testing Tool: Postman

## Contributors
 Komal Mukhtar