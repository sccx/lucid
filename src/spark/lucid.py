

'''
Pyspark application to ingest, clean, and transfer data on Tweet IDs that contained reference to COVID-19.
Data acquired from Harvard Dataverse.

Methodology follows Pew Research Center's use of the Botometer API for analyzing Twitter accounts.
https://www.pewresearch.org/internet/2018/04/09/bots-in-the-twittersphere-methodology/
Botometer assigns scores to accounts on a scale of 0 to 1. The Pew Research Center used a score
of 0.43 or higher to declare an account likely automated, and that same standard is applied here.
'''

from twitter_credentials import consumer_key, consumer_secret, access_token, access_token_secret, rapidapi_key
import tweepy
import botometer
from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream
from pyspark import *
from pyspark import SparkConf, SparkContext
from pyspark.sql.types import StringType, json, _merge_type, FloatType
from pyspark.sql import Row, SparkSession
import pyspark.sql.functions
from pyspark.sql.functions import col, regexp_extract, udf
from pyspark.sql import functions as F
from time import sleep
from datetime import datetime


spark = SparkSession \
         .builder \
         .appName("test6")\
         .getOrCreate()
spark.conf.set("spark.executor.memory", "6G")
spark.conf.set("spark.sql.shuffle.partitions", 100)
spark.conf.set("spark.jars", "org.postgresql_postgresql-42.2.14.jar")
sc = spark.sparkContext

'''
Account credentials must be in file in the same folder as this application.
Future versions will utilize os.environ to set the environment for the application.
'''


@udf(returnType=StringType())
def fetch_account(tweet_id):
        try:
                from twitter_credentials import consumer_key, consumer_secret, access_token, access_token_secret
                auth = OAuthHandler(consumer_key, consumer_secret)
                auth.set_access_token(access_token, access_token_secret)
                api = tweepy.API(auth)
                status = api.get_status(tweet_id, text_mode='extended')
                json_str = json.dumps(status._json)
                parsed = json.loads(json_str)
                if parsed['lang'] == 'en':
                        return status
                else:
                        pass
        except tweepy.TweepError as e:
                return e.response


@udf(returnType=StringType())
def validate_account(screen_name):
        try:
                from twitter_credentials import consumer_key, consumer_secret, access_token, access_token_secret, rapidapi_key
                twitter_app_auth = {'consumer_key': consumer_key,'consumer_secret': consumer_secret, \
                                'access_token': access_token,'access_token_secret': access_token_secret}
                bmeter = botometer.Botometer(wait_on_ratelimit=True, rapidapi_key=rapidapi_key, **twitter_app_auth)
                user = bmeter.check_account(screen_name)
                return user['scores']
        except (botometer.NoTimelineError, tweepy.TweepError) as e:
                pass

path = "s3a://sccx-tweet-bucket-01/coronavirus-through-09-june/coronavirus-through-09-June-2020-11.txt"

screen_name_regex = ("(user.*)(\sscreen_name\=)([a-zA-Z0-9]{0,}|[a-zA-Z0-9\-\_])")
retweet_regex = ("(text=)(RT)")
tweet_regex = ("(text=.*)(\,|\.|\s)(id=)")
error_regex = ("(\{elapsed\=Timedelta)")
date_regex = ("(\[id\=\"Etc\/UTC\")(.*)(DST_OFFSET\=\?\])")
score_regex = ("(\{english=)(\d{1,2}\.\d{1,5})")

tweet_year_regex = ("(YEAR=)([\d]{4})")
tweet_month_regex = ("(MONTH=)([\d]{1,2})")
tweet_day_regex = ("(DAY_OF_MONTH=)([\d]{1,2})")
tweet_hour_regex = ("(HOUR_OF_DAY=)([\d]{1,2})")
tweet_minute_regex = ("(MINUTE=)([\d]{1,2})")
tweet_second_regex = ("(SECOND=)([\d]{1,2})")


tweet_id_df = spark.read.text(path) # Start with 10m tweet IDs
tweet_id_df = tweet_id_df.withColumnRenamed('value', 'tweet_id')
tweet_id_df = tweet_id_df.persist(pyspark.StorageLevel.MEMORY_AND_DISK)
tweet_id_df_sample = tweet_id_df.sample(False, 0.00001) # Sample 100 tweet IDs


df_parse_tweet = tweet_id_df_sample.withColumn('full_tweet', fetch_account(tweet_id_df_sample.tweet_id))
df_parse_tweet = df_parse_tweet.dropna()
df_parse_tweet = df_parse_tweet.filter(~ df_parse_tweet['full_tweet'].rlike(error_regex))


df_format_account = df_parse_tweet.withColumn('screen_name', regexp_extract(col('full_tweet'), screen_name_regex, 3)). \
        withColumn('retweet', regexp_extract(col('full_tweet'), retweet_regex, 2)). \
        withColumn('date_posted', regexp_extract(col('full_tweet'), date_regex, 2))

'''
Month format is offset by -1 month
'''
df_format_date_columns1 = df_format_account.withColumn('year', regexp_extract(col('date_posted'), tweet_year_regex, 2)). \
        withColumn('month', regexp_extract(col('date_posted'), tweet_month_regex, 2)). \
        withColumn('day', regexp_extract(col('date_posted'), tweet_day_regex, 2)). \
        withColumn('hour', regexp_extract(col('date_posted'), tweet_hour_regex, 2)). \
        withColumn('minute', regexp_extract(col('date_posted'), tweet_minute_regex, 2)). \
        withColumn('second', regexp_extract(col('date_posted'), tweet_second_regex, 2))

df_drop_tweet = df_format_date_columns1.drop('full_tweet')

# In future version, move df formatting into  dedicated function.
df_format_date_columns2 = (df_drop_tweet.withColumn('month', F.when(F.length(F.col('month')) == 1, F.concat(F.lit('0'), F.col('month'))).otherwise(F.col('month')))
    .withColumn('day', F.when(F.length(F.col('day')) == 1, F.concat(F.lit('0'), F.col('day'))).otherwise(F.col('day')))
    .withColumn('hour', F.when(F.length(F.col('hour')) == 1, F.concat(F.lit('0'), F.col('hour'))).otherwise(F.col('hour')))
    .withColumn('minute', F.when(F.length(F.col('minute')) == 1, F.concat(F.lit('0'), F.col('minute'))).otherwise(F.col('minute')))
    .withColumn('second', F.when(F.length(F.col('second')) == 1, F.concat(F.lit('0'), F.col('second'))).otherwise(F.col('second')))
    )

df_format_date_columns3 = df_format_date_columns2.withColumn('time_posted', F.concat(F.col('year'), F.col('month'), F.col('day'), \
        F.col('hour'), F.col('minute'), F.col('second')))

df_format_date_columns4 = df_format_date_columns3.withColumn('date', F.to_timestamp(col('time_posted'), format='yyyyMMddHHmmss'))
df_format_date_columns4 = df_format_date_columns4.drop('date_posted','year','month','day','hour','minute','second','time_posted')


# Retreive the bot score
df_get_botscore = df_format_date_columns4.withColumn('botometer_score', validate_account(df_format_date_columns4.screen_name))
df_get_botscore = df_get_botscore.withColumn('score', regexp_extract(col('botometer_score'), score_regex, 2))
df_get_botscore = df_get_botscore.withColumn('score', col('score').cast('float'))
df_final = df_get_botscore.drop('account', 'botometer_score')


# Fill with database values.
POSTGRESQL_URL = '',
#POSTGRES_PORT = ''
POSTGRESQL_USER = '',
POSTGRESQL_PASSWORD = '',
#POSTGRES_DBNAME = ''
POSTGRESQL_TABLE = 'tweets'

save_dataframe = (
        df_final.write.format("jdbc") \
    .option("url", 'jdbc:postgresql://10.0.0.9:5432/tweets') \
    .option("driver", "org.postgresql.Driver") \
    .option("dbtable", 'public.tweets') \
    .option("user", 'postgres') \
    .option("password", 'simple123') \
    .mode("append")
    )
    # .option("truncate", "true") \

save_dataframe.save()


print(datetime.now().time())
print("End of script.")

spark.stop()



