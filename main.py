import json
import requests
import base64
import os
from google.cloud import storage


# auto-retrieve project id
project_id = os.environ.get('GCP_PROJECT')

# setup storage client, bucket and object
storage_client = storage_client = storage.Client()
bucket_name = 'prisma-host-defender'
bucket = storage_client.bucket(bucket_name)
gcs_object_pcc_token = 'pcc_api_token.txt'

# add the address of your console
console_address = 'https://us-west1.cloud.twistlock.com/us-3-159237196/api/v1/authenticate/renew' 


def refresh_token(event, context):
    """
    helper function to refresh defender token and store in secrets manager
    runs on a cron job (Cloud Scheduler) which triggers via pub/sub
    """
    # get current token from gcs object
    current_token = get_file_content(gcs_object_pcc_token)
    print("DEBUG: ", current_token)  # remove
    # format request to prisma
    bearer = 'Bearer ' + str(current_token)
    headers = {'authorization': bearer}
    # call prisma api to refresh token and receive its new value
    refresh_token_result = requests.get(console_address, headers=headers, verify=False)
    print("RESPONSE: ", refresh_token_result)
    assert refresh_token_result.status_code == 200
    content = json.loads(refresh_token_result.content)
    print("DEBUG: ", content)  # remove
    new_token = content.get('token')

    # test that we really have new token
    assert current_token != new_token

    # update storage object with new token value
    update_file_content(gcs_object_pcc_token, new_token)
    print('DONE')    


# get file from cloud storage
def get_file_content(name):
    print('fetching file content...')
    source_blob_name = name # bucket object
    destination_file_name = "/tmp/" + name # local file - save to /tmp/ on runtime container
    blob = bucket.blob(source_blob_name) # prepare the object for file download
    blob.download_to_filename(destination_file_name) # save object as local file

    contents = None
    with open(destination_file_name, 'r') as f:
        contents = f.read()

    return contents

# overwrite file and upload to gcs
def update_file_content(name, data):
    print("updating contents...")
    local_file = '/tmp/' + name
    with open(local_file, 'w') as f:  # using w, not w+, so old token gets overwritten
        f.write(data)
    
    blob = bucket.blob(name)  # assign the object a filename for GCS
    try:
        blob.upload_from_filename(local_file)
    except Exception as e:
        print(e)

    

