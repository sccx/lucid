# Lucid
Analyzing Twitter Bots tweeting about COVID-19

## Table of Contents
* Introduction
* Data Set
* Data Pipeline
* Data Visualization
* Conclusion

## Introduction
In April 2020, following the outbreak of COVID-19 in the US, [Twitter made tweet data available](https://www.reuters.com/article/us-health-coronavirus-twitter-data/twitter-opens-up-data-for-researchers-to-study-covid-19-tweets-idUSKBN22B2Q1) to researchers interested in assessing the spread of the disease and the scale of misinformation surrounding it. [Early assessments](https://www.cbsnews.com/news/bots-account-for-nearly-half-of-twitter-accounts-spreading-coronavirus-misinformation-researchers-say/) indicated nearly half of tweets with content about the virus were from bots. This project reproduces some of this research and provides an architecture for further analysis at scale.

The objective of this project is to create a database of Twitter bot accounts that tweeted about COVID-19, preserving the account data for analysis in a Plotly Dash interface and providing insight into trends among bot actors. The project was executed as part of the Insight Data Engineering fellowship, over three weeks in the summer of 2020.

## Data Set
The data used for this project was retreived from the Harvard Dataverse, which mines tweets related to COVID-19 and saves the tweet ID for future analysis. From March 3, 2020, through June 3, approximately 1.4GB of text files were generated comprising nearly 240,000,000 19-digit tweet ID strings from around the world.  

![Tweet ID Example](/Images/Tweet_IDs.png)

Using the Tweepy API, the full tweet can be retreived from the ID (if it still exists) and from there it is possible to extrapolate additional information about the author.

![ID and Account Example](/Images/TweetID_and_Account.png)


## Data Pipeline

![](/Images/Pipeline_Architecture.png)

The ETL pipeline ingests the data from and AWS S3 Bucket into an Apache Spark cluster, where the Tweepy and Botometer API calls are made. Account data is fetched with Tweepy and the screen name is fed to Botometer, which analyzes the account and ranks it from 0 to 1 (1 being more bot-like). For the purposes of this project, only English-language accounts were analyzed. May tweets in the corpus had been deleted by the time of this analysis, as were some accounts. The data that remained was loaded into a PostgreSQL RDS with the following structure.

![RDS_Example](/Images/Bot_RDS.png)

## Data Visualization (Plotly Dash)

The Plotly Dash framework provides a number of visualization tools that are accesible with Python. To provide a simple demonstration of the results, bar charts are used to indicate the percentage of bots tweeting about COVID-19 on the date given, while an overlapping line graph shows the percentage of thier tweets that are retweets of other content. Two slider bars allow the user to zoom in and focus on specific days of the month, and the graphs are enabled with mouse-over support.

![Dash_Example1](/Images/Dash_01.png)

Note the slider bar limits, below.
![Dash_Example2](/Images/Dash_02.png)

Note the mouse-over, below.
![Dash_Example3](/Images/Dash_04.png)

## Conclusion

The project sampled thousands of tweets for each day, from the hundreds of millions available in the data. This was due to bottleneck limitations of the Tweepy and Botometer APIs, that increased runtime and capped the number of freely available calls. Still, the results found that on a given day some 20% of the tweets about COVID-19 came from bots, and upwards of 90% (or more) of these tweets were retweeted content. These results are consistent with others who conducted [similar studies](https://spectrum.ieee.org/tech-talk/telecom/internet/twitter-bots-are-spreading-massive-amounts-of-covid-19-misinformation) during the same period.
