import subprocess
import pandas
import hashlib
import sqlalchemy
import json
from datetime import datetime

# create class for handling sqs queue interaction
class SqsHandler:
    def __init__(self, url):
        self.url = url

    # get next set of messages in sqs queue
    def next_batch(self):
        # get sqs response with up to 10 messages
        response = subprocess.check_output(f'awslocal sqs receive-message --queue-url {self.url} --max-number-of-messages 10', shell=True)
        if not response: return []
        # return messages as dataframe
        return pandas.json_normalize(json.loads(response), "Messages")

    # delete messages from sqs queue
    def delete_batch(self, df):
        if not len(df): return []
        # create 'Id' column to send in delete message batch entries
        df['Id'] = df['MessageId']
        # build entries variable
        entries = df[['Id', 'ReceiptHandle']].to_json(orient='records')
        # send delete message request for up to 10 messages
        response = subprocess.check_output(f"awslocal sqs delete-message-batch --queue-url {self.url} --entries '{entries}'", shell=True)
        return json.loads(response)

# function to hash PII strings
def sha256(string):
    m = hashlib.sha256()
    m.update(bytes(string, 'utf-8'))
    return m.hexdigest()

# get major version from app_version string
def app_major_version(version):
    return version.split('.')[0]

def main():
    # track invalid user login messages in list
    invalid_messages = []

    # setup sqs handler and postgres db engine
    print('setting up...')
    sqs_handler = SqsHandler('http://localhost:4566/000000000000/login-queue')
    engine = sqlalchemy.create_engine('postgresql://postgres:postgres@localhost:5432/postgres')

    print('starting...')
    # loop through messages until queue is empty
    while True:
        # get dataframe with new messages from sqs queue
        messages_df = sqs_handler.next_batch()
        # if queue is empty stop
        if not len(messages_df): break

        # extract fields from message 'Body' and add them to to messages_df
        messages_df['Body'] = messages_df['Body'].apply(json.loads)
        body_df = pandas.json_normalize(messages_df['Body'])
        messages_df = messages_df.join(body_df[[ 'user_id', 'device_type', 'ip', 'device_id', 'locale', 'app_version' ]])
        del body_df

        # check for rows missing 'user_id' and delete the message from the sqs queue, add it to invalid_messages list and drop from messages_df
        invalid_rows = messages_df.loc[messages_df['user_id'].isna(), ['MessageId', 'ReceiptHandle', 'Body']]
        if len(invalid_rows):
            delete_response = sqs_handler.delete_batch(invalid_rows)
            invalid_messages = invalid_messages + json.loads(invalid_rows.to_json(orient='records'))
            messages_df.drop(invalid_rows.index, inplace=True)
        
        # add fields necessary for db insert
        messages_df['create_date'] = datetime.today().strftime('%Y-%m-%d')
        messages_df['masked_ip'] = messages_df['ip'].apply(sha256)
        messages_df['masked_device_id'] = messages_df['device_id'].apply(sha256)
        messages_df['app_version'] = messages_df['app_version'].apply(app_major_version)

        # insert rows into postgress db and delete from sqs queue
        insert_columns = ['user_id', 'device_type', 'masked_ip', 'masked_device_id', 'locale', 'app_version', 'create_date']
        insert_count = messages_df[insert_columns].to_sql('user_logins', engine, if_exists='append', index=False)
        delete_response = sqs_handler.delete_batch(messages_df)
        print(f'{insert_count} records saved to db and {len(delete_response["Successful"])} messages removed from sqs queue')
        
    print('done')
    print(f'{len(invalid_messages)} bad user login event messages found: ', json.dumps(invalid_messages))

# run application
main()