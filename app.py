import streamlit as st
import os
import re
import requests
import base64
from base64 import b64encode
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from io import StringIO
from twilio.rest import Client

load_dotenv()
st.title('311+🫶')
image = Image.open('bridge.jpeg')
st.image(image, caption='Golden Gate Bridge')
# need OpenAI API Key in .env
# Set the API endpoint and your API key
url = "https://api.openai.com/v1/completions"

api_key = st.secrets['OPENAI_API_KEY'] #os.environ.get('OPENAI_API_KEY')

problem_input = st.text_input('What is the problem, please') 
uploaded_file = st.file_uploader("Upload An Image",type=['png','jpeg','jpg'])
location = st.text_input("What is the location of the problem?")
user_num = st.text_input("Enter your phone #, please")
if st.button('Enter'):
    if uploaded_file is not None:
        file_details = {"FileName":uploaded_file.name,"FileType":uploaded_file.type}
        img_det = "Got the image!"
        st.write(img_det)
        st.write(file_details)
        encoded_file = base64.encodebytes(uploaded_file.read())
        output_temporary_file = b64encode(encoded_file).decode('utf-8')
        print(output_temporary_file)

        # Set the request headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        # Set the request data
        data = { 
            "model": "text-davinci-003",
            "prompt": f"Score the urgency of the user's request {problem_input}. Return a score between 0 and 1 where 0 is low urgency and 1 is high urgency. Graffiti is not very urgent, public safety is more important, as is cars blocking people.",
            "max_tokens": 2400,
            "temperature": 0.1,
        }
        data2 = { 
            "model": "text-davinci-003",
            "prompt": f"Which San Francisco city department could help with the user's request: {problem_input}",
            "max_tokens": 2400,
            "temperature": 0.1,
        } 

        # Send the request and store the response
        urgency = requests.post(url, headers=headers, json=data)
        department = requests.post(url, headers=headers, json=data2)
        # Parse the response
        response_data = urgency.json()
        urgency_num = response_data['choices'][0]['text']
        print(urgency_num)
        dept_data = department.json()
        dept = dept_data['choices'][0]['text']
        #account_sid = os.environ['TWILIO_ACCOUNT_SID']
        account_sid = st.secrets['TWILIO_ACCOUNT_SID']
        auth_token = st.secrets['TWILIO_AUTH_TOKEN']
        client = Client(account_sid, auth_token)
        client.messages.create(
            to=user_num,
            from_="8553021845",
            body="Got your chat message. Someone from the City will reach out soon."
        ) 
        #hit 
        requests.post('https://trigger.brox.dev/?api_key=Rcy0rczwEnxogAakhnFQ&account_id=ufoAcA4gXLcwK6GXESd8&source=chat311&event=user-submission', json={"phone_number": user_num, "location": location, "department": dept, "why": problem_input, "score": urgency_num, "image": output_temporary_file })