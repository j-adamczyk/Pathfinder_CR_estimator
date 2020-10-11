# Pathfinder CR estimator

## Introduction
Pathfinder is a very popular and my personal favorite pen&paper RPG (Role-Playing Game). Frequent task and challenge for Game Masters (game designers and narrators) is monster creation, especially estimating monster power relative to level of players.

In this project I want to:
1. Create the dataset - use web scraper to gather monster statistics from [available site](https://www.d20pfsrd.com/) and parse it, making an easily usable .csv file.
2. Exploratory Data Analysis (EDA) - find answers e. g. to the following questions:
  - Are monster levels equally distributed?
  - Which monsters are outliers for their power levels? Which are too weak / too powerful?
  - Which statistics are correlated and how strong? How many can be automatically inferred for given levels?
3. CR estimator - create end-to-end platform, using machine learning models to help Game Masters estimate the power (Challenge Rating, CR) of their newly created monsters.

## Dataset creation

### Technology stack
- Python
- BeautifulSoup
- regexes, `re` module
- pytest
- Pandas (planned)
- SQLAlchemy (planned)
- SQLite (planned)

### Goals
1. Parse Pathfinder monsters pages and create a tabular dataset from their statistics.
2. Create dataset files in CSV and SQLite database formats.
3. Organize data in a way that makes it easy to use in data science and ML tasks: fast and easy data manipulation with SQL, regression/classification based on selected target feature, new monsters generation (statistics and/or description).

### Methodology
1. I found the page listing all individual monster pages ([link](https://www.d20pfsrd.com/bestiary/bestiary-hub/monsters-by-cr/)).
2. I parsed the raw HTML, getting all of the links (it's easier than with plaintext because of the explicit syntax like `<href...`).
3. I created a single monster page scraper and parser ([link](https://github.com/j-adamczyk/Pathfinder_CR_estimator/blob/master/web_scraper/src/monsters_scraper.py)), along with object-oriented monster representation ([link](https://github.com/j-adamczyk/Pathfinder_CR_estimator/blob/master/web_scraper/src/model.py)).
4. I wrote tests to check my code ([link](https://github.com/j-adamczyk/Pathfinder_CR_estimator/tree/master/web_scraper/tests)) and fixed all of the bugs that I've found.

### Results
TODO

## Project progress and status
1. Dataset creation - in progress
2. EDA - TODO
3. Machine learning model - TODO
4. Deployment - TODO
