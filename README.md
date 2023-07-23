# Fetch Data Takehome Test
## Requirements
- docker
- docker-compose
- postgres
- python3

## Run app (on Mac)
1. `cd` into application directory
2. `docker compose up -d`
3. `python3 -m venv .venv`
4. `source .venv/bin/activate`
5. `export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"` (specific for Mac with Postgres installed as application, not sure about other systems/configurations)
6. `pip install -r requirements.txt`
7. `python main.py` (may take a while to start after fresh venv build and requirements install)

*** note sometimes if main.py is run too soon after starting docker containers awslocal will exit with error status 255 ***

## Questions
1. How would you deploy this application in production?
    - Modify this to run as a service
    - Create a dockerhub build for it (preferably auto built after pushing commit to prod repo)
    - Add it to the docker-compose orchestration.
2. What other components would you want to add to make this production ready?
    - Continuous polling of SQS queue (or use lambda function to run application) and multi-threading
    - Use Kubernetes to add redundancy in case any one service goes down
    - Modularize the code
    - Use boto3 to interface with SQS queue rather than using 'subprocess' and shell commands (couldn't use boto3 because it required AWS credentials)
    - Better logging and monitoring tools
    - Error checking and retries for sqs queue, db
    - Enforce/validate data types and data formats (espcially for masked fields that you cannot verify later on)
    - Check for other missing fields that might be required (right now just checking 'user_id')
    - Confirmation of successful db insert
    - Handling of erred messages list (right now just prints at the end)
3. How can this application scale with a growing dataset?
    - Have multiple instances of this application running, batch writes to the database, use distributed database
4. How can PII be recovered later on?
    - I used a hash function to mask the data so the only way to recover the PII would be to have a secure lookup table somewhere. I did this because hash functions are less likely to have collisions and have a uniform output size that fits VARCHAR(256). I don't know enough about all the different encryption methods to know whether they are sufficient for guaranteeing uniqueness and they will vary in size depending on the data being encrypted.
5. What are the assumptions you made?
    - No duplicate messages from SQS queue
    - All data types are correct
    - Localstack and postgres are available and connections are always successful
    - If 'user_id' exists then all other fields also exist