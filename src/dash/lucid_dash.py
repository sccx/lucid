# -*- coding: utf-8 -*-

# Import libraries
import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objects as go


# Load data and functions
def saveliy_function(string_df):
    '''
    Bypasses error introduced by '\n' in the SQL database. 
    Courtesy of my colleague, Saveliy.
    Returns dataframe.
    '''
    try: 
        d = pd.Timestamp(string_df).strftime("%Y-%m-%d")
    except:
        d = ""
    return d


def clean_dataframe(df):
    '''
    Receives the input dataframe, removes null values, and formats dates/errors.
    Returns dataframe.
    '''
    df = (df.dropna(how='any', subset=['screen_name'])
            .dropna(how='any', subset=['bot_score']))
    df['date'] = df['date'].apply(saveliy_function)
    df = df[df['date'] > '2020-00-01']
    df['bot_score'] = pd.to_numeric(df['bot_score'], errors='coerce')
    df = df.dropna(how='any', subset=['bot_score'])
    df['date'] = pd.DatetimeIndex(df['date']) + pd.DateOffset(months=1)
    return df

def percent_bots(df, bot_threshold):
    '''
    Determines the percentage of bots active in the sample on a given day.
    Returns dataframe.
    '''
    date_groups = df.groupby('date')
    bots_per_day = df.groupby('date')['bot_score'].apply(lambda x: x[x >= bot_threshold].count())
    daily_bot_percent = (bots_per_day / date_groups['date'].count()) * 100
    return daily_bot_percent


def retweeted_bots(df, bot_threshold):
    '''
    Determines percentage of bot activity that comprises retweets.
    Returns dataframe.
    '''
    bot_df = clean_df.drop(clean_df[clean_df.bot_score < bot_threshold].index)
    bots_by_date = bot_df.groupby('date')
    retweet_count = bot_df.groupby('date')['retweet'].count().reset_index()
    bots_per_day = bots_by_date['tweet_id'].count().reset_index()
    bot_retweet_percent = (retweet_count['retweet'] / bots_per_day['tweet_id']) * 100
    return bot_retweet_percent


path_and_file = 'bot_accounts.csv' # File maintained locally, pushed from PostgreSQL database.
columns = ['tweet_id', 'screen_name', 'retweet', 'date', 'bot_score']
input_df = pd.read_csv(path_and_file, sep='\t', header=0, names=columns)
bot_threshold = 0.43

clean_df = clean_dataframe(input_df)
daily_bots = percent_bots(clean_df, bot_threshold).round(2)
pcnt_bot_rts = retweeted_bots(clean_df, bot_threshold).round(2)
graph_data = daily_bots.reset_index()
graph_data.rename(columns={0:'percent_bots'}, inplace=True)
graph_data['bot_retweet_pcnt'] = pcnt_bot_rts


# App layout
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']


# Begin Dash app
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# Define Layout
fig = go.Figure()

fig.add_trace(
        go.Line(x=graph_data['date'], 
                y=graph_data['bot_retweet_pcnt'],
                name='Retweets (%)')
        )

fig.add_trace(
        go.Bar(x=graph_data['date'], 
               y=graph_data["percent_bots"],
               name='Bots (%)')
        )


fig.update_xaxes(rangeslider_visible=True)


app.layout = html.Div(children=[
    html.H1(children='Tracking Bots Tweeting about Covid-19', style={'text-align':'center'}),

    dcc.Graph(style={'height': '600px'},
        id='Bots Retweeting COVID-19 Content',
        figure=fig
    )
])

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=80)



