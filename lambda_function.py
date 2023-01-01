import fitbit
import datetime
import requests
import ast
import os
import boto3

# AWS Setting
S3_BUKET_NAME = 'footsteps-token'
TOKEN_OBJECT_KEY_NAME = 'token'

# Fitbit Setting
FITBIT_API_CLIENT_ID = os.environ['FITBIT_API_CLIENT_ID']
FITBIT_API_CLIENT_SECRET = os.environ['FITBIT_API_CLIENT_SECRET']

# Pixela Setting
PIXELA_USER_TOKEN = os.environ['PIXELA_USER_TOKEN']
PIXELA_URL = os.environ['PIXELA_URL']
PIXELA_503_RETRY_COUNT = 10

token_tmp_file_name = '/tmp/token_tmp.txt'

s3 = boto3.resource('s3')
bucket = s3.Bucket(S3_BUKET_NAME)

def lambda_handler(event, context):
    print(datetime.datetime.today())
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    steps_list = get_steps_list(yesterday, today)

    for steps_dict in steps_list:
        plot_pixela(steps_dict)
    
def get_steps_list(from_date: datetime, to_date: datetime):
    authd_client = fitbit.Fitbit(FITBIT_API_CLIENT_ID, FITBIT_API_CLIENT_SECRET,
                                 access_token = load_fitbit_token('access_token'), 
                                 refresh_token = load_fitbit_token('refresh_token'),
                                 refresh_cb = replace_fitbit_token)
    activities_dict = authd_client.time_series('activities/steps',
                                               base_date = from_date,
                                               end_date  = to_date)
    return activities_dict['activities-steps']

def load_fitbit_token(key: str):
    bucket.download_file(TOKEN_OBJECT_KEY_NAME, token_tmp_file_name)
    with open(token_tmp_file_name) as f:
        token_str = f.read()
        token_dict = ast.literal_eval(token_str)
        return token_dict[key]

def replace_fitbit_token(token: dict):
    print('replace token!')
    with open(token_tmp_file_name, 'w') as f:
        f.write(str(token))
    bucket.upload_file(token_tmp_file_name, TOKEN_OBJECT_KEY_NAME)

def plot_pixela(steps_dict: dict):
    date_str = steps_dict['dateTime']
    steps = steps_dict['value']

    headers = {'X-USER-TOKEN': PIXELA_USER_TOKEN}
    body = {
        'date': date_str.replace('-', ''),
        'quantity': steps
    }
    retries = 0
    while True:
        res = requests.post(PIXELA_URL, headers=headers, json=body)
        if res.status_code != 503:
            print(date_str + ': ' + steps + ' steps is plotted.')
            break
        elif retries >= PIXELA_503_RETRY_COUNT:
            raise Exception(date_str + ': ' + steps + ' retry count exceeded.')
        retries += 1
        print('503 encounted: retries = ' + str(retries))
