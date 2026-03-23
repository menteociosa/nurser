


message  = {    "to": "+46761968978",    "body": "Hello World!"}




import requests
import base64
import dotenv
import os
dotenv.load_dotenv()

def main():
    
    # This URL is used for sending messages
    my_uri = "https://api.bulksms.com/v1/messages"

    # Change these values to match your own account
    my_username = os.getenv("BULKSMS_USERNAME")
    my_password = os.getenv("BULKSMS_PASSWORD")

    # The details of the message we want to send
    my_data = {
        "to": [ "+46761968978"],
        "body": "Hello World!",
        "encoding": "UNICODE",
        "longMessageMaxParts": "30",
    }

    # Encode credentials to Base64
    credentials = f"{my_username}:{my_password}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')

    # Headers for the request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {encoded_credentials}"
    }

    # Make the POST request
    try:
        response = requests.post(
            my_uri,
            json=my_data,
            headers=headers
        )
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Print the response from the API
        print(response.text)
    except requests.exceptions.RequestException as ex:
        # Show the general message
        print("An error occurred: {}".format(ex))
        # Print the detail that comes with the error if available
        if ex.response is not None:
            print("Error details: {}".format(ex.response.text))

if __name__ == "__main__":
    main()
